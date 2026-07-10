from __future__ import annotations

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.llm.client import LLMClient
from .base import BaseTool, ToolResult


_WRITE_TOOL_NAMES: set[str] = {
    "update_chapter", "update_act", "update_scene",
    "set_chapter_goal", "create_scene",
    "update_character", "create_character", "update_relation",
    "write_scene_content", "continue_scene", "rewrite_scene",
    "expand_selection", "compress_selection",
    "call_goal_agent", "call_outline_agent",
    "create_act", "create_chapter", "update_project",
    "delete_scene", "delete_chapter", "delete_act",
    "create_project_from_material",
    "create_edge", "update_edge", "delete_edge",
}


def _safe_instantiate(cls: type[BaseTool], llm_client: LLMClient | None = None) -> BaseTool | None:
    try:
        return cls(llm_client=llm_client)
    except Exception:
        import logging
        logging.getLogger(__name__).warning("Failed to instantiate tool %s", cls.__name__, exc_info=True)
        return None


def get_tool_registry(db: AsyncSession | None = None, llm_client: LLMClient | None = None) -> dict[str, BaseTool]:
    from .project_tools import (
        ReadProjectTool, ReadChapterTool, ReadSceneTool, CreateSceneTool, UpdateSceneTool,
        ReadFullProjectTool, SetChapterGoalTool, UpdateChapterTool, UpdateActTool,
    )
    from .character_tools import ListCharactersTool, CreateCharacterTool, UpdateCharacterTool, UpdateRelationTool
    from .agent_tools import GoalAgentTool, OutlineAgentTool
    from .analysis_tools import ConsistencyCheckTool, RhythmAnalyzeTool
    from .analysis_v2_tools import AnalyzeChapterTool, AnalyzeCharacterArcTool, SuggestNextTool, ProjectHealthTool
    from .writing_tools import WriteSceneContentTool, ContinueSceneTool, RewriteSceneTool, ExpandSelectionTool, CompressSelectionTool
    from .knowledge_tools import SearchKnowledgeTool
    from .project_admin_tools import (
        CreateActTool, CreateChapterTool, UpdateProjectTool,
        DeleteSceneTool, DeleteChapterTool, DeleteActTool,
        CreateProjectFromMaterialTool,
        CreateEdgeTool, UpdateEdgeTool, DeleteEdgeTool,
    )
    classes = [
        ReadProjectTool, ReadChapterTool, ReadSceneTool, CreateSceneTool, UpdateSceneTool,
        ReadFullProjectTool, SetChapterGoalTool, UpdateChapterTool, UpdateActTool,
        ListCharactersTool, CreateCharacterTool, UpdateCharacterTool, UpdateRelationTool,
        GoalAgentTool, OutlineAgentTool,
        ConsistencyCheckTool, RhythmAnalyzeTool,
        AnalyzeChapterTool, AnalyzeCharacterArcTool, SuggestNextTool, ProjectHealthTool,
        WriteSceneContentTool, ContinueSceneTool, RewriteSceneTool, ExpandSelectionTool, CompressSelectionTool,
        SearchKnowledgeTool,
        CreateActTool, CreateChapterTool, UpdateProjectTool,
        DeleteSceneTool, DeleteChapterTool, DeleteActTool,
        CreateProjectFromMaterialTool,
        CreateEdgeTool, UpdateEdgeTool, DeleteEdgeTool,
    ]
    registry: dict[str, BaseTool] = {}
    for cls in classes:
        inst = _safe_instantiate(cls, llm_client)
        if inst is not None:
            registry[cls.name] = inst
    return registry



def get_filtered_tools(
    all_tools: dict[str, BaseTool],
    active_skills: list[str | dict[str, Any]] | None = None,
    mode: str = "chat",
) -> dict[str, BaseTool]:
    from app.agent.tool_filter import get_available_tools
    return get_available_tools(all_tools, active_skills or [], mode=mode)


def get_tool_descriptions(tools: dict[str, BaseTool]) -> str:
    lines = []
    for t_name, t_inst in sorted(tools.items()):
        d = t_inst.to_openai_tool()
        fn = d.get("function", {})
        params = fn.get("parameters", {})
        required = params.get("required", [])
        props = params.get("properties", {})
        lines.append(f"- {t_name}: {fn.get('description', '')}")
        for p_name, p_schema in props.items():
            req = "(required)" if p_name in required else ""
            lines.append(f"    {p_name}: {p_schema.get('description', '')} {req}")
    return "\n".join(lines)


__all__ = [
    "BaseTool",
    "ToolResult",
    "get_tool_registry",
    "get_filtered_tools",
    "get_tool_descriptions",
]
