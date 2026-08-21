from app.ai.base import AIProvider, AIProviderConfigurationError


class AIProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}

    def register(self, provider: AIProvider) -> None:
        key = provider.name.strip().lower()
        if not key:
            raise ValueError("provider name must not be empty")
        if key in self._providers:
            raise ValueError(f"provider '{key}' is already registered")
        self._providers[key] = provider

    def get(self, provider_name: str) -> AIProvider:
        key = provider_name.strip().lower()
        try:
            return self._providers[key]
        except KeyError as exc:
            raise AIProviderConfigurationError(f"provider '{key}' is not registered") from exc

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))
