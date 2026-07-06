from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.memory import MemorySaver
from app.agent.project_creator.state import MaterialState
from app.agent.project_creator.nodes.analyze import analyze_material
from app.agent.project_creator.nodes.plan import plan_structure
from app.agent.project_creator.nodes.scenes import generate_scene_chapter
from app.agent.project_creator.nodes.characters import design_characters
from app.agent.project_creator.nodes.settings import build_settings
from app.agent.project_creator.nodes.validate import validate


def _fanout_scenes(state: MaterialState):
    sends = []
    for act_idx, act in enumerate(state.get("acts", [])):
        for chap_idx in range(len(act.get("chapters", []))):
            sends.append(Send("generate_scene_chapter", {
                "_fanout_act_idx": act_idx,
                "_fanout_chap_idx": chap_idx,
            }))
    return sends


def build_graph():
    builder = StateGraph(state_schema=MaterialState)

    builder.add_node("analyze_material", analyze_material)
    builder.add_node("plan_structure", plan_structure)
    builder.add_node("generate_scene_chapter", generate_scene_chapter)
    builder.add_node("design_characters", design_characters)
    builder.add_node("build_settings", build_settings)
    builder.add_node("validate", validate)

    builder.add_edge(START, "analyze_material")
    builder.add_edge("analyze_material", "plan_structure")
    builder.add_conditional_edges("plan_structure", _fanout_scenes)
    builder.add_edge("generate_scene_chapter", "design_characters")
    builder.add_edge("design_characters", "build_settings")
    builder.add_edge("build_settings", "validate")
    builder.add_edge("validate", END)

    return builder.compile(checkpointer=MemorySaver())
