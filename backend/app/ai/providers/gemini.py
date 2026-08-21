from app.ai.base import AIProviderConfigurationError, CloudAIProvider, ProviderTransport


class GeminiProvider(CloudAIProvider):
    """Gemini adapter; the vendor transport is injected outside domain workflows."""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        transport: ProviderTransport | None = None,
    ) -> None:
        if not api_key:
            raise AIProviderConfigurationError("GEMINI_API_KEY is not configured")
        if not model.strip():
            raise AIProviderConfigurationError("GEMINI_MODEL is not configured")
        super().__init__(name="gemini", model=model, transport=transport)
