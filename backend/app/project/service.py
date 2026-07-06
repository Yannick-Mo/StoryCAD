import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.project.repository import ProjectRepository


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.repo = ProjectRepository(db)

    async def create_project(self, title: str, description: str, owner_id: uuid.UUID) -> dict:
        project = await self.repo.create(title, description, owner_id)
        return {
            "id": str(project.id),
            "title": project.title,
            "status": project.status,
            "workflow_stage": project.workflow_stage,
            "created_at": project.created_at.isoformat()
        }

    async def get_project(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> Optional[dict]:
        project = await self.repo.get(project_id)
        if not project or project.owner_id != owner_id:
            return None
        return {
            "id": str(project.id), "title": project.title, "description": project.description,
            "genre": project.genre, "status": project.status,
            "workflow_stage": project.workflow_stage,
            "created_at": project.created_at.isoformat(), "updated_at": project.updated_at.isoformat()
        }

    async def list_projects(self, owner_id: uuid.UUID, page: int = 1, size: int = 20) -> list[dict]:
        projects = await self.repo.list_projects(owner_id, page, size)
        return [{"id": str(p.id), "title": p.title, "status": p.status, "created_at": p.created_at.isoformat()} for p in projects]

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
