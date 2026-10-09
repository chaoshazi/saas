"""Notification preference and password reset schemas."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class NotificationPreferenceRead(ORMModel):
    id: int
    user_id: int
    channel: str
    event_type: str
    enabled: bool


class NotificationPreferenceUpdate(BaseModel):
    channel: str
    event_type: str
    enabled: bool


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
