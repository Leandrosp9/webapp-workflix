import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.models import Role

password_hash = PasswordHash.recommended()


class AccessTokenError(Exception):
    """The access token is expired, malformed, or has an invalid claim."""


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(*, user_id: UUID, company_id: UUID, role: Role) -> tuple[str, int]:
    settings = get_settings()
    now = datetime.now(UTC)
    expires_in = settings.jwt_access_expires_minutes * 60
    payload = {
        "sub": str(user_id),
        "company_id": str(company_id),
        "role": role.value,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "iss": "workflix",
        "aud": "workflix-api",
    }
    token = jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    return token, expires_in


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            audience="workflix-api",
            issuer="workflix",
        )
    except InvalidTokenError as exc:
        raise AccessTokenError("Invalid access token") from exc
    if payload.get("type") != "access" or not payload.get("sub"):
        raise AccessTokenError("Invalid access token claims")
    return payload


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
