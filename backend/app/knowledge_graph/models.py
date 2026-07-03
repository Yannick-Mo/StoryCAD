from enum import Enum
from pydantic import BaseModel


class EntityType(str, Enum):
    CHARACTER = "Character"
    EVENT = "Event"
    CHAPTER = "Chapter"
    ACT = "Act"
    FORESHADOW = "Foreshadow"
    THEME = "Theme"
    SETTING = "Setting"


class RelationType(str, Enum):
    ACTED_IN = "ACTED_IN"
    CAUSES = "CAUSES"
    HAS_FORESHAW = "HAS_FORESHAW"
    RESOLVED_AT = "RESOLVED_AT"
    RELATES_TO = "RELATES_TO"
    BELONGS_TO = "BELONGS_TO"
    PART_OF = "PART_OF"
    THEMATIZES = "THEMATIZES"
    SET_IN = "SET_IN"


class GraphEntity(BaseModel):
    id: str
    type: EntityType
    properties: dict


class GraphRelation(BaseModel):
    source_id: str
    target_id: str
    type: RelationType
    properties: dict = {}
