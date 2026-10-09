"""Notification service: persistence, real-time fan-out, and channel dispatch."""
from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.notification import Notification
from app.models.user import User
from app.realtime.manager import manager


async def notify(
    db: AsyncSession,
    user_id: int,
    title: str,
    *,
    body: str | None = None,
    actor_id: int | None = None,
    type_: str = "info",
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        actor_id=actor_id,
        title=title,
        body=body,
        type=type_,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    await manager.publish(
        "notification.created",
        {
            "user_id": user_id,
            "id": notification.id,
            "title": notification.title,
            "type": notification.type,
        },
    )

    await _dispatch_channels(db, user_id, title, body or title)
    return notification


async def _dispatch_channels(db: AsyncSession, user_id: int, title: str, body: str) -> None:
    if not settings.smtp_host and not settings.wecom_agent_id:
        return
    user = await db.get(User, user_id)
    if user is None:
        return

    if settings.smtp_host and user.email and not user.email.endswith("@wecom.local"):
        await _send_task("app.tasks.jobs.send_email", [user.email, title, body])

    if settings.wecom_agent_id and user.wecom_userid:
        await _send_task("app.tasks.jobs.send_wecom", [user.wecom_userid, f"{title}\n{body}"])


async def _send_task(name: str, args: list) -> None:
    try:
        from app.tasks.celery_app import celery_app

        await asyncio.to_thread(celery_app.send_task, name, args=args)
    except Exception:
        # Broker outage must not break the request; in-app notification is still delivered.
        return
