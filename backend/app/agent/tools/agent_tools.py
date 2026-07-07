import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.tools.base import BaseTool, ToolResult
from app.agent.orchestrator import AgentOrchestrator


class GoalAgentTool(BaseTool):
    name = "call_goal_agent"
    description = "调用目标设定智能体，为当前章节设定写作目标"
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "chapter_id": {"type": "string"},
            "user_prompt": {"type": "string", "description": "对目标设定的额外指示"},
        },
        "required": ["project_id", "chapter_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            orch = AgentOrchestrator(db)
            result = await orch.generate(
                project_id=uuid.UUID(kwargs["project_id"]),
                chapter_id=uuid.UUID(kwargs["chapter_id"]),
                mode="goal",
                user_prompt=kwargs.get("user_prompt", ""),
            )
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class OutlineAgentTool(BaseTool):
    name = "call_outline_agent"
    description = "调用大纲智能体，为当前章节生成写作大纲"
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "chapter_id": {"type": "string"},
            "user_prompt": {"type": "string", "description": "对大纲生成的额外指示"},
        },
        "required": ["project_id", "chapter_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            orch = AgentOrchestrator(db)
            result = await orch.generate(
                project_id=uuid.UUID(kwargs["project_id"]),
                chapter_id=uuid.UUID(kwargs["chapter_id"]),
                mode="outline",
                user_prompt=kwargs.get("user_prompt", ""),
            )
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class WritingAgentTool(BaseTool):
    name = "call_writing_agent"
    description = "调用写作智能体，根据大纲和目标生成章节正文"
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "chapter_id": {"type": "string"},
            "user_prompt": {"type": "string", "description": "对写作的额外指示"},
        },
        "required": ["project_id", "chapter_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            orch = AgentOrchestrator(db)
            result = await orch.generate(
                project_id=uuid.UUID(kwargs["project_id"]),
                chapter_id=uuid.UUID(kwargs["chapter_id"]),
                mode="writing",
                user_prompt=kwargs.get("user_prompt", ""),
            )
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
