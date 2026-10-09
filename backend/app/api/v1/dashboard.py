"""Dashboard statistics endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.notification import Notification
from app.models.project import Project, Task
from app.models.team import Team
from app.models.user import User

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/stats")
async def dashboard_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    projects = await db.scalar(select(func.count()).select_from(Project).where(Project.is_archived.is_(False)))
    tasks = await db.scalar(select(func.count()).select_from(Task))
    unread = await db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False)))
    users = await db.scalar(select(func.count()).select_from(User))
    teams = await db.scalar(select(func.count()).select_from(Team))
    return {
        "projects": projects or 0,
        "tasks": tasks or 0,
        "unread_notifications": unread or 0,
        "users": users or 0,
        "teams": teams or 0,
    }
