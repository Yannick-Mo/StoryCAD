import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ProjectRef(BaseModel):
    project_id: uuid.UUID


class TimestampMixin(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
