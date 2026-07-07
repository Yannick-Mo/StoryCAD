# backend/app/agent/context.py
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.storycad.models import Act, Chapter, Scene, SceneContent, Character, CharacterRelation, Theme
from app.project.models import Project, ProjectConfig
from app.knowledge.rag import RAGEngine
from app.knowledge.skill_engine import SkillEngine


class ContextBuilder:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def build(self, mode: str, project_id: uuid.UUID, chapter_id: uuid.UUID) -> dict:
        ctx = {}

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
            ctx["adjacent_chapters"] = await self._adjacent_chapters_text(project_id, target_chapter.sort_order, target_chapter.act_id)
            ctx["position_desc"] = self._position_desc(target_chapter.sort_order)

        if mode in ("outline", "writing"):
            ctx["relations_summary"] = await self._relations_text(project_id)

        if mode == "writing":
            ctx["all_scenes_content"] = await self._scenes_content_text(chapter_id)

        ctx["active_skills"] = await self._get_active_skills(project_id)
        ctx["rag_context"] = await self._get_rag_context(ctx["genre"], mode)

        return ctx

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
        lines = []
        for c in chars:
            parts = [f"- {c.name}（{c.role or '未指定角色'}）"]
            if c.personality:
                parts.append(f"  性格：{c.personality}")
            if c.motivation:
                parts.append(f"  动机：{c.motivation}")
            if c.background:
                parts.append(f"  背景：{c.background}")
            lines.append("\n".join(parts))
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

    def _position_desc(self, sort_order: int) -> str:
        if sort_order <= 1:
            return "故事开篇章节"
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

    async def _scenes_content_text(self, chapter_id: uuid.UUID) -> str:
        r = await self.db.execute(
            select(Scene).where(Scene.chapter_id == chapter_id).order_by(Scene.sort_order)
        )
        scenes = r.scalars().all()
        if not scenes:
            return "暂无场景"

        parts = []
        for sc in scenes:
            content = ""
            cr = await self.db.execute(select(SceneContent).where(SceneContent.scene_id == sc.id))
            sc_content = cr.scalar_one_or_none()
            if sc_content and sc_content.content:
                content = sc_content.content[:2000]

            parts.append(
                f"【{sc.title}】\n"
                f"POV: {sc.pov_character or '未指定'} | 地点: {sc.setting or '未指定'} | 时间: {sc.scene_time or '未指定'}\n"
                f"梗概: {sc.summary or '无'}\n"
                f"正文: {content or '（尚未写作）'}"
            )
        return "\n\n".join(parts)

    async def _get_active_skills(self, project_id: uuid.UUID) -> list:
        engine = SkillEngine(self.db)
        return await engine.get_active_skills(project_id)

    async def _get_rag_context(self, genre: str, mode: str) -> str:
        engine = RAGEngine(self.db)
        if mode == "goal":
            query = f"{genre} 故事目标设定技巧"
        elif mode == "writing":
            query = f"{genre} 写作技巧 场景描写"
        else:
            query = f"{genre} 写作技巧"
        return await engine.retrieve_context(project_id=None, genre=genre, query=query)
