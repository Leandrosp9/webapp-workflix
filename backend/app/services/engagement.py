from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Role, TrainingAssignment, User, UserProgress
from app.schemas.engagement import LeaderboardEntry, LeaderboardResponse


class EngagementService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _entry(row, current_user_id: UUID) -> LeaderboardEntry:
        return LeaderboardEntry(
            rank=int(row["rank"]),
            user_id=row["user_id"],
            full_name=row["full_name"],
            completed_trainings=int(row["completed_trainings"]),
            average_progress=round(float(row["average_progress"])),
            has_avatar=bool(row["has_avatar"]),
            avatar_updated_at=row["avatar_updated_at"],
            is_current_user=row["user_id"] == current_user_id,
        )

    async def leaderboard(self, *, company_id: UUID, current_user_id: UUID) -> LeaderboardResponse:
        completed = func.count(UserProgress.id).filter(UserProgress.progress_percent == 100)
        average = func.coalesce(func.avg(func.coalesce(UserProgress.progress_percent, 0)), 0)
        stats = (
            select(
                User.id.label("user_id"),
                User.full_name.label("full_name"),
                User.avatar_updated_at.label("avatar_updated_at"),
                User.avatar_object_key.is_not(None).label("has_avatar"),
                completed.label("completed_trainings"),
                average.label("average_progress"),
            )
            .outerjoin(
                TrainingAssignment,
                (TrainingAssignment.employee_id == User.id)
                & (TrainingAssignment.company_id == company_id),
            )
            .outerjoin(
                UserProgress,
                (UserProgress.user_id == User.id)
                & (UserProgress.training_id == TrainingAssignment.training_id)
                & (UserProgress.company_id == company_id),
            )
            .where(
                User.company_id == company_id,
                User.role == Role.EMPLOYEE,
                User.is_active.is_(True),
            )
            .group_by(User.id)
            .subquery()
        )
        ranked = select(
            stats,
            func.rank()
            .over(
                order_by=(
                    stats.c.completed_trainings.desc(),
                    stats.c.average_progress.desc(),
                )
            )
            .label("rank"),
        ).subquery()
        top_rows = (
            await self._session.execute(
                select(ranked).order_by(ranked.c.rank, ranked.c.full_name).limit(10)
            )
        ).mappings()
        current_row = (
            (await self._session.execute(select(ranked).where(ranked.c.user_id == current_user_id)))
            .mappings()
            .one_or_none()
        )
        if current_row is None:
            raise AppError(
                code="LEADERBOARD_UNAVAILABLE",
                message="The current employee is not eligible for the leaderboard.",
                status_code=404,
            )
        return LeaderboardResponse(
            entries=[self._entry(row, current_user_id) for row in top_rows],
            current_user=self._entry(current_row, current_user_id),
        )
