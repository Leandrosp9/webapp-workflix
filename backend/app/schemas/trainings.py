from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models import TrainingStatus, TrainingType


class TrainingCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=600)
    type: TrainingType
    thumbnail_url: str | None = Field(default=None, max_length=500)
    content: str = ""
    video_url: str | None = Field(default=None, max_length=500)
    estimated_minutes: int = Field(ge=1, le=1440)
    status: TrainingStatus = TrainingStatus.DRAFT

    @model_validator(mode="after")
    def validate_type_content(self) -> "TrainingCreate":
        if self.type == TrainingType.VIDEO and not self.video_url:
            raise ValueError("video_url is required for video training")
        return self


class TrainingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=180)
    description: str | None = Field(default=None, min_length=3, max_length=600)
    type: TrainingType | None = None
    thumbnail_url: str | None = Field(default=None, max_length=500)
    content: str | None = None
    video_url: str | None = Field(default=None, max_length=500)
    estimated_minutes: int | None = Field(default=None, ge=1, le=1440)
    status: TrainingStatus | None = None


class TrainingResponse(BaseModel):
    id: UUID
    company_id: UUID
    title: str
    description: str
    type: TrainingType
    thumbnail_url: str | None
    content: str
    video_url: str | None
    has_pdf: bool
    estimated_minutes: int
    status: TrainingStatus
    created_at: datetime
    updated_at: datetime
    progress_percent: int | None = None
    assigned_at: datetime | None = None
    due_date: date | None = None
    has_quiz: bool = False


class TrainingAssignmentCreate(BaseModel):
    employee_ids: list[UUID] = Field(min_length=1, max_length=500)
    due_date: date | None = None


class TrainingAssignmentResult(BaseModel):
    assigned: int
    updated: int


class ProgressUpdate(BaseModel):
    progress_percent: int = Field(ge=0, le=100)


class EmployeeHomeResponse(BaseModel):
    featured: TrainingResponse | None
    continue_learning: list[TrainingResponse]
    required: list[TrainingResponse]
    new: list[TrainingResponse]
    completed: list[TrainingResponse]


class AdminDashboardResponse(BaseModel):
    total_employees: int
    published_trainings: int
    active_assignments: int
    completion_percent: int
    completed_assignments: int
    pending_assignments: int
    recent_trainings: list[TrainingResponse]
