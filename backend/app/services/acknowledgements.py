from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import (
    Document,
    DocumentAcknowledgement,
    DocumentVersion,
    Training,
    TrainingAssignment,
    TrainingStatus,
    User,
)
from app.schemas.acknowledgements import (
    AdminAcknowledgementItem,
    AdminAcknowledgementSummary,
    DocumentAcknowledgementResponse,
    EmployeeAcknowledgementStatus,
)

ATTESTATION = "Confirmo que li e compreendi esta versão do documento."


class DocumentAcknowledgementService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def employee_status(
        self, *, training_id: UUID, company_id: UUID, employee_id: UUID
    ) -> EmployeeAcknowledgementStatus:
        _document, version = await self._latest_for_employee(
            training_id=training_id,
            company_id=company_id,
            employee_id=employee_id,
        )
        acknowledgement = await self._session.scalar(
            select(DocumentAcknowledgement).where(
                DocumentAcknowledgement.company_id == company_id,
                DocumentAcknowledgement.training_id == training_id,
                DocumentAcknowledgement.document_version_id == version.id,
                DocumentAcknowledgement.user_id == employee_id,
            )
        )
        return self._employee_response(version, acknowledgement)

    async def acknowledge(
        self,
        *,
        training_id: UUID,
        company_id: UUID,
        employee: User,
        document_version_id: UUID,
    ) -> EmployeeAcknowledgementStatus:
        await self._lock_employee_training(
            training_id=training_id,
            company_id=company_id,
            employee_id=employee.id,
        )
        document, version = await self._latest_for_employee(
            training_id=training_id,
            company_id=company_id,
            employee_id=employee.id,
            lock=True,
        )
        if version.id != document_version_id:
            raise AppError(
                code="DOCUMENT_VERSION_CHANGED",
                message="A new document version is available. Review it before acknowledging.",
                status_code=409,
            )
        existing = await self._session.scalar(
            select(DocumentAcknowledgement).where(
                DocumentAcknowledgement.user_id == employee.id,
                DocumentAcknowledgement.document_version_id == version.id,
            )
        )
        if existing is not None:
            return self._employee_response(version, existing)

        acknowledgement = DocumentAcknowledgement(
            company_id=company_id,
            training_id=training_id,
            document_id=document.id,
            document_version_id=version.id,
            user_id=employee.id,
            user_email=employee.email,
            user_full_name=employee.full_name,
            document_title=document.title,
            original_filename=version.original_filename,
            version_number=version.version_number,
            document_checksum=version.checksum,
            attestation=ATTESTATION,
        )
        version_id = version.id
        self._session.add(acknowledgement)
        try:
            await self._session.commit()
            await self._session.refresh(acknowledgement)
        except IntegrityError:
            await self._session.rollback()
            version = await self._session.get(DocumentVersion, version_id)
            if version is None:
                raise AppError(
                    code="DOCUMENT_NOT_FOUND", message="Document not found.", status_code=404
                ) from None
            acknowledgement = await self._session.scalar(
                select(DocumentAcknowledgement).where(
                    DocumentAcknowledgement.user_id == employee.id,
                    DocumentAcknowledgement.document_version_id == version_id,
                )
            )
            if acknowledgement is None:
                raise
        return self._employee_response(version, acknowledgement)

    async def _lock_employee_training(
        self, *, training_id: UUID, company_id: UUID, employee_id: UUID
    ) -> None:
        training = await self._session.scalar(
            select(Training)
            .join(
                TrainingAssignment,
                (TrainingAssignment.training_id == Training.id)
                & (TrainingAssignment.employee_id == employee_id)
                & (TrainingAssignment.company_id == company_id),
            )
            .where(
                Training.id == training_id,
                Training.company_id == company_id,
                Training.status == TrainingStatus.PUBLISHED,
            )
            .with_for_update()
        )
        if training is None:
            raise AppError(
                code="DOCUMENT_NOT_FOUND", message="Document not found.", status_code=404
            )

    async def admin_summary(
        self, *, training_id: UUID, company_id: UUID
    ) -> AdminAcknowledgementSummary:
        version = await self._latest_for_admin(training_id=training_id, company_id=company_id)
        total_assigned = int(
            await self._session.scalar(
                select(func.count(TrainingAssignment.id)).where(
                    TrainingAssignment.company_id == company_id,
                    TrainingAssignment.training_id == training_id,
                )
            )
            or 0
        )
        acknowledged_current = int(
            await self._session.scalar(
                select(func.count(DocumentAcknowledgement.id)).where(
                    DocumentAcknowledgement.company_id == company_id,
                    DocumentAcknowledgement.training_id == training_id,
                    DocumentAcknowledgement.document_version_id == version.id,
                )
            )
            or 0
        )
        acknowledgements = (
            await self._session.scalars(
                select(DocumentAcknowledgement)
                .where(
                    DocumentAcknowledgement.company_id == company_id,
                    DocumentAcknowledgement.training_id == training_id,
                )
                .order_by(DocumentAcknowledgement.acknowledged_at.desc())
            )
        ).all()
        history = [
            AdminAcknowledgementItem(
                **DocumentAcknowledgementResponse.model_validate(item).model_dump(),
                is_current=item.document_version_id == version.id,
            )
            for item in acknowledgements
        ]
        return AdminAcknowledgementSummary(
            document_version_id=version.id,
            version_number=version.version_number,
            total_assigned=total_assigned,
            acknowledged_current=acknowledged_current,
            pending_current=max(total_assigned - acknowledged_current, 0),
            history=history,
        )

    async def _latest_for_employee(
        self,
        *,
        training_id: UUID,
        company_id: UUID,
        employee_id: UUID,
        lock: bool = False,
    ) -> tuple[Document, DocumentVersion]:
        statement = (
            select(Document, DocumentVersion)
            .join(Training, Training.id == Document.training_id)
            .join(DocumentVersion, DocumentVersion.document_id == Document.id)
            .join(
                TrainingAssignment,
                (TrainingAssignment.training_id == Training.id)
                & (TrainingAssignment.employee_id == employee_id)
                & (TrainingAssignment.company_id == company_id),
            )
            .where(
                Training.id == training_id,
                Training.company_id == company_id,
                Training.status == TrainingStatus.PUBLISHED,
                Document.company_id == company_id,
                DocumentVersion.company_id == company_id,
            )
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )
        if lock:
            statement = statement.with_for_update(of=DocumentVersion)
        row = (await self._session.execute(statement)).first()
        if row is None:
            raise AppError(
                code="DOCUMENT_NOT_FOUND", message="Document not found.", status_code=404
            )
        return row._tuple()

    async def _latest_for_admin(self, *, training_id: UUID, company_id: UUID) -> DocumentVersion:
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

    @staticmethod
    def _employee_response(
        version: DocumentVersion,
        acknowledgement: DocumentAcknowledgement | None,
    ) -> EmployeeAcknowledgementStatus:
        return EmployeeAcknowledgementStatus(
            document_version_id=version.id,
            version_number=version.version_number,
            document_checksum=version.checksum,
            attestation=ATTESTATION,
            acknowledged=acknowledgement is not None,
            acknowledgement=(
                DocumentAcknowledgementResponse.model_validate(acknowledgement)
                if acknowledgement is not None
                else None
            ),
        )
