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


def _raw_chars_text(raw_chars: list[dict]) -> str:
    if not raw_chars:
        return "素材中未明确提及角色"
    return "\n".join(f"- {c['name']}: {c.get('description', '')}" for c in raw_chars)


async def design_characters(state: MaterialState) -> dict:
    client = LLMClient()
    system = _load("material_characters").format(
        genre=state.get("genre", ""),
        tone=state.get("tone", ""),
        plot_summary=state.get("plot_summary", ""),
        characters_raw_text=_raw_chars_text(state.get("characters_raw", [])),
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "请设计角色"},
    ]

    raw = await client.chat(messages, temperature=0.7, max_tokens=4096)
    parsed = _parse_json(raw)

    characters = parsed.get("characters", [])
    for c in characters:
        c.setdefault("role", "supporting")
        c.setdefault("personality", "")
        c.setdefault("appearance", "")
        c.setdefault("background", "")
        c.setdefault("motivation", "")

    relations = parsed.get("relations", [])
    for r in relations:
        r.setdefault("rel_type", "关联")
        r.setdefault("label", "")
        r.setdefault("description", "")

    return {"characters": characters, "relations": relations}
