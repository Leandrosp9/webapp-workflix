from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Response, UploadFile, status

from app.api.dependencies import AdminUser, CurrentUser, SessionDependency
from app.models import Role
from app.schemas.users import UserCreate, UserResponse, UserSummary, UserUpdate
from app.services.users import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserSummary], summary="List company users")
async def list_users(
    admin: AdminUser,
    session: SessionDependency,
    role: Role | None = None,
) -> list[UserSummary]:
    return await UserService(session).list_users(company_id=admin.company_id, role=role)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a company user",
)
async def create_user(
    payload: UserCreate,
    admin: AdminUser,
    session: SessionDependency,
) -> UserResponse:
    user = await UserService(session).create_user(company_id=admin.company_id, payload=payload)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a company user",
)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    admin: AdminUser,
    session: SessionDependency,
) -> UserResponse:
    user = await UserService(session).update_user(
        company_id=admin.company_id,
        user_id=user_id,
        payload=payload,
    )
    return UserResponse.model_validate(user)


@router.post(
    "/{user_id}/avatar",
    response_model=UserResponse,
    summary="Upload a user profile image",
)
async def upload_user_avatar(
    user_id: UUID,
    file: Annotated[UploadFile, File()],
    admin: AdminUser,
    session: SessionDependency,
) -> UserResponse:
    user = await UserService(session).upload_avatar(
        company_id=admin.company_id,
        user_id=user_id,
        upload=file,
    )
    return UserResponse.model_validate(user)


@router.get("/{user_id}/avatar", response_class=Response, summary="Read a company profile image")
async def get_user_avatar(
    user_id: UUID,
    current_user: CurrentUser,
    session: SessionDependency,
) -> Response:
    stored = await UserService(session).get_avatar(
        company_id=current_user.company_id,
        user_id=user_id,
    )
    return Response(
        content=stored.data,
        media_type=stored.content_type,
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.delete(
    "/{user_id}/avatar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a user profile image",
)
async def delete_user_avatar(
    user_id: UUID,
    admin: AdminUser,
    session: SessionDependency,
) -> Response:
    await UserService(session).delete_avatar(company_id=admin.company_id, user_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
