from app.agent.client import LLMClient
from app.agent.project_creator.state import MaterialState
from app.agent.utils import parse_json, load_project_prompt


def _raw_chars_text(raw_chars: list[dict]) -> str:
    if not raw_chars:
        return "素材中未明确提及角色"
    return "\n".join(f"- {c['name']}: {c.get('description', '')}" for c in raw_chars)


async def design_characters(state: MaterialState) -> dict:
    client = LLMClient()
    system_raw = load_project_prompt("material_characters")
    try:
        system = system_raw.format(
            genre=state.get("genre", ""),
            tone=state.get("tone", ""),
            plot_summary=state.get("plot_summary", ""),
            characters_raw_text=_raw_chars_text(state.get("characters_raw", [])),
        )
    except KeyError:
        system = system_raw

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "请设计角色"},
    ]

    raw = await client.chat(messages, temperature=0.7, max_tokens=4096)
    try:
        parsed = parse_json(raw)
    except Exception:
        parsed = {}

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
