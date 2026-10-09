"""Task, comment, and attachment endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.db.session import get_db
from app.models.project import Board, BoardColumn, Task, TaskAttachment, TaskComment
from app.models.user import User
from app.realtime.manager import manager
from app.schemas.attachment import TaskAttachmentRead
from app.schemas.project import SubtaskCreate, TaskCommentCreate, TaskCommentRead, TaskCreate, TaskRead, TaskUpdate
from app.services.activities import record_activity
from app.services.notifications import notify
from app.storage import get_storage

router = APIRouter(tags=["tasks"])


async def _get_task(db: AsyncSession, task_id: int) -> Task:
    task = await db.scalar(
        select(Task)
        .where(Task.id == task_id)
        .options(selectinload(Task.assignee), selectinload(Task.creator))
    )
    if task is None:
        raise NotFoundError("Task not found")
    return task


async def _publish_task(task_id: int, project_id: int) -> None:
    await manager.publish("task.updated", {"project_id": project_id, "task_id": task_id})


@router.get("/tasks", response_model=list[TaskRead])
async def list_tasks(
    project_id: int,
    column_id: int | None = None,
    assignee_id: int | None = None,
    q: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskRead]:
    query = (
        select(Task)
        .where(Task.project_id == project_id)
        .options(selectinload(Task.assignee), selectinload(Task.creator))
        .order_by(Task.position, Task.id)
    )
    if column_id is not None:
        query = query.where(Task.column_id == column_id)
    if assignee_id is not None:
        query = query.where(Task.assignee_id == assignee_id)
    if q:
        query = query.where(Task.title.contains(q))
    tasks = (await db.scalars(query)).all()
    return [TaskRead.model_validate(task) for task in tasks]


@router.post("/tasks", response_model=TaskRead, status_code=201)
async def create_task(
    payload: TaskCreate,
    user: User = Depends(require_permission("task.create")),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    board = await db.get(Board, payload.board_id)
    if board is None:
        raise NotFoundError("Board not found")
    column = None
    if payload.column_id is not None:
        column = await db.get(BoardColumn, payload.column_id)
        if column is None or column.board_id != board.id:
            raise ValidationError("Column does not belong to this board")
    task = Task(
        project_id=board.project_id,
        column_id=payload.column_id,
        parent_id=payload.parent_id,
        assignee_id=payload.assignee_id,
        creator_id=user.id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_date=payload.due_date,
    )
    db.add(task)
    await db.commit()
    task = await _get_task(db, task.id)
    await _publish_task(task.id, task.project_id)
    await record_activity(db, project_id=task.project_id, actor_id=user.id, action="task.create", target_type="task", target_id=task.id)
    if task.assignee_id and task.assignee_id != user.id:
        await notify(
            db, task.assignee_id, f"New task assigned: {task.title}",
            actor_id=user.id, type_="task", resource_type="task", resource_id=str(task.id),
        )
    return TaskRead.model_validate(task)


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    return TaskRead.model_validate(await _get_task(db, task_id))


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    user: User = Depends(require_permission("task.update")),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    task = await _get_task(db, task_id)
    if payload.version is not None and payload.version != task.version:
        raise ConflictError("Task was modified concurrently; refresh and retry")
    previous_assignee = task.assignee_id
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field != "version":
            setattr(task, field, value)
    task.version += 1
    await db.commit()
    task = await _get_task(db, task.id)
    await _publish_task(task.id, task.project_id)
    if task.assignee_id and task.assignee_id != previous_assignee and task.assignee_id != user.id:
        await notify(
            db, task.assignee_id, f"Task assigned to you: {task.title}",
            actor_id=user.id, type_="task", resource_type="task", resource_id=str(task.id),
        )
    return TaskRead.model_validate(task)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    user: User = Depends(require_permission("task.delete")),
    db: AsyncSession = Depends(get_db),
) -> None:
    task = await _get_task(db, task_id)
    project_id = task.project_id
    await db.delete(task)
    await db.commit()
    await _publish_task(0, project_id)


@router.get("/tasks/{task_id}/comments", response_model=list[TaskCommentRead])
async def list_comments(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskCommentRead]:
    await _get_task(db, task_id)
    comments = (await db.scalars(
        select(TaskComment).where(TaskComment.task_id == task_id).options(selectinload(TaskComment.author)).order_by(TaskComment.created_at)
    )).all()
    return [TaskCommentRead.model_validate(comment) for comment in comments]


@router.post("/tasks/{task_id}/comments", response_model=TaskCommentRead, status_code=201)
async def create_comment(
    task_id: int,
    payload: TaskCommentCreate,
    user: User = Depends(require_permission("task.update")),
    db: AsyncSession = Depends(get_db),
) -> TaskCommentRead:
    task = await _get_task(db, task_id)
    comment = TaskComment(task_id=task.id, author_id=user.id, body=payload.body)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    comment = await db.scalar(
        select(TaskComment).where(TaskComment.id == comment.id).options(selectinload(TaskComment.author))
    )
    await _publish_task(task.id, task.project_id)
    await record_activity(db, project_id=task.project_id, actor_id=user.id, action="task.comment", target_type="task", target_id=task.id)
    if task.creator_id != user.id:
        await notify(
            db, task.creator_id, f"New comment on {task.title}",
            actor_id=user.id, type_="comment", resource_type="task", resource_id=str(task.id),
        )
    return TaskCommentRead.model_validate(comment)


@router.post("/tasks/{task_id}/attachments", response_model=TaskAttachmentRead, status_code=201)
async def upload_attachment(
    task_id: int,
    file: UploadFile = File(...),
    user: User = Depends(require_permission("task.update")),
    db: AsyncSession = Depends(get_db),
) -> TaskAttachmentRead:
    task = await _get_task(db, task_id)
    data = await file.read()
    if not data:
        raise ValidationError("Empty file")
    key = f"attachments/{task.project_id}/{task_id}/{file.filename}"
    storage = get_storage()
    await storage.put(key, data, file.content_type)
    attachment = TaskAttachment(
        task_id=task.id,
        uploader_id=user.id,
        filename=file.filename or "file",
        content_type=file.content_type,
        size=len(data),
        storage_key=key,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    return TaskAttachmentRead.model_validate(attachment)


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    attachment = await db.get(TaskAttachment, attachment_id)
    if attachment is None:
        raise NotFoundError("Attachment not found")
    storage = get_storage()
    data = await storage.get(attachment.storage_key)
    if data is None:
        raise NotFoundError("Attachment data missing")
    return Response(
        content=data,
        media_type=attachment.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{attachment.filename}"'},
    )

@router.get("/tasks/{task_id}/subtasks", response_model=list[TaskRead])
async def list_subtasks(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskRead]:
    await _get_task(db, task_id)
    tasks = (await db.scalars(
        select(Task).where(Task.parent_id == task_id).options(selectinload(Task.assignee), selectinload(Task.creator)).order_by(Task.id)
    )).all()
    return [TaskRead.model_validate(task) for task in tasks]


@router.post("/tasks/{task_id}/subtasks", response_model=TaskRead, status_code=201)
async def create_subtask(
    task_id: int,
    payload: SubtaskCreate,
    user: User = Depends(require_permission("task.create")),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    parent = await _get_task(db, task_id)
    task = Task(
        project_id=parent.project_id,
        parent_id=parent.id,
        assignee_id=payload.assignee_id,
        creator_id=user.id,
        title=payload.title,
        priority=payload.priority,
    )
    db.add(task)
    await db.commit()
    task = await _get_task(db, task.id)
    await record_activity(db, project_id=task.project_id, actor_id=user.id, action="subtask.create", target_type="task", target_id=task.id)
    return TaskRead.model_validate(task)
