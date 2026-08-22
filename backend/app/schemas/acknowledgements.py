from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentAcknowledgementCreate(BaseModel):
    document_version_id: UUID


class DocumentAcknowledgementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    training_id: UUID
    document_id: UUID
    document_version_id: UUID
    user_id: UUID
    user_email: str
    user_full_name: str
    document_title: str
    original_filename: str
    version_number: int
    document_checksum: str
    attestation: str
    acknowledged_at: datetime


class EmployeeAcknowledgementStatus(BaseModel):
    document_version_id: UUID
    version_number: int
    document_checksum: str
    attestation: str
    acknowledged: bool
    acknowledgement: DocumentAcknowledgementResponse | None


class AdminAcknowledgementItem(DocumentAcknowledgementResponse):
    is_current: bool


class AdminAcknowledgementSummary(BaseModel):
    document_version_id: UUID
    version_number: int
    total_assigned: int
    acknowledged_current: int
    pending_current: int
    history: list[AdminAcknowledgementItem]
