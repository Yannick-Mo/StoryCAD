from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from app.llm.client import LLMClient
from .base import BaseTool, ToolResult, ToolMeta, ConcurrencyMode


def _safe_instantiate(cls: type[BaseTool], llm_client: LLMClient | None = None) -> BaseTool | None:
    try:
        return cls(llm_client=llm_client)
    except Exception:
        import logging
        logging.getLogger(__name__).warning("Failed to instantiate tool %s", cls.__name__, exc_info=True)
        return None


def get_tool_registry(db: AsyncSession | None = None, llm_client: LLMClient | None = None) -> dict[str, BaseTool]:
    from .list_tools import (
        ListChaptersTool, ListScenesTool,
        ListRelationsTool, ListEdgesTool, SearchNodesTool,
    )
    from .project_tools import (
        ReadProjectTool, ReadChapterTool, ReadSceneTool, CreateSceneTool, UpdateSceneTool,
        ReadFullProjectTool, SetChapterGoalTool, UpdateChapterTool, UpdateActTool,
    )
    from .character_tools import (
        ListCharactersTool, CreateCharacterTool, UpdateCharacterTool, UpdateRelationTool,
        DeleteCharacterTool, DeleteRelationTool,
    )
    from .agent_tools import GoalAgentTool, OutlineAgentTool
    from .analysis_tools import ConsistencyCheckTool, RhythmAnalyzeTool
    from .analysis_v2_tools import AnalyzeChapterTool, AnalyzeCharacterArcTool, SuggestNextTool, ProjectHealthTool
    from .writing_tools import WriteSceneContentTool, ContinueSceneTool, RewriteSceneTool, ExpandSelectionTool, CompressSelectionTool
    from .knowledge_tools import SearchKnowledgeTool
    from .web_search import WebSearchTool
    from .web_fetch import WebFetchTool
    from .project_admin_tools import (
        CreateActTool, CreateChapterTool, UpdateProjectTool,
        DeleteSceneTool, DeleteChapterTool, DeleteActTool,
        CreateProjectFromMaterialTool,
        CreateEdgeTool, UpdateEdgeTool, DeleteEdgeTool,
    )
    from .theme_tools import (
        CreateThemeTool, UpdateThemeTool, DeleteThemeTool,
        LinkThemeChapterTool, UnlinkThemeChapterTool, SetChapterRhythmTool,
    )
    from .skill_tool import InvokeSkillTool
    classes = [
        ListChaptersTool, ListScenesTool, ListRelationsTool, ListEdgesTool, SearchNodesTool,
        ReadProjectTool, ReadChapterTool, ReadSceneTool, CreateSceneTool, UpdateSceneTool,
        ReadFullProjectTool, SetChapterGoalTool, UpdateChapterTool, UpdateActTool,
        ListCharactersTool, CreateCharacterTool, UpdateCharacterTool, UpdateRelationTool,
        DeleteCharacterTool, DeleteRelationTool,
        GoalAgentTool, OutlineAgentTool,
        ConsistencyCheckTool, RhythmAnalyzeTool,
        AnalyzeChapterTool, AnalyzeCharacterArcTool, SuggestNextTool, ProjectHealthTool,
        WriteSceneContentTool, ContinueSceneTool, RewriteSceneTool, ExpandSelectionTool, CompressSelectionTool,
        SearchKnowledgeTool,
        WebSearchTool, WebFetchTool,
        CreateActTool, CreateChapterTool, UpdateProjectTool,
        DeleteSceneTool, DeleteChapterTool, DeleteActTool,
        CreateProjectFromMaterialTool,
        CreateEdgeTool, UpdateEdgeTool, DeleteEdgeTool,
        CreateThemeTool, UpdateThemeTool, DeleteThemeTool,
        LinkThemeChapterTool, UnlinkThemeChapterTool, SetChapterRhythmTool,
        InvokeSkillTool,
    ]
    registry: dict[str, BaseTool] = {}
    for cls in classes:
        if cls.name in registry:
            raise ValueError(f"Duplicate tool name: {cls.name}")
        inst = _safe_instantiate(cls, llm_client)
        if inst is not None:
            registry[cls.name] = inst
    return registry


def get_filtered_tools(
    all_tools: dict[str, BaseTool],
    mode: str = "chat",
) -> dict[str, BaseTool]:
    from app.agent.tool_filter import get_available_tools
    return get_available_tools(all_tools, mode=mode)


def get_tool_descriptions(tools: dict[str, BaseTool]) -> str:
    """Build a human-readable description string for a tool dict.

    Includes concurrency mode when available on the tool's meta.
    """
    lines = []
    for t_name, t_inst in sorted(tools.items()):
        d = t_inst.to_openai_tool()
        fn = d.get("function", {})
        params = fn.get("parameters", {})
        required = params.get("required", [])
        props = params.get("properties", {})

        concurrency_str = ""
        if hasattr(t_inst, "meta") and t_inst.meta is not None:
            concurrency_str = f" [并发:{t_inst.meta.concurrency.value}]"
        destructive_str = ""
        if hasattr(t_inst, "meta") and t_inst.meta is not None and t_inst.meta.is_destructive:
            destructive_str = " [破坏性]"

        lines.append(f"- {t_name}: {fn.get('description', '')}{concurrency_str}{destructive_str}")
        for p_name, p_schema in props.items():
            req = "(required)" if p_name in required else ""
            lines.append(f"    {p_name}: {p_schema.get('description', '')} {req}")
    return "\n".join(lines)


__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolMeta",
    "ConcurrencyMode",
    "get_tool_registry",
    "get_filtered_tools",
    "get_tool_descriptions",
]
