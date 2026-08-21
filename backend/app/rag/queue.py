from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import (
    DocumentJobStatus,
    DocumentProcessingJob,
    DocumentStatus,
    DocumentVersion,
)


@dataclass(frozen=True)
class DocumentJobClaim:
    id: UUID
    document_version_id: UUID
    attempt: int
    max_attempts: int
    worker_id: str


class DocumentJobQueue:
    """PostgreSQL-backed queue with leased, at-least-once delivery."""

    def __init__(
        self,
        *,
        lease_seconds: int | None = None,
        max_attempts: int | None = None,
        retry_base_seconds: int | None = None,
        retry_max_seconds: int | None = None,
    ) -> None:
        settings = get_settings()
        self.lease_seconds = lease_seconds or settings.document_job_lease_seconds
        self.max_attempts = max_attempts or settings.document_job_max_attempts
        self.retry_base_seconds = retry_base_seconds or settings.document_job_retry_base_seconds
        self.retry_max_seconds = retry_max_seconds or settings.document_job_retry_max_seconds

    async def enqueue(
        self,
        session: AsyncSession,
        version_id: UUID,
        *,
        company_id: UUID | None = None,
    ) -> bool:
        job = await session.scalar(
            select(DocumentProcessingJob)
            .where(DocumentProcessingJob.document_version_id == version_id)
            .with_for_update()
        )
        if job is not None and job.status in {
            DocumentJobStatus.PENDING,
            DocumentJobStatus.RUNNING,
            DocumentJobStatus.RETRYING,
        }:
            return False

        now = datetime.now(UTC)
        if job is None:
            if company_id is None:
                company_id = await session.scalar(
                    select(DocumentVersion.company_id).where(DocumentVersion.id == version_id)
                )
            if company_id is None:
                raise ValueError("Cannot enqueue a missing document version")
            session.add(
                DocumentProcessingJob(
                    company_id=company_id,
                    document_version_id=version_id,
                    status=DocumentJobStatus.PENDING,
                    attempts=0,
                    max_attempts=self.max_attempts,
                    available_at=now,
                )
            )
        else:
            job.status = DocumentJobStatus.PENDING
            job.attempts = 0
            job.max_attempts = self.max_attempts
            job.available_at = now
            job.leased_until = None
            job.worker_id = None
            job.last_error_code = None
            job.completed_at = None
        await session.flush()
        return True

    async def claim(self, session: AsyncSession, worker_id: str) -> DocumentJobClaim | None:
        now = datetime.now(UTC)
        await self._dead_letter_exhausted_leases(session, now)
        job = await session.scalar(
            select(DocumentProcessingJob)
            .where(
                DocumentProcessingJob.attempts < DocumentProcessingJob.max_attempts,
                or_(
                    and_(
                        DocumentProcessingJob.status.in_(
                            (DocumentJobStatus.PENDING, DocumentJobStatus.RETRYING)
                        ),
                        DocumentProcessingJob.available_at <= now,
                    ),
                    and_(
                        DocumentProcessingJob.status == DocumentJobStatus.RUNNING,
                        DocumentProcessingJob.leased_until <= now,
                    ),
                ),
            )
            .order_by(DocumentProcessingJob.available_at, DocumentProcessingJob.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        job.status = DocumentJobStatus.RUNNING
        job.attempts += 1
        job.worker_id = worker_id
        job.leased_until = now + timedelta(seconds=self.lease_seconds)
        job.last_error_code = None
        await session.flush()
        return DocumentJobClaim(
            id=job.id,
            document_version_id=job.document_version_id,
            attempt=job.attempts,
            max_attempts=job.max_attempts,
            worker_id=worker_id,
        )

    async def heartbeat(self, session: AsyncSession, claim: DocumentJobClaim) -> bool:
        result = await session.execute(
            update(DocumentProcessingJob)
            .where(
                DocumentProcessingJob.id == claim.id,
                DocumentProcessingJob.status == DocumentJobStatus.RUNNING,
                DocumentProcessingJob.worker_id == claim.worker_id,
            )
            .values(leased_until=datetime.now(UTC) + timedelta(seconds=self.lease_seconds))
        )
        return bool(result.rowcount)

    async def complete(self, session: AsyncSession, claim: DocumentJobClaim) -> bool:
        now = datetime.now(UTC)
        result = await session.execute(
            update(DocumentProcessingJob)
            .where(
                DocumentProcessingJob.id == claim.id,
                DocumentProcessingJob.status == DocumentJobStatus.RUNNING,
                DocumentProcessingJob.worker_id == claim.worker_id,
            )
            .values(
                status=DocumentJobStatus.COMPLETED,
                completed_at=now,
                leased_until=None,
                worker_id=None,
                last_error_code=None,
            )
        )
        return bool(result.rowcount)

    async def fail(
        self,
        session: AsyncSession,
        claim: DocumentJobClaim,
        *,
        error_code: str,
        retryable: bool,
    ) -> DocumentJobStatus | None:
        job = await session.scalar(
            select(DocumentProcessingJob)
            .where(
                DocumentProcessingJob.id == claim.id,
                DocumentProcessingJob.status == DocumentJobStatus.RUNNING,
                DocumentProcessingJob.worker_id == claim.worker_id,
            )
            .with_for_update()
        )
        if job is None:
            return None

        now = datetime.now(UTC)
        should_retry = retryable and job.attempts < job.max_attempts
        if should_retry:
            delay = min(
                self.retry_base_seconds * (2 ** max(job.attempts - 1, 0)),
                self.retry_max_seconds,
            )
            job.status = DocumentJobStatus.RETRYING
            job.available_at = now + timedelta(seconds=delay)
            job.completed_at = None
        else:
            job.status = DocumentJobStatus.DEAD_LETTER
            job.completed_at = now
        job.leased_until = None
        job.worker_id = None
        job.last_error_code = error_code[:80]
        await session.flush()
        return job.status

    async def _dead_letter_exhausted_leases(self, session: AsyncSession, now: datetime) -> None:
        jobs = (
            await session.scalars(
                select(DocumentProcessingJob)
                .where(
                    DocumentProcessingJob.status == DocumentJobStatus.RUNNING,
                    DocumentProcessingJob.leased_until <= now,
                    DocumentProcessingJob.attempts >= DocumentProcessingJob.max_attempts,
                )
                .with_for_update(skip_locked=True)
                .limit(20)
            )
        ).all()
        for job in jobs:
            job.status = DocumentJobStatus.DEAD_LETTER
            job.leased_until = None
            job.worker_id = None
            job.last_error_code = "WORKER_LEASE_EXPIRED"
            job.completed_at = now
            version = await session.get(DocumentVersion, job.document_version_id)
            if version is not None and version.status != DocumentStatus.READY:
                version.status = DocumentStatus.FAILED
                version.error_code = "WORKER_LEASE_EXPIRED"
                version.processed_at = now


def get_document_job_queue() -> DocumentJobQueue:
    return DocumentJobQueue()


DocumentQueueDependency = Annotated[DocumentJobQueue, Depends(get_document_job_queue)]
