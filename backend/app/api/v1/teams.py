"""Team endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.db.session import get_db
from app.models.team import Team
from app.models.user import User
from app.schemas.team import TeamCreate, TeamRead, TeamUpdate

router = APIRouter(prefix="/teams", tags=["teams"])


async def _get_team(db: AsyncSession, team_id: int) -> Team:
    team = await db.scalar(
        select(Team).where(Team.id == team_id).options(selectinload(Team.owner), selectinload(Team.members))
    )
    if team is None:
        raise NotFoundError("Team not found")
    return team


@router.get("", response_model=list[TeamRead])
async def list_teams(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TeamRead]:
    teams = (await db.scalars(
        select(Team).options(selectinload(Team.owner), selectinload(Team.members)).order_by(Team.name)
    )).all()
    return [TeamRead.model_validate(team) for team in teams]


@router.post("", response_model=TeamRead, status_code=201)
async def create_team(
    payload: TeamCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TeamRead:
    team = Team(name=payload.name, description=payload.description, owner_id=user.id)
    team.members.append(user)
    db.add(team)
    await db.commit()
    await db.refresh(team)
    team = await _get_team(db, team.id)
    return TeamRead.model_validate(team)


@router.patch("/{team_id}", response_model=TeamRead)
async def update_team(
    team_id: int,
    payload: TeamUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TeamRead:
    team = await _get_team(db, team_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(team, field, value)
    await db.commit()
    await db.refresh(team)
    team = await _get_team(db, team.id)
    return TeamRead.model_validate(team)


@router.delete("/{team_id}", status_code=204)
async def delete_team(
    team_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    team = await _get_team(db, team_id)
    if team.owner_id != user.id and not user.is_superuser:
        raise PermissionDeniedError("Only the team owner can delete it")
    await db.delete(team)
    await db.commit()


@router.post("/{team_id}/members", response_model=TeamRead)
async def add_member(
    team_id: int,
    user_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TeamRead:
    team = await _get_team(db, team_id)
    member = await db.get(User, user_id)
    if member is None:
        raise NotFoundError("User not found")
    if member in team.members:
        raise ConflictError("User is already a team member")
    team.members.append(member)
    await db.commit()
    team = await _get_team(db, team.id)
    return TeamRead.model_validate(team)


@router.delete("/{team_id}/members/{user_id}", status_code=204)
async def remove_member(
    team_id: int,
    user_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    team = await _get_team(db, team_id)
    member = await db.get(User, user_id)
    if member is None:
        raise NotFoundError("User not found")
    if member in team.members:
        team.members.remove(member)
        await db.commit()
