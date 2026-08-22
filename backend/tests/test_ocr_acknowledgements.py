import asyncio
from uuid import UUID, uuid4

import pymupdf
import pytest
from app.core.config import get_settings
from app.models import DocumentPage, DocumentStatus, DocumentVersion, Role
from app.rag.chunker import ExtractionMethod
from app.rag.extractor import PDFExtractionError, PyMuPDFExtractor
from app.rag.jobs import DocumentProcessingService
from app.storage.local import LocalObjectStorage
from sqlalchemy import select

from conftest import ApiContext, create_company_user, login
from test_documents_rag import FakeEmbeddingProvider, pdf_bytes
from test_trainings import add_employee, auth, training_payload


class FakeOCR:
    def __init__(self, text: str = "Texto reconhecido por OCR") -> None:
        self.text = text
        self.calls = 0

    def extract(self, page: pymupdf.Page) -> str:
        del page
        self.calls += 1
        return self.text


def test_hybrid_extractor_uses_ocr_only_for_pages_without_native_text() -> None:
    ocr = FakeOCR()
    extractor = PyMuPDFExtractor(
        max_pages=10,
        ocr=ocr,
        min_native_chars=1,
        max_ocr_pages=2,
    )

    pages = extractor.extract(pdf_bytes("Texto nativo", ""))

    assert ocr.calls == 1
    assert pages[0].extraction_method == ExtractionMethod.NATIVE
    assert pages[1].extraction_method == ExtractionMethod.OCR
    assert pages[1].text == "Texto reconhecido por OCR"


def test_hybrid_extractor_bounds_ocr_work() -> None:
    extractor = PyMuPDFExtractor(
        max_pages=10,
        ocr=FakeOCR(),
        min_native_chars=1,
        max_ocr_pages=1,
    )

    with pytest.raises(PDFExtractionError, match="PDF_OCR_PAGE_LIMIT_EXCEEDED"):
        extractor.extract(pdf_bytes("", ""))


def test_processing_persists_ocr_provenance(api: ApiContext, tmp_path) -> None:
    get_settings().upload_directory = tmp_path
    _company, admin = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="OCR Corp",
            email="admin@ocr.example.com",
            role=Role.ADMIN,
        )
    )
    token = login(api.client, admin.email)["access_token"]
    training_id = api.client.post(
        "/api/v1/trainings",
        json=training_payload(status="PUBLISHED"),
        headers=auth(token),
    ).json()["id"]
    uploaded = api.client.post(
        f"/api/v1/trainings/{training_id}/pdf",
        files={"file": ("scan.pdf", pdf_bytes(""), "application/pdf")},
        headers=auth(token),
    ).json()
    version_id = UUID(uploaded["document_version"]["id"])

    async def process() -> tuple[DocumentStatus, int, str]:
        async with api.sessions() as session:
            outcome = await DocumentProcessingService(
                session,
                storage=LocalObjectStorage(tmp_path),
                embedding_provider=FakeEmbeddingProvider(),
                extractor=PyMuPDFExtractor(
                    max_pages=10,
                    ocr=FakeOCR("Procedimento reconhecido no documento digitalizado."),
                    min_native_chars=1,
                    max_ocr_pages=2,
                ),
            ).process(version_id)
            assert outcome.completed is True
            version = await session.get(DocumentVersion, version_id)
            page = await session.scalar(
                select(DocumentPage).where(DocumentPage.document_version_id == version_id)
            )
            assert version is not None
            assert page is not None
            return version.status, version.ocr_page_count, page.extraction_method

    status, ocr_page_count, method = asyncio.run(process())
    assert status == DocumentStatus.READY
    assert ocr_page_count == 1
    assert method == ExtractionMethod.OCR


