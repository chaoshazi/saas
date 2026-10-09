"""Public system configuration endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.services.seed import ADMIN_EMAIL, ADMIN_PASSWORD, DEMO_PASSWORD, DEMO_USERS

router = APIRouter(tags=["system"])


@router.get("/system/config")
async def system_config(db: AsyncSession = Depends(get_db)) -> dict:
    config = {
        "app_name": settings.app_name,
        "version": "0.1.0",
        "app_env": settings.app_env,
        "registration_open": True,
        "sso": {"wecom_enabled": bool(settings.wecom_corp_id)},
        "payments": {
            "alipay_enabled": bool(settings.alipay_app_id),
            "wechat_enabled": bool(settings.wechat_mch_id),
        },
        "totp_issuer": settings.totp_issuer,
        "demo": None,
    }

    # Advertise demo credentials when explicitly enabled, or in development once
    # the seeded demo administrator actually exists.
    if settings.seed_demo or settings.app_env == "development":
        exists = await db.scalar(select(User.id).where(User.email == ADMIN_EMAIL))
        if exists is not None or settings.seed_demo:
            config["demo"] = {
                "admin_email": ADMIN_EMAIL,
                "admin_password": ADMIN_PASSWORD,
                "demo_password": DEMO_PASSWORD,
                "demo_emails": [email for email, *_ in DEMO_USERS if email != ADMIN_EMAIL],
            }
    return config
