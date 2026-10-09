"""Background jobs: email, WeCom push, subscription renewal."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.models.billing import Plan, Subscription
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run(coro):
    return asyncio.run(coro)


@celery_app.task(name="app.tasks.jobs.send_email")
def send_email(to_email: str, subject: str, body: str) -> None:
    from app.services.email import send_email as _send

    _run(_send(to_email, subject, body))


@celery_app.task(name="app.tasks.jobs.send_wecom")
def send_wecom(user_id: str, content: str) -> None:
    if not settings.wecom_agent_id:
        return
    from app.integrations.wecom import send_text

    _run(send_text(user_id, content))


@celery_app.task(name="app.tasks.jobs.renew_subscriptions")
def renew_subscriptions() -> int:
    from app.db.session import SessionLocal

    async def _renew() -> int:
        count = 0
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        horizon = now + timedelta(days=3)
        async with SessionLocal() as db:
            subscriptions = (await db.scalars(
                select(Subscription).where(
                    Subscription.status == "active",
                    Subscription.auto_renew.is_(True),
                    Subscription.current_period_end <= horizon,
                )
            )).all()
            for subscription in subscriptions:
                plan = await db.get(Plan, subscription.plan_id)
                if plan is None:
                    continue
                interval = timedelta(days=365 if plan.interval == "year" else 30)
                subscription.current_period_end += interval
                count += 1
            await db.commit()
        return count

    return _run(_renew())
