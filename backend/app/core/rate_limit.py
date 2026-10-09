"""Simple rate limiting backed by Redis with in-memory fallback."""
from __future__ import annotations

import time
from collections import defaultdict

try:
    import redis.asyncio as aioredis
except Exception:  # pragma: no cover
    aioredis = None

from app.core.config import settings


class RateLimiter:
    def __init__(self) -> None:
        self._memory: dict[str, list[float]] = defaultdict(list)
        self._redis = None

    async def _client(self):
        if self._redis is None and aioredis is not None:
            try:
                self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
                await self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    async def is_allowed(self, key: str) -> bool:
        limit = settings.rate_limit_requests
        window = settings.rate_limit_window_seconds
        try:
            client = await self._client()
            if client is not None:
                pipe = client.pipeline()
                pipe.incr(key)
                pipe.expire(key, window)
                count, _ = await pipe.execute()
                return int(count) <= limit
        except Exception:
            pass
        now = time.monotonic()
        bucket = [ts for ts in self._memory[key] if now - ts < window]
        if len(bucket) >= limit:
            self._memory[key] = bucket
            return False
        bucket.append(now)
        self._memory[key] = bucket
        return True


rate_limiter = RateLimiter()
