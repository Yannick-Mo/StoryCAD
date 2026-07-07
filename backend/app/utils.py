import uuid
from datetime import datetime
from typing import Any, Optional, TypeVar
from pydantic import BaseModel, Field


T = TypeVar("T")


def row_to_dict(obj: Any) -> dict:
    if obj is None:
        return {}
    d = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, uuid.UUID):
            d[col.name] = str(val)
        elif isinstance(val, datetime):
            d[col.name] = val.isoformat()
        else:
            d[col.name] = val
    return d


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    size: int
