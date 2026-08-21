from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import Response

from app.api.dependencies import AdminUser, CurrentUser, EmployeeUser, SessionDependency
from app.core.errors import AppError
from app.models import DocumentStatus
from app.rag.queue import DocumentQueueDependency
from app.schemas.trainings import (
    AdminDashboardResponse,
    DocumentVersionResponse,
    EmployeeHomeResponse,
    ProgressUpdate,
    TrainingAssignmentCreate,
    TrainingAssignmentResult,
    TrainingCreate,
    TrainingResponse,
    TrainingUpdate,
)
from app.services.documents import DocumentService
from app.services.trainings import TrainingService

router = APIRouter(tags=["Trainings"])


@router.get("/trainings", response_model=list[TrainingResponse])
async def list_trainings(admin: AdminUser, session: SessionDependency) -> list[TrainingResponse]:
    return await TrainingService(session).list_admin(admin.company_id)


@router.post("/trainings", response_model=TrainingResponse, status_code=status.HTTP_201_CREATED)
async def create_training(
    payload: TrainingCreate, admin: AdminUser, session: SessionDependency
) -> TrainingResponse:
    return await TrainingService(session).create(admin.company_id, admin.id, payload)


@router.get("/trainings/{training_id}", response_model=TrainingResponse)
async def get_training(
    training_id: UUID, admin: AdminUser, session: SessionDependency
) -> TrainingResponse:
    return await TrainingService(session).get_admin(training_id, admin.company_id)


@router.patch("/trainings/{training_id}", response_model=TrainingResponse)
async def update_training(
    training_id: UUID,
    payload: TrainingUpdate,
    admin: AdminUser,
    session: SessionDependency,
) -> TrainingResponse:
    return await TrainingService(session).update(training_id, admin.company_id, payload)


@router.delete("/trainings/{training_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_training(
    training_id: UUID, admin: AdminUser, session: SessionDependency
) -> Response:
    await TrainingService(session).delete(training_id, admin.company_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/trainings/{training_id}/assignments", response_model=TrainingAssignmentResult)
async def assign_training(
    training_id: UUID,
    payload: TrainingAssignmentCreate,
    admin: AdminUser,
    session: SessionDependency,
) -> TrainingAssignmentResult:
    return await TrainingService(session).assign(training_id, admin.company_id, payload)


@router.post("/trainings/{training_id}/pdf", response_model=TrainingResponse)
async def upload_training_pdf(
    training_id: UUID,
    admin: AdminUser,
    session: SessionDependency,
    file: Annotated[UploadFile, File()],
) -> TrainingResponse:
    response = await DocumentService(session).upload_version(
        training_id=training_id,
        company_id=admin.company_id,
        creator_id=admin.id,
        upload=file,
    )
    return response


@router.get(
    "/trainings/{training_id}/document",
    response_model=DocumentVersionResponse,
)
async def latest_training_document(
    training_id: UUID, user: CurrentUser, session: SessionDependency
) -> DocumentVersionResponse:
    return await DocumentService(session).latest_version(
        training_id=training_id, company_id=user.company_id, user=user
    )


@router.get(
    "/trainings/{training_id}/document/versions",
    response_model=list[DocumentVersionResponse],
)
async def list_training_document_versions(
    training_id: UUID, admin: AdminUser, session: SessionDependency
) -> list[DocumentVersionResponse]:
    return await DocumentService(session).list_versions(
        training_id=training_id, company_id=admin.company_id
    )


@router.post(
    "/trainings/{training_id}/document/process",
    response_model=DocumentVersionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def process_training_document(
    training_id: UUID,
    admin: AdminUser,
    session: SessionDependency,
    queue: DocumentQueueDependency,
) -> DocumentVersionResponse:
    version = await DocumentService(session).latest_model_for_admin(
        training_id=training_id, company_id=admin.company_id
    )
    if version.status != DocumentStatus.READY:
        scheduled = await queue.enqueue(session, version.id, company_id=version.company_id)
        if not scheduled:
            raise AppError(
                code="DOCUMENT_PROCESSING",
                message="Document processing is already queued or running.",
                status_code=409,
            )
        version.status = DocumentStatus.UPLOADED
        version.error_code = None
        await session.commit()
        await session.refresh(version)
    return DocumentVersionResponse.model_validate(version)


@router.get("/trainings/{training_id}/pdf", response_class=Response)
async def download_training_pdf(
    training_id: UUID, user: CurrentUser, session: SessionDependency
) -> Response:
    document = await DocumentService(session).pdf_object(
        training_id=training_id, company_id=user.company_id, user=user
    )
    return Response(
        content=document.data,
        media_type=document.content_type,
        headers={"Content-Disposition": f'inline; filename="{training_id}.pdf"'},
    )


@router.get("/employee/trainings", response_model=list[TrainingResponse])
async def list_employee_trainings(
    employee: EmployeeUser, session: SessionDependency
) -> list[TrainingResponse]:
    return await TrainingService(session).list_employee(employee.company_id, employee.id)


@router.get("/employee/trainings/{training_id}", response_model=TrainingResponse)
async def get_employee_training(
    training_id: UUID, employee: EmployeeUser, session: SessionDependency
) -> TrainingResponse:
    return await TrainingService(session).get_employee(
        training_id, employee.company_id, employee.id
    )


@router.patch("/employee/trainings/{training_id}/progress", response_model=TrainingResponse)
async def update_employee_progress(
    training_id: UUID,
    payload: ProgressUpdate,
    employee: EmployeeUser,
    session: SessionDependency,
) -> TrainingResponse:
    return await TrainingService(session).update_progress(
        training_id, employee.company_id, employee.id, payload.progress_percent
    )


@router.get("/employee/home", response_model=EmployeeHomeResponse)
async def employee_home(employee: EmployeeUser, session: SessionDependency) -> EmployeeHomeResponse:
    return await TrainingService(session).employee_home(employee.company_id, employee.id)


@router.get("/admin/dashboard", response_model=AdminDashboardResponse)
async def admin_dashboard(admin: AdminUser, session: SessionDependency) -> AdminDashboardResponse:
    return await TrainingService(session).dashboard(admin.company_id)
