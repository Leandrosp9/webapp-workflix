import asyncio
import json
from collections.abc import Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.rag.embeddings import EmbeddingError, EmbeddingProvider, EmbeddingTask, validate_embeddings


class GeminiEmbeddingProvider(EmbeddingProvider):
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        dimensions: int = 768,
        max_concurrency: int = 4,
        timeout_seconds: int = 45,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must not be empty")
        if not model.strip():
            raise ValueError("model must not be empty")
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        self._api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._timeout_seconds = timeout_seconds

    async def embed(
        self,
        texts: Sequence[str],
        *,
        task: EmbeddingTask = EmbeddingTask.DOCUMENT,
        titles: Sequence[str] | None = None,
    ) -> list[list[float]]:
        normalized = [text.strip() for text in texts]
        if any(not text for text in normalized):
            raise EmbeddingError("embedding text must not be empty")
        if titles is not None and len(titles) != len(normalized):
            raise EmbeddingError("embedding titles must match text count")

        async def generate(index: int, text: str) -> list[float]:
            title = titles[index].strip() if titles is not None else ""
            if task == EmbeddingTask.QUERY:
                content = f"task: question answering | query: {text}"
            else:
                prefix = f"title: {title} | " if title else ""
                content = f"{prefix}text: {text}"
            async with self._semaphore:
                return await asyncio.to_thread(self._embed_sync, content)

        embeddings = await asyncio.gather(
            *(generate(index, text) for index, text in enumerate(normalized))
        )
        validate_embeddings(texts=normalized, embeddings=embeddings, dimensions=self.dimensions)
        return embeddings

    def _embed_sync(self, content: str) -> list[float]:
        payload = {
            "content": {"parts": [{"text": content}]},
            "outputDimensionality": self.dimensions,
        }
        request = Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310
                body = json.loads(response.read())
            values = body["embedding"]["values"]
            return [float(value) for value in values]
        except (
            HTTPError,
            URLError,
            TimeoutError,
            json.JSONDecodeError,
            UnicodeDecodeError,
            KeyError,
            TypeError,
        ) as exc:
            raise EmbeddingError("Gemini embedding request failed") from exc
