from app.agent.client import LLMClient
from app.agent.project_creator.state import MaterialState
from app.agent.utils import parse_json, load_project_prompt


async def analyze_material(state: MaterialState) -> dict:
    client = LLMClient()
    system_prompt = load_project_prompt("material_analyze")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"素材内容：\n\n{state['material']}"},
    ]

    raw = await client.chat(messages, temperature=0.3)
    try:
        parsed = parse_json(raw)
    except Exception:
        parsed = {}

    return {
        "genre": parsed.get("genre", ""),
        "tone": parsed.get("tone", ""),
        "characters_raw": parsed.get("characters_raw", []),
        "plot_summary": parsed.get("plot_summary", ""),
        "world_elements": parsed.get("world_elements", ""),
    }
