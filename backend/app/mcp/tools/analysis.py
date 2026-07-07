from app.mcp.server import mcp
from app.database import async_session


@mcp.tool()
async def check_consistency(project_id: str) -> dict:
    """检查故事一致性（角色、情节、设定），返回一致性报告"""
    async with async_session() as db:
        from app.agent.consistency.checker import ConsistencyChecker
        checker = ConsistencyChecker(db)
        report = await checker.check_all(project_id)
        return report.model_dump(mode="json")


@mcp.tool()
async def analyze_rhythm(project_id: str) -> dict:
    """分析故事节奏（动作、悬疑、情感、幽默、强度），返回分析报告"""
    from app.agent.rhythm.analyzer import RhythmAnalyzer
    async with async_session() as db:
        analyzer = RhythmAnalyzer(db)
        return await analyzer.analyze(project_id)
