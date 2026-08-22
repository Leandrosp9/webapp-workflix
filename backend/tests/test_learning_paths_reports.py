import asyncio
from datetime import date

from app.models import Role

from conftest import ApiContext, create_company_user, login
from test_trainings import add_employee, auth, training_payload


def create_training(api: ApiContext, token: str, title: str, minutes: int = 30) -> dict:
    payload = training_payload(status="PUBLISHED")
    payload.update({"title": title, "estimated_minutes": minutes})
    response = api.client.post("/api/v1/trainings", json=payload, headers=auth(token))
    assert response.status_code == 201, response.text
    return response.json()


def create_published_path(
    api: ApiContext, token: str, training_ids: list[str], title: str = "Trilha Essencial"
) -> dict:
    created = api.client.post(
        "/api/v1/learning-paths",
        json={"title": title, "description": "Uma jornada corporativa ordenada."},
        headers=auth(token),
    )
    assert created.status_code == 201, created.text
    path_id = created.json()["id"]
    replaced = api.client.put(
        f"/api/v1/learning-paths/{path_id}/items",
        json={"items": [{"training_id": item, "required": True} for item in training_ids]},
        headers=auth(token),
    )
    assert replaced.status_code == 200, replaced.text
    published = api.client.patch(
        f"/api/v1/learning-paths/{path_id}",
        json={"status": "PUBLISHED"},
        headers=auth(token),
    )
    assert published.status_code == 200, published.text
    return published.json()


def test_learning_path_completion_issues_verifiable_pdf_certificate(api: ApiContext) -> None:
    company, admin = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Learning Corp",
            email="admin@learning.example.com",
            role=Role.ADMIN,
        )
    )
    employee = asyncio.run(add_employee(api, company.id, "learner@learning.example.com"))
    admin_token = login(api.client, admin.email)["access_token"]
    employee_token = login(api.client, employee.email)["access_token"]
    first = create_training(api, admin_token, "Fundamentos", 30)
    second = create_training(api, admin_token, "Prática segura", 45)
    learning_path = create_published_path(api, admin_token, [first["id"], second["id"]])

    assigned = api.client.post(
        f"/api/v1/learning-paths/{learning_path['id']}/assignments",
        json={"employee_ids": [str(employee.id)], "due_date": str(date(2026, 9, 30))},
        headers=auth(admin_token),
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json() == {
        "assigned": 1,
        "updated": 0,
        "training_assignments_created": 2,
    }

    employee_path = api.client.get(
        f"/api/v1/employee/learning-paths/{learning_path['id']}",
        headers=auth(employee_token),
    )
    assert employee_path.status_code == 200, employee_path.text
    assert [item["available"] for item in employee_path.json()["items"]] == [True, False]
    assert employee_path.json()["progress_percent"] == 0

    api.client.patch(
        f"/api/v1/employee/trainings/{first['id']}/progress",
        json={"progress_percent": 100},
        headers=auth(employee_token),
    )
    midway = api.client.get(
        f"/api/v1/employee/learning-paths/{learning_path['id']}",
        headers=auth(employee_token),
    ).json()
    assert midway["progress_percent"] == 50
    assert [item["available"] for item in midway["items"]] == [True, True]
    assert (
        api.client.get("/api/v1/employee/certificates", headers=auth(employee_token)).json() == []
    )

    completed = api.client.patch(
        f"/api/v1/employee/trainings/{second['id']}/progress",
        json={"progress_percent": 100},
        headers=auth(employee_token),
    )
    assert completed.status_code == 200, completed.text
    certificates = api.client.get(
        "/api/v1/employee/certificates", headers=auth(employee_token)
    ).json()
    assert len(certificates) == 1
    certificate = certificates[0]
    assert certificate["workload_minutes"] == 75

    # Replaying completion cannot create duplicate evidence.
    api.client.patch(
        f"/api/v1/employee/trainings/{second['id']}/progress",
        json={"progress_percent": 100},
        headers=auth(employee_token),
    )
    assert (
        len(api.client.get("/api/v1/employee/certificates", headers=auth(employee_token)).json())
        == 1
    )

    verification = api.client.get(f"/api/v1/certificates/verify/{certificate['code']}")
    assert verification.status_code == 200
    assert verification.json()["learning_path_title"] == learning_path["title"]
    pdf = api.client.get(
        f"/api/v1/certificates/{certificate['id']}/pdf", headers=auth(employee_token)
    )
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-")
    _outside_company, outside_admin = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Outside Certificates",
            email="admin@outside-certificates.example.com",
            role=Role.ADMIN,
        )
    )
    outside_token = login(api.client, outside_admin.email)["access_token"]
    assert (
        api.client.get(
            f"/api/v1/certificates/{certificate['id']}/pdf", headers=auth(outside_token)
        ).status_code
        == 404
    )
    assert api.client.get("/api/v1/certificates", headers=auth(outside_token)).json() == []


