"""Activity stream service."""
from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Activity


async def record_activity(
    db: AsyncSession,
    *,
    project_id: int | None,
    actor_id: int | None,
    action: str,
    target_type: str,
    target_id: str | int,
    metadata: dict | None = None,
) -> Activity:
    entry = Activity(
        project_id=project_id,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        metadata_json=json.dumps(metadata, ensure_ascii=False, default=str) if metadata else None,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
