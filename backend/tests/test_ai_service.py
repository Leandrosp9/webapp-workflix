from collections.abc import AsyncIterator

import pytest
from app.ai.base import (
    AIProvider,
    AIProviderError,
    AIRequest,
    AIResponse,
    UnsupportedAIProviderError,
)
from app.ai.providers.ollama import OllamaProvider
from app.ai.service import AIService


class FakeProvider(AIProvider):
    def __init__(self, *, name: str, response: str | None = None) -> None:
        self.name = name
        self.model = f"{name}-model"
        self._response = response

    async def generate_text(self, request: AIRequest) -> AIResponse:
        if self._response is None:
            raise AIProviderError(f"{self.name} unavailable")
        return AIResponse(text=self._response, provider=self.name, model=self.model)

    async def _stream(self, request: AIRequest) -> AsyncIterator[str]:
        response = await self.generate_text(request)
        yield response.text

    def stream(self, request: AIRequest) -> AsyncIterator[str]:
        return self._stream(request)


@pytest.mark.asyncio
async def test_service_exposes_fallback_usage() -> None:
    service = AIService(
        primary=FakeProvider(name="gemini"),
        fallback=FakeProvider(name="groq", response="safe fallback"),
    )

    response = await service.generate_text(AIRequest(feature="quiz", prompt="Generate a quiz"))

    assert response.text == "safe fallback"
    assert response.provider == "groq"
    assert response.fallback_used is True


@pytest.mark.asyncio
async def test_ollama_is_explicitly_disabled() -> None:
    provider = OllamaProvider()

    with pytest.raises(UnsupportedAIProviderError, match="cloud AI providers only"):
        await provider.generate_text(AIRequest(feature="training", prompt="Generate content"))
