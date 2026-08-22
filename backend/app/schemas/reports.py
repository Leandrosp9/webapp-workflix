from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class AnalyticsKpis(BaseModel):
    total_employees: int
    total_assignments: int
    completed_assignments: int
    completion_percent: int
    overdue_assignments: int
    learning_hours: float
    certificates_issued: int
    published_paths: int


class TrainingAnalyticsRow(BaseModel):
    training_id: UUID
    title: str
    assignments: int
    completed: int
    completion_percent: int
    learning_hours: float


class PathAnalyticsRow(BaseModel):
    learning_path_id: UUID
    title: str
    assignments: int
    certificates: int
    completion_percent: int


class EmployeeAnalyticsRow(BaseModel):
    user_id: UUID
    full_name: str
    email: str
    assignments: int
    completed: int
    completion_percent: int
    learning_hours: float
    certificates: int


class ManagerAnalyticsResponse(BaseModel):
    generated_at: datetime
    kpis: AnalyticsKpis
    trainings: list[TrainingAnalyticsRow]
    paths: list[PathAnalyticsRow]
    employees: list[EmployeeAnalyticsRow]


class ProgressExportRow(BaseModel):
    employee_name: str
    employee_email: str
    training_title: str
    progress_percent: int
    status: str
    assigned_at: datetime
    due_date: date | None
    completed_at: datetime | None
