"""License activation and status endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.exceptions import ValidationError
from app.db.session import get_db
from app.models.system import License
from app.models.user import User
from app.schemas.billing import LicenseActivate, LicenseRead
from app.services.license import license_status, verify_license_key

router = APIRouter(tags=["license"])


@router.post("/license/activate", response_model=LicenseRead)
async def activate_license(
    payload: LicenseActivate,
    _: User = Depends(require_permission("settings.manage")),
    db: AsyncSession = Depends(get_db),
) -> LicenseRead:
    try:
        claims = verify_license_key(payload.key)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    status, expires_at = license_status(claims)
    existing = await db.scalar(select(License).order_by(License.id.desc()).limit(1))
    if existing is None:
        existing = License(key=payload.key)
        db.add(existing)
    else:
        existing.key = payload.key
    existing.status = status
    existing.plan_code = claims.get("plan_code", "free")
    existing.issued_to = claims.get("issued_to")
    existing.expires_at = expires_at
    await db.commit()
    await db.refresh(existing)
    return LicenseRead.model_validate(existing)


@router.get("/license/status", response_model=LicenseRead | None)
async def get_license_status(
    _: User = Depends(require_permission("settings.manage")),
    db: AsyncSession = Depends(get_db),
) -> LicenseRead | None:
    license_ = await db.scalar(select(License).order_by(License.id.desc()).limit(1))
    if license_ is None:
        return None
    return LicenseRead.model_validate(license_)
