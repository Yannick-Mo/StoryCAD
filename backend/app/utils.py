import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


def _serialize_value(val: Any) -> Any:
    if isinstance(val, uuid.UUID):
        return str(val)
    if isinstance(val, datetime):
        return val.isoformat()
    return val


def row_to_dict(obj: Any) -> dict:
    if obj is None:
        return None
    try:
        if hasattr(obj, '__table__'):
            return {c.name: _serialize_value(getattr(obj, c.name)) for c in obj.__table__.columns}
        return dict(obj)
    except Exception:
        return dict(obj)


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    size: int
