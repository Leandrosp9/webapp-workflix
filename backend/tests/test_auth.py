import asyncio

from app.models import Role

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
            "password": "StrongEmployee@2026",
        },
    )
    listed = api.client.get("/api/v1/users", headers=headers)

    assert created.status_code == 201
    assert created.json()["company_id"] == str(company_a.id)
    assert listed.status_code == 200
    assert [user["email"] for user in listed.json()] == ["employee-a@example.com"]
