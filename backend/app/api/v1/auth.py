from fastapi import APIRouter, status

from app.api.dependencies import CurrentUser, SessionDependency
from app.schemas.auth import AuthUser, LoginRequest, LogoutRequest, RefreshRequest, TokenResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, summary="Authenticate with email and password")
async def login(payload: LoginRequest, session: SessionDependency) -> TokenResponse:
    return await AuthService(session).login(email=str(payload.email), password=payload.password)


@router.post("/refresh", response_model=TokenResponse, summary="Rotate a refresh token")
async def refresh(payload: RefreshRequest, session: SessionDependency) -> TokenResponse:
    return await AuthService(session).refresh(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke a session")
async def logout(payload: LogoutRequest, user: CurrentUser, session: SessionDependency) -> None:
    await AuthService(session).logout(user_id=user.id, raw_token=payload.refresh_token)


@router.get("/me", response_model=AuthUser, summary="Read the current authenticated user")
async def me(user: CurrentUser) -> AuthUser:
    return AuthUser.model_validate(user)
