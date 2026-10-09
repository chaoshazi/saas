"""Real-time WebSocket connection manager with optional Redis fan-out."""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

try:
    import redis.asyncio as aioredis
except Exception:  # pragma: no cover - redis optional at import time
    aioredis = None

from app.core.config import settings

REDIS_CHANNEL = "realtime"


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._redis = None
        self._listener_task: asyncio.Task | None = None

    async def _redis_client(self):
        if self._redis is None and aioredis is not None:
            try:
                self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
                await self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[user_id].append(websocket)
        self._ensure_listener()

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        connections = self._connections.get(user_id)
        if connections and websocket in connections:
            connections.remove(websocket)
        if not connections:
            self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, event: dict[str, Any]) -> None:
        message = json.dumps(event, ensure_ascii=False, default=str)
        dead: list[WebSocket] = []
        for websocket in list(self._connections.get(user_id, [])):
            try:
                await websocket.send_text(message)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(user_id, websocket)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        event = {"type": topic, "data": payload}
        # Local fan-out to connected clients in this process.
        user_id = payload.get("user_id")
        if user_id is not None:
            await self.send_to_user(int(user_id), event)
        else:
            for uid in list(self._connections.keys()):
                await self.send_to_user(uid, event)
        # Best-effort cross-process fan-out.
        try:
            client = await self._redis_client()
            if client is not None:
                await client.publish(REDIS_CHANNEL, json.dumps(event, default=str))
        except Exception:
            pass

    def _ensure_listener(self) -> None:
        if self._listener_task is None or self._listener_task.done():
            self._listener_task = asyncio.create_task(self._listen())

    async def _listen(self) -> None:
        client = await self._redis_client()
        if client is None:
            return
        try:
            pubsub = client.pubsub()
            await pubsub.subscribe(REDIS_CHANNEL)
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                try:
                    event = json.loads(message["data"])
                except (TypeError, json.JSONDecodeError):
                    continue
                uid = event.get("data", {}).get("user_id")
                if uid is not None:
                    await self.send_to_user(int(uid), event)
        except Exception:
            pass


manager = ConnectionManager()
