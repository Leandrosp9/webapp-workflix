from uuid import UUID

from fastapi import APIRouter, status
from fastapi.responses import Response

from app.api.dependencies import AdminUser, EmployeeUser, SessionDependency
from app.schemas.learning_paths import (
    LearningPathAssignmentCreate,
    LearningPathAssignmentResult,
    LearningPathCreate,
    LearningPathItemsReplace,
    LearningPathResponse,
    LearningPathUpdate,
)
from app.services.learning_paths import LearningPathService

router = APIRouter(tags=["Learning paths"])


@router.get("/learning-paths", response_model=list[LearningPathResponse])
async def list_learning_paths(
    admin: AdminUser, session: SessionDependency
) -> list[LearningPathResponse]:
    return await LearningPathService(session).list_admin(admin.company_id)


@router.post(
    "/learning-paths", response_model=LearningPathResponse, status_code=status.HTTP_201_CREATED
)
async def create_learning_path(
    payload: LearningPathCreate, admin: AdminUser, session: SessionDependency
) -> LearningPathResponse:
    return await LearningPathService(session).create(admin.company_id, admin.id, payload)


@router.get("/learning-paths/{path_id}", response_model=LearningPathResponse)
async def get_learning_path(
    path_id: UUID, admin: AdminUser, session: SessionDependency
) -> LearningPathResponse:
    return await LearningPathService(session).get_admin(path_id, admin.company_id)


@router.patch("/learning-paths/{path_id}", response_model=LearningPathResponse)
async def update_learning_path(
    path_id: UUID,
    payload: LearningPathUpdate,
    admin: AdminUser,
    session: SessionDependency,
) -> LearningPathResponse:
    return await LearningPathService(session).update(path_id, admin.company_id, payload)


@router.put("/learning-paths/{path_id}/items", response_model=LearningPathResponse)
async def replace_learning_path_items(
    path_id: UUID,
    payload: LearningPathItemsReplace,
    admin: AdminUser,
    session: SessionDependency,
) -> LearningPathResponse:
    return await LearningPathService(session).replace_items(path_id, admin.company_id, payload)


@router.post("/learning-paths/{path_id}/assignments", response_model=LearningPathAssignmentResult)
async def assign_learning_path(
    path_id: UUID,
    payload: LearningPathAssignmentCreate,
    admin: AdminUser,
    session: SessionDependency,
) -> LearningPathAssignmentResult:
    return await LearningPathService(session).assign(path_id, admin.company_id, payload)


@router.delete("/learning-paths/{path_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_learning_path(
    path_id: UUID, admin: AdminUser, session: SessionDependency
) -> Response:
    await LearningPathService(session).delete(path_id, admin.company_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/employee/learning-paths", response_model=list[LearningPathResponse])
async def list_employee_learning_paths(
    employee: EmployeeUser, session: SessionDependency
) -> list[LearningPathResponse]:
    return await LearningPathService(session).list_employee(employee.company_id, employee.id)


@router.get("/employee/learning-paths/{path_id}", response_model=LearningPathResponse)
async def get_employee_learning_path(
    path_id: UUID, employee: EmployeeUser, session: SessionDependency
) -> LearningPathResponse:
    return await LearningPathService(session).get_employee(
        path_id, employee.company_id, employee.id
    )
