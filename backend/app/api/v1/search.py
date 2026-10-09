"""Global search endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import ValidationError
from app.db.session import get_db
from app.models.document import Document
from app.models.project import Project, Task
from app.models.user import User

router = APIRouter(tags=["search"])


@router.get("/search")
async def search(
    q: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    q = q.strip()
    if not q:
        raise ValidationError("q is required")

    projects = (await db.scalars(select(Project).where(Project.name.contains(q) | Project.key.contains(q)).limit(10))).all()
    tasks = (await db.scalars(select(Task).where(Task.title.contains(q)).limit(20))).all()
    documents = (await db.scalars(select(Document).where(Document.title.contains(q)).limit(20))).all()

    return {
        "projects": [{"id": p.id, "name": p.name, "key": p.key} for p in projects],
        "tasks": [{"id": t.id, "project_id": t.project_id, "title": t.title, "status": t.status} for t in tasks],
        "documents": [{"id": d.id, "project_id": d.project_id, "title": d.title} for d in documents],
    }
