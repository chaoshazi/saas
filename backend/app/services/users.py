"""User-oriented service helpers."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import Role, User


async def user_to_read_data(db: AsyncSession, user: User) -> dict:
    # Ensure roles/permissions are loaded, then build a serializable view.
    if "roles" not in user.__dict__:
        loaded = await load_user_full(db, user.id)
        user = loaded or user
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "locale": user.locale,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "totp_enabled": user.totp_enabled,
        "wecom_userid": user.wecom_userid,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "role_slugs": [role.slug for role in user.roles],
        "permission_codes": sorted(user.permission_codes),
    }


async def load_user_full(db: AsyncSession, user_id: int) -> User | None:
    from app.api.deps import load_user_full as _load

    return await _load(db, user_id)
