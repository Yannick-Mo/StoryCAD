from __future__ import annotations

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.llm.client import LLMClient
from app.agent.tools.base import BaseTool, ToolResult, ToolMeta, ConcurrencyMode, verify_project_owner
from app.agent.orchestrator import AgentOrchestrator


class _CallAgentBase(BaseTool):
    """Base class for agent-calling tools. Subclasses differ only in name/description/mode."""
    mode: str = ""

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            await verify_project_owner(db, uuid.UUID(kwargs["project_id"]), kwargs.get("user_id"))
            orch = AgentOrchestrator(db, llm_client=self.llm_client)
            result = await orch.generate(
                project_id=uuid.UUID(kwargs["project_id"]),
                chapter_id=uuid.UUID(kwargs["chapter_id"]),
                mode=self.mode,
                user_prompt=kwargs.get("user_prompt", ""),
            )
            return ToolResult(success=True, data=result)
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class GoalAgentTool(_CallAgentBase):
    meta = ToolMeta(
        name="call_goal_agent",
        description="调用目标设定智能体，为当前章节设定写作目标",
        concurrency=ConcurrencyMode.EXCLUSIVE,
        timeout=120,
        parameters={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节ID，来自 list_chapters 或 read_full_project"},
                "user_prompt": {"type": "string", "description": "对目标设定的额外指示"},
            },
            "required": ["chapter_id"],
        },
    )
    mode = "goal"


class OutlineAgentTool(_CallAgentBase):
    meta = ToolMeta(
        name="call_outline_agent",
        description="调用大纲智能体，为当前章节生成写作大纲",
        concurrency=ConcurrencyMode.EXCLUSIVE,
        timeout=120,
        parameters={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节ID，来自 list_chapters 或 read_full_project"},
                "user_prompt": {"type": "string", "description": "对大纲生成的额外指示"},
            },
            "required": ["chapter_id"],
        },
    )
    mode = "outline"


