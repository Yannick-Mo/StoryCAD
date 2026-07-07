from app.agent.project_creator.state import MaterialState

MAX_ACTS = 5
MAX_CHAPTERS_PER_ACT = 5
MAX_SCENES_PER_CHAPTER = 5
MAX_CHARACTERS = 10


async def validate(state: MaterialState) -> dict:
    errors: list[str] = []
    acts = list(state.get("acts", []))
    characters = list(state.get("characters", []))
    scenes = list(state.get("scenes", []))

    if len(acts) > MAX_ACTS:
        errors.append(f"幕数 {len(acts)} 超过上限 {MAX_ACTS}")
        acts = acts[:MAX_ACTS]

    trimmed_acts = []
    for act in acts:
        act = dict(act)
        chapters = list(act.get("chapters", []))
        if len(chapters) > MAX_CHAPTERS_PER_ACT:
            errors.append(f"幕 '{act.get('name', '')}' 的章数 {len(chapters)} 超过上限 {MAX_CHAPTERS_PER_ACT}")
            chapters = chapters[:MAX_CHAPTERS_PER_ACT]
        act["chapters"] = chapters
        trimmed_acts.append(act)

    if len(characters) > MAX_CHARACTERS:
        errors.append(f"角色数超过上限 {MAX_CHARACTERS}")
        characters = characters[:MAX_CHARACTERS]

    chapter_scene_counts: dict[str, int] = {}
    trimmed_scenes = []
    for sc in scenes:
        key = f"{sc.get('act_idx', 0)}-{sc.get('chapter_idx', 0)}"
        count = chapter_scene_counts.get(key, 0)
        if count < MAX_SCENES_PER_CHAPTER:
            chapter_scene_counts[key] = count + 1
            trimmed_scenes.append(sc)
        else:
            errors.append(f"章节 {key} 的场景数超过上限")

    return {"acts": trimmed_acts, "characters": characters, "scenes": trimmed_scenes, "errors": errors}
