from enum import Enum
from pydantic import BaseModel


class ExportFormat(str, Enum):
    JSON = "json"
    MARKDOWN = "markdown"


class ExportRequest(BaseModel):
    format: ExportFormat = ExportFormat.JSON
    include_analysis: bool = True
    include_characters: bool = True
    include_world: bool = True
    include_story: bool = True
    include_validation: bool = True


class ExportResult(BaseModel):
    content: str
    filename: str
    mime_type: str
