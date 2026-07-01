from pydantic import BaseModel
from typing import List, Optional

class WorldRule(BaseModel):
    category: str
    description: str
    limitation: str

class WorldRules(BaseModel):
    rules: List[WorldRule]
    history: str
    forbidden_events: List[str]

class CharacterProfile(BaseModel):
    name: str
    desire_topology: dict
    bottom_line: str
    vulnerability: str
    language_genes: List[str]
    relationships: dict
    growth_arc: str

class EventNode(BaseModel):
    id: str
    description: str
    emotion_value: int  # 0-100

class CausalityEdge(BaseModel):
    source: str
    target: str
    type: str  # "necessary", "possible", "indirect"

class PlotGraph(BaseModel):
    nodes: List[EventNode]
    edges: List[CausalityEdge]

class Branch(BaseModel):
    divergence_point: str
    paths: List[dict]
    convergence_point: Optional[str]

class Foreshadow(BaseModel):
    id: str
    planted_at: str
    content: str
    status: str  # "pending", "recycled", "abandoned"
    planned_recycle_interval: Optional[str]

class NarrativeSkeleton(BaseModel):
    world_rules: WorldRules
    characters: List[CharacterProfile]
    graph: PlotGraph
    branches: List[Branch]
    foreshadows: List[Foreshadow]
