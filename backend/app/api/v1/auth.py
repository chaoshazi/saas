"""Authentication endpoints: register, login, refresh, TOTP, WeCom."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import ConflictError, PermissionDeniedError, UnauthorizedError
from app.core.security import (
    build_totp_uri, create_access_token, create_refresh_token, create_token,
    decode_token, generate_totp_secret, hash_password, verify_password, verify_totp,
)
from app.db.session import get_db
from app.integrations import wecom
from app.models.user import Role, User
from app.schemas.system import PasswordReset, PasswordResetRequest
from app.schemas.user import (
    LoginRequest, PasswordChange, RefreshRequest, TOTPEnable, TOTPSetup,
    TokenPair, UserCreate, UserRead,
)
from app.services.users import user_to_read_data

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_pair(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id, user.token_version),
        refresh_token=create_refresh_token(user.id, user.token_version),
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def _assign_member(db: AsyncSession, user: User) -> None:
    role = await db.scalar(select(Role).where(Role.slug == "member"))
    if role is not None:
        user.roles.append(role)


@router.post("/register", response_model=TokenPair, status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> TokenPair:
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise ConflictError("Email already registered")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    await _assign_member(db, user)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _token_pair(user)


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None or user.hashed_password is None or not verify_password(payload.password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    if user.totp_enabled:
        if not payload.totp_code or not verify_totp(user.totp_secret or "", payload.totp_code):
            raise UnauthorizedError("Invalid two-factor code")
    user.set_login()
    await db.commit()
    return _token_pair(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        claims = decode_token(payload.refresh_token, "refresh")
    except Exception as exc:  # noqa: BLE001
        raise UnauthorizedError("Invalid refresh token") from exc
    user = await db.get(User, int(claims["sub"]))
    if user is None or not user.is_active or int(claims.get("ver", 0)) != user.token_version:
        raise UnauthorizedError("Invalid refresh token")
    return _token_pair(user)


@router.post("/logout", status_code=204)
async def logout(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    user.token_version += 1
    await db.commit()


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    return await user_to_read_data(db, user)


@router.get("/totp/setup", response_model=TOTPSetup)
async def totp_setup(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TOTPSetup:
    if not user.totp_secret:
        user.totp_secret = generate_totp_secret()
        await db.commit()
    return TOTPSetup(secret=user.totp_secret, otpauth_uri=build_totp_uri(user.totp_secret, user.email))


@router.post("/totp/enable", status_code=204)
async def totp_enable(
    payload: TOTPEnable, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    if not user.totp_secret or not verify_totp(user.totp_secret, payload.code):
        raise PermissionDeniedError("Invalid two-factor code")
    user.totp_enabled = True
    await db.commit()


@router.post("/password/change", status_code=204)
async def change_password(
    payload: PasswordChange, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    if user.hashed_password is None or not verify_password(payload.old_password, user.hashed_password):
        raise UnauthorizedError("Old password is incorrect")
    user.hashed_password = hash_password(payload.new_password)
    user.token_version += 1
    await db.commit()


@router.get("/wecom/url")
async def wecom_login_url(state: str, redirect_uri: str) -> dict:
    return {"url": wecom.build_oauth_url(state=state, redirect_uri=redirect_uri)}


@router.get("/wecom/callback", response_model=TokenPair)
async def wecom_callback(code: str, db: AsyncSession = Depends(get_db)) -> TokenPair:
    profile = await wecom.exchange_code(code)
    userid = profile.get("userid")
    if not userid:
        raise UnauthorizedError("WeCom login failed")
    user = await db.scalar(select(User).where(User.wecom_userid == userid))
    if user is None:
        user = User(
            email=f"{userid}@wecom.local",
            full_name=userid,
            wecom_userid=userid,
            hashed_password=None,
        )
        await _assign_member(db, user)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    user.set_login()
    await db.commit()
    return _token_pair(user)


@router.post("/password/reset-request")
async def request_password_reset(payload: PasswordResetRequest, db: AsyncSession = Depends(get_db)) -> dict:
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None:
        return {"message": "If that email exists, a reset link has been sent."}
    token = create_token(user.email, "reset", timedelta(minutes=30))
    reset_link = f"/reset-password?token={token}"
    if settings.smtp_host:
        from app.services.email import send_email
        await send_email(user.email, "Reset your password", f"Use this link to reset your password: {reset_link}")
        return {"message": "If that email exists, a reset link has been sent."}
    return {"message": "Reset token generated", "token": token, "reset_link": reset_link}


@router.post("/password/reset", status_code=204)
async def reset_password(payload: PasswordReset, db: AsyncSession = Depends(get_db)) -> None:
    try:
        claims = decode_token(payload.token, "reset")
    except Exception as exc:  # noqa: BLE001
        raise UnauthorizedError("Invalid or expired reset token") from exc
    user = await db.scalar(select(User).where(User.email == claims["sub"]))
    if user is None:
        raise UnauthorizedError("Invalid reset token")
    user.hashed_password = hash_password(payload.new_password)
    user.token_version += 1
    await db.commit()
