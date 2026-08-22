from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import Response

from app.api.dependencies import AdminUser, CurrentUser, EmployeeUser, SessionDependency
from app.models import Role
from app.schemas.learning_paths import CertificateResponse, CertificateVerification
from app.services.certificates import CertificateService

router = APIRouter(tags=["Certificates"])


@router.get("/certificates/verify/{code}", response_model=CertificateVerification)
async def verify_certificate(code: str, session: SessionDependency) -> CertificateVerification:
    return await CertificateService(session).verify(code)


@router.get("/employee/certificates", response_model=list[CertificateResponse])
async def list_employee_certificates(
    employee: EmployeeUser, session: SessionDependency
) -> list[CertificateResponse]:
    return await CertificateService(session).list_employee(employee.company_id, employee.id)


@router.get("/certificates", response_model=list[CertificateResponse])
async def list_certificates(
    admin: AdminUser, session: SessionDependency
) -> list[CertificateResponse]:
    return await CertificateService(session).list_admin(admin.company_id)


@router.get("/certificates/{certificate_id}/pdf", response_class=Response)
async def download_certificate(
    certificate_id: UUID, user: CurrentUser, session: SessionDependency
) -> Response:
    service = CertificateService(session)
    certificate = await service.get_authorized(
        certificate_id,
        company_id=user.company_id,
        user_id=user.id,
        is_admin=user.role == Role.ADMIN,
    )
    return Response(
        content=service.render_pdf(certificate),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="workflix-{certificate.id}.pdf"'},
    )
