from pydantic import BaseModel


class Location(BaseModel):
    name: str
    description: str = ""
    type: str = "location"
    significance: str = ""
    connections: list[str] = []


class Faction(BaseModel):
    name: str
    ideology: str = ""
    power_structure: str = ""
    goals: str = ""
    allies: list[str] = []
    enemies: list[str] = []


class WorldRule(BaseModel):
    domain: str
    description: str
    constraints: str = ""
    exceptions: list[str] = []


class WorldDesignResult(BaseModel):
    world_name: str = ""
    logline: str = ""
    locations: list[Location] = []
    factions: list[Faction] = []
    rules: list[WorldRule] = []
    timeline: list[dict] = []
    pending_choices: list[dict] = []
