from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import hash_password
from app.models import Role, TrainingAssignment, User, UserProgress
from app.schemas.users import UserCreate, UserResponse, UserSummary, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_employee(self, *, company_id, payload: UserCreate) -> User:
        email = str(payload.email).lower()
        if await self._session.scalar(select(User.id).where(User.email == email)):
            raise AppError(
                code="EMAIL_ALREADY_EXISTS",
                message="This email is already in use.",
                status_code=409,
            )
        if await self._session.scalar(
            select(User.id).where(User.company_id == company_id, User.cpf == payload.cpf)
        ):
            raise AppError(
                code="CPF_ALREADY_EXISTS",
                message="This CPF is already in use by the company.",
                status_code=409,
            )
        user = User(
            company_id=company_id,
            email=email,
            full_name=payload.full_name.strip(),
            cpf=payload.cpf,
            password_hash=hash_password(payload.password),
            role=Role.EMPLOYEE,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def list_employees(self, *, company_id) -> list[UserSummary]:
        rows = (
            await self._session.execute(
                select(
                    User,
                    func.count(TrainingAssignment.id.distinct()).label("assigned"),
                    func.count(UserProgress.id.distinct())
                    .filter(UserProgress.progress_percent == 100)
                    .label("completed"),
                )
                .outerjoin(
                    TrainingAssignment,
                    (TrainingAssignment.employee_id == User.id)
                    & (TrainingAssignment.company_id == company_id),
                )
                .outerjoin(
                    UserProgress,
                    (UserProgress.user_id == User.id) & (UserProgress.company_id == company_id),
                )
                .where(User.company_id == company_id, User.role == Role.EMPLOYEE)
                .group_by(User.id)
                .order_by(User.full_name)
            )
        ).all()
        result: list[UserSummary] = []
        for user, assigned, completed in rows:
            assigned_count = int(assigned)
            completed_count = min(int(completed), assigned_count)
            result.append(
                UserSummary(
                    **UserResponse.model_validate(user).model_dump(),
                    assigned=assigned_count,
                    completed=completed_count,
                    pending=max(assigned_count - completed_count, 0),
                    completion_percent=(
                        round(completed_count / assigned_count * 100) if assigned_count else 0
                    ),
                )
            )
        return result

    async def update_employee(self, *, company_id, user_id, payload: UserUpdate) -> User:
        user = await self._session.scalar(
            select(User).where(
                User.id == user_id,
                User.company_id == company_id,
                User.role == Role.EMPLOYEE,
            )
        )
        if user is None:
            raise AppError(
                code="USER_NOT_FOUND",
                message="The employee was not found.",
                status_code=404,
            )

        if payload.email is not None:
            email = str(payload.email).lower()
            duplicate = await self._session.scalar(
                select(User.id).where(User.email == email, User.id != user.id)
            )
            if duplicate:
                raise AppError(
                    code="EMAIL_ALREADY_EXISTS",
                    message="This email is already in use.",
                    status_code=409,
                )
            user.email = email
        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()
        if payload.cpf is not None:
            duplicate_cpf = await self._session.scalar(
                select(User.id).where(
                    User.company_id == company_id,
                    User.cpf == payload.cpf,
                    User.id != user.id,
                )
            )
            if duplicate_cpf:
                raise AppError(
                    code="CPF_ALREADY_EXISTS",
                    message="This CPF is already in use by the company.",
                    status_code=409,
                )
            user.cpf = payload.cpf
        if payload.is_active is not None:
            user.is_active = payload.is_active

        await self._session.commit()
        await self._session.refresh(user)
        return user
