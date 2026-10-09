"""Label schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LabelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    color: str | None = None


class LabelRead(ORMModel):
    id: int
    project_id: int
    name: str
    color: str | None
    created_at: datetime
