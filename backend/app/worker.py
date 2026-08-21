from __future__ import annotations

import asyncio
import os
import signal
import socket
from contextlib import suppress
from uuid import uuid4

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import SessionFactory
from app.rag.jobs import (
    DocumentProcessingOutcome,
    DocumentProcessingService,
    build_embedding_provider,
)
from app.rag.queue import DocumentJobClaim, DocumentJobQueue
from app.storage import get_object_storage

logger = get_logger(__name__)


class DocumentWorker:
    def __init__(self, *, worker_id: str | None = None) -> None:
        settings = get_settings()
        self.worker_id = worker_id or (f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}")
        self.poll_seconds = settings.document_worker_poll_seconds
        self.heartbeat_seconds = settings.document_job_heartbeat_seconds
        self.queue = DocumentJobQueue()

    async def run(self, stop: asyncio.Event) -> None:
        logger.info("document_worker_started", extra={"worker_id": self.worker_id})
        while not stop.is_set():
            try:
                processed = await self.run_once()
            except Exception:
                logger.exception("document_worker_poll_failed", extra={"worker_id": self.worker_id})
                processed = False
            if not processed:
                with suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=self.poll_seconds)
        logger.info("document_worker_stopped", extra={"worker_id": self.worker_id})

    async def run_once(self) -> bool:
        async with SessionFactory() as session:
            claim = await self.queue.claim(session, self.worker_id)
            await session.commit()
        if claim is None:
            return False

        logger.info(
            "document_job_claimed",
            extra={
                "worker_id": self.worker_id,
                "job_id": str(claim.id),
                "version_id": str(claim.document_version_id),
                "attempt": claim.attempt,
            },
        )
        heartbeat = asyncio.create_task(self._heartbeat(claim))
        try:
            async with SessionFactory() as session:
                outcome = await DocumentProcessingService(
                    session,
                    storage=get_object_storage(),
                    embedding_provider=build_embedding_provider(),
                ).process(claim.document_version_id)
        except Exception:
            logger.exception(
                "document_job_unhandled_failure",
                extra={"job_id": str(claim.id), "worker_id": self.worker_id},
            )
            outcome = DocumentProcessingOutcome(
                completed=False,
                retryable=True,
                error_code="WORKER_PROCESSING_FAILED",
            )
        finally:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat

        async with SessionFactory() as session:
            if outcome.completed:
                updated = await self.queue.complete(session, claim)
                next_status = "COMPLETED"
            else:
                status = await self.queue.fail(
                    session,
                    claim,
                    error_code=outcome.error_code or "PROCESSING_FAILED",
                    retryable=outcome.retryable,
                )
                updated = status is not None
                next_status = status.value if status is not None else "LEASE_LOST"
            await session.commit()

        logger.info(
            "document_job_finished",
            extra={
                "worker_id": self.worker_id,
                "job_id": str(claim.id),
                "version_id": str(claim.document_version_id),
                "job_status": next_status,
                "lease_owned": updated,
                "error_code": outcome.error_code,
            },
        )
        return True

    async def _heartbeat(self, claim: DocumentJobClaim) -> None:
        while True:
            await asyncio.sleep(self.heartbeat_seconds)
            try:
                async with SessionFactory() as session:
                    renewed = await self.queue.heartbeat(session, claim)
                    await session.commit()
                if not renewed:
                    logger.warning(
                        "document_job_lease_lost",
                        extra={"job_id": str(claim.id), "worker_id": self.worker_id},
                    )
                    return
            except Exception:
                logger.exception(
                    "document_job_heartbeat_failed",
                    extra={"job_id": str(claim.id), "worker_id": self.worker_id},
                )


async def serve() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(signal_name, stop.set)
    await DocumentWorker().run(stop)


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()
