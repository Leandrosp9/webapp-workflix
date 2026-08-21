import asyncio
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://workflix:workflix@localhost/workflix_test"
)
os.environ.setdefault("JWT_SECRET", "test-secret-that-is-at-least-32-characters")
os.environ["GEMINI_API_KEY"] = ""
os.environ["GROQ_API_KEY"] = ""
os.environ.setdefault("RATE_LIMIT_LOGIN_PER_MINUTE", "10000")
os.environ.setdefault("RATE_LIMIT_REFRESH_PER_MINUTE", "10000")
os.environ.setdefault("RATE_LIMIT_AI_PER_MINUTE", "10000")

import pytest
from app import models  # noqa: F401
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.models import Company, Role, User
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


@dataclass(frozen=True)
class ApiContext:
    client: TestClient
    sessions: async_sessionmaker[AsyncSession]


@pytest.fixture
def api() -> AsyncIterator[ApiContext]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            yield session

    asyncio.run(prepare())
    app.dependency_overrides[get_db_session] = override_session
    try:
        with TestClient(app) as client:
            yield ApiContext(client=client, sessions=sessions)
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


async def create_company_user(
    sessions: async_sessionmaker[AsyncSession],
    *,
    company_name: str,
    email: str,
    role: Role,
    password: str = "StrongDemo@2026",
) -> tuple[Company, User]:
    async with sessions() as session:
        company = Company(
            name=company_name,
            slug=f"{company_name.lower().replace(' ', '-')}-{uuid4().hex[:6]}",
        )
        session.add(company)
        await session.flush()
        user = User(
            company_id=company.id,
            email=email,
            full_name=email.split("@")[0].replace(".", " ").title(),
            password_hash=hash_password(password),
            role=role,
        )
        session.add(user)
        await session.commit()
        return company, user


def login(
    client: TestClient,
    email: str,
    password: str = "StrongDemo@2026",
) -> dict[str, Any]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()
