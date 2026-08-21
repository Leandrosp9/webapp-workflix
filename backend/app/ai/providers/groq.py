from app.ai.base import AIProviderConfigurationError, CloudAIProvider, ProviderTransport


class GroqProvider(CloudAIProvider):
    """Groq fallback adapter; the vendor transport is injected by the composition root."""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        transport: ProviderTransport | None = None,
    ) -> None:
        if not api_key:
            raise AIProviderConfigurationError("GROQ_API_KEY is not configured")
        if not model.strip():
            raise AIProviderConfigurationError("GROQ_MODEL is not configured")
        super().__init__(name="groq", model=model, transport=transport)
