"""Rate limiting for login and the endpoints that cost money (tutor, TTS).

There are two backends behind one interface:

- MemoryRateLimiter keeps counts in this process. Fine for one container
  or local development, but on Vercel every function instance would have
  its own counts, so the limit wouldn't really hold.
- RedisRateLimiter keeps counts in Redis through Upstash's REST API, so all
  instances share them. It talks HTTP rather than the Redis protocol, which
  means no connections to manage from serverless functions.

If Redis can't be reached the limiter lets the request through. A Redis
blip shouldn't lock learners out of the app; the paid APIs have their own
spending limits as a second line of defence.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from functools import lru_cache
from threading import Lock
from typing import Protocol

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)


class RateLimiter(Protocol):
    async def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool: ...


class MemoryRateLimiter:
    """Sliding window, in process memory."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    async def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


class RedisRateLimiter:
    """Fixed window counter: INCR a key per window, let it expire after."""

    def __init__(self, url: str, token: str, client: httpx.AsyncClient | None = None) -> None:
        self._url = url.rstrip("/") + "/pipeline"
        self._headers = {"Authorization": f"Bearer {token}"}
        self._client = client or httpx.AsyncClient(timeout=2.0)

    async def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        window = int(time.time() // window_seconds)
        redis_key = f"lexilearn:rl:{key}:{window}"
        commands = [["INCR", redis_key], ["EXPIRE", redis_key, str(window_seconds + 1)]]
        try:
            response = await self._client.post(self._url, json=commands, headers=self._headers)
            response.raise_for_status()
            count = int(response.json()[0]["result"])
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            log.warning("rate limiter unavailable, letting the request through")
            return True
        return count <= limit


memory_limiter = MemoryRateLimiter()


@lru_cache
def get_rate_limiter() -> RateLimiter:
    settings = get_settings()
    if settings.redis_rest_url and settings.redis_rest_token:
        return RedisRateLimiter(settings.redis_rest_url, settings.redis_rest_token.get_secret_value())
    return memory_limiter
