from fastapi import APIRouter
from fastapi.responses import Response

from app.api.dependencies import AdminUser, SessionDependency
from app.schemas.reports import ManagerAnalyticsResponse
from app.services.reports import ReportService

router = APIRouter(tags=["Reports"])


@router.get("/admin/analytics", response_model=ManagerAnalyticsResponse)
async def manager_analytics(
    admin: AdminUser, session: SessionDependency
) -> ManagerAnalyticsResponse:
    return await ReportService(session).analytics(admin.company_id)


@router.get("/admin/reports/progress.csv", response_class=Response)
async def export_progress(admin: AdminUser, session: SessionDependency) -> Response:
    return Response(
        content=await ReportService(session).progress_csv(admin.company_id),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="workflix-progresso.csv"'},
    )


@router.get("/admin/reports/certificates.csv", response_class=Response)
async def export_certificates(admin: AdminUser, session: SessionDependency) -> Response:
    return Response(
        content=await ReportService(session).certificates_csv(admin.company_id),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="workflix-certificados.csv"'},
    )
