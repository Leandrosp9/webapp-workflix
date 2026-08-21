import hashlib
from contextlib import suppress
from pathlib import PurePath
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import (
    Document,
    DocumentStatus,
    DocumentVersion,
    Quiz,
    Role,
    Training,
    TrainingAssignment,
    TrainingStatus,
    TrainingType,
    User,
)
from app.rag.queue import DocumentJobQueue
from app.schemas.trainings import DocumentVersionResponse, TrainingResponse
from app.services.trainings import TrainingService
from app.storage import (
    ObjectNotFoundError,
    ObjectStorage,
    StorageError,
    StoredObject,
    get_object_storage,
)


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        storage: ObjectStorage | None = None,
        queue: DocumentJobQueue | None = None,
    ) -> None:
        self._session = session
        self._storage = storage or get_object_storage()
        self._queue = queue or DocumentJobQueue()

    async def _authorized_training(
        self, training_id: UUID, company_id: UUID, user: User
    ) -> Training:
        statement = select(Training).where(
            Training.id == training_id,
            Training.company_id == company_id,
        )
        if user.role == Role.EMPLOYEE:
            statement = statement.join(
                TrainingAssignment,
                TrainingAssignment.training_id == Training.id,
            ).where(
                TrainingAssignment.company_id == company_id,
                TrainingAssignment.employee_id == user.id,
                Training.status == TrainingStatus.PUBLISHED,
            )
        training = await self._session.scalar(statement)
        if training is None:
            raise AppError(
                code="TRAINING_NOT_FOUND", message="Training not found.", status_code=404
            )
        return training

    async def upload_version(
        self,
        *,
        training_id: UUID,
        company_id: UUID,
        creator_id: UUID,
        upload: UploadFile,
    ) -> TrainingResponse:
        training = await self._session.scalar(
            select(Training)
            .where(
                Training.id == training_id,
                Training.company_id == company_id,
            )
            .with_for_update()
        )
        if training is None:
            raise AppError(
                code="TRAINING_NOT_FOUND", message="Training not found.", status_code=404
            )
        if upload.content_type != "application/pdf":
            raise AppError(
                code="INVALID_PDF", message="Only PDF files are accepted.", status_code=415
            )

        settings = get_settings()
        maximum_bytes = settings.max_upload_size_mb * 1024 * 1024
        data = await upload.read(maximum_bytes + 1)
        if len(data) > maximum_bytes:
            raise AppError(
                code="FILE_TOO_LARGE", message="The PDF exceeds the upload limit.", status_code=413
            )
        if not data.startswith(b"%PDF-"):
            raise AppError(
                code="INVALID_PDF", message="The uploaded file is not a valid PDF.", status_code=415
            )

        document = await self._session.scalar(
            select(Document)
            .where(Document.training_id == training_id, Document.company_id == company_id)
            .with_for_update()
        )
        if document is None:
            document = Document(
                company_id=company_id,
                training_id=training_id,
                title=training.title,
                created_by=creator_id,
            )
            self._session.add(document)
            await self._session.flush()
        else:
            document.title = training.title

        latest_number = await self._session.scalar(
            select(func.max(DocumentVersion.version_number)).where(
                DocumentVersion.document_id == document.id
            )
        )
        version_id = uuid4()
        object_key = f"companies/{company_id}/documents/{document.id}/versions/{version_id}.pdf"
        try:
            await self._storage.put(object_key, data, content_type="application/pdf")
        except StorageError as exc:
            await self._session.rollback()
            raise AppError(
                code="STORAGE_UNAVAILABLE",
                message="The document storage service is temporarily unavailable.",
                status_code=503,
            ) from exc

        filename = PurePath((upload.filename or "document.pdf").replace("\\", "/")).name
        version = DocumentVersion(
            id=version_id,
            company_id=company_id,
            document_id=document.id,
            version_number=int(latest_number or 0) + 1,
            object_key=object_key,
            original_filename=filename[:255] or "document.pdf",
            content_type="application/pdf",
            size_bytes=len(data),
            checksum=hashlib.sha256(data).hexdigest(),
            status=DocumentStatus.UPLOADED,
            created_by=creator_id,
        )
        self._session.add(version)
        training.pdf_path = object_key
        training.type = TrainingType.PDF
        try:
            await self._session.flush()
            await self._queue.enqueue(self._session, version.id, company_id=company_id)
            await self._session.commit()
            await self._session.refresh(version)
            await self._session.refresh(training)
        except Exception:
            await self._session.rollback()
            with suppress(StorageError):
                await self._storage.delete(object_key)
            raise

        has_quiz = bool(
            await self._session.scalar(
                select(Quiz.id).where(
                    Quiz.training_id == training.id,
                    Quiz.company_id == company_id,
                )
            )
        )
        response = TrainingService._response(training, has_quiz=has_quiz)
        return response.model_copy(
            update={"document_version": DocumentVersionResponse.model_validate(version)}
        )

    async def latest_version(
        self, *, training_id: UUID, company_id: UUID, user: User
    ) -> DocumentVersionResponse:
        await self._authorized_training(training_id, company_id, user)
        version = await self._session.scalar(
            select(DocumentVersion)
            .join(Document, Document.id == DocumentVersion.document_id)
            .where(
                Document.training_id == training_id,
                Document.company_id == company_id,
                DocumentVersion.company_id == company_id,
            )
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )
        if version is None:
            raise AppError(
                code="DOCUMENT_NOT_FOUND", message="Document not found.", status_code=404
            )
        return DocumentVersionResponse.model_validate(version)

    async def list_versions(
        self, *, training_id: UUID, company_id: UUID
    ) -> list[DocumentVersionResponse]:
        training = await self._session.scalar(
            select(Training.id).where(Training.id == training_id, Training.company_id == company_id)
        )
        if training is None:
            raise AppError(
                code="TRAINING_NOT_FOUND", message="Training not found.", status_code=404
            )
        versions = (
            await self._session.scalars(
                select(DocumentVersion)
                .join(Document, Document.id == DocumentVersion.document_id)
                .where(
                    Document.training_id == training_id,
                    Document.company_id == company_id,
                    DocumentVersion.company_id == company_id,
                )
                .order_by(DocumentVersion.version_number.desc())
            )
        ).all()
        return [DocumentVersionResponse.model_validate(version) for version in versions]

    async def latest_model_for_admin(
        self, *, training_id: UUID, company_id: UUID
    ) -> DocumentVersion:
        version = await self._session.scalar(
            select(DocumentVersion)
            .join(Document, Document.id == DocumentVersion.document_id)
            .join(Training, Training.id == Document.training_id)
            .where(
                Training.id == training_id,
                Training.company_id == company_id,
                Document.company_id == company_id,
                DocumentVersion.company_id == company_id,
            )
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )
        if version is None:
            raise AppError(
                code="DOCUMENT_NOT_FOUND", message="Document not found.", status_code=404
            )
        return version

    async def pdf_object(self, *, training_id: UUID, company_id: UUID, user: User) -> StoredObject:
        training = await self._authorized_training(training_id, company_id, user)
        version = await self._session.scalar(
            select(DocumentVersion)
            .join(Document, Document.id == DocumentVersion.document_id)
            .where(
                Document.training_id == training_id,
                Document.company_id == company_id,
                DocumentVersion.company_id == company_id,
            )
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )
        object_key = version.object_key if version else training.pdf_path
        if not object_key:
            raise AppError(code="PDF_NOT_FOUND", message="PDF not found.", status_code=404)
        try:
            return await self._storage.get(object_key)
        except ObjectNotFoundError as exc:
            raise AppError(code="PDF_NOT_FOUND", message="PDF not found.", status_code=404) from exc
        except StorageError as exc:
            raise AppError(
                code="STORAGE_UNAVAILABLE",
                message="The document storage service is temporarily unavailable.",
                status_code=503,
            ) from exc
