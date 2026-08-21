from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class AIError(Exception):
    """Base error for safe AI orchestration failures."""


class AIProviderError(AIError):
    """A provider failed before producing a usable result."""


class AIProviderConfigurationError(AIProviderError):
    """A provider is missing required configuration or transport."""


class UnsupportedAIProviderError(AIProviderError):
    """A provider is deliberately unsupported by the platform policy."""


class AIStructuredOutputError(AIProviderError):
    """A provider returned data that did not match the requested schema."""


@dataclass(frozen=True, slots=True)
class AIRequest:
    feature: str
    prompt: str
    system_prompt: str | None = None
    temperature: float = 0.2
    max_output_tokens: int = 2048

    def __post_init__(self) -> None:
        if not self.feature.strip():
            raise ValueError("feature must not be empty")
        if not self.prompt.strip():
            raise ValueError("prompt must not be empty")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        if not 1 <= self.max_output_tokens <= 65_536:
            raise ValueError("max_output_tokens must be between 1 and 65536")


@dataclass(frozen=True, slots=True)
class ProviderResult:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class AIResponse:
    text: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    fallback_used: bool = False


class ProviderTransport(Protocol):
    """SDK/HTTP boundary supplied to a cloud provider adapter in the AI phase."""

    async def generate_text(
        self,
        *,
        provider: str,
        model: str,
        request: AIRequest,
    ) -> ProviderResult: ...

    def stream(
        self,
        *,
        provider: str,
        model: str,
        request: AIRequest,
    ) -> AsyncIterator[str]: ...


class AIProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def generate_text(self, request: AIRequest) -> AIResponse:
        """Generate one complete text response."""

    async def generate_structured(
        self,
        request: AIRequest,
        schema: type[StructuredModel],
    ) -> tuple[StructuredModel, AIResponse]:
        response = await self.generate_text(request)
        try:
            parsed = schema.model_validate_json(response.text)
        except ValidationError as exc:
            raise AIStructuredOutputError(
                f"{self.name} returned output that does not match {schema.__name__}"
            ) from exc
        return parsed, response

    @abstractmethod
    def stream(self, request: AIRequest) -> AsyncIterator[str]:
        """Stream text chunks.

        Technical errors must be translated at the API boundary.
        """


class CloudAIProvider(AIProvider):
    """Shared provider implementation with an injected vendor transport."""

    def __init__(
        self,
        *,
        name: str,
        model: str,
        transport: ProviderTransport | None,
    ) -> None:
        self.name = name
        self.model = model
        self._transport = transport

    def _require_transport(self) -> ProviderTransport:
        if self._transport is None:
            raise AIProviderConfigurationError(
                f"{self.name} transport is not configured for this environment"
            )
        return self._transport

    async def generate_text(self, request: AIRequest) -> AIResponse:
        transport = self._require_transport()
        result = await transport.generate_text(
            provider=self.name,
            model=self.model,
            request=request,
        )
        return AIResponse(
            text=result.text,
            provider=self.name,
            model=self.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )

    async def _stream(self, request: AIRequest) -> AsyncIterator[str]:
        transport = self._require_transport()
        async for chunk in transport.stream(
            provider=self.name,
            model=self.model,
            request=request,
        ):
            yield chunk

    def stream(self, request: AIRequest) -> AsyncIterator[str]:
        return self._stream(request)
