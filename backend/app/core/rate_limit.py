import asyncio
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

REDIS_FIXED_WINDOW_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: int


class RateLimitBackendError(RuntimeError):
    """Raised when the distributed limiter cannot make a safe decision."""


class RateLimiter(Protocol):
    async def consume(self, key: str, *, limit: int, window_seconds: int) -> RateLimitResult: ...


class MemoryRateLimiter:
    def __init__(self) -> None:
        self._windows: dict[str, tuple[int, float]] = {}
        self._lock = asyncio.Lock()

    async def consume(self, key: str, *, limit: int, window_seconds: int) -> RateLimitResult:
        now = time.monotonic()
        async with self._lock:
            count, expires_at = self._windows.get(key, (0, now + window_seconds))
            if expires_at <= now:
                count, expires_at = 0, now + window_seconds
            count += 1
            self._windows[key] = (count, expires_at)
        retry_after = max(1, int(expires_at - now + 0.999))
        return RateLimitResult(
            allowed=count <= limit,
            remaining=max(limit - count, 0),
            retry_after=retry_after,
        )


class RedisRateLimiter:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def consume(self, key: str, *, limit: int, window_seconds: int) -> RateLimitResult:
        try:
            result = await self._client.eval(REDIS_FIXED_WINDOW_SCRIPT, 1, key, window_seconds)
            count, ttl = int(result[0]), max(int(result[1]), 1)
        except (RedisError, TypeError, ValueError, IndexError) as exc:
            raise RateLimitBackendError("The rate limit backend is unavailable.") from exc
        return RateLimitResult(
            allowed=count <= limit,
            remaining=max(limit - count, 0),
            retry_after=ttl,
        )


@lru_cache
def _build_rate_limiter(provider: str, redis_url: str) -> RateLimiter:
    if provider == "redis":
        return RedisRateLimiter(Redis.from_url(redis_url, decode_responses=True))
    return MemoryRateLimiter()


def get_rate_limiter() -> RateLimiter:
    settings = get_settings()
    return _build_rate_limiter(
        settings.rate_limit_provider,
        settings.redis_url.get_secret_value(),
    )
