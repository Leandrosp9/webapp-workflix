from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.system import build_readiness_response
from app.db.health import DatabaseProbe, probe_database

operational_router = APIRouter(include_in_schema=True)


@operational_router.get(
    "/health",
    summary="Process liveness",
    description="Confirms that the API process can serve requests without exposing dependencies.",
    tags=["Operations"],
)
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "workflix-api"}


@operational_router.get(
    "/ready",
    summary="Application readiness",
    description="Checks whether the API can reach dependencies required to serve traffic.",
    tags=["Operations"],
)
async def ready(probe: Annotated[DatabaseProbe, Depends(probe_database)]):
    return build_readiness_response(probe)
