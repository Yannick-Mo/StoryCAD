from app.mcp.server import mcp
from app.database import async_session


@mcp.tool()
async def check_consistency(project_id: str) -> dict:
    """检查故事一致性（角色、情节、设定），返回一致性报告"""
    async with async_session() as db:
        return {
            "status": "ok",
            "checks": [],
            "note": "一致性检查将在 Phase 4 中完整实现 — 当前返回空报告",
        }


@mcp.tool()
async def analyze_rhythm(project_id: str) -> dict:
    """分析故事节奏（动作、悬疑、情感、幽默、强度），返回分析报告"""
    async with async_session() as db:
        return {
            "status": "ok",
            "metrics": {},
            "note": "节奏分析将在 Phase 4 中完整实现 — 当前返回空报告",
        }
