from typing import TypedDict, List
from langgraph.graph import StateGraph, END


class StoryState(TypedDict):
    raw_input: dict
    creative_doc: dict
    world_rules: dict
    characters: List[dict]
    graph_data: dict
    branches: List[dict]
    foreshadows: List[dict]
    validation_report: List[dict]
    iteration: int
    repaired_category: str


def repair_router(state: StoryState) -> dict:
    iteration = state.get("iteration", 0) + 1
    report = state.get("validation_report", [])

    if iteration >= 3 or not report or len(report) == 0:
        return {"iteration": iteration, "repaired_category": "end"}

    first = report[0]
    category = first.get("category", "")
    if "OOC" in category or "角色" in category:
        return {"iteration": iteration, "repaired_category": "repair_characters"}
    elif "锚点" in category or "因果" in category or "情节" in category:
        return {"iteration": iteration, "repaired_category": "repair_plot"}
    elif "规则" in category or "世界观" in category:
        return {"iteration": iteration, "repaired_category": "repair_world"}
    else:
        return {"iteration": iteration, "repaired_category": "repair_plot"}


def route_from_repair(state: StoryState) -> str:
    return state.get("repaired_category", "end")


def build_story_graph():
    from app.agents.idea_parser import parse as parse_idea
    from app.agents.world_builder import run as build_world
    from app.agents.character_designer import run as build_characters
    from app.agents.plot_graph import run as build_plot
    from app.agents.branch_foreshadow import run as build_branches
    from app.agents.validator import run as validate

    workflow = StateGraph(StoryState)

    workflow.add_node("parse_idea", parse_idea)
    workflow.add_node("build_world", build_world)
    workflow.add_node("build_characters", build_characters)
    workflow.add_node("build_plot", build_plot)
    workflow.add_node("build_branches", build_branches)
    workflow.add_node("validate", validate)
    workflow.add_node("repair_router", repair_router)

    workflow.set_entry_point("parse_idea")
    workflow.add_edge("parse_idea", "build_world")
    workflow.add_edge("build_world", "build_characters")
    workflow.add_edge("build_characters", "build_plot")
    workflow.add_edge("build_plot", "build_branches")
    workflow.add_edge("build_branches", "validate")
    workflow.add_edge("validate", "repair_router")

    workflow.add_conditional_edges(
        "repair_router",
        route_from_repair,
        {
            "end": END,
            "repair_world": "build_world",
            "repair_characters": "build_characters",
            "repair_plot": "build_plot",
        }
    )

    return workflow.compile()
