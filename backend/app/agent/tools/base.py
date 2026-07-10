from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import LLMClient


@dataclass
class ToolResult:
    success: bool = True
    data: Any = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {"success": self.success, "data": self.data, "error": self.error}


async def verify_project_owner(db: AsyncSession, project_id, user_id: str | None) -> None:
    if user_id is None:
        return
    from app.project.models import Project
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    if not result.scalar_one_or_none():
        raise PermissionError(f"User {user_id} does not own project {project_id}")


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    parameters: dict = {}
    is_write_operation: bool = False
    llm_client: LLMClient | None = None

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client

    @abstractmethod
    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        pass

    def to_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
