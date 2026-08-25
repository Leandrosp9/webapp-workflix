from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from secrets import token_hex
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models import (
    Certificate,
    CertificateType,
    Company,
    LearningPath,
    LearningPathAssignment,
    LearningPathItem,
    LearningPathStatus,
    Training,
    TrainingAssignment,
    TrainingStatus,
    User,
    UserProgress,
)
from app.schemas.learning_paths import CertificateResponse, CertificateVerification


def format_cpf(cpf: str) -> str:
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def mask_cpf(cpf: str | None) -> str | None:
    return f"***.{cpf[3:6]}.{cpf[6:9]}-**" if cpf else None


class CertificateService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _response(certificate: Certificate) -> CertificateResponse:
        return CertificateResponse.model_validate(certificate, from_attributes=True)

    async def issue_training(
        self,
        *,
        company_id: UUID,
        user_id: UUID,
        training_id: UUID,
    ) -> Certificate | None:
        existing = await self._session.scalar(
            select(Certificate).where(
                Certificate.training_id == training_id,
                Certificate.user_id == user_id,
            )
        )
        if existing is not None:
            return existing

        training = await self._session.scalar(
            select(Training)
            .join(
                TrainingAssignment,
                TrainingAssignment.training_id == Training.id,
            )
            .join(
                UserProgress,
                (UserProgress.training_id == Training.id)
                & (UserProgress.user_id == TrainingAssignment.employee_id),
            )
            .where(
                Training.id == training_id,
                Training.company_id == company_id,
                Training.status == TrainingStatus.PUBLISHED,
                TrainingAssignment.company_id == company_id,
                TrainingAssignment.employee_id == user_id,
                UserProgress.company_id == company_id,
                UserProgress.progress_percent == 100,
            )
        )
        if training is None:
            return None

        user = await self._session.scalar(
            select(User).where(User.id == user_id, User.company_id == company_id)
        )
        company = await self._session.scalar(select(Company).where(Company.id == company_id))
        if user is None or company is None:
            return None

        certificate = Certificate(
            company_id=company_id,
            learning_path_id=None,
            training_id=training.id,
            certificate_type=CertificateType.TRAINING,
            user_id=user_id,
            code=f"WFX-{token_hex(16).upper()}",
            user_full_name=user.full_name,
            user_email=user.email,
            user_cpf=user.cpf,
            company_name=company.name,
            learning_path_title=training.title,
            workload_minutes=training.estimated_minutes,
            issued_at=datetime.now(UTC),
        )
        try:
            async with self._session.begin_nested():
                self._session.add(certificate)
                await self._session.flush()
        except IntegrityError:
            return await self._session.scalar(
                select(Certificate).where(
                    Certificate.training_id == training_id,
                    Certificate.user_id == user_id,
                )
            )
        return certificate

    async def issue_eligible(
        self,
        *,
        company_id: UUID,
        user_id: UUID,
        learning_path_ids: list[UUID] | None = None,
    ) -> list[Certificate]:
        query = (
            select(LearningPath)
            .join(
                LearningPathAssignment,
                LearningPathAssignment.learning_path_id == LearningPath.id,
            )
            .options(selectinload(LearningPath.items).selectinload(LearningPathItem.training))
            .where(
                LearningPath.company_id == company_id,
                LearningPath.status == LearningPathStatus.PUBLISHED,
                LearningPathAssignment.company_id == company_id,
                LearningPathAssignment.employee_id == user_id,
            )
        )
        if learning_path_ids is not None:
            query = query.where(LearningPath.id.in_(learning_path_ids))
        paths = (await self._session.scalars(query)).unique().all()
        if not paths:
            return []

        user = await self._session.scalar(
            select(User).where(User.id == user_id, User.company_id == company_id)
        )
        company = await self._session.scalar(select(Company).where(Company.id == company_id))
        if user is None or company is None:
            return []

        issued: list[Certificate] = []
        for learning_path in paths:
            existing = await self._session.scalar(
                select(Certificate).where(
                    Certificate.learning_path_id == learning_path.id,
                    Certificate.user_id == user_id,
                )
            )
            if existing is not None:
                continue
            required_items = [item for item in learning_path.items if item.required]
            if not required_items:
                continue
            required_ids = [item.training_id for item in required_items]
            completed_ids = set(
                (
                    await self._session.scalars(
                        select(UserProgress.training_id).where(
                            UserProgress.company_id == company_id,
                            UserProgress.user_id == user_id,
                            UserProgress.training_id.in_(required_ids),
                            UserProgress.progress_percent == 100,
                        )
                    )
                ).all()
            )
            if completed_ids != set(required_ids):
                continue
            certificate = Certificate(
                company_id=company_id,
                learning_path_id=learning_path.id,
                training_id=None,
                certificate_type=CertificateType.LEARNING_PATH,
                user_id=user_id,
                code=f"WFX-{token_hex(16).upper()}",
                user_full_name=user.full_name,
                user_email=user.email,
                user_cpf=user.cpf,
                company_name=company.name,
                learning_path_title=learning_path.title,
                workload_minutes=sum(item.training.estimated_minutes for item in required_items),
                issued_at=datetime.now(UTC),
            )
            try:
                async with self._session.begin_nested():
                    self._session.add(certificate)
                    await self._session.flush()
            except IntegrityError:
                continue
            issued.append(certificate)
        return issued

    async def list_employee(self, company_id: UUID, user_id: UUID) -> list[CertificateResponse]:
        certificates = (
            await self._session.scalars(
                select(Certificate)
                .where(Certificate.company_id == company_id, Certificate.user_id == user_id)
                .order_by(Certificate.issued_at.desc())
            )
        ).all()
        return [self._response(item) for item in certificates]

    async def list_admin(self, company_id: UUID) -> list[CertificateResponse]:
        certificates = (
            await self._session.scalars(
                select(Certificate)
                .where(Certificate.company_id == company_id)
                .order_by(Certificate.issued_at.desc())
            )
        ).all()
        return [self._response(item) for item in certificates]

    async def get_authorized(
        self,
        certificate_id: UUID,
        *,
        company_id: UUID,
        user_id: UUID,
        is_admin: bool,
    ) -> Certificate:
        query = select(Certificate).where(
            Certificate.id == certificate_id, Certificate.company_id == company_id
        )
        if not is_admin:
            query = query.where(Certificate.user_id == user_id)
        certificate = await self._session.scalar(query)
        if certificate is None:
            raise AppError(
                code="CERTIFICATE_NOT_FOUND", message="Certificate not found.", status_code=404
            )
        return certificate

    async def verify(self, code: str) -> CertificateVerification:
        certificate = await self._session.scalar(
            select(Certificate).where(Certificate.code == code.strip().upper())
        )
        if certificate is None:
            raise AppError(
                code="CERTIFICATE_NOT_FOUND", message="Certificate not found.", status_code=404
            )
        return CertificateVerification(
            code=certificate.code,
            certificate_type=certificate.certificate_type,
            user_full_name=certificate.user_full_name,
            user_cpf_masked=mask_cpf(certificate.user_cpf),
            company_name=certificate.company_name,
            learning_path_title=certificate.learning_path_title,
            title=certificate.title,
            workload_minutes=certificate.workload_minutes,
            issued_at=certificate.issued_at,
        )

    @staticmethod
    def render_pdf(certificate: Certificate) -> bytes:
        buffer = BytesIO()
        page_size = landscape(A4)
        width, height = page_size
        pdf = canvas.Canvas(buffer, pagesize=page_size, pageCompression=1)
        pdf.setTitle(f"Certificado Workflix - {certificate.user_full_name}")
        pdf.setAuthor("Workflix")
        pdf.setSubject(certificate.learning_path_title)

        navy = colors.HexColor("#13243A")
        blue = colors.HexColor("#3A78F2")
        cyan = colors.HexColor("#5DDBE8")
        ink = colors.HexColor("#243247")
        muted = colors.HexColor("#66758A")
        paper = colors.HexColor("#F7FAFC")

        pdf.setFillColor(paper)
        pdf.rect(0, 0, width, height, stroke=0, fill=1)
        pdf.setFillColor(navy)
        pdf.rect(0, height - 76, width, 76, stroke=0, fill=1)
        pdf.setFillColor(blue)
        pdf.rect(0, 0, 18, height, stroke=0, fill=1)
        pdf.setFillColor(cyan)
        pdf.rect(18, 0, 5, height, stroke=0, fill=1)

        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 19)
        pdf.drawString(50, height - 47, "WORKFLIX")
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(width - 45, height - 45, "ACADEMIA CORPORATIVA")

        pdf.setFillColor(blue)
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawCentredString(width / 2, height - 130, "CERTIFICADO DE CONCLUSÃO")
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 11)
        pdf.drawCentredString(width / 2, height - 167, "Certificamos que")

        name_size = 30
        while stringWidth(certificate.user_full_name, "Helvetica-Bold", name_size) > width - 150:
            name_size -= 1
        pdf.setFillColor(ink)
        pdf.setFont("Helvetica-Bold", name_size)
        pdf.drawCentredString(width / 2, height - 211, certificate.user_full_name)
        pdf.setStrokeColor(cyan)
        pdf.setLineWidth(2)
        pdf.line(150, height - 226, width - 150, height - 226)

        if certificate.user_cpf:
            pdf.setFillColor(muted)
            pdf.setFont("Helvetica", 10)
            pdf.drawCentredString(
                width / 2, height - 246, f"CPF {format_cpf(certificate.user_cpf)}"
            )

        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 11)
        completion_text = (
            f"concluiu com êxito o treinamento da {certificate.company_name}"
            if certificate.certificate_type == CertificateType.TRAINING
            else f"concluiu com êxito a trilha de aprendizagem da {certificate.company_name}"
        )
        pdf.drawCentredString(width / 2, height - 263, completion_text)
        title_size = 20
        while (
            stringWidth(certificate.learning_path_title, "Helvetica-Bold", title_size) > width - 130
        ):
            title_size -= 1
        pdf.setFillColor(navy)
        pdf.setFont("Helvetica-Bold", title_size)
        pdf.drawCentredString(width / 2, height - 303, certificate.learning_path_title)

        hours = certificate.workload_minutes / 60
        workload = f"{hours:g} hora{'s' if hours != 1 else ''}"
        issued = certificate.issued_at.strftime("%d/%m/%Y")
        pdf.setFillColor(ink)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawCentredString(width / 2 - 110, 145, "CARGA HORÁRIA")
        pdf.drawCentredString(width / 2 + 110, 145, "EMISSÃO")
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 11)
        pdf.drawCentredString(width / 2 - 110, 126, workload)
        pdf.drawCentredString(width / 2 + 110, 126, issued)

        pdf.setStrokeColor(colors.HexColor("#D7E0EA"))
        pdf.line(70, 92, width - 70, 92)
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 8)
        pdf.drawString(70, 70, "Código de validação")
        pdf.setFillColor(ink)
        pdf.setFont("Courier-Bold", 9)
        pdf.drawString(70, 54, certificate.code)
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica", 8)
        pdf.drawRightString(width - 70, 58, "Autenticidade verificável no Workflix")

        pdf.showPage()
        pdf.save()
        return buffer.getvalue()
