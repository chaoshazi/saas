"""FastAPI dependencies: database session, current user, permissions."""
from __future__ import annotations

import jwt as pyjwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import PermissionDeniedError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import Role, User

bearer_scheme = HTTPBearer(auto_error=False)


async def load_user_full(db: AsyncSession, user_id: int) -> User | None:
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError()
    try:
        payload = decode_token(credentials.credentials, "access")
    except pyjwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired access token") from exc
    user = await load_user_full(db, int(payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("User is inactive or missing")
    if int(payload.get("ver", 0)) != user.token_version:
        raise UnauthorizedError("Token has been revoked")
    return user


async def get_current_superuser(user: User = Depends(get_current_user)) -> User:
    if not user.is_superuser:
        raise PermissionDeniedError("Superuser privileges required")
    return user


def require_permission(code: str):
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.is_superuser or code in user.permission_codes:
            return user
        raise PermissionDeniedError(f"Missing permission: {code}")
    return dependency
