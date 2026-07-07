from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.tools.base import BaseTool, ToolResult
from app.knowledge.rag import RAGEngine


class SearchKnowledgeTool(BaseTool):
    name = "search_knowledge"
    description = "搜索写作知识库，获取与当前创作相关的技巧和参考"
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "项目ID（可选）"},
            "genre": {"type": "string", "description": "体裁"},
            "query": {"type": "string", "description": "搜索关键词"},
            "limit": {"type": "integer", "description": "返回结果数量"},
        },
        "required": ["query"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        try:
            engine = RAGEngine(db)
            result = await engine.retrieve_context(
                project_id=kwargs.get("project_id"),
                genre=kwargs.get("genre", ""),
                query=kwargs.get("query", ""),
                limit=kwargs.get("limit", 5),
            )
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
