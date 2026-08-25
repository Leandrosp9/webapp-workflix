from uuid import UUID

from fastapi import APIRouter, status

from app.api.dependencies import AdminUser, SessionDependency
from app.schemas.users import UserCreate, UserResponse, UserSummary, UserUpdate
from app.services.users import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserSummary], summary="List company employees")
async def list_users(admin: AdminUser, session: SessionDependency) -> list[UserSummary]:
    return await UserService(session).list_employees(company_id=admin.company_id)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a company employee",
)
async def create_user(
    payload: UserCreate,
    admin: AdminUser,
    session: SessionDependency,
) -> UserResponse:
    user = await UserService(session).create_employee(company_id=admin.company_id, payload=payload)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a company employee",
)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    admin: AdminUser,
    session: SessionDependency,
) -> UserResponse:
    user = await UserService(session).update_employee(
        company_id=admin.company_id,
        user_id=user_id,
        payload=payload,
    )
    return UserResponse.model_validate(user)
