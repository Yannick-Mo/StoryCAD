"""Mode-based tool filtering — tools are independent of skills.

- ``chat`` mode: only read-only tools (read, list, search, analyze)
- ``cowriter`` mode: all tools (read + write + delete)
"""

from app.agent.tools.base import BaseTool

READ_ONLY_TOOLS: set[str] = {
    "read_project", "read_chapter", "read_scene", "read_full_project",
    "search_knowledge",
    "analyze_chapter", "analyze_character_arc", "project_health",
    "check_consistency", "analyze_rhythm", "suggest_next",
    "list_characters", "list_chapters", "list_scenes",
    "list_relations", "list_edges", "search_nodes",
    "web_search",
    "invoke_skill",
}

COWRITER_TOOLS: set[str] = {
    # CRUD — project
    "update_project", "create_project_from_material",
    # CRUD — act
    "create_act", "update_act", "delete_act",
    # CRUD — chapter
    "create_chapter", "update_chapter", "delete_chapter",
    "set_chapter_goal",
    # CRUD — scene
    "create_scene", "update_scene", "delete_scene",
    # CRUD — character
    "create_character", "update_character", "delete_character",
    "update_relation", "delete_relation",
    # CRUD — edge
    "create_edge", "update_edge", "delete_edge",
    # CRUD — theme
    "create_theme", "update_theme", "delete_theme",
    "link_theme_chapter", "unlink_theme_chapter", "set_chapter_rhythm",
    # Writing
    "write_scene_content", "continue_scene", "rewrite_scene",
    "expand_selection", "compress_selection",
    # Agents
    "call_goal_agent", "call_outline_agent",
}


def get_available_tools(
    all_tools: dict[str, BaseTool],
    mode: str = "chat",
) -> dict[str, BaseTool]:
    """Filter tools by mode.

    Skills never gate tools — they only inject prompt guidance and
    knowledge tags.  A skill's ``tools_enabled`` / ``SKILL_TO_TOOLS``
    no longer exist.
    """
    if mode == "chat":
        return {n: t for n, t in all_tools.items() if n in READ_ONLY_TOOLS}
    return {n: t for n, t in all_tools.items() if n in READ_ONLY_TOOLS | COWRITER_TOOLS}
