"""Real-time WebSocket endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import Role, User
from app.realtime.manager import manager

router = APIRouter(tags=["realtime"])


async def _authenticate(db: AsyncSession, token: str) -> User:
    import jwt as pyjwt

    try:
        payload = decode_token(token, "access")
    except pyjwt.PyJWTError as exc:
        raise UnauthorizedError() from exc
    user = await db.scalar(
        select(User).where(User.id == int(payload["sub"])).options(selectinload(User.roles).selectinload(Role.permissions))
    )
    if user is None or not user.is_active:
        raise UnauthorizedError()
    return user


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = "") -> None:
    if not token:
        token = websocket.query_params.get("token", "")
    db = None
    try:
        async for session in get_db():
            db = session
            break
        user = await _authenticate(db, token)
    except Exception:
        await websocket.close(code=1008)
        return

    await manager.connect(user.id, websocket)
    try:
        while True:
            # Keep the connection alive and await messages (heartbeats).
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(user.id, websocket)
    except Exception:
        manager.disconnect(user.id, websocket)
