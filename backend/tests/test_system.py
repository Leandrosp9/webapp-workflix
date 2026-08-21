from app.db.health import DatabaseProbe, probe_database
from app.main import app
from fastapi.testclient import TestClient


def test_health_returns_public_service_metadata() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/system/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "workflix-api",
        "version": "0.1.0",
        "environment": "test",
    }
    assert response.headers["X-Request-ID"]


def test_safe_correlation_id_is_preserved() -> None:
    request_id = "portfolio-check-123"

    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": request_id})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_invalid_correlation_id_is_replaced() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "unsafe id with spaces"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "unsafe id with spaces"


def test_ready_reports_available_database() -> None:
    async def available_database() -> DatabaseProbe:
        return DatabaseProbe(database_available=True)

    app.dependency_overrides[probe_database] = available_database
    try:
        with TestClient(app) as client:
            response = client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {"database": "available"},
    }


def test_ready_reports_unavailable_database() -> None:
    async def unavailable_database() -> DatabaseProbe:
        return DatabaseProbe(database_available=False)

    app.dependency_overrides[probe_database] = unavailable_database
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/system/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "dependencies": {"database": "unavailable"},
    }


def test_not_found_uses_stable_error_envelope() -> None:
    with TestClient(app) as client:
        response = client.get("/does-not-exist")

    assert response.status_code == 404
    payload = response.json()["error"]
    assert payload["code"] == "NOT_FOUND"
    assert payload["message"] == "Not Found"
    assert payload["request_id"] == response.headers["X-Request-ID"]
