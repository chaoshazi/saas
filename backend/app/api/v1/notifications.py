"""Notification endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.notification import Notification, NotificationPreference
from app.models.user import User
from app.schemas.notification import NotificationRead
from app.schemas.system import NotificationPreferenceRead, NotificationPreferenceUpdate
from app.schemas.common import Page

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=Page)
async def list_notifications(
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Page:
    query = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    total = await db.scalar(
        select(func.count()).select_from(Notification).where(Notification.user_id == user.id)
    )
    offset = (page - 1) * page_size
    notifications = (await db.scalars(query.order_by(Notification.created_at.desc()).offset(offset).limit(page_size))).all()
    return Page(total=total or 0, page=page, page_size=page_size, items=[NotificationRead.model_validate(n) for n in notifications])


@router.patch("/notifications/{notification_id}", response_model=NotificationRead)
async def mark_read(
    notification_id: int,
    is_read: bool = True,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationRead:
    notification = await db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise NotFoundError("Notification not found")
    notification.is_read = is_read
    await db.commit()
    await db.refresh(notification)
    return NotificationRead.model_validate(notification)


@router.post("/notifications/read-all", status_code=204)
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await db.execute(update(Notification).where(Notification.user_id == user.id).values(is_read=True))
    await db.commit()

@router.get("/notifications/preferences", response_model=list[NotificationPreferenceRead])
async def list_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationPreferenceRead]:
    rows = (await db.scalars(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id).order_by(NotificationPreference.channel, NotificationPreference.event_type)
    )).all()
    return [NotificationPreferenceRead.model_validate(row) for row in rows]


@router.put("/notifications/preferences", response_model=NotificationPreferenceRead)
async def upsert_preference(
    payload: NotificationPreferenceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferenceRead:
    row = await db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user.id,
            NotificationPreference.channel == payload.channel,
            NotificationPreference.event_type == payload.event_type,
        )
    )
    if row is None:
        row = NotificationPreference(user_id=user.id, channel=payload.channel, event_type=payload.event_type, enabled=payload.enabled)
        db.add(row)
    else:
        row.enabled = payload.enabled
    await db.commit()
    await db.refresh(row)
    return NotificationPreferenceRead.model_validate(row)
