from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.tools.base import BaseTool, ToolResult
from app.agent.consistency.checker import ConsistencyChecker


class ConsistencyCheckTool(BaseTool):
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
            checker = ConsistencyChecker(db)
            report = await checker.check_all(kwargs["project_id"])
            return ToolResult(success=True, data=report.model_dump(mode="json"))
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class RhythmAnalyzeTool(BaseTool):
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
            from app.agent.rhythm.analyzer import RhythmAnalyzer
            project_id = kwargs["project_id"]
            analyzer = RhythmAnalyzer(db)
            result = await analyzer.analyze(project_id)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
