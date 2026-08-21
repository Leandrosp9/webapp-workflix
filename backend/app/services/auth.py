from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.models import RefreshToken, User
from app.schemas.auth import AuthUser, TokenResponse


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def login(self, *, email: str, password: str) -> TokenResponse:
        user = await self._session.scalar(select(User).where(User.email == email.lower()))
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            raise AppError(
                code="INVALID_CREDENTIALS",
                message="Email or password is incorrect.",
                status_code=401,
            )
        return await self._issue_tokens(user)

    async def refresh(self, raw_token: str) -> TokenResponse:
        now = datetime.now(UTC)
        token = await self._session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        )
        if token is None or token.revoked_at is not None or self._is_expired(token.expires_at, now):
            raise AppError(
                code="INVALID_REFRESH_TOKEN", message="Session has expired.", status_code=401
            )

        user = await self._session.get(User, token.user_id)
        if user is None or not user.is_active:
            raise AppError(
                code="INVALID_REFRESH_TOKEN", message="Session has expired.", status_code=401
            )

        token.revoked_at = now
        return await self._issue_tokens(user)

    async def logout(self, *, raw_token: str) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == hash_refresh_token(raw_token),
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.commit()

    async def _issue_tokens(self, user: User) -> TokenResponse:
        settings = get_settings()
        access_token, expires_in = create_access_token(
            user_id=user.id,
            company_id=user.company_id,
            role=user.role,
        )
        raw_refresh = create_refresh_token()
        self._session.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_refresh_token(raw_refresh),
                expires_at=datetime.now(UTC) + timedelta(days=settings.jwt_refresh_expires_days),
            )
        )
        await self._session.commit()
        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=expires_in,
            user=AuthUser.model_validate(user),
        )

    @staticmethod
    def _is_expired(expires_at: datetime, now: datetime) -> bool:
        comparable = expires_at if expires_at.tzinfo is not None else expires_at.replace(tzinfo=UTC)
        return comparable <= now
