"""Project, board, and task schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.user import UserRead


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    key: str = Field(min_length=1, max_length=16, pattern=r"^[A-Za-z0-9_-]+$")
    description: str | None = None
    due_date: datetime | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    due_date: datetime | None = None
    is_archived: bool | None = None


class ProjectRead(ORMModel):
    id: int
    name: str
    key: str
    description: str | None
    owner_id: int
    is_archived: bool
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime


class BoardColumnCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    color: str | None = None


class BoardColumnUpdate(BaseModel):
    name: str | None = None
    position: int | None = None
    color: str | None = None


class BoardColumnRead(ORMModel):
    id: int
    board_id: int
    name: str
    position: int
    color: str | None


class BoardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    columns: list[BoardColumnCreate] = []


class BoardRead(ORMModel):
    id: int
    project_id: int
    name: str
    position: int
    columns: list[BoardColumnRead]


class TaskCreate(BaseModel):
    board_id: int
    column_id: int | None = None
    parent_id: int | None = None
    assignee_id: int | None = None
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    priority: str = "medium"
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    column_id: int | None = None
    assignee_id: int | None = None
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    position: int | None = None
    due_date: datetime | None = None
    version: int | None = None


class TaskRead(ORMModel):
    id: int
    project_id: int
    column_id: int | None
    parent_id: int | None
    assignee_id: int | None
    creator_id: int
    title: str
    description: str | None
    status: str
    priority: str
    position: int
    due_date: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime
    assignee: UserRead | None = None
    creator: UserRead


class TaskCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class TaskCommentRead(ORMModel):
    id: int
    task_id: int
    author_id: int
    body: str
    created_at: datetime
    author: UserRead


class ProjectMemberRead(ORMModel):
    id: int
    project_id: int
    user_id: int
    role: str


class SubtaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    assignee_id: int | None = None
    priority: str = "medium"

class ActivityRead(ORMModel):
    id: int
    project_id: int | None
    actor_id: int | None
    action: str
    target_type: str
    target_id: str
    metadata_json: str | None
    created_at: datetime