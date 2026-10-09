"""Admin endpoints: settings, audit, upgrade status."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_superuser, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.models.org import SystemSetting
from app.models.system import AuditLog
from app.models.user import User
from app.schemas.common import Page

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/settings")
async def get_settings(
    _: User = Depends(require_permission("settings.manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = (await db.scalars(select(SystemSetting))).all()
    return {row.key: row.value for row in rows}


@router.put("/settings/{key}")
async def set_setting(
    key: str,
    value: str,
    _: User = Depends(require_permission("settings.manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await db.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if row is None:
        row = SystemSetting(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    await db.commit()
    return {"key": key, "value": value}


@router.get("/audit", response_model=Page)
async def list_audit(
    page: int = 1,
    page_size: int = 50,
    _: User = Depends(require_permission("audit.read")),
    db: AsyncSession = Depends(get_db),
) -> Page:
    total = await db.scalar(select(func.count()).select_from(AuditLog))
    offset = (page - 1) * page_size
    rows = (await db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size))).all()
    items = [{
        "id": row.id,
        "actor_id": row.actor_id,
        "action": row.action,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "ip_address": row.ip_address,
        "created_at": row.created_at,
    } for row in rows]
    return Page(total=total or 0, page=page, page_size=page_size, items=items)


@router.get("/upgrade")
async def upgrade_status(_: User = Depends(get_current_superuser)) -> dict:
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "version": "0.1.0",
        "status": "healthy",
    }
