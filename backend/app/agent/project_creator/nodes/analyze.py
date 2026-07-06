import json
import yaml
from pathlib import Path
from app.agent.client import LLMClient
from app.agent.project_creator.state import MaterialState

PROMPT_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("system", "")


async def analyze_material(state: MaterialState) -> dict:
    client = LLMClient()
    system_prompt = _load_prompt("material_analyze")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"素材内容：\n\n{state['material']}"},
    ]

    raw = await client.chat(messages, temperature=0.3)
    parsed = _parse_json(raw)

    return {
        "genre": parsed.get("genre", ""),
        "tone": parsed.get("tone", ""),
        "characters_raw": parsed.get("characters_raw", []),
        "plot_summary": parsed.get("plot_summary", ""),
        "world_elements": parsed.get("world_elements", ""),
    }


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = next((i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"), len(lines))
        text = "\n".join(lines[1:end])
    return json.loads(text)
