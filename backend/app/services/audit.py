"""Audit log service."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import AuditLog


async def audit(
    db: AsyncSession,
    *,
    actor_id: int | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    detail: dict | None = None,
) -> AuditLog:
    import json

    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        detail_json=json.dumps(detail, ensure_ascii=False, default=str) if detail else None,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
