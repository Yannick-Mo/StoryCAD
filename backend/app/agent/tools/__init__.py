from sqlalchemy.ext.asyncio import AsyncSession
from .base import BaseTool, ToolResult


def get_tool_registry(db: AsyncSession | None = None) -> dict[str, BaseTool]:
    from .project_tools import ReadProjectTool, ReadChapterTool, ReadSceneTool, CreateSceneTool, UpdateSceneTool
    from .character_tools import ListCharactersTool, CreateCharacterTool, UpdateCharacterTool, UpdateRelationTool
    from .agent_tools import GoalAgentTool, OutlineAgentTool, WritingAgentTool
    from .analysis_tools import ConsistencyCheckTool, RhythmAnalyzeTool
    from .knowledge_tools import SearchKnowledgeTool
    classes = [
        ReadProjectTool, ReadChapterTool, ReadSceneTool, CreateSceneTool, UpdateSceneTool,
        ListCharactersTool, CreateCharacterTool, UpdateCharacterTool, UpdateRelationTool,
        GoalAgentTool, OutlineAgentTool, WritingAgentTool,
        ConsistencyCheckTool, RhythmAnalyzeTool,
        SearchKnowledgeTool,
    ]
    return {cls.name: cls() for cls in classes}


__all__ = [
    "BaseTool",
    "ToolResult",
    "get_tool_registry",
]
