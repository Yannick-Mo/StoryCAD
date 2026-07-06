from app.agent.project_creator.state import MaterialState

MAX_ACTS = 5
MAX_CHAPTERS_PER_ACT = 5
MAX_SCENES_PER_CHAPTER = 5
MAX_CHARACTERS = 10


async def validate(state: MaterialState) -> dict:
    errors: list[str] = []
    acts = state.get("acts", [])

    if len(acts) > MAX_ACTS:
        errors.append(f"幕数 {len(acts)} 超过上限 {MAX_ACTS}")
        state["acts"] = acts[:MAX_ACTS]

    for act in acts:
        chapters = act.get("chapters", [])
        if len(chapters) > MAX_CHAPTERS_PER_ACT:
            errors.append(f"幕 '{act.get('name', '')}' 的章数 {len(chapters)} 超过上限 {MAX_CHAPTERS_PER_ACT}")
            act["chapters"] = chapters[:MAX_CHAPTERS_PER_ACT]

    if len(state.get("characters", [])) > MAX_CHARACTERS:
        errors.append(f"角色数超过上限 {MAX_CHARACTERS}")
        state["characters"] = state["characters"][:MAX_CHARACTERS]

    scenes = state.get("scenes", [])
    chapter_scene_counts: dict[str, int] = {}
    trimmed_scenes = []
    for sc in scenes:
        key = f"{sc['act_idx']}-{sc['chapter_idx']}"
        count = chapter_scene_counts.get(key, 0)
        if count < MAX_SCENES_PER_CHAPTER:
            chapter_scene_counts[key] = count + 1
            trimmed_scenes.append(sc)
        else:
            errors.append(f"章节 {key} 的场景数超过上限")

    return {"scenes": trimmed_scenes, "errors": errors}
