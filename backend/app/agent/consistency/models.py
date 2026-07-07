from datetime import datetime, timezone
from pydantic import BaseModel


class ConsistencyIssue(BaseModel):
    check_type: str
    severity: str
    entity_type: str
    entity_id: str | None = None
    description: str
    suggestion: str | None = None
    chapter_id: str | None = None
    scene_id: str | None = None


class ConsistencyReport(BaseModel):
    project_id: str
    issues: list[ConsistencyIssue]
    summary: str
    timestamp: datetime | None = None
