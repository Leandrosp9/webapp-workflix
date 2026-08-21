from collections.abc import AsyncIterator

from app.ai.base import AIProvider, AIRequest, AIResponse, UnsupportedAIProviderError


class OllamaProvider(AIProvider):
    """Explicitly blocked local provider retained only as an architectural guardrail."""

    name = "ollama"
    model = "unsupported-local-model"

    @staticmethod
    def _unsupported() -> UnsupportedAIProviderError:
        return UnsupportedAIProviderError(
            "Ollama is disabled: Workflix permits cloud AI providers only"
        )

    async def generate_text(self, request: AIRequest) -> AIResponse:
        del request
        raise self._unsupported()

    async def _stream(self, request: AIRequest) -> AsyncIterator[str]:
        del request
        raise self._unsupported()
        yield  # pragma: no cover

    def stream(self, request: AIRequest) -> AsyncIterator[str]:
        return self._stream(request)
