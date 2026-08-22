from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models import (
    Certificate,
    LearningPath,
    LearningPathAssignment,
    LearningPathItem,
    LearningPathStatus,
    Role,
    Training,
    TrainingAssignment,
    TrainingStatus,
    User,
    UserProgress,
)
from app.schemas.learning_paths import (
    LearningPathAssignmentCreate,
    LearningPathAssignmentResult,
    LearningPathCreate,
    LearningPathItemResponse,
    LearningPathItemsReplace,
    LearningPathResponse,
    LearningPathUpdate,
)
from app.services.certificates import CertificateService


class LearningPathService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _options():
        return (
            selectinload(LearningPath.items).selectinload(LearningPathItem.training),
            selectinload(LearningPath.assignments),
            selectinload(LearningPath.certificates),
        )

    async def _path(self, path_id: UUID, company_id: UUID) -> LearningPath:
        path = await self._session.scalar(
            select(LearningPath)
            .options(*self._options())
            .where(LearningPath.id == path_id, LearningPath.company_id == company_id)
        )
        if path is None:
            raise AppError(
                code="LEARNING_PATH_NOT_FOUND",
                message="Learning path not found.",
                status_code=404,
            )
        return path

    @staticmethod
    def _item_response(
        item: LearningPathItem, *, progress: int | None = None, available: bool = True
    ) -> LearningPathItemResponse:
        return LearningPathItemResponse(
            id=item.id,
            training_id=item.training_id,
            position=item.position,
            required=item.required,
            title=item.training.title,
            description=item.training.description,
            type=item.training.type,
            status=item.training.status,
            estimated_minutes=item.training.estimated_minutes,
            progress_percent=progress,
            available=available,
        )

    def _admin_response(self, path: LearningPath) -> LearningPathResponse:
        return LearningPathResponse(
            id=path.id,
            company_id=path.company_id,
            title=path.title,
            description=path.description,
            status=path.status,
            created_at=path.created_at,
            updated_at=path.updated_at,
            items=[self._item_response(item) for item in path.items],
            assignment_count=len(path.assignments),
            certificate_count=len(path.certificates),
        )

    async def _employee_response(
        self, path: LearningPath, assignment: LearningPathAssignment
    ) -> LearningPathResponse:
        training_ids = [item.training_id for item in path.items]
        progress_rows = (
            await self._session.execute(
                select(UserProgress.training_id, UserProgress.progress_percent).where(
                    UserProgress.company_id == path.company_id,
                    UserProgress.user_id == assignment.employee_id,
                    UserProgress.training_id.in_(training_ids),
                )
            )
        ).all()
        progress_by_training = {training_id: progress for training_id, progress in progress_rows}
        item_responses: list[LearningPathItemResponse] = []
        prior_required_complete = True
        required_progress: list[int] = []
        for item in path.items:
            progress = progress_by_training.get(item.training_id, 0)
            item_responses.append(
                self._item_response(item, progress=progress, available=prior_required_complete)
            )
            if item.required:
                required_progress.append(progress)
                prior_required_complete = prior_required_complete and progress == 100
        aggregate = (
            round(sum(required_progress) / len(required_progress)) if required_progress else 0
        )
        certificate = await self._session.scalar(
            select(Certificate).where(
                Certificate.learning_path_id == path.id,
                Certificate.user_id == assignment.employee_id,
            )
        )
        return LearningPathResponse(
            id=path.id,
            company_id=path.company_id,
            title=path.title,
            description=path.description,
            status=path.status,
            created_at=path.created_at,
            updated_at=path.updated_at,
            items=item_responses,
            assigned_at=assignment.assigned_at,
            due_date=assignment.due_date,
            progress_percent=aggregate,
            completed=bool(required_progress) and all(value == 100 for value in required_progress),
            certificate_code=certificate.code if certificate else None,
        )

    async def list_admin(self, company_id: UUID) -> list[LearningPathResponse]:
        paths = (
            (
                await self._session.scalars(
                    select(LearningPath)
                    .options(*self._options())
                    .where(LearningPath.company_id == company_id)
                    .order_by(LearningPath.created_at.desc())
                )
            )
            .unique()
            .all()
        )
        return [self._admin_response(path) for path in paths]

    async def get_admin(self, path_id: UUID, company_id: UUID) -> LearningPathResponse:
        return self._admin_response(await self._path(path_id, company_id))

    async def create(
        self, company_id: UUID, creator_id: UUID, payload: LearningPathCreate
    ) -> LearningPathResponse:
        path = LearningPath(
            company_id=company_id,
            created_by=creator_id,
            title=payload.title.strip(),
            description=payload.description.strip(),
        )
        self._session.add(path)
        await self._session.commit()
        return self._admin_response(await self._path(path.id, company_id))

    async def update(
        self, path_id: UUID, company_id: UUID, payload: LearningPathUpdate
    ) -> LearningPathResponse:
        path = await self._path(path_id, company_id)
        changes = payload.model_dump(exclude_unset=True)
        next_status = changes.get("status")
        if path.status == LearningPathStatus.PUBLISHED and next_status == LearningPathStatus.DRAFT:
            raise AppError(
                code="LEARNING_PATH_ALREADY_PUBLISHED",
                message="A published path cannot return to draft.",
                status_code=409,
            )
        if next_status == LearningPathStatus.PUBLISHED:
            if not path.items or not any(item.required for item in path.items):
                raise AppError(
                    code="LEARNING_PATH_EMPTY",
                    message="Add at least one required training before publishing.",
                    status_code=409,
                )
            if any(item.training.status != TrainingStatus.PUBLISHED for item in path.items):
                raise AppError(
                    code="LEARNING_PATH_HAS_DRAFT_TRAINING",
                    message="Publish every training before publishing the path.",
                    status_code=409,
                )
        for field, value in changes.items():
            setattr(path, field, value.strip() if isinstance(value, str) else value)
        await self._session.commit()
        return self._admin_response(await self._path(path_id, company_id))

    async def replace_items(
        self, path_id: UUID, company_id: UUID, payload: LearningPathItemsReplace
    ) -> LearningPathResponse:
        path = await self._path(path_id, company_id)
        if path.status != LearningPathStatus.DRAFT:
            raise AppError(
                code="LEARNING_PATH_PUBLISHED",
                message="Only draft paths can change their content order.",
                status_code=409,
            )
        ids = [item.training_id for item in payload.items]
        if len(set(ids)) != len(ids):
            raise AppError(
                code="LEARNING_PATH_DUPLICATE_TRAINING",
                message="A training can appear only once in a path.",
                status_code=422,
            )
        trainings = (
            await self._session.scalars(
                select(Training).where(Training.company_id == company_id, Training.id.in_(ids))
            )
        ).all()
        by_id = {training.id: training for training in trainings}
        if len(by_id) != len(ids):
            raise AppError(
                code="TRAINING_NOT_FOUND", message="Training not found.", status_code=404
            )
        path.items.clear()
        await self._session.flush()
        path.items = [
            LearningPathItem(
                company_id=company_id,
                training_id=item.training_id,
                position=position,
                required=item.required,
                training=by_id[item.training_id],
            )
            for position, item in enumerate(payload.items)
        ]
        await self._session.commit()
        return self._admin_response(await self._path(path_id, company_id))

    async def assign(
        self, path_id: UUID, company_id: UUID, payload: LearningPathAssignmentCreate
    ) -> LearningPathAssignmentResult:
        path = await self._path(path_id, company_id)
        if path.status != LearningPathStatus.PUBLISHED:
            raise AppError(
                code="LEARNING_PATH_NOT_PUBLISHED",
                message="Publish the path before assigning it.",
                status_code=409,
            )
        employee_ids = list(dict.fromkeys(payload.employee_ids))
        valid_employees = set(
            (
                await self._session.scalars(
                    select(User.id).where(
                        User.company_id == company_id,
                        User.id.in_(employee_ids),
                        User.role == Role.EMPLOYEE,
                        User.is_active.is_(True),
                    )
                )
            ).all()
        )
        if valid_employees != set(employee_ids):
            raise AppError(
                code="EMPLOYEE_NOT_FOUND", message="Employee not found.", status_code=404
            )

        current_path_assignments = (
            await self._session.scalars(
                select(LearningPathAssignment).where(
                    LearningPathAssignment.learning_path_id == path_id,
                    LearningPathAssignment.employee_id.in_(employee_ids),
                )
            )
        ).all()
        path_by_employee = {item.employee_id: item for item in current_path_assignments}
        assigned = 0
        updated = 0
        for employee_id in employee_ids:
            current = path_by_employee.get(employee_id)
            if current is None:
                self._session.add(
                    LearningPathAssignment(
                        company_id=company_id,
                        learning_path_id=path_id,
                        employee_id=employee_id,
                        due_date=payload.due_date,
                    )
                )
                assigned += 1
            elif current.due_date != payload.due_date:
                current.due_date = payload.due_date
                updated += 1

        training_ids = [item.training_id for item in path.items]
        current_training_assignments = (
            await self._session.scalars(
                select(TrainingAssignment).where(
                    TrainingAssignment.company_id == company_id,
                    TrainingAssignment.training_id.in_(training_ids),
                    TrainingAssignment.employee_id.in_(employee_ids),
                )
            )
        ).all()
        training_by_pair = {
            (item.training_id, item.employee_id): item for item in current_training_assignments
        }
        training_created = 0
        for employee_id in employee_ids:
            for training_id in training_ids:
                pair = (training_id, employee_id)
                current = training_by_pair.get(pair)
                if current is None:
                    self._session.add(
                        TrainingAssignment(
                            company_id=company_id,
                            training_id=training_id,
                            employee_id=employee_id,
                            due_date=payload.due_date,
                        )
                    )
                    training_created += 1
                elif payload.due_date and (
                    current.due_date is None or payload.due_date < current.due_date
                ):
                    current.due_date = payload.due_date
        await self._session.flush()
        certificates = CertificateService(self._session)
        for employee_id in employee_ids:
            await certificates.issue_eligible(
                company_id=company_id,
                user_id=employee_id,
                learning_path_ids=[path_id],
            )
        await self._session.commit()
        return LearningPathAssignmentResult(
            assigned=assigned,
            updated=updated,
            training_assignments_created=training_created,
        )

    async def list_employee(
        self, company_id: UUID, employee_id: UUID
    ) -> list[LearningPathResponse]:
        rows = (
            (
                await self._session.execute(
                    select(LearningPath, LearningPathAssignment)
                    .join(
                        LearningPathAssignment,
                        LearningPathAssignment.learning_path_id == LearningPath.id,
                    )
                    .options(*self._options())
                    .where(
                        LearningPath.company_id == company_id,
                        LearningPath.status == LearningPathStatus.PUBLISHED,
                        LearningPathAssignment.company_id == company_id,
                        LearningPathAssignment.employee_id == employee_id,
                    )
                    .order_by(LearningPathAssignment.assigned_at.desc())
                )
            )
            .unique()
            .all()
        )
        return [await self._employee_response(path, assignment) for path, assignment in rows]

    async def get_employee(
        self, path_id: UUID, company_id: UUID, employee_id: UUID
    ) -> LearningPathResponse:
        row = (
            (
                await self._session.execute(
                    select(LearningPath, LearningPathAssignment)
                    .join(
                        LearningPathAssignment,
                        LearningPathAssignment.learning_path_id == LearningPath.id,
                    )
                    .options(*self._options())
                    .where(
                        LearningPath.id == path_id,
                        LearningPath.company_id == company_id,
                        LearningPath.status == LearningPathStatus.PUBLISHED,
                        LearningPathAssignment.employee_id == employee_id,
                    )
                )
            )
            .unique()
            .one_or_none()
        )
        if row is None:
            raise AppError(
                code="LEARNING_PATH_NOT_FOUND",
                message="Learning path not found.",
                status_code=404,
            )
        return await self._employee_response(*row)

    async def delete(self, path_id: UUID, company_id: UUID) -> None:
        path = await self._path(path_id, company_id)
        if path.status != LearningPathStatus.DRAFT or path.assignments or path.certificates:
            raise AppError(
                code="LEARNING_PATH_HAS_HISTORY",
                message="Only unassigned draft paths can be deleted.",
                status_code=409,
            )
        await self._session.delete(path)
        await self._session.commit()
