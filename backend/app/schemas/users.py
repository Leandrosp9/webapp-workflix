from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import Role


def normalize_cpf(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    if len(digits) != 11 or len(set(digits)) == 1:
        raise ValueError("CPF inválido.")
    for size in (9, 10):
        total = sum(int(digits[index]) * (size + 1 - index) for index in range(size))
        digit = 11 - (total % 11)
        expected = 0 if digit >= 10 else digit
        if int(digits[size]) != expected:
            raise ValueError("CPF inválido.")
    return digits


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=140)
    cpf: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, value: str) -> str:
        return normalize_cpf(value)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=140)
    cpf: str | None = None
    is_active: bool | None = None

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, value: str | None) -> str | None:
        return normalize_cpf(value) if value is not None else None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    email: EmailStr
    full_name: str
    cpf: str | None
    role: Role
    is_active: bool
    created_at: datetime


class UserSummary(UserResponse):
    assigned: int = 0
    completed: int = 0
    pending: int = 0
    completion_percent: int = 0
