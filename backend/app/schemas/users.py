from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Role


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=140)
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime


class UserSummary(UserResponse):
    assigned: int = 0
    completed: int = 0
    pending: int = 0
    completion_percent: int = 0
