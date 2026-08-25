import asyncio
from io import BytesIO

from app.core.config import get_settings
from app.models import Role
from PIL import Image

from conftest import ApiContext, create_company_user, login


def test_login_me_refresh_and_logout(api: ApiContext) -> None:
    asyncio.run(
        create_company_user(
            api.sessions,
            company_name="NovaTech",
            email="admin@workflix.demo",
            role=Role.ADMIN,
        )
    )

    tokens = login(api.client, "admin@workflix.demo")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = api.client.get("/api/v1/auth/me", headers=headers)

    assert me.status_code == 200
    assert me.json()["email"] == "admin@workflix.demo"
    assert me.json()["role"] == "ADMIN"

    rotated = api.client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert rotated.status_code == 200
    rotated_tokens = rotated.json()
    assert rotated_tokens["refresh_token"] != tokens["refresh_token"]
    assert (
        api.client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        ).status_code
        == 401
    )

    logout_response = api.client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": rotated_tokens["refresh_token"]},
    )
    assert logout_response.status_code == 204
    assert (
        api.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": rotated_tokens["refresh_token"]},
        ).status_code
        == 401
    )


def test_invalid_credentials_use_safe_error(api: ApiContext) -> None:
    response = api.client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "incorrect-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_employee_cannot_manage_users(api: ApiContext) -> None:
    asyncio.run(
        create_company_user(
            api.sessions,
            company_name="NovaTech",
            email="employee@workflix.demo",
            role=Role.EMPLOYEE,
        )
    )
    tokens = login(api.client, "employee@workflix.demo")

    response = api.client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_admin_only_lists_own_company_employees(api: ApiContext) -> None:
    company_a, _ = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Company A",
            email="admin-a@example.com",
            role=Role.ADMIN,
        )
    )
    asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Company B",
            email="employee-b@example.com",
            role=Role.EMPLOYEE,
        )
    )
    admin_tokens = login(api.client, "admin-a@example.com")
    headers = {"Authorization": f"Bearer {admin_tokens['access_token']}"}

    created = api.client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "employee-a@example.com",
            "full_name": "Employee A",
            "cpf": "900.000.006-80",
            "password": "StrongEmployee@2026",
        },
    )
    listed = api.client.get("/api/v1/users", headers=headers)

    assert created.status_code == 201
    assert created.json()["company_id"] == str(company_a.id)
    assert created.json()["cpf"] == "90000000680"
    assert listed.status_code == 200
    assert [user["email"] for user in listed.json()] == ["employee-a@example.com"]


def test_admin_edits_and_deactivates_own_company_employee(api: ApiContext) -> None:
    asyncio.run(
        create_company_user(
            api.sessions,
            company_name="NovaTech",
            email="admin@workflix.demo",
            role=Role.ADMIN,
        )
    )
    _, external_employee = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="External Company",
            email="external@example.com",
            role=Role.EMPLOYEE,
        )
    )
    tokens = login(api.client, "admin@workflix.demo")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    created = api.client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "employee@workflix.demo",
            "full_name": "Employee Demo",
            "cpf": "900.000.007-60",
            "password": "StrongEmployee@2026",
        },
    )

    updated = api.client.patch(
        f"/api/v1/users/{created.json()['id']}",
        headers=headers,
        json={
            "email": "renata.alves@workflix.demo",
            "full_name": "Renata Alves",
            "cpf": "900.000.008-41",
            "is_active": False,
        },
    )
    external = api.client.patch(
        f"/api/v1/users/{external_employee.id}",
        headers=headers,
        json={"is_active": False},
    )

    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Renata Alves"
    assert updated.json()["email"] == "renata.alves@workflix.demo"
    assert updated.json()["cpf"] == "90000000841"
    assert updated.json()["is_active"] is False
    assert external.status_code == 404
    assert (
        api.client.post(
            "/api/v1/auth/login",
            json={
                "email": "renata.alves@workflix.demo",
                "password": "StrongEmployee@2026",
            },
        ).status_code
        == 401
    )


def test_admin_manages_private_employee_avatar(api: ApiContext, tmp_path) -> None:
    get_settings().upload_directory = tmp_path
    _company, admin = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Avatar Company",
            email="admin@avatar.example.com",
            role=Role.ADMIN,
        )
    )
    _outside_company, outside_admin = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Outside Avatar",
            email="admin@outside-avatar.example.com",
            role=Role.ADMIN,
        )
    )
    admin_headers = {"Authorization": f"Bearer {login(api.client, admin.email)['access_token']}"}
    created = api.client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": "employee@avatar.example.com",
            "full_name": "Camila Ferreira",
            "cpf": "90000001066",
            "password": "StrongEmployee@2026",
        },
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]

    invalid = api.client.post(
        f"/api/v1/users/{user_id}/avatar",
        headers=admin_headers,
        files={"file": ("avatar.png", b"not-an-image", "image/png")},
    )
    assert invalid.status_code == 415

    image = Image.new("RGB", (720, 480), color=(31, 121, 255))
    avatar = BytesIO()
    image.save(avatar, format="PNG")
    uploaded = api.client.post(
        f"/api/v1/users/{user_id}/avatar",
        headers=admin_headers,
        files={"file": ("camila.png", avatar.getvalue(), "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["has_avatar"] is True

    employee_token = login(api.client, "employee@avatar.example.com", "StrongEmployee@2026")[
        "access_token"
    ]
    employee_headers = {"Authorization": f"Bearer {employee_token}"}
    downloaded = api.client.get(
        f"/api/v1/users/{user_id}/avatar",
        headers=employee_headers,
    )
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "image/webp"
    assert downloaded.content.startswith(b"RIFF")

    outside_headers = {
        "Authorization": f"Bearer {login(api.client, outside_admin.email)['access_token']}"
    }
    assert (
        api.client.get(f"/api/v1/users/{user_id}/avatar", headers=outside_headers).status_code
        == 404
    )
    removed = api.client.delete(f"/api/v1/users/{user_id}/avatar", headers=admin_headers)
    assert removed.status_code == 204
    assert (
        api.client.get(f"/api/v1/users/{user_id}/avatar", headers=employee_headers).status_code
        == 404
    )
