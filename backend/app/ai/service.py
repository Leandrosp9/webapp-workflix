from collections.abc import AsyncIterator
from dataclasses import replace

from app.ai.base import AIProvider, AIProviderError, AIRequest, AIResponse, StructuredModel
from app.core.logging import get_logger

logger = get_logger(__name__)


class AIServiceUnavailableError(Exception):
    """All configured providers failed to produce a response."""


class AIService:
    def __init__(self, primary: AIProvider, fallback: AIProvider | None = None) -> None:
        if fallback is not None and fallback.name == primary.name:
            raise ValueError("fallback provider must differ from the primary provider")
        self._primary = primary
        self._fallback = fallback

    @property
    def providers(self) -> tuple[AIProvider, ...]:
        if self._fallback is None:
            return (self._primary,)
        return (self._primary, self._fallback)

    async def generate_text(self, request: AIRequest) -> AIResponse:
        last_error: AIProviderError | None = None
        for index, provider in enumerate(self.providers):
            try:
                response = await provider.generate_text(request)
                return replace(response, fallback_used=index > 0)
            except AIProviderError as exc:
                last_error = exc
                logger.warning(
                    "ai_provider_failed",
                    extra={"error_type": type(exc).__name__},
                )

        raise AIServiceUnavailableError(
            "No configured AI provider is currently available"
        ) from last_error

    async def generate_structured(
        self,
        request: AIRequest,
        schema: type[StructuredModel],
    ) -> tuple[StructuredModel, AIResponse]:
        last_error: AIProviderError | None = None
        for index, provider in enumerate(self.providers):
            try:
                parsed, response = await provider.generate_structured(request, schema)
                return parsed, replace(response, fallback_used=index > 0)
            except AIProviderError as exc:
                last_error = exc
                logger.warning(
                    "ai_structured_provider_failed",
                    extra={"error_type": type(exc).__name__},
                )

        raise AIServiceUnavailableError(
            "No provider returned valid structured output"
        ) from last_error

    async def _stream(self, request: AIRequest) -> AsyncIterator[str]:
        last_error: AIProviderError | None = None
        for provider in self.providers:
            emitted_chunk = False
            try:
                async for chunk in provider.stream(request):
                    emitted_chunk = True
                    yield chunk
                return
            except AIProviderError as exc:
                if emitted_chunk:
                    raise AIServiceUnavailableError(
                        "The provider stream failed after output started"
                    ) from exc
                last_error = exc
                logger.warning(
                    "ai_stream_provider_failed",
                    extra={"error_type": type(exc).__name__},
                )

        raise AIServiceUnavailableError(
            "No configured provider could start a stream"
        ) from last_error

    def stream(self, request: AIRequest) -> AsyncIterator[str]:
        return self._stream(request)
