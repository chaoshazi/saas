"""Label endpoints for projects and tasks."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import NotFoundError, ValidationError
from app.db.session import get_db
from app.models.label import Label
from app.models.project import Project, Task
from app.models.user import User
from app.schemas.label import LabelCreate, LabelRead

router = APIRouter(tags=["labels"])


async def _get_task_with_labels(db: AsyncSession, task_id: int) -> Task:
    task = await db.scalar(select(Task).where(Task.id == task_id).options(selectinload(Task.labels)))
    if task is None:
        raise NotFoundError("Task not found")
    return task


@router.get("/projects/{project_id}/labels", response_model=list[LabelRead])
async def list_labels(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LabelRead]:
    labels = (await db.scalars(select(Label).where(Label.project_id == project_id).order_by(Label.name))).all()
    return [LabelRead.model_validate(label) for label in labels]


@router.post("/projects/{project_id}/labels", response_model=LabelRead, status_code=201)
async def create_label(
    project_id: int,
    payload: LabelCreate,
    user: User = Depends(require_permission("project.update")),
    db: AsyncSession = Depends(get_db),
) -> LabelRead:
    project = await db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")
    label = Label(project_id=project_id, name=payload.name, color=payload.color)
    db.add(label)
    await db.commit()
    await db.refresh(label)
    return LabelRead.model_validate(label)


@router.get("/tasks/{task_id}/labels", response_model=list[LabelRead])
async def task_labels(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LabelRead]:
    task = await _get_task_with_labels(db, task_id)
    return [LabelRead.model_validate(label) for label in task.labels]


@router.post("/tasks/{task_id}/labels", response_model=LabelRead)
async def assign_label(
    task_id: int,
    label_id: int,
    user: User = Depends(require_permission("task.update")),
    db: AsyncSession = Depends(get_db),
) -> LabelRead:
    task = await _get_task_with_labels(db, task_id)
    label = await db.get(Label, label_id)
    if label is None or label.project_id != task.project_id:
        raise ValidationError("Label does not belong to this task's project")
    if label not in task.labels:
        task.labels.append(label)
        await db.commit()
    return LabelRead.model_validate(label)


@router.delete("/tasks/{task_id}/labels/{label_id}", status_code=204)
async def remove_label(
    task_id: int,
    label_id: int,
    user: User = Depends(require_permission("task.update")),
    db: AsyncSession = Depends(get_db),
) -> None:
    task = await _get_task_with_labels(db, task_id)
    label = await db.get(Label, label_id)
    if label is not None and label in task.labels:
        task.labels.remove(label)
        await db.commit()
