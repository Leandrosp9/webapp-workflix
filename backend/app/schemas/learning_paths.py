from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import LearningPathStatus, TrainingStatus, TrainingType


class LearningPathCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=700)


class LearningPathUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=180)
    description: str | None = Field(default=None, max_length=700)
    status: LearningPathStatus | None = None


class LearningPathItemInput(BaseModel):
    training_id: UUID
    required: bool = True


class LearningPathItemsReplace(BaseModel):
    items: list[LearningPathItemInput] = Field(min_length=1, max_length=100)


class LearningPathAssignmentCreate(BaseModel):
    employee_ids: list[UUID] = Field(min_length=1, max_length=500)
    due_date: date | None = None


class LearningPathAssignmentResult(BaseModel):
    assigned: int
    updated: int
    training_assignments_created: int


class LearningPathItemResponse(BaseModel):
    id: UUID
    training_id: UUID
    position: int
    required: bool
    title: str
    description: str
    type: TrainingType
    status: TrainingStatus
    estimated_minutes: int
    progress_percent: int | None = None
    available: bool = True


class LearningPathResponse(BaseModel):
    id: UUID
    company_id: UUID
    title: str
    description: str
    status: LearningPathStatus
    created_at: datetime
    updated_at: datetime
    items: list[LearningPathItemResponse]
    assignment_count: int = 0
    certificate_count: int = 0
    assigned_at: datetime | None = None
    due_date: date | None = None
    progress_percent: int | None = None
    completed: bool = False
    certificate_code: str | None = None


class CertificateResponse(BaseModel):
    id: UUID
    learning_path_id: UUID
    user_id: UUID
    code: str
    user_full_name: str
    user_email: str
    company_name: str
    learning_path_title: str
    workload_minutes: int
    issued_at: datetime


class CertificateVerification(BaseModel):
    valid: bool = True
    code: str
    user_full_name: str
    company_name: str
    learning_path_title: str
    workload_minutes: int
    issued_at: datetime
