from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.tools.base import BaseTool, ToolResult, ToolMeta, ConcurrencyMode, verify_project_owner
from app.agent.consistency.checker import ConsistencyChecker


class ConsistencyCheckTool(BaseTool):
    meta = ToolMeta(
        name="check_consistency",
        description="检查故事一致性，返回基本的角色、情节、设定一致性报告",
        concurrency=ConcurrencyMode.SAFE,
        search_hint="consistency check story analysis",
    )
    name = "check_consistency"
    description = "检查故事一致性，返回基本的角色、情节、设定一致性报告"
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "项目ID"},
        },
        "required": ["project_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            import uuid
            pid = uuid.UUID(kwargs["project_id"])
            await verify_project_owner(db, pid, kwargs.get("user_id"))
            checker = ConsistencyChecker(db)
            report = await checker.check_all(pid)
            return ToolResult(success=True, data=report.model_dump(mode="json"))
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))


class RhythmAnalyzeTool(BaseTool):
    meta = ToolMeta(
        name="analyze_rhythm",
        description="分析故事节奏（动作、悬疑、情感、幽默、强度），返回基本分析报告",
        concurrency=ConcurrencyMode.SAFE,
        search_hint="rhythm analyze story pacing",
    )
    name = "analyze_rhythm"
    description = "分析故事节奏（动作、悬疑、情感、幽默、强度），返回基本分析报告"
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "项目ID"},
        },
        "required": ["project_id"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            import uuid
            pid = uuid.UUID(kwargs["project_id"])
            await verify_project_owner(db, pid, kwargs.get("user_id"))
            from app.agent.rhythm.analyzer import RhythmAnalyzer
            analyzer = RhythmAnalyzer(db)
            result = await analyzer.analyze(pid)
            return ToolResult(success=True, data=result)
        except Exception as e:
            await db.rollback()
            return ToolResult(success=False, error=str(e))
