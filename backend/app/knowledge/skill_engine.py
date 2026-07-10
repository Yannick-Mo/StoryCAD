import asyncio
import time
import uuid
from collections import OrderedDict
from pathlib import Path
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles
import yaml


_SKILLS_DIR = Path(__file__).parent / "skills"
_SKILL_CACHE_TTL = 300
_SKILL_CACHE_MAX = 50


class SkillEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._skills_cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()

    async def _load_yaml(self, name: str) -> dict | None:
        now = time.monotonic()
        if name in self._skills_cache:
            ts, data = self._skills_cache[name]
            if now - ts < _SKILL_CACHE_TTL:
                self._skills_cache.move_to_end(name)
                return data
        path = _SKILLS_DIR / f"{name}.yaml"
        if not path.exists():
            return None
        async with aiofiles.open(path, 'r', encoding='utf-8') as f:
            content = await f.read()
        data = await asyncio.to_thread(yaml.safe_load, content)
        self._skills_cache[name] = (now, data)
        self._skills_cache.move_to_end(name)
        while len(self._skills_cache) > _SKILL_CACHE_MAX:
            self._skills_cache.popitem(last=False)
        return data

    async def get_active_skills(self, project_id: uuid.UUID) -> list[dict]:
        sql = text("""
            SELECT sd.name, sd.genre, sd.config, ps.config_override, ps.sort_order
            FROM project_skills ps
            JOIN skill_definitions sd ON ps.skill_name = sd.name
            WHERE ps.project_id = :project_id AND sd.is_active = true
            ORDER BY ps.sort_order
        """)
        result = await self.db.execute(sql, {"project_id": project_id})
        rows = result.fetchall()
        skills = []
        for r in rows:
            config = dict(r[2] or {})
            override = dict(r[3] or {})
            config.update(override)
            skills.append({
                "name": r[0],
                "genre": r[1],
                "config": config,
                "sort_order": r[4],
            })
        return skills

    async def get_skill(self, skill_name: str) -> dict | None:
        return await self._load_yaml(skill_name)

    async def get_merged_prompts(
        self, project_id: uuid.UUID
    ) -> dict[str, str]:
        active = await self.get_active_skills(project_id)
        merged: dict[str, str] = {}
        for skill in active:
            yaml_data = await self._load_yaml(skill["name"])
            if yaml_data is None:
                continue
            overrides = yaml_data.get("prompt_overrides", {}) or {}
            config_overrides = skill.get("config", {}).get("prompt_overrides", {}) or {}
            combined = dict(overrides)
            combined.update(config_overrides)
            merged.update(combined)
        return merged

    async def get_merged_tags(self, project_id: uuid.UUID) -> list[str]:
        active = await self.get_active_skills(project_id)
        tags: set[str] = set()
        for skill in active:
            yaml_data = await self._load_yaml(skill["name"])
            if yaml_data is None:
                continue
            skill_tags = yaml_data.get("rag_tags", []) or []
            tags.update(skill_tags)
        return sorted(tags)

    async def get_merged_tools(self, project_id: uuid.UUID) -> list[str]:
        active = await self.get_active_skills(project_id)
        tools: set[str] = set()
        for skill in active:
            yaml_data = await self._load_yaml(skill["name"])
            if yaml_data is None:
                continue
            skill_tools = yaml_data.get("tools_enabled", []) or []
            tools.update(skill_tools)
        return sorted(tools)

    def list_all_skills(self) -> list[str]:
        if not _SKILLS_DIR.exists():
            return []
        return sorted(
            p.stem for p in _SKILLS_DIR.glob("*.yaml") if p.stem != "__init__"
        )
