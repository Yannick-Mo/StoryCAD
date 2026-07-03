from pydantic import BaseModel


class StoryBeat(BaseModel):
    title: str
    act: int = 1
    description: str = ""
    characters_involved: list[str] = []
    tension_level: int = 5
    notes: str = ""


class PlotArc(BaseModel):
    name: str
    type: str = "main"
    beats: list[StoryBeat] = []
    description: str = ""
    resolution: str = ""


class StoryStructureResult(BaseModel):
    three_act_summary: dict = {}
    logline: str = ""
    plot_arcs: list[PlotArc] = []
    major_plot_points: list[dict] = []
    pending_choices: list[dict] = []
    narrative_framework_complete: bool = False


class StoryGenerationInput(BaseModel):
    character_metadata: dict = {}
    world_metadata: dict = {}
    analysis_metadata: dict = {}
