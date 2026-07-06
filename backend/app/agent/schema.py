# backend/app/agent/schema.py
from pydantic import BaseModel


class GoalOutput(BaseModel):
    goal: str
    reasoning: str


class SceneOutlineItem(BaseModel):
    title: str
    pov_character: str
    setting: str
    scene_time: str
    summary: str


class OutlineOutput(BaseModel):
    planning: str
    scenes: list[SceneOutlineItem]


class WritingOutput(BaseModel):
    content: str
    note: str | None = None
