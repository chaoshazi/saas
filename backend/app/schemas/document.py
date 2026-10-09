"""Document schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.user import UserRead


class DocumentCreate(BaseModel):
    project_id: int | None = None
    title: str = Field(min_length=1, max_length=512)
    content: str | None = None


class DocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    change_note: str | None = None
    is_published: bool | None = None


class DocumentRead(ORMModel):
    id: int
    project_id: int | None
    creator_id: int
    title: str
    content: str | None
    is_published: bool
    version: int
    created_at: datetime
    updated_at: datetime
    creator: UserRead


class DocumentVersionRead(ORMModel):
    id: int
    document_id: int
    author_id: int
    version: int
    content: str | None
    change_note: str | None
    created_at: datetime
