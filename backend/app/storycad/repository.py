import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.project.models import Project
from app.project.repository import ProjectRepository
from app.storycad.models import (
    Act, Chapter, Scene, SceneContent, ChapterEdge,
    Character, CharacterRelation,
    Theme, ThemeChapter,
)
from app.storycad.entity_map import ENTITY_MAP


class StoryCADRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # Editor data: full load
    # ============================================================

    async def get_editor_data(self, project_id: uuid.UUID) -> dict:
        result = {"project_id": str(project_id)}

        acts = await self.db.execute(
            select(Act).where(Act.project_id == project_id).order_by(Act.sort_order)
        )
        result["acts"] = [self._row(r) for r in acts.scalars().all()]

        chapters = await self.db.execute(
            select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.sort_order)
        )
        result["chapters"] = [self._row(r) for r in chapters.scalars().all()]

        scenes = await self.db.execute(
            select(Scene).where(Scene.project_id == project_id).order_by(Scene.sort_order)
        )
        result["scenes"] = [self._row(r) for r in scenes.scalars().all()]

        edges = await self.db.execute(
            select(ChapterEdge).where(ChapterEdge.project_id == project_id)
        )
        result["edges"] = [self._row(r) for r in edges.scalars().all()]

        characters = await self.db.execute(
            select(Character).where(Character.project_id == project_id).order_by(Character.sort_order)
        )
        result["characters"] = [self._row(r) for r in characters.scalars().all()]

        char_rels = await self.db.execute(
            select(CharacterRelation).where(CharacterRelation.project_id == project_id)
        )
        result["character_relations"] = [self._row(r) for r in char_rels.scalars().all()]

        themes = await self.db.execute(
            select(Theme).where(Theme.project_id == project_id).order_by(Theme.sort_order)
        )
        result["themes"] = [self._row(r) for r in themes.scalars().all()]

        theme_chs = await self.db.execute(
            select(ThemeChapter).where(ThemeChapter.project_id == project_id)
        )
        result["theme_chapters"] = [self._row(r) for r in theme_chs.scalars().all()]

        proj_result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        proj = proj_result.scalar_one_or_none()
        if proj:
            result["global_settings"] = proj.global_settings or ""

        return result

    # ============================================================
    # Editor data: incremental sync
    # ============================================================

    async def sync_editor_data(self, project_id: uuid.UUID, changes: dict) -> int:
        for entity_type in ["acts", "chapters", "scenes", "edges", "characters",
                            "character_relations", "themes", "theme_chapters",
                            "projects"]:
            ops = changes.get(entity_type, {})
            if not ops:
                continue
            for delete_id in ops.get("deleted", []):
                await self._delete_entity(entity_type, delete_id)
            for item in ops.get("created", []):
                item["project_id"] = project_id
                await self._create_entity(entity_type, item)
            for item in ops.get("updated", []):
                item["project_id"] = project_id
                await self._update_entity(entity_type, item)

        await self.db.flush()
        await self._recalc_chapter_counts(project_id)
        await self.db.commit()

        project_repo = ProjectRepository(self.db)
        pv = await project_repo.save_version(project_id, {"type": "editor_sync"})
        return pv.version

    async def _recalc_chapter_counts(self, project_id: uuid.UUID):
        counts = await self.db.execute(
            select(Scene.chapter_id, func.count(Scene.id), func.coalesce(func.sum(Scene.word_count), 0))
            .where(Scene.project_id == project_id)
            .group_by(Scene.chapter_id)
        )
        for row in counts.all():
            await self.db.execute(
                Chapter.__table__.update().where(Chapter.id == row[0])
                .values(scene_count=row[1], total_words=row[2])
            )
        chapters_without_scenes = await self.db.execute(
            select(Chapter.id).where(Chapter.project_id == project_id)
            .where(~Chapter.id.in_(select(Scene.chapter_id).where(Scene.project_id == project_id)))
        )
        for (cid,) in chapters_without_scenes.all():
            await self.db.execute(
                Chapter.__table__.update().where(Chapter.id == cid)
                .values(scene_count=0, total_words=0)
            )

    # ============================================================
    # Scene content (separate, lazy-loaded)
    # ============================================================

    async def get_scene_content(self, scene_id: uuid.UUID) -> str | None:
        result = await self.db.execute(
            select(SceneContent).where(SceneContent.scene_id == scene_id)
        )
        sc = result.scalar_one_or_none()
        return sc.content if sc else None

    async def save_scene_content(self, scene_id: uuid.UUID, project_id: uuid.UUID, content: str):
        result = await self.db.execute(
            select(SceneContent).where(SceneContent.scene_id == scene_id)
        )
        sc = result.scalar_one_or_none()
        if sc:
            sc.content = content
        else:
            self.db.add(SceneContent(scene_id=scene_id, project_id=project_id, content=content))
        await self.db.commit()

    # ============================================================
    # Per-entity CRUD
    # ============================================================

    async def list_entities(self, model_class: type, project_id: uuid.UUID, order_field: str = "sort_order") -> list[dict]:
        result = await self.db.execute(
            select(model_class).where(model_class.project_id == project_id).order_by(getattr(model_class, order_field))
        )
        return [self._row(r) for r in result.scalars().all()]

    async def get_entity(self, model_class: type, entity_id: uuid.UUID) -> dict | None:
        result = await self.db.execute(select(model_class).where(model_class.id == entity_id))
        row = result.scalar_one_or_none()
        return self._row(row) if row else None

    async def create_entity(self, model_class: type, data: dict, extra_attrs: dict | None = None) -> dict:
        for col in model_class.__table__.columns:
            if col.name in data and isinstance(data[col.name], str) and isinstance(col.type, UUID):
                data[col.name] = uuid.UUID(data[col.name])
        obj = model_class(**data)
        self.db.add(obj)
        await self.db.flush()
        if extra_attrs:
            for k, v in extra_attrs.items():
                setattr(obj, k, v)
        return self._row(obj)

    async def update_entity(self, model_class: type, data: dict) -> dict | None:
        for col in model_class.__table__.columns:
            if col.name in data and isinstance(data[col.name], str) and isinstance(col.type, UUID):
                data[col.name] = uuid.UUID(data[col.name])
        entity_id = data.pop("id", None)
        if isinstance(entity_id, str):
            entity_id = uuid.UUID(entity_id)
        if not entity_id:
            return None
        result = await self.db.execute(select(model_class).where(model_class.id == entity_id))
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        await self.db.flush()
        return self._row(obj)

    async def delete_entity(self, model_class: type, entity_id: uuid.UUID) -> bool:
        result = await self.db.execute(select(model_class).where(model_class.id == entity_id))
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        await self.db.delete(obj)
        await self.db.flush()
        return True

    # ============================================================
    # Internal helpers
    # ============================================================

    async def _create_entity(self, entity_type: str, data: dict):
        model_class = ENTITY_MAP.get(entity_type)
        if not model_class:
            return
        extra = {}
        if entity_type == "scenes" and "content" in data:
            content = data.pop("content")
            extra["word_count"] = len(content.split())
        await self.create_entity(model_class, data, extra_attrs=extra or None)

    async def _update_entity(self, entity_type: str, data: dict):
        model_class = ENTITY_MAP.get(entity_type)
        if not model_class:
            return
        scene_content = None
        entity_id = data.get("id")
        if entity_type == "scenes" and "content" in data:
            scene_content = data.pop("content")
        await self.update_entity(model_class, data)
        if entity_type == "scenes" and scene_content is not None and entity_id:
            if isinstance(entity_id, str):
                entity_id = uuid.UUID(entity_id)
            result = await self.db.execute(select(Scene).where(Scene.id == entity_id))
            obj = result.scalar_one_or_none()
            if obj:
                obj.word_count = len(scene_content.split())

    async def _delete_entity(self, entity_type: str, entity_id_str: str):
        model_class = ENTITY_MAP.get(entity_type)
        if not model_class:
            return
        if isinstance(entity_id_str, str):
            entity_id = uuid.UUID(entity_id_str)
        else:
            entity_id = entity_id_str
        await self.delete_entity(model_class, entity_id)

    @staticmethod
    def _row(obj: Any) -> dict:
        if obj is None:
            return {}
        d = {}
        for col in obj.__table__.columns:
            val = getattr(obj, col.name)
            if isinstance(val, uuid.UUID):
                d[col.name] = str(val)
            elif isinstance(val, datetime):
                d[col.name] = val.isoformat()
            else:
                d[col.name] = val
        return d
