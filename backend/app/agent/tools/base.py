from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession


class ToolResult(dict):
    success: bool
    data: Any
    error: str | None

    def __init__(self, success: bool = True, data: Any = None, error: str | None = None):
        super().__init__(success=success, data=data, error=error)


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    parameters: dict = {}

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
