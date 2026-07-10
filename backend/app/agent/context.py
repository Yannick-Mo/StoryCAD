from __future__ import annotations

import json
import logging
import time
import uuid
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)


class _UUIDEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, uuid.UUID):
            return str(o)
        return super().default(o)

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.rag import RAGEngine
from app.knowledge.skill_engine import SkillEngine
from app.project.models import Project, ProjectConfig
from app.storycad.models import (
    Act,
    Chapter,
    ChapterEdge,
    Character,
    CharacterRelation,
    Scene,
    SceneContent,
    Theme,
)
from app.utils import row_to_dict

_CONTEXT_CACHE_TTL = 300
_CONTEXT_CACHE_MAX_SIZE = 100
_REDIS_CACHE_PREFIX = "ctx_cache:"


class _LRUCache:
    """In-memory LRU fallback cache used when Redis is unavailable."""

    def __init__(self, ttl: int, maxsize: int):
        self._ttl = ttl
        self._maxsize = maxsize
        self._store: OrderedDict[str, tuple[float, dict]] = OrderedDict()

    def get(self, key: str) -> dict | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, data = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return data

    def set(self, key: str, data: dict) -> None:
        self._store[key] = (time.monotonic(), data)
        self._store.move_to_end(key)
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)


_CONTEXT_CACHE = _LRUCache(ttl=_CONTEXT_CACHE_TTL, maxsize=_CONTEXT_CACHE_MAX_SIZE)


def _is_meaningful_query(query_hint: str) -> bool:
    if len(query_hint) < 10:
        return False
    stripped = query_hint.strip().lower()
    greetings = {"hi", "hello", "hey", "你好", "您好", "嗨", "哈喽", "nihao", "hi there", "hello there"}
    if stripped in greetings or stripped.rstrip("?!。，,.") in greetings:
        return False
    short_patterns = {"嗯", "是", "好", "ok", "yes", "no", "y", "n", "哦", "嗯嗯", "好的", "是的"}
    if stripped in short_patterns:
        return False
    return True


