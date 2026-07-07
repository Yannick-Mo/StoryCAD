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

        items = []
        for p in projects:
            ch_count = (await self.repo.db.execute(
                select(func.count()).select_from(Chapter).where(Chapter.project_id == p.id)
            )).scalar() or 0
            sc_count = (await self.repo.db.execute(
                select(func.count()).select_from(Scene).where(Scene.project_id == p.id)
            )).scalar() or 0
            words = (await self.repo.db.execute(
                select(func.coalesce(func.sum(Chapter.total_words), 0)).where(Chapter.project_id == p.id)
            )).scalar() or 0
            config = (await self.repo.db.execute(
                select(ProjectConfig).where(ProjectConfig.project_id == p.id)
            )).scalar_one_or_none()

            item = row_to_dict(p)
            item["template_type"] = config.template_type if config else ""
            item["total_words"] = int(words)
            item["total_chapters"] = int(ch_count)
            item["total_scenes"] = int(sc_count)
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
