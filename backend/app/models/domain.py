from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Role(StrEnum):
    ADMIN = "ADMIN"
    EMPLOYEE = "EMPLOYEE"


class TrainingType(StrEnum):
    ARTICLE = "ARTICLE"
    VIDEO = "VIDEO"
    PDF = "PDF"


class TrainingStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


role_enum = Enum(Role, native_enum=False, length=16, validate_strings=True)
training_type_enum = Enum(TrainingType, native_enum=False, length=16, validate_strings=True)
training_status_enum = Enum(TrainingStatus, native_enum=False, length=16, validate_strings=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    users: Mapped[list[User]] = relationship(back_populates="company", cascade="all, delete-orphan")
    trainings: Mapped[list[Training]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_company_role", "company_id", "role"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(140), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(role_enum, nullable=False, default=Role.EMPLOYEE)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    company: Mapped[Company] = relationship(back_populates="users")
    created_trainings: Mapped[list[Training]] = relationship(back_populates="creator")
    assignments: Mapped[list[TrainingAssignment]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    progress: Mapped[list[UserProgress]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class Training(TimestampMixin, Base):
    __tablename__ = "trainings"
    __table_args__ = (
        CheckConstraint("estimated_minutes > 0", name="positive_estimated_minutes"),
        Index("ix_trainings_company_status_created", "company_id", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(String(600), nullable=False)
    type: Mapped[TrainingType] = mapped_column(training_type_enum, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    video_url: Mapped[str | None] = mapped_column(String(500))
    pdf_path: Mapped[str | None] = mapped_column(String(500))
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[TrainingStatus] = mapped_column(
        training_status_enum, nullable=False, default=TrainingStatus.DRAFT
    )
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    company: Mapped[Company] = relationship(back_populates="trainings")
    creator: Mapped[User] = relationship(back_populates="created_trainings")
    assignments: Mapped[list[TrainingAssignment]] = relationship(
        back_populates="training", cascade="all, delete-orphan"
    )
    progress: Mapped[list[UserProgress]] = relationship(
        back_populates="training", cascade="all, delete-orphan"
    )
    quiz: Mapped[Quiz | None] = relationship(
        back_populates="training", cascade="all, delete-orphan", uselist=False
    )


class TrainingAssignment(Base):
    __tablename__ = "training_assignments"
    __table_args__ = (
        UniqueConstraint("training_id", "employee_id", name="training_employee"),
        Index("ix_assignments_company_employee", "company_id", "employee_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    training_id: Mapped[UUID] = mapped_column(
        ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    due_date: Mapped[date | None] = mapped_column(Date)

    training: Mapped[Training] = relationship(back_populates="assignments")
    employee: Mapped[User] = relationship(back_populates="assignments")


class UserProgress(Base):
    __tablename__ = "user_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "training_id", name="user_training"),
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="valid_progress_percent",
        ),
        Index("ix_progress_company_user", "company_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    training_id: Mapped[UUID] = mapped_column(
        ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="progress")
    training: Mapped[Training] = relationship(back_populates="progress")


class Quiz(TimestampMixin, Base):
    __tablename__ = "quizzes"
    __table_args__ = (
        UniqueConstraint("training_id", name="one_quiz_per_training"),
        CheckConstraint("passing_score >= 0 AND passing_score <= 100", name="valid_passing_score"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    training_id: Mapped[UUID] = mapped_column(
        ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False
    )
    passing_score: Mapped[int] = mapped_column(Integer, nullable=False, default=70)

    training: Mapped[Training] = relationship(back_populates="quiz")
    questions: Mapped[list[Question]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan", order_by="Question.position"
    )
    attempts: Mapped[list[QuizAttempt]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("quiz_id", "position", name="quiz_position"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    quiz_id: Mapped[UUID] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    explanation: Mapped[str] = mapped_column(String(700), nullable=False, default="")
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    quiz: Mapped[Quiz] = relationship(back_populates="questions")
    options: Mapped[list[QuestionOption]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionOption.position",
    )


class QuestionOption(Base):
    __tablename__ = "question_options"
    __table_args__ = (UniqueConstraint("question_id", "position", name="question_position"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(String(350), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    question: Mapped[Question] = relationship(back_populates="options")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (Index("ix_attempts_company_user", "company_id", "user_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    quiz_id: Mapped[UUID] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    quiz: Mapped[Quiz] = relationship(back_populates="attempts")
