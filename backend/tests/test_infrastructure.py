import asyncio
import json
from io import BytesIO

import pytest
from app.core.config import get_settings
from app.core.rate_limit import MemoryRateLimiter, RedisRateLimiter, get_rate_limiter
from app.core.secrets import AWSSecretsManagerLoader, load_managed_secrets
from app.main import app
from app.storage.base import StorageError
from app.storage.local import LocalObjectStorage
from app.storage.s3 import S3ObjectStorage

from conftest import ApiContext


def test_memory_rate_limiter_enforces_a_fixed_window() -> None:
    async def exercise() -> None:
        limiter = MemoryRateLimiter()
        first = await limiter.consume("login:test", limit=2, window_seconds=60)
        second = await limiter.consume("login:test", limit=2, window_seconds=60)
        blocked = await limiter.consume("login:test", limit=2, window_seconds=60)

        assert first.allowed is True
        assert second.remaining == 0
        assert blocked.allowed is False
        assert blocked.retry_after > 0

    asyncio.run(exercise())


def test_redis_rate_limiter_uses_atomic_script() -> None:
    class FakeRedis:
        def __init__(self) -> None:
            self.calls: list[tuple[object, ...]] = []

        async def eval(self, *args):
            self.calls.append(args)
            return [2, 47]

    async def exercise() -> None:
        client = FakeRedis()
        result = await RedisRateLimiter(client).consume("login:test", limit=3, window_seconds=60)

        assert result.allowed is True
        assert result.remaining == 1
        assert result.retry_after == 47
        assert client.calls[0][1:] == (1, "login:test", 60)

    asyncio.run(exercise())


def test_login_endpoint_returns_429_with_retry_after(
    api: ApiContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    limiter = MemoryRateLimiter()
    monkeypatch.setattr(get_settings(), "rate_limit_login_per_minute", 2)
    app.dependency_overrides[get_rate_limiter] = lambda: limiter

    payload = {"email": "nobody@example.com", "password": "incorrect-password"}
    assert api.client.post("/api/v1/auth/login", json=payload).status_code == 401
    assert api.client.post("/api/v1/auth/login", json=payload).status_code == 401
    blocked = api.client.post("/api/v1/auth/login", json=payload)

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"
    assert int(blocked.headers["retry-after"]) > 0


def test_managed_secrets_are_whitelisted_and_do_not_override_environment() -> None:
    class FakeLoader:
        def load(self) -> dict[str, str]:
            return {
                "JWT_SECRET": "manager-secret-that-is-at-least-32-characters",
                "DATABASE_URL": "postgresql://managed",
                "UNSAFE_KEY": "ignored",
            }

    environ = {
        "SECRETS_MANAGER_PROVIDER": "aws",
        "JWT_SECRET": "existing-secret-that-is-at-least-32-characters",
    }
    load_managed_secrets(environ, loader=FakeLoader())

    assert environ["JWT_SECRET"].startswith("existing")
    assert environ["DATABASE_URL"] == "postgresql://managed"
    assert "UNSAFE_KEY" not in environ


def test_aws_secrets_loader_reads_json_secret() -> None:
    class FakeClient:
        def get_secret_value(self, **kwargs):
            assert kwargs == {"SecretId": "workflix/staging"}
            return {"SecretString": json.dumps({"JWT_SECRET": "managed-value"})}

    loader = AWSSecretsManagerLoader(
        secret_id="workflix/staging", region="us-east-1", client=FakeClient()
    )

    assert loader.load() == {"JWT_SECRET": "managed-value"}


def test_local_storage_round_trip_and_traversal_protection(tmp_path) -> None:
    async def exercise() -> None:
        storage = LocalObjectStorage(tmp_path)
        await storage.put("company/training.pdf", b"%PDF-test", content_type="application/pdf")
        stored = await storage.get("company/training.pdf")

        assert stored.data == b"%PDF-test"
        with pytest.raises(StorageError):
            await storage.put("../escape.pdf", b"bad", content_type="application/pdf")

        await storage.delete("company/training.pdf")
        assert not (tmp_path / "company" / "training.pdf").exists()

    asyncio.run(exercise())


def test_s3_storage_preserves_bucket_key_and_encryption() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.put: dict = {}
            self.deleted: dict = {}

        def put_object(self, **kwargs):
            self.put = kwargs

        def get_object(self, **kwargs):
            assert kwargs == {"Bucket": "workflix", "Key": "tenant/material.pdf"}
            return {"Body": BytesIO(b"%PDF-test"), "ContentType": "application/pdf"}

        def delete_object(self, **kwargs):
            self.deleted = kwargs

    async def exercise() -> None:
        client = FakeClient()
        storage = S3ObjectStorage(
            bucket="workflix",
            region="us-east-1",
            server_side_encryption="AES256",
            client=client,
        )
        await storage.put("tenant/material.pdf", b"%PDF-test", content_type="application/pdf")
        stored = await storage.get("tenant/material.pdf")
        await storage.delete("tenant/material.pdf")

        assert client.put["Bucket"] == "workflix"
        assert client.put["ServerSideEncryption"] == "AES256"
        assert stored.data == b"%PDF-test"
        assert client.deleted == {"Bucket": "workflix", "Key": "tenant/material.pdf"}

    asyncio.run(exercise())
