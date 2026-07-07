from app.agent.client import LLMClient
from app.agent.project_creator.state import MaterialState
from app.agent.utils import parse_json, load_project_prompt


async def build_settings(state: MaterialState) -> dict:
    client = LLMClient()
    system_raw = load_project_prompt("material_settings")
    try:
        system = system_raw.format(
            genre=state.get("genre", ""),
            tone=state.get("tone", ""),
            plot_summary=state.get("plot_summary", ""),
            world_elements=state.get("world_elements", ""),
        )
    except KeyError:
        system = system_raw

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "请生成世界观设定"},
    ]

    raw = await client.chat(messages, temperature=0.5, max_tokens=2048)
    try:
        parsed = parse_json(raw)
    except Exception:
        parsed = {}

    return {"global_settings": parsed.get("global_settings", "")}
