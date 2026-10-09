"""Project, board, column, and membership endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.db.session import get_db
from app.models.project import Activity, Board, BoardColumn, Project, ProjectMember
from app.models.user import User
from app.schemas.common import Page
from app.schemas.project import (
    BoardColumnCreate, BoardColumnRead, BoardColumnUpdate, BoardCreate, BoardRead,
    ProjectCreate, ProjectMemberRead, ProjectRead, ProjectUpdate,
)
from app.services.activities import record_activity
from app.services.audit import audit

router = APIRouter(tags=["projects"])


async def _get_project(db: AsyncSession, project_id: int) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")
    return project


async def _get_board(db: AsyncSession, board_id: int) -> Board:
    board = await db.scalar(
        select(Board).where(Board.id == board_id).options(selectinload(Board.columns))
    )
    if board is None:
        raise NotFoundError("Board not found")
    return board


@router.get("/projects", response_model=Page)
async def list_projects(
    page: int = 1,
    page_size: int = 20,
    archived: bool | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Page:
    count_query = select(func.count()).select_from(Project)
    query = select(Project)
    if archived is not None:
        count_query = count_query.where(Project.is_archived == archived)
        query = query.where(Project.is_archived == archived)
    total = await db.scalar(count_query)
    offset = (page - 1) * page_size
    projects = (await db.scalars(query.order_by(Project.updated_at.desc()).offset(offset).limit(page_size))).all()
    return Page(total=total or 0, page=page, page_size=page_size, items=[ProjectRead.model_validate(p) for p in projects])


@router.post("/projects", response_model=ProjectRead, status_code=201)
async def create_project(
    payload: ProjectCreate,
    user: User = Depends(require_permission("project.create")),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    exists = await db.scalar(select(Project).where(Project.key == payload.key))
    if exists is not None:
        raise ConflictError("Project key already in use")
    project = Project(
        name=payload.name,
        key=payload.key,
        description=payload.description,
        due_date=payload.due_date,
        owner_id=user.id,
    )
    db.add(project)
    await db.flush()

    board = Board(project_id=project.id, name="Main Board", position=0)
    db.add(board)
    await db.flush()
    for position, name in enumerate(["To Do", "In Progress", "Done"]):
        db.add(BoardColumn(board_id=board.id, name=name, position=position))

    db.add(ProjectMember(project_id=project.id, user_id=user.id, role="admin"))
    await db.commit()
    await db.refresh(project)
    await audit(db, actor_id=user.id, action="project.create", resource_type="project", resource_id=str(project.id))
    await record_activity(db, project_id=project.id, actor_id=user.id, action="project.create", target_type="project", target_id=project.id)
    return ProjectRead.model_validate(project)


@router.get("/projects/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    project = await _get_project(db, project_id)
    return ProjectRead.model_validate(project)


@router.patch("/projects/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    user: User = Depends(require_permission("project.update")),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    project = await _get_project(db, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return ProjectRead.model_validate(project)


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    user: User = Depends(require_permission("project.delete")),
    db: AsyncSession = Depends(get_db),
) -> None:
    project = await _get_project(db, project_id)
    if project.owner_id != user.id and not user.is_superuser:
        raise PermissionDeniedError("Only the project owner can delete it")
    await db.delete(project)
    await db.commit()


@router.get("/projects/{project_id}/boards", response_model=list[BoardRead])
async def list_boards(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BoardRead]:
    await _get_project(db, project_id)
    boards = (await db.scalars(
        select(Board).where(Board.project_id == project_id).options(selectinload(Board.columns)).order_by(Board.position)
    )).all()
    return [BoardRead.model_validate(board) for board in boards]


@router.post("/projects/{project_id}/boards", response_model=BoardRead, status_code=201)
async def create_board(
    project_id: int,
    payload: BoardCreate,
    user: User = Depends(require_permission("project.update")),
    db: AsyncSession = Depends(get_db),
) -> BoardRead:
    await _get_project(db, project_id)
    board = Board(project_id=project_id, name=payload.name)
    db.add(board)
    await db.flush()
    for position, column in enumerate(payload.columns):
        db.add(BoardColumn(board_id=board.id, name=column.name, color=column.color, position=position))
    await db.commit()
    board = await _get_board(db, board.id)
    return BoardRead.model_validate(board)


@router.post("/boards/{board_id}/columns", response_model=BoardColumnRead, status_code=201)
async def create_column(
    board_id: int,
    payload: BoardColumnCreate,
    user: User = Depends(require_permission("project.update")),
    db: AsyncSession = Depends(get_db),
) -> BoardColumnRead:
    await _get_board(db, board_id)
    max_pos = await db.scalar(select(BoardColumn.position).where(BoardColumn.board_id == board_id).order_by(BoardColumn.position.desc()).limit(1))
    column = BoardColumn(board_id=board_id, name=payload.name, color=payload.color, position=(max_pos or 0) + 1)
    db.add(column)
    await db.commit()
    await db.refresh(column)
    return BoardColumnRead.model_validate(column)


@router.patch("/columns/{column_id}", response_model=BoardColumnRead)
async def update_column(
    column_id: int,
    payload: BoardColumnUpdate,
    user: User = Depends(require_permission("project.update")),
    db: AsyncSession = Depends(get_db),
) -> BoardColumnRead:
    column = await db.get(BoardColumn, column_id)
    if column is None:
        raise NotFoundError("Column not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(column, field, value)
    await db.commit()
    await db.refresh(column)
    return BoardColumnRead.model_validate(column)


@router.delete("/columns/{column_id}", status_code=204)
async def delete_column(
    column_id: int,
    user: User = Depends(require_permission("project.update")),
    db: AsyncSession = Depends(get_db),
) -> None:
    column = await db.get(BoardColumn, column_id)
    if column is None:
        raise NotFoundError("Column not found")
    await db.delete(column)
    await db.commit()


@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberRead])
async def list_members(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectMemberRead]:
    await _get_project(db, project_id)
    members = (await db.scalars(select(ProjectMember).where(ProjectMember.project_id == project_id))).all()
    return [ProjectMemberRead.model_validate(m) for m in members]


@router.post("/projects/{project_id}/members", response_model=ProjectMemberRead, status_code=201)
async def add_member(
    project_id: int,
    user_id: int,
    role: str = "member",
    user: User = Depends(require_permission("project.update")),
    db: AsyncSession = Depends(get_db),
) -> ProjectMemberRead:
    await _get_project(db, project_id)
    member = await db.scalar(select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id))
    if member is not None:
        raise ConflictError("User is already a project member")
    member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return ProjectMemberRead.model_validate(member)

@router.patch("/projects/{project_id}/members/{member_id}", response_model=ProjectMemberRead)
async def update_member_role(
    project_id: int,
    member_id: int,
    role: str,
    user: User = Depends(require_permission("project.update")),
    db: AsyncSession = Depends(get_db),
) -> ProjectMemberRead:
    await _get_project(db, project_id)
    member = await db.get(ProjectMember, member_id)
    if member is None or member.project_id != project_id:
        raise NotFoundError("Member not found")
    member.role = role
    await db.commit()
    await db.refresh(member)
    return ProjectMemberRead.model_validate(member)


@router.delete("/projects/{project_id}/members/{member_id}", status_code=204)
async def remove_member(
    project_id: int,
    member_id: int,
    user: User = Depends(require_permission("project.update")),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _get_project(db, project_id)
    member = await db.get(ProjectMember, member_id)
    if member is not None and member.project_id == project_id:
        await db.delete(member)
        await db.commit()


@router.get("/projects/{project_id}/activities")
async def list_activities(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    await _get_project(db, project_id)
    rows = (await db.scalars(
        select(Activity).where(Activity.project_id == project_id).options(selectinload(Activity.actor)).order_by(Activity.created_at.desc()).limit(100)
    )).all()
    return [{
        "id": row.id,
        "actor_id": row.actor_id,
        "actor_name": row.actor.full_name if row.actor else None,
        "action": row.action,
        "target_type": row.target_type,
        "target_id": row.target_id,
        "created_at": row.created_at,
    } for row in rows]
