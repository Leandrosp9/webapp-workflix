from __future__ import annotations

import csv
from collections import defaultdict
from datetime import UTC, date, datetime
from io import StringIO
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Certificate,
    LearningPath,
    LearningPathStatus,
    Role,
    Training,
    TrainingAssignment,
    User,
    UserProgress,
)
from app.schemas.reports import (
    AnalyticsKpis,
    EmployeeAnalyticsRow,
    ManagerAnalyticsResponse,
    PathAnalyticsRow,
    TrainingAnalyticsRow,
)


def _csv_safe(value: object) -> str:
    text = "" if value is None else str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _assignment_rows(self, company_id: UUID):
        return (
            await self._session.execute(
                select(TrainingAssignment, Training, User, UserProgress)
                .join(Training, Training.id == TrainingAssignment.training_id)
                .join(User, User.id == TrainingAssignment.employee_id)
                .outerjoin(
                    UserProgress,
                    and_(
                        UserProgress.company_id == company_id,
                        UserProgress.training_id == TrainingAssignment.training_id,
                        UserProgress.user_id == TrainingAssignment.employee_id,
                    ),
                )
                .where(
                    TrainingAssignment.company_id == company_id,
                    Training.company_id == company_id,
                    User.company_id == company_id,
                )
                .order_by(User.full_name, Training.title)
            )
        ).all()

    async def analytics(self, company_id: UUID) -> ManagerAnalyticsResponse:
        employees = (
            await self._session.scalars(
                select(User)
                .where(User.company_id == company_id, User.role == Role.EMPLOYEE)
                .order_by(User.full_name)
            )
        ).all()
        trainings = (
            await self._session.scalars(
                select(Training).where(Training.company_id == company_id).order_by(Training.title)
            )
        ).all()
        assignments = await self._assignment_rows(company_id)
        certificates = (
            await self._session.scalars(
                select(Certificate).where(Certificate.company_id == company_id)
            )
        ).all()
        paths = (
            (
                await self._session.scalars(
                    select(LearningPath)
                    .options(
                        selectinload(LearningPath.assignments),
                        selectinload(LearningPath.certificates),
                    )
                    .where(
                        LearningPath.company_id == company_id,
                        LearningPath.status == LearningPathStatus.PUBLISHED,
                    )
                    .order_by(LearningPath.title)
                )
            )
            .unique()
            .all()
        )

        training_stats: dict[UUID, dict[str, float]] = defaultdict(
            lambda: {"assignments": 0, "completed": 0, "minutes": 0}
        )
        employee_stats: dict[UUID, dict[str, float]] = defaultdict(
            lambda: {"assignments": 0, "completed": 0, "minutes": 0}
        )
        overdue = 0
        today = date.today()
        for assignment, training, user, progress in assignments:
            complete = progress is not None and progress.progress_percent == 100
            training_stats[training.id]["assignments"] += 1
            employee_stats[user.id]["assignments"] += 1
            if complete:
                training_stats[training.id]["completed"] += 1
                training_stats[training.id]["minutes"] += training.estimated_minutes
                employee_stats[user.id]["completed"] += 1
                employee_stats[user.id]["minutes"] += training.estimated_minutes
            elif assignment.due_date is not None and assignment.due_date < today:
                overdue += 1

        certificates_by_user: dict[UUID, int] = defaultdict(int)
        for certificate in certificates:
            certificates_by_user[certificate.user_id] += 1

        total = len(assignments)
        completed = sum(int(stats["completed"]) for stats in training_stats.values())
        learning_minutes = sum(stats["minutes"] for stats in training_stats.values())
        training_rows = []
        for training in trainings:
            stats = training_stats[training.id]
            count = int(stats["assignments"])
            done = int(stats["completed"])
            training_rows.append(
                TrainingAnalyticsRow(
                    training_id=training.id,
                    title=training.title,
                    assignments=count,
                    completed=done,
                    completion_percent=round(done / count * 100) if count else 0,
                    learning_hours=round(stats["minutes"] / 60, 1),
                )
            )
        employee_rows = []
        for employee in employees:
            stats = employee_stats[employee.id]
            count = int(stats["assignments"])
            done = int(stats["completed"])
            employee_rows.append(
                EmployeeAnalyticsRow(
                    user_id=employee.id,
                    full_name=employee.full_name,
                    email=employee.email,
                    assignments=count,
                    completed=done,
                    completion_percent=round(done / count * 100) if count else 0,
                    learning_hours=round(stats["minutes"] / 60, 1),
                    certificates=certificates_by_user[employee.id],
                )
            )
        path_rows = [
            PathAnalyticsRow(
                learning_path_id=path.id,
                title=path.title,
                assignments=len(path.assignments),
                certificates=len(path.certificates),
                completion_percent=(
                    round(len(path.certificates) / len(path.assignments) * 100)
                    if path.assignments
                    else 0
                ),
            )
            for path in paths
        ]
        return ManagerAnalyticsResponse(
            generated_at=datetime.now(UTC),
            kpis=AnalyticsKpis(
                total_employees=len(employees),
                total_assignments=total,
                completed_assignments=completed,
                completion_percent=round(completed / total * 100) if total else 0,
                overdue_assignments=overdue,
                learning_hours=round(learning_minutes / 60, 1),
                certificates_issued=len(certificates),
                published_paths=len(paths),
            ),
            trainings=training_rows,
            paths=path_rows,
            employees=employee_rows,
        )

    @staticmethod
    def _encode_csv(headers: list[str], rows: list[list[object]]) -> bytes:
        stream = StringIO(newline="")
        writer = csv.writer(stream, dialect="excel", lineterminator="\r\n")
        writer.writerow(headers)
        writer.writerows([[_csv_safe(value) for value in row] for row in rows])
        return stream.getvalue().encode("utf-8-sig")

    async def progress_csv(self, company_id: UUID) -> bytes:
        rows = []
        for assignment, training, user, progress in await self._assignment_rows(company_id):
            percent = progress.progress_percent if progress else 0
            status = "Concluído" if percent == 100 else "Em andamento" if percent else "Pendente"
            rows.append(
                [
                    user.full_name,
                    user.email,
                    training.title,
                    percent,
                    status,
                    assignment.assigned_at.isoformat(),
                    assignment.due_date.isoformat() if assignment.due_date else "",
                    progress.completed_at.isoformat() if progress and progress.completed_at else "",
                ]
            )
        return self._encode_csv(
            [
                "Colaborador",
                "E-mail",
                "Treinamento",
                "Progresso (%)",
                "Status",
                "Atribuído em",
                "Prazo",
                "Concluído em",
            ],
            rows,
        )

    async def certificates_csv(self, company_id: UUID) -> bytes:
        certificates = (
            await self._session.scalars(
                select(Certificate)
                .where(Certificate.company_id == company_id)
                .order_by(Certificate.issued_at.desc())
            )
        ).all()
        rows = [
            [
                item.user_full_name,
                item.user_email,
                item.certificate_type.value,
                item.title,
                item.company_name,
                item.workload_minutes,
                item.issued_at.isoformat(),
                item.code,
            ]
            for item in certificates
        ]
        return self._encode_csv(
            [
                "Colaborador",
                "E-mail",
                "Tipo",
                "Treinamento ou trilha",
                "Empresa",
                "Carga (minutos)",
                "Emitido em",
                "Código",
            ],
            rows,
        )
