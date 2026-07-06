import json
import yaml
from pathlib import Path
from app.agent.client import LLMClient
from app.agent.project_creator.state import MaterialState

PROMPT_DIR = Path(__file__).parent.parent / "prompts"

COLORS = ["#f97316", "#8b5cf6", "#06b6d4", "#ec4899", "#10b981"]


def _load(name: str) -> str:
    path = PROMPT_DIR / f"{name}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("system", "")


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = next((i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"), len(lines))
        text = "\n".join(lines[1:end])
    return json.loads(text)


async def plan_structure(state: MaterialState) -> dict:
    client = LLMClient()
    system = _load("material_structure").format(
        genre=state.get("genre", ""),
        tone=state.get("tone", ""),
        plot_summary=state.get("plot_summary", ""),
        world_elements=state.get("world_elements", ""),
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "请规划完整的幕-章结构"},
    ]

    raw = await client.chat(messages, temperature=0.5, max_tokens=4096)
    parsed = _parse_json(raw)

    acts = parsed.get("acts", [])
    for i, act in enumerate(acts):
        if "color" not in act:
            act["color"] = COLORS[i % len(COLORS)]
        for ch in act.get("chapters", []):
            if "goal" not in ch:
                ch["goal"] = ""

    return {
        "acts": acts,
        "estimated_words": parsed.get("estimated_words", 50000),
    }
