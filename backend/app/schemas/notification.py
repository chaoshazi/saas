"""Notification schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class NotificationRead(ORMModel):
    id: int
    user_id: int
    actor_id: int | None
    title: str
    body: str | None
    type: str
    resource_type: str | None
    resource_id: str | None
    is_read: bool
    created_at: datetime


class NotificationUpdate(BaseModel):
    is_read: bool | None = None
