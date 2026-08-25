import asyncio
from datetime import date

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import Role, User

from conftest import ApiContext, create_company_user, login


async def add_employee(api: ApiContext, company_id, email: str) -> User:
    async with api.sessions() as session:
        employee = User(
            company_id=company_id,
            email=email,
            full_name="Demo Employee",
            cpf="90000000680",
            password_hash=hash_password("StrongDemo@2026"),
            role=Role.EMPLOYEE,
        )
        session.add(employee)
        await session.commit()
        return employee


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def training_payload(*, status: str = "PUBLISHED", training_type: str = "ARTICLE") -> dict:
    payload = {
        "title": "Security essentials",
        "description": "A practical introduction to secure work habits.",
        "type": training_type,
        "content": "Use unique passwords and report suspicious activity.",
        "estimated_minutes": 12,
        "status": status,
    }
    if training_type == "VIDEO":
        payload["video_url"] = "https://example.com/video"
    return payload


def test_admin_crud_assignment_and_employee_progress(api: ApiContext) -> None:
    company, admin = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="NovaTech",
            email="admin@novatech.example.com",
            role=Role.ADMIN,
        )
    )
    employee = asyncio.run(add_employee(api, company.id, "employee@novatech.example.com"))
    admin_token = login(api.client, admin.email)["access_token"]
    employee_token = login(api.client, employee.email)["access_token"]

    created = api.client.post(
        "/api/v1/trainings", json=training_payload(), headers=auth(admin_token)
    )
    assert created.status_code == 201, created.text
    training_id = created.json()["id"]

    assigned = api.client.post(
        f"/api/v1/trainings/{training_id}/assignments",
        json={"employee_ids": [str(employee.id)], "due_date": str(date(2026, 9, 1))},
        headers=auth(admin_token),
    )
    assert assigned.status_code == 200
    assert assigned.json() == {"assigned": 1, "updated": 0}

    catalog = api.client.get("/api/v1/employee/trainings", headers=auth(employee_token))
    assert catalog.status_code == 200
    assert len(catalog.json()) == 1
    assert catalog.json()[0]["progress_percent"] is None

    progressed = api.client.patch(
        f"/api/v1/employee/trainings/{training_id}/progress",
        json={"progress_percent": 60},
        headers=auth(employee_token),
    )
    assert progressed.status_code == 200
    assert progressed.json()["progress_percent"] == 60

    regressed = api.client.patch(
        f"/api/v1/employee/trainings/{training_id}/progress",
        json={"progress_percent": 20},
        headers=auth(employee_token),
    )
    assert regressed.json()["progress_percent"] == 60

    dashboard = api.client.get("/api/v1/admin/dashboard", headers=auth(admin_token))
    assert dashboard.status_code == 200
    assert dashboard.json()["active_assignments"] == 1
    assert dashboard.json()["completion_percent"] == 0


def test_training_tenant_isolation_and_draft_visibility(api: ApiContext) -> None:
    company_a, admin_a = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Company A",
            email="admin-a@company-a.example.com",
            role=Role.ADMIN,
        )
    )
    employee_a = asyncio.run(add_employee(api, company_a.id, "employee-a@company-a.example.com"))
    _, admin_b = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Company B",
            email="admin-b@company-b.example.com",
            role=Role.ADMIN,
        )
    )
    token_a = login(api.client, admin_a.email)["access_token"]
    token_b = login(api.client, admin_b.email)["access_token"]
    employee_token = login(api.client, employee_a.email)["access_token"]
    training = api.client.post(
        "/api/v1/trainings",
        json=training_payload(status="DRAFT"),
        headers=auth(token_a),
    ).json()

    forbidden_by_absence = api.client.get(
        f"/api/v1/trainings/{training['id']}", headers=auth(token_b)
    )
    assert forbidden_by_absence.status_code == 404
    assert api.client.get("/api/v1/trainings", headers=auth(token_b)).json() == []

    api.client.post(
        f"/api/v1/trainings/{training['id']}/assignments",
        json={"employee_ids": [str(employee_a.id)]},
        headers=auth(token_a),
    )
    assert api.client.get("/api/v1/employee/trainings", headers=auth(employee_token)).json() == []


def test_pdf_upload_requires_valid_pdf_and_authorized_assignment(api: ApiContext, tmp_path) -> None:
    get_settings().upload_directory = tmp_path
    company, admin = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="PDF Corp",
            email="admin@pdf.example.com",
            role=Role.ADMIN,
        )
    )
    employee = asyncio.run(add_employee(api, company.id, "employee@pdf.example.com"))
    admin_token = login(api.client, admin.email)["access_token"]
    employee_token = login(api.client, employee.email)["access_token"]
    training_id = api.client.post(
        "/api/v1/trainings",
        json=training_payload(status="PUBLISHED"),
        headers=auth(admin_token),
    ).json()["id"]

    invalid = api.client.post(
        f"/api/v1/trainings/{training_id}/pdf",
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
        headers=auth(admin_token),
    )
    assert invalid.status_code == 415

    uploaded = api.client.post(
        f"/api/v1/trainings/{training_id}/pdf",
        files={"file": ("guide.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
        headers=auth(admin_token),
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["has_pdf"] is True
    assert uploaded.json()["type"] == "PDF"
    assert (
        api.client.get(
            f"/api/v1/trainings/{training_id}/pdf", headers=auth(employee_token)
        ).status_code
        == 404
    )

    api.client.post(
        f"/api/v1/trainings/{training_id}/assignments",
        json={"employee_ids": [str(employee.id)]},
        headers=auth(admin_token),
    )
    downloaded = api.client.get(
        f"/api/v1/trainings/{training_id}/pdf", headers=auth(employee_token)
    )
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"%PDF-")