def test_paths_and_certificates_are_tenant_isolated(api: ApiContext) -> None:
    company_a, admin_a = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Path Company A",
            email="admin@path-a.example.com",
            role=Role.ADMIN,
        )
    )
    employee_a = asyncio.run(add_employee(api, company_a.id, "learner@path-a.example.com"))
    _company_b, admin_b = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Path Company B",
            email="admin@path-b.example.com",
            role=Role.ADMIN,
        )
    )
    token_a = login(api.client, admin_a.email)["access_token"]
    token_b = login(api.client, admin_b.email)["access_token"]
    training = create_training(api, token_a, "Tenant content")
    learning_path = create_published_path(api, token_a, [training["id"]])

    assert (
        api.client.get(
            f"/api/v1/learning-paths/{learning_path['id']}", headers=auth(token_b)
        ).status_code
        == 404
    )
    assert api.client.get("/api/v1/learning-paths", headers=auth(token_b)).json() == []
    cross_assignment = api.client.post(
        f"/api/v1/learning-paths/{learning_path['id']}/assignments",
        json={"employee_ids": [str(employee_a.id)]},
        headers=auth(token_b),
    )
    assert cross_assignment.status_code == 404


def test_manager_analytics_and_csv_exports_use_real_scoped_data(api: ApiContext) -> None:
    company, admin = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Analytics Corp",
            email="admin@analytics.example.com",
            role=Role.ADMIN,
        )
    )
    employee = asyncio.run(add_employee(api, company.id, "analyst@analytics.example.com"))
    admin_token = login(api.client, admin.email)["access_token"]
    employee_token = login(api.client, employee.email)["access_token"]
    training = create_training(api, admin_token, "=SUM(A1:A2)", 60)
    learning_path = create_published_path(api, admin_token, [training["id"]], "Analytics")
    api.client.post(
        f"/api/v1/learning-paths/{learning_path['id']}/assignments",
        json={"employee_ids": [str(employee.id)]},
        headers=auth(admin_token),
    )
    api.client.patch(
        f"/api/v1/employee/trainings/{training['id']}/progress",
        json={"progress_percent": 100},
        headers=auth(employee_token),
    )
    outside_company, outside_admin = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Outside Analytics",
            email="admin@outside-analytics.example.com",
            role=Role.ADMIN,
        )
    )
    outside_employee = asyncio.run(
        add_employee(api, outside_company.id, "employee@outside-analytics.example.com")
    )
    outside_token = login(api.client, outside_admin.email)["access_token"]
    outside_training = create_training(api, outside_token, "Other tenant secret", 10)
    api.client.post(
        f"/api/v1/trainings/{outside_training['id']}/assignments",
        json={"employee_ids": [str(outside_employee.id)]},
        headers=auth(outside_token),
    )

    analytics = api.client.get("/api/v1/admin/analytics", headers=auth(admin_token))
    assert analytics.status_code == 200, analytics.text
    assert analytics.json()["kpis"] == {
        "total_employees": 1,
        "total_assignments": 1,
        "completed_assignments": 1,
        "completion_percent": 100,
        "overdue_assignments": 0,
        "learning_hours": 1.0,
        "certificates_issued": 1,
        "published_paths": 1,
    }
    progress_csv = api.client.get("/api/v1/admin/reports/progress.csv", headers=auth(admin_token))
    assert progress_csv.status_code == 200
    assert progress_csv.content.startswith(b"\xef\xbb\xbf")
    assert "'=SUM(A1:A2)" in progress_csv.content.decode("utf-8-sig")
    assert "Other tenant secret" not in progress_csv.content.decode("utf-8-sig")
    certificates_csv = api.client.get(
        "/api/v1/admin/reports/certificates.csv", headers=auth(admin_token)
    )
    assert certificates_csv.status_code == 200
    assert "WFX-" in certificates_csv.content.decode("utf-8-sig")
