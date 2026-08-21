import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.config import get_settings
from app.models import (
    DocumentJobStatus,
    DocumentProcessingJob,
    DocumentStatus,
    DocumentVersion,
    Role,
)
from app.rag.queue import DocumentJobQueue
from app.worker import DocumentWorker
from sqlalchemy import select

from conftest import ApiContext, create_company_user, login
from test_documents_rag import pdf_bytes
from test_trainings import auth, training_payload


def _upload_document(api: ApiContext, tmp_path) -> UUID:
    get_settings().upload_directory = tmp_path
    _company, admin = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Queue Corp",
            email="admin@queue.example.com",
            role=Role.ADMIN,
        )
    )
    token = login(api.client, admin.email)["access_token"]
    training_id = api.client.post(
        "/api/v1/trainings",
        json=training_payload(status="PUBLISHED"),
        headers=auth(token),
    ).json()["id"]
    uploaded = api.client.post(
        f"/api/v1/trainings/{training_id}/pdf",
        files={"file": ("durable.pdf", pdf_bytes("Durable queue"), "application/pdf")},
        headers=auth(token),
    )
    assert uploaded.status_code == 200
    retry = api.client.post(
        f"/api/v1/trainings/{training_id}/document/process", headers=auth(token)
    )
    assert retry.status_code == 409
    assert retry.json()["error"]["code"] == "DOCUMENT_PROCESSING"
    return UUID(uploaded.json()["document_version"]["id"])


def test_queue_claim_retry_dead_letter_and_manual_requeue(api: ApiContext, tmp_path) -> None:
    version_id = _upload_document(api, tmp_path)

    async def exercise() -> tuple[DocumentJobStatus, int, DocumentJobStatus, int]:
        queue = DocumentJobQueue(
            lease_seconds=30,
            max_attempts=3,
            retry_base_seconds=1,
            retry_max_seconds=4,
        )
        async with api.sessions() as session:
            initial = await session.scalar(
                select(DocumentProcessingJob).where(
                    DocumentProcessingJob.document_version_id == version_id
                )
            )
            assert initial is not None
            assert initial.status == DocumentJobStatus.PENDING
            assert await queue.enqueue(session, version_id) is False

            first = await queue.claim(session, "worker-one")
            assert first is not None
            await session.commit()
            assert await queue.claim(session, "worker-two") is None
            first_status = await queue.fail(
                session,
                first,
                error_code="STORAGE_UNAVAILABLE",
                retryable=True,
            )
            assert first_status == DocumentJobStatus.RETRYING
            job = await session.get(DocumentProcessingJob, first.id)
            assert job is not None
            job.available_at = datetime.now(UTC) - timedelta(seconds=1)
            await session.commit()

            second = await queue.claim(session, "worker-two")
            assert second is not None
            assert second.attempt == 2
            second_status = await queue.fail(
                session,
                second,
                error_code="PDF_PASSWORD_PROTECTED",
                retryable=False,
            )
            await session.commit()
            assert second_status == DocumentJobStatus.DEAD_LETTER

            assert await queue.enqueue(session, version_id) is True
            await session.commit()
            job = await session.get(DocumentProcessingJob, first.id)
            assert job is not None
            return first_status, second.attempt, job.status, job.attempts

    first_status, second_attempt, final_status, attempts = asyncio.run(exercise())
    assert first_status == DocumentJobStatus.RETRYING
    assert second_attempt == 2
    assert final_status == DocumentJobStatus.PENDING
    assert attempts == 0


def test_worker_consumes_persisted_job_and_completes_extraction(
    api: ApiContext, tmp_path, monkeypatch
) -> None:
    version_id = _upload_document(api, tmp_path)
    monkeypatch.setattr("app.worker.SessionFactory", api.sessions)

    async def exercise() -> tuple[DocumentStatus, DocumentJobStatus, int]:
        worker = DocumentWorker(worker_id="test-worker")
        assert await worker.run_once() is True
        async with api.sessions() as session:
            version = await session.get(DocumentVersion, version_id)
            job = await session.scalar(
                select(DocumentProcessingJob).where(
                    DocumentProcessingJob.document_version_id == version_id
                )
            )
            assert version is not None
            assert job is not None
            return version.status, job.status, job.attempts

    version_status, job_status, attempts = asyncio.run(exercise())
    assert version_status == DocumentStatus.EXTRACTED
    assert job_status == DocumentJobStatus.COMPLETED
    assert attempts == 1


def test_expired_final_lease_moves_job_and_document_to_dead_letter(
    api: ApiContext, tmp_path
) -> None:
    version_id = _upload_document(api, tmp_path)

    async def exercise() -> tuple[DocumentJobStatus, DocumentStatus, str | None]:
        queue = DocumentJobQueue(lease_seconds=30, max_attempts=1)
        async with api.sessions() as session:
            job = await session.scalar(
                select(DocumentProcessingJob).where(
                    DocumentProcessingJob.document_version_id == version_id
                )
            )
            assert job is not None
            job.max_attempts = 1
            await session.commit()
            claim = await queue.claim(session, "crashed-worker")
            assert claim is not None
            await session.commit()
            job = await session.get(DocumentProcessingJob, claim.id)
            assert job is not None
            job.leased_until = datetime.now(UTC) - timedelta(seconds=1)
            await session.commit()

            assert await queue.claim(session, "recovery-worker") is None
            await session.commit()
            version = await session.get(DocumentVersion, version_id)
            job = await session.get(DocumentProcessingJob, claim.id)
            assert version is not None
            assert job is not None
            return job.status, version.status, job.last_error_code

    job_status, version_status, error_code = asyncio.run(exercise())
    assert job_status == DocumentJobStatus.DEAD_LETTER
    assert version_status == DocumentStatus.FAILED
    assert error_code == "WORKER_LEASE_EXPIRED"
