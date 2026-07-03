from enum import Enum
from pydantic import BaseModel


class StoryPhase(str, Enum):
    ANALYSIS = "analysis"
    CHARACTER = "character"
    WORLD = "world"
    STORY = "story"
    VALIDATION = "validation"
    COMPLETE = "complete"


class WorkflowState(BaseModel):
    project_id: str
    current_phase: StoryPhase = StoryPhase.ANALYSIS
    completed_phases: list[str] = []
    status: str = "idle"
    error: str = ""
    phase_results: dict = {}
