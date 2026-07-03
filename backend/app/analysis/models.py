from pydantic import BaseModel


class SixDimMetadata(BaseModel):
    core_high_concept: str = ""
    protagonist_identity: str = ""
    core_conflict: str = ""
    non_negotiable_events: list[str] = []
    tone_and_length: str = ""
    world_genre: str = ""
    main_characters: list[dict] = []
    core_relationships: list[dict] = []
    landmark_scenes: list[str] = []
    subplot_hints: list[str] = []
    style_details: str = ""


class MissingDiagnosis(BaseModel):
    field: str
    severity: str
    description: str
    suggestion: str = ""


class AnalysisResult(BaseModel):
    metadata: SixDimMetadata = SixDimMetadata()
    missing_diagnosis: list[MissingDiagnosis] = []
    raw_input: dict = {}
