"""User and auth schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = None
    locale: str | None = None
    avatar_url: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class UserRead(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    avatar_url: str | None = None
    locale: str
    is_active: bool
    is_superuser: bool
    totp_enabled: bool
    wecom_userid: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    role_slugs: list[str] = []
    permission_codes: list[str] = []


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TOTPSetup(BaseModel):
    secret: str
    otpauth_uri: str


class TOTPEnable(BaseModel):
    code: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)
