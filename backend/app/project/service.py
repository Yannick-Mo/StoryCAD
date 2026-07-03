import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.project.repository import ProjectRepository
from app.knowledge_graph.repository import neo4j_repo


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.repo = ProjectRepository(db)

    async def create_project(self, title: str = "Untitled", description: str = "") -> dict:
        project = await self.repo.create(title, description)
        return {
            "id": str(project.id),
            "title": project.title,
            "status": project.status,
            "workflow_stage": project.workflow_stage,
            "created_at": project.created_at.isoformat()
        }

    async def get_project(self, project_id: uuid.UUID) -> Optional[dict]:
        project = await self.repo.get(project_id)
        if not project:
            return None
        return {
            "id": str(project.id), "title": project.title, "description": project.description,
            "genre": project.genre, "status": project.status,
            "workflow_stage": project.workflow_stage,
            "created_at": project.created_at.isoformat(), "updated_at": project.updated_at.isoformat()
        }

    async def list_projects(self, page: int = 1, size: int = 20) -> list[dict]:
        projects = await self.repo.list_projects(page, size)
        return [{"id": str(p.id), "title": p.title, "status": p.status, "created_at": p.created_at.isoformat()} for p in projects]

    async def update_project(self, project_id: uuid.UUID, **kwargs) -> bool:
        return await self.repo.update(project_id, **kwargs)

    async def delete_project(self, project_id: uuid.UUID) -> bool:
        await neo4j_repo.delete_project_graph(str(project_id))
        return await self.repo.delete(project_id)
