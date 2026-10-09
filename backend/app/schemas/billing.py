"""Billing and license schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class PlanRead(ORMModel):
    id: int
    code: str
    name: str
    interval: str
    amount_cents: int
    currency: str
    max_users: int
    max_projects: int
    max_storage_gb: int
    is_active: bool


class OrderCreate(BaseModel):
    plan_code: str
    channel: str = "alipay"


class OrderRead(ORMModel):
    id: int
    order_no: str
    plan_id: int
    amount_cents: int
    currency: str
    status: str
    channel: str
    paid_at: datetime | None
    created_at: datetime


class SubscriptionRead(ORMModel):
    id: int
    plan_id: int
    status: str
    current_period_start: datetime
    current_period_end: datetime
    auto_renew: bool


class LicenseActivate(BaseModel):
    key: str
    fingerprint: str | None = None


class LicenseRead(ORMModel):
    id: int
    key: str
    status: str
    plan_code: str
    issued_to: str | None
    issued_at: datetime | None
    expires_at: datetime | None
    last_checked_at: datetime | None
