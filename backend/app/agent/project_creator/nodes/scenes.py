# backend/app/agent/project_creator/nodes/scenes.py
import json
import asyncio
import yaml
from pathlib import Path
from app.agent.client import LLMClient
from app.agent.project_creator.state import MaterialState, SceneDef

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
        return "暂无角色"
    return "\n".join(f"- {c['name']}: {c.get('description', '')}" for c in raw_chars)


async def _generate_one_chapter(
    act_idx: int,
    chap_idx: int,
    act_name: str,
    chapter_title: str,
    chapter_goal: str,
    characters_raw: list[dict],
    world_elements: str,
) -> list[SceneDef]:
    client = LLMClient()
    system = _load("material_scenes").format(
        act_name=act_name,
        chapter_title=chapter_title,
        chapter_goal=chapter_goal,
        characters_raw_text=_raw_chars_text(characters_raw),
        world_elements=world_elements,
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "请为这一章规划场景"},
    ]
    raw = await client.chat(messages, temperature=0.6, max_tokens=2048)
    try:
        parsed = _parse_json(raw)
    except Exception:
        return []
    scene_dicts = parsed.get("scenes", [])
    scenes: list[SceneDef] = []
    for sc in scene_dicts:
        scenes.append(SceneDef(
            act_idx=act_idx,
            chapter_idx=chap_idx,
            title=sc.get("title", ""),
            pov_character=sc.get("pov_character", ""),
            setting=sc.get("setting", ""),
            scene_time=sc.get("scene_time", ""),
            summary=sc.get("summary", ""),
        ))
    return scenes


async def generate_scene_chapter(state: MaterialState) -> dict:
    act_idx = state.get("_fanout_act_idx", 0)
    chap_idx = state.get("_fanout_chap_idx", 0)
    acts = state.get("acts", [])

    if act_idx >= len(acts):
        return {"scenes": []}
    act = acts[act_idx]
    chapters = act.get("chapters", [])
    if chap_idx >= len(chapters):
        return {"scenes": []}

    chapter = chapters[chap_idx]
    result = await _generate_one_chapter(
        act_idx, chap_idx,
        act.get("name", ""),
        chapter.get("title", ""),
        chapter.get("goal", ""),
        state.get("characters_raw", []),
        state.get("world_elements", ""),
    )
    return {"scenes": result}


async def generate_all_scenes(state: MaterialState) -> dict:
    tasks = []
    for act_idx, act in enumerate(state.get("acts", [])):
        for chap_idx, chapter in enumerate(act.get("chapters", [])):
            tasks.append(_generate_one_chapter(
                act_idx, chap_idx,
                act.get("name", ""),
                chapter.get("title", ""),
                chapter.get("goal", ""),
                state.get("characters_raw", []),
                state.get("world_elements", ""),
            ))

    results = await asyncio.gather(*tasks)
    all_scenes: list[SceneDef] = []
    for scenes in results:
        all_scenes.extend(scenes)
    return {"scenes": all_scenes}
