import asyncio
import json
from collections.abc import AsyncIterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.ai.base import (
    AIProviderConfigurationError,
    AIProviderError,
    AIRequest,
    CloudAIProvider,
    ProviderResult,
    ProviderTransport,
)


class GeminiRESTTransport:
    """Small HTTP boundary for Gemini generateContent with structured JSON support."""

    def __init__(self, api_key: str, *, timeout_seconds: int = 45) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def generate_text(
        self, *, provider: str, model: str, request: AIRequest
    ) -> ProviderResult:
        del provider
        return await asyncio.to_thread(self._generate_sync, model, request)

    def _generate_sync(self, model: str, request: AIRequest) -> ProviderResult:
        generation_config: dict[str, object] = {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_output_tokens,
        }
        if request.response_schema:
            generation_config.update(
                {
                    "responseMimeType": "application/json",
                    "responseJsonSchema": request.response_schema,
                }
            )
        payload: dict[str, object] = {
            "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
            "generationConfig": generation_config,
        }
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        http_request = Request(
            url,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
            },
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=self._timeout_seconds) as response:  # noqa: S310
                body = json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AIProviderError("Gemini request failed") from exc
        try:
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            usage = body.get("usageMetadata", {})
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError("Gemini returned no usable candidate") from exc
        return ProviderResult(
            text=text,
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=usage.get("candidatesTokenCount"),
        )

    async def _stream(self) -> AsyncIterator[str]:
        raise AIProviderConfigurationError("Gemini streaming is not enabled in this MVP")
        yield ""  # pragma: no cover

    def stream(self, *, provider: str, model: str, request: AIRequest) -> AsyncIterator[str]:
        del provider, model, request
        return self._stream()


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
        resolved_transport = transport or GeminiRESTTransport(api_key)
        super().__init__(name="gemini", model=model, transport=resolved_transport)
