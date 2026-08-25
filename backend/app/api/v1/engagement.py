from fastapi import APIRouter

from app.api.dependencies import EmployeeUser, SessionDependency
from app.schemas.engagement import LeaderboardResponse
from app.services.engagement import EngagementService

router = APIRouter(tags=["Engagement"])


@router.get(
    "/employee/leaderboard",
    response_model=LeaderboardResponse,
    summary="Read the company learning leaderboard",
)
async def employee_leaderboard(
    employee: EmployeeUser,
    session: SessionDependency,
) -> LeaderboardResponse:
    return await EngagementService(session).leaderboard(
        company_id=employee.company_id,
        current_user_id=employee.id,
    )
