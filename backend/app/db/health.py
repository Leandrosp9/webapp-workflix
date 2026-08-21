from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger
from app.db.session import engine

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DatabaseProbe:
    database_available: bool


async def probe_database() -> DatabaseProbe:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return DatabaseProbe(database_available=True)
    except SQLAlchemyError as exc:
        logger.warning("database_readiness_failed", extra={"error_type": type(exc).__name__})
        return DatabaseProbe(database_available=False)
