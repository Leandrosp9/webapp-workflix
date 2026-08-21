from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.db.health import DatabaseProbe, probe_database

router = APIRouter(prefix="/system", tags=["System"])


class HealthResponse(BaseModel):
    status: Literal["healthy"]
    service: str
    version: str
    environment: str


class DependencyStatus(BaseModel):
    database: Literal["available", "unavailable"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    dependencies: DependencyStatus


def build_readiness_response(probe: DatabaseProbe) -> JSONResponse:
    is_ready = probe.database_available
    payload = ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        dependencies=DependencyStatus(
            database="available" if is_ready else "unavailable",
        ),
    )
    return JSONResponse(
        content=payload.model_dump(),
        status_code=status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Read public application health",
)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        service="workflix-api",
        version=settings.app_version,
        environment=settings.app_env,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse, "description": "A dependency is unavailable."}},
    summary="Read application readiness",
)
async def ready(
    probe: Annotated[DatabaseProbe, Depends(probe_database)],
) -> JSONResponse:
    return build_readiness_response(probe)
