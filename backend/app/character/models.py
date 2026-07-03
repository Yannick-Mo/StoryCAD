from pydantic import BaseModel


class DesireTopology(BaseModel):
    surface_desire: str = ""
    deep_need: str = ""
    core_fear: str = ""


class CharacterProfile(BaseModel):
    name: str
    role: str = "supporting"
    desire_topology: DesireTopology = DesireTopology()
    bottom_line: str = ""
    vulnerability: str = ""
    language_genes: list[str] = []
    growth_arc: str = ""
    backstory: str = ""


class Relationship(BaseModel):
    from_name: str
    to_name: str
    trust: int = 50
    threat: int = 50
    attraction: int = 50
    description: str = ""


class CharacterDesignResult(BaseModel):
    logline: str = ""
    core_theme: str = ""
    characters: list[CharacterProfile] = []
    relationships: list[Relationship] = []
    pending_choices: list[dict] = []