class ContextBuilder:
    def __init__(self, db: AsyncSession, redis_client: Redis | None = None):
        self.db = db
        self._redis = redis_client
        self._skill_engine: SkillEngine | None = None
        self._rag_engine: RAGEngine | None = None

    @property
    def skill_engine(self) -> SkillEngine:
        if self._skill_engine is None:
            self._skill_engine = SkillEngine(self.db)
        return self._skill_engine

    @property
    def rag_engine(self) -> RAGEngine:
        if self._rag_engine is None:
            self._rag_engine = RAGEngine(self.db)
        return self._rag_engine

    # ------------------------------------------------------------------
    # Cache  — Redis primary, in-memory _LRUCache as fallback
    # ------------------------------------------------------------------

    def _cache_key(self, project_id: uuid.UUID, kind: str, depth: str = "") -> str:
        return f"{_REDIS_CACHE_PREFIX}{project_id}:{kind}:{depth}"

    async def _cache_get(self, key: str) -> dict | None:
        if self._redis is not None:
            try:
                raw = await self._redis.get(key)
                if raw is not None:
                    data = raw.decode() if isinstance(raw, bytes) else raw
                    return json.loads(data)
            except Exception as exc:
                logger.warning("Redis cache get failed for key=%s: %s", key, exc)
            return _CONTEXT_CACHE.get(key)
        return _CONTEXT_CACHE.get(key)

    async def _cache_set(self, key: str, data: dict) -> None:
        if self._redis is not None:
            try:
                raw = json.dumps(data, ensure_ascii=False, cls=_UUIDEncoder)
                await self._redis.setex(key, _CONTEXT_CACHE_TTL, raw)
            except Exception as exc:
                logger.warning("Redis cache set failed for key=%s: %s", key, exc)
            _CONTEXT_CACHE.set(key, data)
        else:
            _CONTEXT_CACHE.set(key, data)

    # ------------------------------------------------------------------
    # Build (legacy mode-specific)
    # ------------------------------------------------------------------

    async def build(self, mode: str, project_id: uuid.UUID, chapter_id: uuid.UUID) -> dict:
        ctx: dict[str, Any] = {}

        proj = await self._get_project(project_id)
        target_chapter = await self._get_chapter(chapter_id)
        if not proj or not target_chapter:
            return ctx

        ctx["project_title"] = proj.title
        ctx["genre"] = proj.genre or "未指定"
        ctx["chapter_title"] = target_chapter.title
        ctx["chapter_goal"] = target_chapter.goal or "未设定"

        config = await self._get_config(project_id)
        ctx["total_words"] = config.total_words if config else 100000

        act = await self._get_act(target_chapter.act_id)
        ctx["act_name"] = act.name if act else "未命名幕"

        ctx["characters_summary"] = await self._characters_text(project_id)

        if mode in ("goal", "outline", "writing"):
            ctx["themes_summary"] = await self._themes_text(project_id)

        if mode == "goal":
            ctx["adjacent_chapters"] = await self._adjacent_chapters_text(
                project_id, target_chapter.sort_order, target_chapter.act_id
            )
            ctx["position_desc"] = self._position_desc(target_chapter.sort_order)

        if mode in ("outline", "writing"):
            ctx["relations_summary"] = await self._relations_text(project_id)

        ctx["active_skills"] = await self._get_active_skills(project_id)

        return ctx

    # ------------------------------------------------------------------
    # Shared project tree loader (used by both build_full and build_summary)
    # ------------------------------------------------------------------

    async def _load_project_tree(self, project_id: uuid.UUID) -> dict:
        acts_result = await self.db.execute(
            select(Act).where(Act.project_id == project_id).order_by(Act.sort_order)
        )
        acts = acts_result.scalars().all()

        chapters_result = await self.db.execute(
            select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.sort_order)
        )
        all_chapters = chapters_result.scalars().all()
        chapters_by_act: dict[uuid.UUID, list] = {}
        for ch in all_chapters:
            chapters_by_act.setdefault(ch.act_id, []).append(ch)

        chapter_ids = [ch.id for ch in all_chapters]
        scenes_result = await self.db.execute(
            select(Scene).where(Scene.chapter_id.in_(chapter_ids)).order_by(Scene.sort_order)
        )
        all_scenes = scenes_result.scalars().all()
        scenes_by_chapter: dict[uuid.UUID, list] = {}
        for sc in all_scenes:
            scenes_by_chapter.setdefault(sc.chapter_id, []).append(sc)

        return {
            "acts": acts,
            "all_chapters": all_chapters,
            "chapters_by_act": chapters_by_act,
            "all_scenes": all_scenes,
            "scenes_by_chapter": scenes_by_chapter,
            "chapter_ids": chapter_ids,
        }

    # ------------------------------------------------------------------
    # Build full
    # ------------------------------------------------------------------

    async def build_full(self, project_id: uuid.UUID, query_hint: str = "") -> dict:
        ck = self._cache_key(project_id, "full", "")
        cached = await self._cache_get(ck)
        if cached is not None:
            return cached

        proj = await self._get_project(project_id)
        if not proj:
            return {}

        config = await self._get_config(project_id)
        tree = await self._load_project_tree(project_id)
        acts = tree["acts"]
        all_chapters = tree["all_chapters"]
        chapters_by_act = tree["chapters_by_act"]
        all_scenes = tree["all_scenes"]
        scenes_by_chapter = tree["scenes_by_chapter"]
        chapter_ids = tree["chapter_ids"]

        scene_ids = [sc.id for sc in all_scenes]
        content_by_scene: dict[uuid.UUID, str] = {}
        if scene_ids:
            sc_content_result = await self.db.execute(
                select(SceneContent).where(SceneContent.scene_id.in_(scene_ids))
            )
            for sc in sc_content_result.scalars().all():
                if sc.content:
                    content_by_scene[sc.scene_id] = sc.content

        acts_data = []
        for act in acts:
            chapters_data = []
            for ch in chapters_by_act.get(act.id, []):
                scenes_data = []
                for sc in scenes_by_chapter.get(ch.id, []):
                    sc_d = row_to_dict(sc)
                    sc_d["content_preview"] = (content_by_scene.get(sc.id) or "")[:500]
                    scenes_data.append(sc_d)
                ch_d = row_to_dict(ch)
                ch_d["scenes"] = scenes_data
                chapters_data.append(ch_d)
            act_d = row_to_dict(act)
            act_d["chapters"] = chapters_data
            acts_data.append(act_d)

        chars_result = await self.db.execute(
            select(Character).where(Character.project_id == project_id).order_by(Character.sort_order)
        )
        characters_data = [row_to_dict(c) for c in chars_result.scalars().all()]

        rels_result = await self.db.execute(
            select(CharacterRelation).where(CharacterRelation.project_id == project_id)
        )
        relations_data = [row_to_dict(r) for r in rels_result.scalars().all()]

        themes_result = await self.db.execute(
            select(Theme).where(Theme.project_id == project_id).order_by(Theme.sort_order)
        )
        themes_data = [row_to_dict(t) for t in themes_result.scalars().all()]

        edges_result = await self.db.execute(
            select(ChapterEdge).where(ChapterEdge.project_id == project_id)
        )
        edges_data = [row_to_dict(e) for e in edges_result.scalars().all()]

        active_skills = await self.skill_engine.get_active_skills(project_id)
        merged_prompts = await self.skill_engine.get_merged_prompts(project_id)

        rag_context = await self._get_rag_context_if_meaningful(query_hint, proj.genre or "")

        result = {
            "project": row_to_dict(proj),
            "config": row_to_dict(config) if config else {},
            "acts": acts_data,
            "characters": characters_data,
            "relations": relations_data,
            "themes": themes_data,
            "edges": edges_data,
            "active_skills": [s["name"] for s in active_skills],
            "merged_prompts": merged_prompts,
            "rag_context": rag_context or "",
        }

        await self._cache_set(ck, result)
        return result

    # ------------------------------------------------------------------
    # Build summary (with depth parameter)
    # ------------------------------------------------------------------

    async def build_summary(
        self,
        project_id: uuid.UUID,
        query_hint: str = "",
        depth: str = "minimal",
    ) -> dict:
        ck = self._cache_key(project_id, "summary", depth)
        cached = await self._cache_get(ck)
        if cached is not None:
            return cached

        proj = await self._get_project(project_id)
        if not proj:
            return {}

        tree = await self._load_project_tree(project_id)
        acts = tree["acts"]
        all_chapters = tree["all_chapters"]
        chapters_by_act = tree["chapters_by_act"]
        all_scenes = tree["all_scenes"]
        scenes_by_chapter = tree["scenes_by_chapter"]
        chapter_ids = tree["chapter_ids"]

        scene_ids = [sc.id for sc in all_scenes]
        content_by_scene: dict[uuid.UUID, str] = {}
        if depth == "full" and scene_ids:
            sc_content_result = await self.db.execute(
                select(SceneContent).where(SceneContent.scene_id.in_(scene_ids))
            )
            for sc in sc_content_result.scalars().all():
                content_by_scene[sc.scene_id] = sc.content or ""

        acts_data = []
        for act in acts:
            chapters_data = []
            for ch in chapters_by_act.get(act.id, []):
                scenes_data = []
                for sc in scenes_by_chapter.get(ch.id, []):
                    entry: dict[str, Any] = {
                        "id": str(sc.id),
                        "title": sc.title,
                        "sort_order": sc.sort_order,
                        "summary": (sc.summary or "")[:200],
                        "pov_character": sc.pov_character or "",
                    }
                    if depth == "summary":
                        entry["setting"] = sc.setting or ""
                        entry["scene_time"] = sc.scene_time or ""
                    if depth == "full":
                        entry["content"] = (content_by_scene.get(sc.id) or "")[:1000]
                    scenes_data.append(entry)

                ch_entry: dict[str, Any] = {
                    "id": str(ch.id),
                    "title": ch.title,
                    "sort_order": ch.sort_order,
                    "goal_preview": (ch.goal or "")[:100],
                    "scenes": scenes_data,
                }
                if depth in ("summary", "full"):
                    ch_entry["status"] = ch.status or ""
                chapters_data.append(ch_entry)

            acts_data.append({
                "id": str(act.id),
                "name": act.name,
                "sort_order": act.sort_order,
                "chapters": chapters_data,
            })

        chars_result = await self.db.execute(
            select(Character).where(Character.project_id == project_id).order_by(Character.sort_order)
        )
        characters_data = []
        for c in chars_result.scalars().all():
            entry: dict[str, Any] = {
                "id": str(c.id),
                "name": c.name,
                "role": c.role or "",
            }
            if depth in ("summary", "full"):
                entry["personality"] = (c.personality or "")[:200]
            characters_data.append(entry)

        themes_result = await self.db.execute(
            select(Theme).where(Theme.project_id == project_id).order_by(Theme.sort_order)
        )
        themes_data = []
        for t in themes_result.scalars().all():
            themes_data.append({
                "name": t.name,
                "proposition": t.proposition or "",
            })

        active_skills = await self.skill_engine.get_active_skills(project_id)
        rag_context = await self._get_rag_context_if_meaningful(query_hint, proj.genre or "")

        scene_count = sum(len(scenes_by_chapter.get(cid, [])) for cid in chapter_ids)

        result = {
            "project": {
                "id": str(proj.id),
                "title": proj.title,
                "genre": proj.genre or "",
                "logline": getattr(proj, "logline", "") or "",
                "status": proj.status or "",
            },
            "acts": acts_data,
            "characters": characters_data,
            "themes": themes_data,
            "active_skills": [s["name"] for s in active_skills],
            "rag_context": rag_context or "",
            "chapter_count": len(all_chapters),
            "scene_count": scene_count,
        }

        await self._cache_set(ck, result)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_project(self, project_id: uuid.UUID):
        r = await self.db.execute(select(Project).where(Project.id == project_id))
        return r.scalar_one_or_none()

    async def _get_config(self, project_id: uuid.UUID):
        r = await self.db.execute(select(ProjectConfig).where(ProjectConfig.project_id == project_id))
        return r.scalar_one_or_none()

    async def _get_chapter(self, chapter_id: uuid.UUID):
        r = await self.db.execute(select(Chapter).where(Chapter.id == chapter_id))
        return r.scalar_one_or_none()

    async def _get_act(self, act_id: uuid.UUID | None):
        if not act_id:
            return None
        r = await self.db.execute(select(Act).where(Act.id == act_id))
        return r.scalar_one_or_none()

    async def _characters_text(self, project_id: uuid.UUID) -> str:
        r = await self.db.execute(
            select(Character).where(Character.project_id == project_id).order_by(Character.sort_order)
        )
        chars = r.scalars().all()
        if not chars:
            return "暂无角色"
        total_chars_limit = 4000
        total = 0
        lines = []
        for c in chars:
            parts = [f"- {c.name}（{c.role or '未指定角色'}）"]
            if c.personality:
                parts.append(f"  性格：{c.personality[:200]}")
            if c.motivation:
                parts.append(f"  动机：{c.motivation[:200]}")
            if c.background:
                parts.append(f"  背景：{c.background[:300]}")
            block = "\n".join(parts)
            total += len(block) + 1
            if total > total_chars_limit:
                lines.append(f"  ... 还有 {len(chars) - len(lines)} 个角色已省略")
                break
            lines.append(block)
        return "\n".join(lines)

    async def _themes_text(self, project_id: uuid.UUID) -> str:
        r = await self.db.execute(
            select(Theme).where(Theme.project_id == project_id).order_by(Theme.sort_order)
        )
        themes = r.scalars().all()
        if not themes:
            return "暂无主题"
        lines = []
        for t in themes:
            prop = f" — {t.proposition}" if t.proposition else ""
            lines.append(f"- {t.name}{prop}")
        return "\n".join(lines)

    async def _adjacent_chapters_text(self, project_id: uuid.UUID, sort_order: int, act_id: uuid.UUID | None) -> str:
        r = await self.db.execute(
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .order_by(Chapter.sort_order)
        )
        all_chapters = r.scalars().all()
        if len(all_chapters) <= 1:
            return "（只有一个章节，暂无相邻章节）"

        idx = next((i for i, ch in enumerate(all_chapters) if ch.sort_order == sort_order), 0)
        start = max(0, idx - 2)
        end = min(len(all_chapters), idx + 3)

        lines = []
        for i in range(start, end):
            ch = all_chapters[i]
            marker = " ← 当前章节" if ch.sort_order == sort_order else ""
            goal_preview = ""
            if ch.goal:
                goal_preview = f" | 目标：{ch.goal[:40]}..." if len(ch.goal) > 40 else f" | 目标：{ch.goal}"
            lines.append(f"{ch.sort_order}. {ch.title}{goal_preview}{marker}")
        return "\n".join(lines)

    def _position_desc(self, sort_order: int, total_chapters: int = 0) -> str:
        if sort_order <= 1:
            return "故事开篇章节"
        if total_chapters > 4 and sort_order >= total_chapters:
            return "故事结尾章节"
        return "故事中段章节"

    async def _relations_text(self, project_id: uuid.UUID) -> str:
        r = await self.db.execute(
            select(CharacterRelation).where(CharacterRelation.project_id == project_id)
        )
        rels = r.scalars().all()
        if not rels:
            return "暂无关系"
        char_map = {}
        cr = await self.db.execute(select(Character).where(Character.project_id == project_id))
        for c in cr.scalars().all():
            char_map[c.id] = c.name
        lines = []
        for rel in rels:
            src = char_map.get(rel.character_id, "?")
            tgt = char_map.get(rel.target_id, "?")
            trust = ""
            if rel.trust and rel.trust != 50:
                trust = f" (信任{rel.trust})"
            lines.append(f"- {src} → {rel.label or rel.rel_type or '关联'} → {tgt}{trust}")
        return "\n".join(lines)

    async def _get_active_skills(self, project_id: uuid.UUID) -> list:
        return await self.skill_engine.get_active_skills(project_id)

    async def _get_rag_context_if_meaningful(self, query_hint: str, genre: str) -> str:
        if not _is_meaningful_query(query_hint):
            return ""
        rag_query = query_hint[:200] if query_hint else f"{genre} 创作指南 写作技巧"
        try:
            return await self.rag_engine.retrieve_context(
                project_id=None,
                genre=genre or None,
                query=rag_query,
            )
        except Exception:
            logger.warning("RAG context retrieval failed, proceeding without it")
            return ""
