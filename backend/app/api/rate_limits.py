from hashlib import sha256
from typing import Annotated

from fastapi import Depends, Request, Response, status

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.rate_limit import RateLimitBackendError, RateLimiter, get_rate_limiter

RateLimiterDependency = Annotated[RateLimiter, Depends(get_rate_limiter)]


class RateLimit:
    def __init__(self, scope: str, limit_setting: str, *, window_seconds: int = 60) -> None:
        self._scope = scope
        self._limit_setting = limit_setting
        self._window_seconds = window_seconds

    async def __call__(
        self,
        request: Request,
        response: Response,
        limiter: RateLimiterDependency,
    ) -> None:
        settings = get_settings()
        client_ip = request.client.host if request.client else "unknown"
        if settings.trust_proxy_headers and (forwarded := request.headers.get("x-forwarded-for")):
            # The staging topology has one trusted Nginx hop. Its observed address is
            # appended to any client-supplied chain, so only the rightmost value is trusted.
            client_ip = forwarded.rsplit(",", maxsplit=1)[-1].strip()[:128] or client_ip
        identity = sha256(client_ip.encode("utf-8")).hexdigest()
        limit = int(getattr(settings, self._limit_setting))
        try:
            result = await limiter.consume(
                f"workflix:rate-limit:{self._scope}:{identity}",
                limit=limit,
                window_seconds=self._window_seconds,
            )
        except RateLimitBackendError as exc:
            raise AppError(
                code="RATE_LIMIT_UNAVAILABLE",
                message="Request protection is temporarily unavailable.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        if not result.allowed:
            raise AppError(
                code="RATE_LIMITED",
                message="Too many requests. Try again later.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(result.retry_after)},
            )


login_rate_limit = RateLimit("auth-login", "rate_limit_login_per_minute")
refresh_rate_limit = RateLimit("auth-refresh", "rate_limit_refresh_per_minute")
ai_rate_limit = RateLimit("ai-generation", "rate_limit_ai_per_minute")

LoginRateLimit = Annotated[None, Depends(login_rate_limit)]
RefreshRateLimit = Annotated[None, Depends(refresh_rate_limit)]
AIRateLimit = Annotated[None, Depends(ai_rate_limit)]
