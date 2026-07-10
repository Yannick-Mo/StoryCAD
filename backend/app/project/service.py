import uuid
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.project.repository import ProjectRepository
from app.project.models import Project, ProjectConfig
from app.storycad.models import Chapter, Scene
from app.utils import row_to_dict


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.repo = ProjectRepository(db)

    async def create_project(self, title: str, description: str, owner_id: uuid.UUID) -> dict:
        project = await self.repo.create(title, description, owner_id)
        return row_to_dict(project)

    async def get_project(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> Optional[dict]:
        project = await self.repo.get(project_id)
        if not project or project.owner_id != owner_id:
            return None
        return row_to_dict(project)

    async def list_projects(self, owner_id: uuid.UUID, page: int = 1, size: int = 20, search: str = "", status: str = "") -> dict:
        projects = await self.repo.list_projects(owner_id, page, size, search, status)

        if not projects:
            return {"items": [], "total": 0, "page": page, "size": size}

        project_ids = [p.id for p in projects]

        ch_stmt = select(Chapter.project_id, func.count().label("ch_count")).where(
            Chapter.project_id.in_(project_ids)
        ).group_by(Chapter.project_id)
        ch_rows = (await self.repo.db.execute(ch_stmt)).all()
        ch_map = {row.project_id: row.ch_count for row in ch_rows}

        sc_stmt = select(Scene.project_id, func.count().label("sc_count"), func.coalesce(func.sum(Scene.word_count), 0).label("word_total")).where(
            Scene.project_id.in_(project_ids)
        ).group_by(Scene.project_id)
        sc_rows = (await self.repo.db.execute(sc_stmt)).all()
        sc_map = {row.project_id: {"count": row.sc_count, "words": row.word_total} for row in sc_rows}

        cfg_stmt = select(ProjectConfig).where(ProjectConfig.project_id.in_(project_ids))
        cfg_rows = (await self.repo.db.execute(cfg_stmt)).scalars().all()
        cfg_map = {c.project_id: c for c in cfg_rows}

        items = []
        for p in projects:
            item = row_to_dict(p)
            sc_data = sc_map.get(p.id, {"count": 0, "words": 0})
            item["total_chapters"] = int(ch_map.get(p.id, 0))
            item["total_scenes"] = int(sc_data["count"])
            item["total_words"] = int(sc_data["words"])
            config = cfg_map.get(p.id)
            item["template_type"] = config.template_type if config else ""
            items.append(item)

        total = (await self.repo.db.execute(
            select(func.count()).select_from(Project).where(Project.owner_id == owner_id)
        )).scalar() or 0

        return {"items": items, "total": total, "page": page, "size": size}

    async def update_project(self, project_id: uuid.UUID, owner_id: uuid.UUID, **kwargs) -> bool:
        project = await self.repo.get(project_id)
        if not project or project.owner_id != owner_id:
            return False
        return await self.repo.update(project_id, **kwargs)

    async def delete_project(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> bool:
        project = await self.repo.get(project_id)
        if not project or project.owner_id != owner_id:
            return False
        return await self.repo.delete(project_id)

    async def get_config(self, owner_id: uuid.UUID, project_id: uuid.UUID):
        project = await self.repo.get(project_id)
        if not project or project.owner_id != owner_id:
            return None
        return await self.repo.get_config(project_id)

    async def update_config(self, owner_id: uuid.UUID, project_id: uuid.UUID, data: dict):
        project = await self.repo.get(project_id)
        if not project or project.owner_id != owner_id:
            return None
        allowed = {"total_words", "template_type", "target_audience"}
        filtered = {k: v for k, v in data.items() if k in allowed}
        return await self.repo.upsert_config(project_id, **filtered)
