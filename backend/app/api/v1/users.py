"""User administration endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_superuser, get_current_user, require_permission
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import Role, User
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.users import user_to_read_data
from app.storage import get_storage

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Page)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    _: User = Depends(require_permission("user.manage")),
    db: AsyncSession = Depends(get_db),
) -> Page:
    offset = (page - 1) * page_size
    total = await db.scalar(select(func.count()).select_from(User))
    users = (await db.scalars(select(User).order_by(User.id).offset(offset).limit(page_size))).all()
    items = [await user_to_read_data(db, user) for user in users]
    return Page(total=total or 0, page=page, page_size=page_size, items=items)


@router.post("", response_model=UserRead, status_code=201)
async def create_user(
    payload: UserCreate,
    _: User = Depends(require_permission("user.manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise ConflictError("Email already registered")
    user = User(email=payload.email, full_name=payload.full_name, hashed_password=hash_password(payload.password))
    role = await db.scalar(select(Role).where(Role.slug == "member"))
    if role is not None:
        user.roles.append(role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return await user_to_read_data(db, user)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    _: User = Depends(require_permission("user.manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return await user_to_read_data(db, user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    _: User = Depends(require_permission("user.manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return await user_to_read_data(db, user)


@router.delete("/{user_id}", status_code=204)
async def deactivate_user(
    user_id: int,
    _: User = Depends(require_permission("user.manage")),
    db: AsyncSession = Depends(get_db),
) -> None:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    user.is_active = False
    user.token_version += 1
    await db.commit()


@router.post("/{user_id}/superuser", status_code=204)
async def grant_superuser(
    user_id: int,
    _: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> None:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    user.is_superuser = True
    await db.commit()

@router.put("/users/me/avatar", response_model=UserRead)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await file.read()
    key = f"avatars/{user.id}/{file.filename or 'avatar'}"
    storage = get_storage()
    await storage.put(key, data, file.content_type)
    user.avatar_url = f"/api/v1/users/{user.id}/avatar"
    await db.commit()
    await db.refresh(user)
    return await user_to_read_data(db, user)


@router.get("/users/{user_id}/avatar")
async def get_avatar(
    user_id: int,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    user = await db.get(User, user_id)
    if user is None or not user.avatar_url:
        raise NotFoundError("Avatar not found")
    storage = get_storage()
    key = f"avatars/{user.id}/{user.avatar_url.rsplit('/', 1)[-1]}"
    data = await storage.get(key)
    if data is None:
        raise NotFoundError("Avatar data missing")
    return Response(content=data, media_type="image/png")
