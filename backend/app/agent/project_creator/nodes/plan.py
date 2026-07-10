from app.agent.project_creator.state import MaterialState
from app.agent.utils import get_shared_client, parse_json_safe, load_project_prompt
from app.llm.types import Message

COLORS = ["#f97316", "#8b5cf6", "#06b6d4", "#ec4899", "#10b981"]


async def plan_structure(state: MaterialState) -> dict:
    client = get_shared_client()
    system_raw = load_project_prompt("material_structure")
    try:
        system = system_raw.format(
            genre=state.get("genre", ""),
            tone=state.get("tone", ""),
            plot_summary=state.get("plot_summary", ""),
            world_elements=state.get("world_elements", ""),
        )
    except KeyError:
        system = system_raw

    messages: list[Message] = [
        Message(role="system", content=system),
        Message(role="user", content="请规划完整的幕-章结构"),
    ]

    result = await client.chat(messages, temperature=0.5, max_tokens=4096)
    raw = result.content or ""
    parsed = await parse_json_safe(raw, client, messages)

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
