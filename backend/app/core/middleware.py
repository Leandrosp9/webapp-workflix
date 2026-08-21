import logging
import re
import time
from contextvars import ContextVar, Token
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_request_id_context: ContextVar[str] = ContextVar("request_id", default="system")


def get_request_id() -> str:
    return _request_id_context.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        supplied_request_id = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = (
            supplied_request_id if _SAFE_REQUEST_ID.fullmatch(supplied_request_id) else str(uuid4())
        )
        token: Token[str] = _request_id_context.set(request_id)
        started_at = time.perf_counter()
        response: Response | None = None
        logger = logging.getLogger(__name__)

        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            status_code = response.status_code if response is not None else 500
            logger.info(
                "http_request_completed",
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status": status_code,
                    "duration_ms": duration_ms,
                },
            )
            if response is not None:
                response.headers[REQUEST_ID_HEADER] = request_id
            _request_id_context.reset(token)
