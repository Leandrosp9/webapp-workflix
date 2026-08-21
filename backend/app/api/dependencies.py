from collections.abc import AsyncIterator, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import AccessTokenError, decode_access_token
from app.db.session import get_db_session
from app.models import Role, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDependency,
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
        company_id = UUID(payload["company_id"])
    except (AccessTokenError, KeyError, TypeError, ValueError) as exc:
        raise AppError(
            code="UNAUTHENTICATED", message="Authentication is required.", status_code=401
        ) from exc

    user = await session.get(User, user_id)
    if user is None or not user.is_active or user.company_id != company_id:
        raise AppError(
            code="UNAUTHENTICATED", message="Authentication is required.", status_code=401
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: Role) -> Callable[..., AsyncIterator[User]]:
    async def dependency(user: CurrentUser) -> AsyncIterator[User]:
        if user.role not in roles:
            raise AppError(
                code="FORBIDDEN",
                message="You do not have permission for this action.",
                status_code=403,
            )
        yield user

    return dependency


AdminUser = Annotated[User, Depends(require_role(Role.ADMIN))]
EmployeeUser = Annotated[User, Depends(require_role(Role.EMPLOYEE))]
