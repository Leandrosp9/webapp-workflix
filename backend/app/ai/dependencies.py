from typing import Annotated

from fastapi import Depends

from app.ai.providers.gemini import GeminiProvider
from app.ai.service import AIService
from app.core.config import get_settings
from app.core.errors import AppError


def get_ai_service() -> AIService:
    settings = get_settings()
    key = settings.gemini_api_key
    if key is None or not key.get_secret_value():
        raise AppError(
            code="AI_NOT_CONFIGURED",
            message="Gemini is not configured. Set GEMINI_API_KEY to enable generation.",
            status_code=503,
        )
    return AIService(
        GeminiProvider(
            api_key=key.get_secret_value(),
            model=settings.gemini_model,
        )
    )


AIServiceDependency = Annotated[AIService, Depends(get_ai_service)]
