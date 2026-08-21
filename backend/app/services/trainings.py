from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.core.logging import get_logger
from app.models import (
    Document,
    DocumentVersion,
    Quiz,
    Role,
    Training,
    TrainingAssignment,
    TrainingStatus,
    TrainingType,
    User,
    UserProgress,
)
from app.schemas.trainings import (
    AdminDashboardResponse,
    EmployeeHomeResponse,
    TrainingAssignmentCreate,
    TrainingAssignmentResult,
    TrainingCreate,
    TrainingResponse,
    TrainingUpdate,
)
from app.storage import (
    ObjectStorage,
    StorageError,
    get_object_storage,
)

logger = get_logger(__name__)


class TrainingService:
    def __init__(self, session: AsyncSession, storage: ObjectStorage | None = None) -> None:
        self._session = session
        self._storage = storage or get_object_storage()

    @staticmethod
    def _response(
        training: Training,
        *,
        progress: UserProgress | None = None,
        assignment: TrainingAssignment | None = None,
        has_quiz: bool | None = None,
    ) -> TrainingResponse:
        return TrainingResponse(
            id=training.id,
            company_id=training.company_id,
            title=training.title,
            description=training.description,
            type=training.type,
            thumbnail_url=training.thumbnail_url,
            content=training.content,
            video_url=training.video_url,
            has_pdf=bool(training.pdf_path),
            estimated_minutes=training.estimated_minutes,
            status=training.status,
            created_at=training.created_at,
            updated_at=training.updated_at,
            progress_percent=progress.progress_percent if progress else None,
            assigned_at=assignment.assigned_at if assignment else None,
            due_date=assignment.due_date if assignment else None,
            has_quiz=bool(training.quiz) if has_quiz is None else has_quiz,
        )

    async def _admin_training(self, training_id: UUID, company_id: UUID) -> Training:
        training = await self._session.scalar(
            select(Training)
            .options(selectinload(Training.quiz))
            .where(Training.id == training_id, Training.company_id == company_id)
        )
        if training is None:
            raise AppError(
                code="TRAINING_NOT_FOUND", message="Training not found.", status_code=404
            )
        return training

    async def create(
        self, company_id: UUID, creator_id: UUID, payload: TrainingCreate
    ) -> TrainingResponse:
        training = Training(
            company_id=company_id,
            created_by=creator_id,
            **payload.model_dump(),
        )
        self._session.add(training)
        await self._session.commit()
        await self._session.refresh(training)
        return self._response(training, has_quiz=False)

    async def list_admin(self, company_id: UUID) -> list[TrainingResponse]:
        trainings = (
            await self._session.scalars(
                select(Training)
                .options(selectinload(Training.quiz))
                .where(Training.company_id == company_id)
                .order_by(Training.created_at.desc())
            )
        ).all()
        return [self._response(training) for training in trainings]

    async def get_admin(self, training_id: UUID, company_id: UUID) -> TrainingResponse:
        return self._response(await self._admin_training(training_id, company_id))

    async def update(
        self, training_id: UUID, company_id: UUID, payload: TrainingUpdate
    ) -> TrainingResponse:
        training = await self._admin_training(training_id, company_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(training, field, value)
        if training.type == TrainingType.VIDEO and not training.video_url:
            raise AppError(
                code="VIDEO_URL_REQUIRED",
                message="A video URL is required for video training.",
            )
        await self._session.commit()
        await self._session.refresh(training)
        return self._response(training)

    async def delete(self, training_id: UUID, company_id: UUID) -> None:
        training = await self._admin_training(training_id, company_id)
        version_keys = list(
            await self._session.scalars(
                select(DocumentVersion.object_key)
                .join(Document, Document.id == DocumentVersion.document_id)
                .where(
                    Document.training_id == training_id,
                    Document.company_id == company_id,
                    DocumentVersion.company_id == company_id,
                )
            )
        )
        object_keys = set(version_keys)
        if training.pdf_path:
            object_keys.add(training.pdf_path)
        await self._session.delete(training)
        await self._session.commit()
        for object_key in object_keys:
            try:
                await self._storage.delete(object_key)
            except StorageError:
                logger.warning(
                    "training_object_cleanup_failed",
                    extra={"training_id": str(training_id), "object_key": object_key},
                )

    async def assign(
        self, training_id: UUID, company_id: UUID, payload: TrainingAssignmentCreate
    ) -> TrainingAssignmentResult:
        await self._admin_training(training_id, company_id)
        employee_ids = list(dict.fromkeys(payload.employee_ids))
        valid_ids = set(
            await self._session.scalars(
                select(User.id).where(
                    User.id.in_(employee_ids),
                    User.company_id == company_id,
                    User.role == Role.EMPLOYEE,
                    User.is_active.is_(True),
                )
            )
        )
        if len(valid_ids) != len(employee_ids):
            raise AppError(
                code="INVALID_EMPLOYEE",
                message="One or more employees are invalid for this company.",
                status_code=422,
            )
        existing = {
            item.employee_id: item
            for item in await self._session.scalars(
                select(TrainingAssignment).where(
                    TrainingAssignment.company_id == company_id,
                    TrainingAssignment.training_id == training_id,
                    TrainingAssignment.employee_id.in_(employee_ids),
                )
            )
        }
        assigned = 0
        updated = 0
        for employee_id in employee_ids:
            if assignment := existing.get(employee_id):
                assignment.due_date = payload.due_date
                updated += 1
            else:
                self._session.add(
                    TrainingAssignment(
                        company_id=company_id,
                        training_id=training_id,
                        employee_id=employee_id,
                        due_date=payload.due_date,
                    )
                )
                assigned += 1
        await self._session.commit()
        return TrainingAssignmentResult(assigned=assigned, updated=updated)

    async def _employee_row(
        self, training_id: UUID, company_id: UUID, employee_id: UUID
    ) -> tuple[Training, TrainingAssignment, UserProgress | None, bool]:
        row = (
            await self._session.execute(
                select(Training, TrainingAssignment, UserProgress, Quiz.id.is_not(None))
                .join(
                    TrainingAssignment,
                    (TrainingAssignment.training_id == Training.id)
                    & (TrainingAssignment.employee_id == employee_id)
                    & (TrainingAssignment.company_id == company_id),
                )
                .outerjoin(
                    UserProgress,
                    (UserProgress.training_id == Training.id)
                    & (UserProgress.user_id == employee_id)
                    & (UserProgress.company_id == company_id),
                )
                .outerjoin(Quiz, Quiz.training_id == Training.id)
                .where(
                    Training.id == training_id,
                    Training.company_id == company_id,
                    Training.status == TrainingStatus.PUBLISHED,
                )
            )
        ).first()
        if row is None:
            raise AppError(
                code="TRAINING_NOT_FOUND", message="Training not found.", status_code=404
            )
        return row._tuple()

    async def get_employee(
        self, training_id: UUID, company_id: UUID, employee_id: UUID
    ) -> TrainingResponse:
        training, assignment, progress, has_quiz = await self._employee_row(
            training_id, company_id, employee_id
        )
        return self._response(training, progress=progress, assignment=assignment, has_quiz=has_quiz)

    async def list_employee(self, company_id: UUID, employee_id: UUID) -> list[TrainingResponse]:
        rows = (
            await self._session.execute(
                select(Training, TrainingAssignment, UserProgress, Quiz.id.is_not(None))
                .join(
                    TrainingAssignment,
                    (TrainingAssignment.training_id == Training.id)
                    & (TrainingAssignment.employee_id == employee_id)
                    & (TrainingAssignment.company_id == company_id),
                )
                .outerjoin(
                    UserProgress,
                    (UserProgress.training_id == Training.id)
                    & (UserProgress.user_id == employee_id)
                    & (UserProgress.company_id == company_id),
                )
                .outerjoin(Quiz, Quiz.training_id == Training.id)
                .where(
                    Training.company_id == company_id,
                    Training.status == TrainingStatus.PUBLISHED,
                )
                .order_by(TrainingAssignment.assigned_at.desc())
            )
        ).all()
        return [
            self._response(training, progress=progress, assignment=assignment, has_quiz=has_quiz)
            for training, assignment, progress, has_quiz in rows
        ]

    async def update_progress(
        self, training_id: UUID, company_id: UUID, employee_id: UUID, percent: int
    ) -> TrainingResponse:
        training, assignment, progress, has_quiz = await self._employee_row(
            training_id, company_id, employee_id
        )
        now = datetime.now(UTC)
        if progress is None:
            progress = UserProgress(
                company_id=company_id,
                user_id=employee_id,
                training_id=training_id,
                progress_percent=percent,
                started_at=now if percent > 0 else None,
                completed_at=now if percent == 100 else None,
            )
            self._session.add(progress)
        else:
            progress.progress_percent = max(progress.progress_percent, percent)
            if progress.progress_percent > 0 and progress.started_at is None:
                progress.started_at = now
            if progress.progress_percent == 100 and progress.completed_at is None:
                progress.completed_at = now
        await self._session.commit()
        await self._session.refresh(progress)
        return self._response(training, progress=progress, assignment=assignment, has_quiz=has_quiz)

    async def employee_home(self, company_id: UUID, employee_id: UUID) -> EmployeeHomeResponse:
        items = await self.list_employee(company_id, employee_id)
        in_progress = [item for item in items if 0 < (item.progress_percent or 0) < 100]
        completed = [item for item in items if item.progress_percent == 100]
        pending = [item for item in items if not item.progress_percent]
        required = sorted(
            [item for item in items if item.due_date and item.progress_percent != 100],
            key=lambda item: item.due_date or datetime.max.date(),
        )
        return EmployeeHomeResponse(
            featured=(in_progress or pending or completed or [None])[0],
            continue_learning=in_progress,
            required=required,
            new=pending,
            completed=completed,
        )

    async def dashboard(self, company_id: UUID) -> AdminDashboardResponse:
        total_employees = await self._session.scalar(
            select(func.count(User.id)).where(
                User.company_id == company_id, User.role == Role.EMPLOYEE
            )
        )
        published = await self._session.scalar(
            select(func.count(Training.id)).where(
                Training.company_id == company_id, Training.status == TrainingStatus.PUBLISHED
            )
        )
        assignments = await self._session.scalar(
            select(func.count(TrainingAssignment.id)).where(
                TrainingAssignment.company_id == company_id
            )
        )
        completed = await self._session.scalar(
            select(func.count(UserProgress.id)).where(
                UserProgress.company_id == company_id, UserProgress.progress_percent == 100
            )
        )
        recent = (
            await self._session.scalars(
                select(Training)
                .options(selectinload(Training.quiz))
                .where(Training.company_id == company_id)
                .order_by(Training.created_at.desc())
                .limit(5)
            )
        ).all()
        total = int(assignments or 0)
        complete = min(int(completed or 0), total)
        return AdminDashboardResponse(
            total_employees=int(total_employees or 0),
            published_trainings=int(published or 0),
            active_assignments=total,
            completion_percent=round(complete / total * 100) if total else 0,
            completed_assignments=complete,
            pending_assignments=max(total - complete, 0),
            recent_trainings=[self._response(item) for item in recent],
        )
