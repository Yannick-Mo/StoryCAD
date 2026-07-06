import json
import yaml
from pathlib import Path
from app.agent.client import LLMClient
from app.agent.project_creator.state import MaterialState

PROMPT_DIR = Path(__file__).parent.parent / "prompts"


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


async def build_settings(state: MaterialState) -> dict:
    client = LLMClient()
    system = _load("material_settings").format(
        genre=state.get("genre", ""),
        tone=state.get("tone", ""),
        plot_summary=state.get("plot_summary", ""),
        world_elements=state.get("world_elements", ""),
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "请生成世界观设定"},
    ]

    raw = await client.chat(messages, temperature=0.5, max_tokens=2048)
    parsed = _parse_json(raw)

    return {"global_settings": parsed.get("global_settings", "")}
