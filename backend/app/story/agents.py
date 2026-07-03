import json
import logging
from app.agents.base import run_agent
from app.story.models import StoryStructureResult

logger = logging.getLogger(__name__)

STRUCTURE_PROMPT = """You are a Plot Architect. Design a story structure with embedded character/world integration.

Given analysis metadata AND character profiles AND world details, design:

1. Three-act summary: For each act, describe inciting incident, midpoint, climax, character arc beat, world impact, character agency moment
2. Plot arcs: main + 1 subplot with name, type, beats array, description, resolution
3. Major plot points: array of objects with fields: act, name, description, characters_involved, world_element, tension_before, tension_after

Output JSON with: three_act_summary object, logline, plot_arcs array, major_plot_points array, pending_choices array, narrative_framework_complete bool."""

PLOT_PROMPT = """You are a Plot Generation Agent. Generate detailed story beats from a story structure.

Given the three-act summary and plot arcs, expand into individual beats:

For each beat include: title, act, description, characters_involved, tension_level (1-10), notes

Output JSON with: beats array, complete bool."""


def _normalize_story_result(result: dict) -> dict:
    """Normalize LLM story output to match Pydantic models, accepting various formats."""
    if not isinstance(result, dict):
        return {}
    # Normalize three_act_summary
    tas = result.get("three_act_summary")
    if not isinstance(tas, dict):
        result["three_act_summary"] = {}
    # Normalize major_plot_points
    mpp = result.get("major_plot_points")
    if not isinstance(mpp, list):
        result["major_plot_points"] = []
    else:
        result["major_plot_points"] = [p for p in mpp if isinstance(p, dict)]
    # Normalize pending_choices
    pc = result.get("pending_choices")
    if isinstance(pc, list):
        result["pending_choices"] = [
            {"choice": c} if isinstance(c, str) else c
            for c in pc if isinstance(c, (str, dict))
        ]
    else:
        result["pending_choices"] = []
    # Normalize plot_arcs beats
    for arc in result.get("plot_arcs") or []:
        if not isinstance(arc, dict):
            continue
        beats = arc.get("beats") or []
        if not isinstance(beats, list):
            beats = []
        parsed = []
        for b in beats:
            if isinstance(b, str):
                parsed.append({"title": b, "act": 1, "description": "", "tension_level": 5})
            elif isinstance(b, dict):
                b.setdefault("title", b.pop("name", ""))
                b.setdefault("act", 1)
                b.setdefault("description", "")
                b.setdefault("tension_level", 5)
                parsed.append(b)
        arc["beats"] = parsed
    return result


async def generate_structure(metadata: dict) -> StoryStructureResult:
    try:
        result = run_agent(
            [("system", STRUCTURE_PROMPT), ("user", "Input:\n{json_data}")],
            {"json_data": json.dumps(metadata, ensure_ascii=False)},
            temperature=0.4
        )
        if isinstance(result, dict):
            result = _normalize_story_result(result)
        return StoryStructureResult(**result)
    except Exception as e:
        logger.error(f"Structure agent failed: {e}")
        # Last-resort fallback: try to salvage logline + three_act_summary
        if isinstance(result, dict):
            try:
                fallback = {
                    "logline": result.get("logline", ""),
                    "three_act_summary": result.get("three_act_summary") if isinstance(result.get("three_act_summary"), dict) else {},
                    "plot_arcs": result.get("plot_arcs", []),
                    "major_plot_points": [],
                    "pending_choices": [],
                    "narrative_framework_complete": True,
                }
                return StoryStructureResult(**fallback)
            except Exception:
                pass
        return StoryStructureResult()


async def generate_plots(structure: dict) -> dict:
    try:
        result = run_agent(
            [("system", PLOT_PROMPT), ("user", "Structure:\n{json_data}")],
            {"json_data": json.dumps(structure, ensure_ascii=False)},
            temperature=0.5
        )
        return result
    except Exception as e:
        logger.error(f"Plot agent failed: {e}")
        return {"beats": [], "complete": False}
