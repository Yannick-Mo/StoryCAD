# backend/app/agent/project_creator/state.py
import operator
from typing import Annotated, TypedDict


class ChapterDef(TypedDict):
    title: str
    goal: str


class ActDef(TypedDict):
    name: str
    order: int
    color: str
    chapters: list[ChapterDef]


class SceneDef(TypedDict):
    act_idx: int
    chapter_idx: int
    title: str
    pov_character: str
    setting: str
    scene_time: str
    summary: str


class RawCharacter(TypedDict):
    name: str
    description: str


class CharacterDef(TypedDict):
    name: str
    role: str
    personality: str
    appearance: str
    background: str
    motivation: str


class RelationDef(TypedDict):
    char_name: str
    target_name: str
    rel_type: str
    label: str
    description: str


class MaterialState(TypedDict):
    material: str
    project_title: str
    genre: str
    tone: str
    characters_raw: list[RawCharacter]
    plot_summary: str
    world_elements: str
    acts: list[ActDef]
    estimated_words: int
    scenes: Annotated[list[SceneDef], operator.add]
    characters: list[CharacterDef]
    relations: list[RelationDef]
    global_settings: str
    errors: list[str]
