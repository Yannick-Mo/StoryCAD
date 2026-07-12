from app.agent.project_creator.state import MaterialState
from app.agent.project_creator.nodes.analyze import analyze_material
from app.agent.project_creator.nodes.plan import plan_structure
from app.agent.project_creator.nodes.scenes import generate_all_scenes
from app.agent.project_creator.nodes.characters import design_characters
from app.agent.project_creator.nodes.settings import build_settings
from app.agent.project_creator.nodes.edges import generate_edges
from app.agent.project_creator.nodes.validate import validate

NODE_STEPS = [
    ("analyze_material", analyze_material),
    ("plan_structure", plan_structure),
    ("design_characters", design_characters),
    ("build_settings", build_settings),
    ("generate_all_scenes", generate_all_scenes),
    ("generate_edges", generate_edges),
    ("validate", validate),
]


async def run_pipeline(initial_state: MaterialState):
    """Run project creation pipeline sequentially, yielding (node_name, output) for each step.

    The initial_state dict is mutated in place to accumulate the final state.
    """
    for name, func in NODE_STEPS:
        output = await func(initial_state)
        initial_state.update(output)
        yield name, output