def test_acknowledgement_is_versioned_idempotent_and_protected(api: ApiContext, tmp_path) -> None:
    get_settings().upload_directory = tmp_path
    company, admin = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Policy Corp",
            email="admin@policy.example.com",
            role=Role.ADMIN,
        )
    )
    employee = asyncio.run(add_employee(api, company.id, "employee@policy.example.com"))
    _other_company, outsider = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Outside Policy Corp",
            email="outsider@policy.example.com",
            role=Role.EMPLOYEE,
        )
    )
    admin_token = login(api.client, admin.email)["access_token"]
    employee_token = login(api.client, employee.email)["access_token"]
    outsider_token = login(api.client, outsider.email)["access_token"]
    training_id = api.client.post(
        "/api/v1/trainings",
        json=training_payload(status="PUBLISHED"),
        headers=auth(admin_token),
    ).json()["id"]
    api.client.post(
        f"/api/v1/trainings/{training_id}/assignments",
        json={"employee_ids": [str(employee.id)]},
        headers=auth(admin_token),
    )
    first = api.client.post(
        f"/api/v1/trainings/{training_id}/pdf",
        files={"file": ("policy-v1.pdf", pdf_bytes("Politica um"), "application/pdf")},
        headers=auth(admin_token),
    ).json()["document_version"]

    status = api.client.get(
        f"/api/v1/employee/trainings/{training_id}/acknowledgement",
        headers=auth(employee_token),
    )
    assert status.status_code == 200
    assert status.json()["acknowledged"] is False
    stale = api.client.post(
        f"/api/v1/employee/trainings/{training_id}/acknowledgement",
        json={"document_version_id": str(uuid4())},
        headers=auth(employee_token),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "DOCUMENT_VERSION_CHANGED"

    accepted = api.client.post(
        f"/api/v1/employee/trainings/{training_id}/acknowledgement",
        json={"document_version_id": first["id"]},
        headers=auth(employee_token),
    )
    repeated = api.client.post(
        f"/api/v1/employee/trainings/{training_id}/acknowledgement",
        json={"document_version_id": first["id"]},
        headers=auth(employee_token),
    )
    assert accepted.status_code == 200
    assert accepted.json()["acknowledged"] is True
    assert accepted.json()["acknowledgement"]["id"] == repeated.json()["acknowledgement"]["id"]
    assert accepted.json()["acknowledgement"]["document_checksum"] == first["checksum"]
    assert accepted.json()["acknowledgement"]["user_email"] == employee.email

    summary = api.client.get(
        f"/api/v1/trainings/{training_id}/acknowledgements",
        headers=auth(admin_token),
    ).json()
    assert summary["total_assigned"] == 1
    assert summary["acknowledged_current"] == 1
    assert summary["pending_current"] == 0
    assert summary["history"][0]["is_current"] is True

    second = api.client.post(
        f"/api/v1/trainings/{training_id}/pdf",
        files={"file": ("policy-v2.pdf", pdf_bytes("Politica dois"), "application/pdf")},
        headers=auth(admin_token),
    ).json()["document_version"]
    current_status = api.client.get(
        f"/api/v1/employee/trainings/{training_id}/acknowledgement",
        headers=auth(employee_token),
    ).json()
    assert current_status["version_number"] == 2
    assert current_status["document_version_id"] == second["id"]
    assert current_status["acknowledged"] is False
    old_version = api.client.post(
        f"/api/v1/employee/trainings/{training_id}/acknowledgement",
        json={"document_version_id": first["id"]},
        headers=auth(employee_token),
    )
    assert old_version.status_code == 409

    refreshed_summary = api.client.get(
        f"/api/v1/trainings/{training_id}/acknowledgements",
        headers=auth(admin_token),
    ).json()
    assert refreshed_summary["acknowledged_current"] == 0
    assert refreshed_summary["pending_current"] == 1
    assert refreshed_summary["history"][0]["is_current"] is False

    assert (
        api.client.get(
            f"/api/v1/employee/trainings/{training_id}/acknowledgement",
            headers=auth(outsider_token),
        ).status_code
        == 404
    )
    protected_delete = api.client.delete(
        f"/api/v1/trainings/{training_id}", headers=auth(admin_token)
    )
    assert protected_delete.status_code == 409
    assert protected_delete.json()["error"]["code"] == "TRAINING_HAS_ACKNOWLEDGEMENTS"
