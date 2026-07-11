"""Per-skill and per-intent tool filtering."""

from app.agent.tools.base import BaseTool

# Map skill names → tool names they enable
SKILL_TO_TOOLS: dict[str, set[str]] = {
    "character_dev": {
        "list_characters", "create_character", "update_character", "update_relation",
        "analyze_character_arc",
    },
    "plot_outline": {
        "read_project", "read_chapter", "read_full_project",
        "update_project",
        "update_chapter", "update_act", "update_scene",
        "create_scene", "set_chapter_goal",
        "create_act", "create_chapter",
        "delete_scene", "delete_chapter", "delete_act",
        "create_project_from_material",
        "create_edge", "update_edge", "delete_edge",
    },
    "writing_assist": {
        "write_scene_content", "continue_scene", "rewrite_scene",
        "expand_selection", "compress_selection",
    },
    "analysis": {
        "analyze_chapter", "analyze_character_arc", "project_health",
        "check_consistency", "analyze_rhythm", "suggest_next",
        "read_full_project", "read_project",
    },
    "goal_setting": {"call_goal_agent", "set_chapter_goal", "read_chapter"},
    "outline_gen": {"call_outline_agent", "read_chapter", "read_full_project"},
    "writing_gen": {"read_scene", "write_scene_content"},
}

READ_ONLY_TOOLS: set[str] = {
    "read_project", "read_chapter", "read_scene", "read_full_project",
    "search_knowledge",
    "analyze_chapter", "analyze_character_arc", "project_health",
    "check_consistency", "analyze_rhythm", "suggest_next",
    "list_characters", "web_search",
}

# Tools available in any mode
GENERAL_TOOLS: set[str] = {
    "read_project", "read_chapter", "read_scene", "read_full_project",
    "search_knowledge",
    "web_search",
}

# Write tools available in cowriter mode without requiring any skill.
# These cover the most fundamental project CRUD operations so that
# users can write content even on empty projects with no skills assigned.
COWRITER_BASE_TOOLS: set[str] = {
    "update_project",
    "create_act",
    "create_chapter",
    "create_scene",
    "create_character",
    "update_scene",
    "update_character",
    "write_scene_content",
}

# Maps actual skill display names (from skill YAML name field)
# to internal functional categories (SKILL_TO_TOOLS keys).
# This bridges the gap between DB skill names and the tool filter system.
SKILL_ALIAS_MAP: dict[str, set[str]] = {
    "言情":         {"character_dev", "writing_assist", "plot_outline"},
    "悬疑推理":      {"character_dev", "analysis", "plot_outline"},
    "现实主义":      {"character_dev", "writing_assist"},
    "网络爽文":     {"writing_assist", "plot_outline", "analysis"},
    "科幻":         {"plot_outline", "writing_gen", "analysis"},
    "奇幻":         {"plot_outline", "writing_gen"},
    "历史":         {"character_dev", "writing_assist", "plot_outline"},
    "恐怖":         {"character_dev", "plot_outline"},
    "武侠":         {"character_dev", "writing_assist", "plot_outline"},
    "仙侠":         {"character_dev", "writing_assist", "plot_outline"},
    "都市":         {"character_dev", "writing_assist"},
    "游戏":         {"plot_outline", "writing_gen", "character_dev"},
    # Self-mappings for backward compat when internal names are passed directly
    "character_dev":  {"character_dev"},
    "plot_outline":   {"plot_outline"},
    "writing_assist": {"writing_assist"},
    "analysis":       {"analysis"},
    "goal_setting":   {"goal_setting"},
    "outline_gen":    {"outline_gen"},
    "writing_gen":    {"writing_gen"},
}

def get_available_tools(
    all_tools: dict[str, BaseTool],
    active_skills: list[str],
    mode: str = "chat",
) -> dict[str, BaseTool]:
    skill_names = set()
    for skill in active_skills:
        if isinstance(skill, dict):
            sname = skill.get("name", "")
        else:
            sname = str(skill)
        skill_names.add(sname)

    allowed: set[str] = set()

    if mode == "chat":
        allowed.update(READ_ONLY_TOOLS)
        for sname in skill_names:
            categories = SKILL_ALIAS_MAP.get(sname, {sname})
            for cat in categories:
                tools = SKILL_TO_TOOLS.get(cat)
                if tools:
                    allowed.update(t for t in tools if t in READ_ONLY_TOOLS)
    else:
        allowed.update(GENERAL_TOOLS)
        allowed.update(COWRITER_BASE_TOOLS)
        for sname in skill_names:
            categories = SKILL_ALIAS_MAP.get(sname, {sname})
            for cat in categories:
                tools = SKILL_TO_TOOLS.get(cat)
                if tools:
                    allowed.update(tools)

    return {name: inst for name, inst in all_tools.items() if name in allowed}
