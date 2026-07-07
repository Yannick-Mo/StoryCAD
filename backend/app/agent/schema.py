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


class CharacterOutput(BaseModel):
    name: str | None = None
    role: str | None = None
    personality: str | None = None
    motivation: str | None = None
    background: str | None = None
    arc_description: str | None = None


class PlotDoctorOutput(BaseModel):
    diagnosis: str
    issues: list[str]
    suggestions: list[str]
    priority: str
