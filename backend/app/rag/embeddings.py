from abc import ABC, abstractmethod
from collections.abc import Sequence


class EmbeddingError(Exception):
    """Embedding generation or validation failed."""


class EmbeddingProvider(ABC):
    name: str
    model: str
    dimensions: int

    @abstractmethod
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Create cloud-hosted embeddings for non-empty text values."""


def validate_embeddings(
    *,
    texts: Sequence[str],
    embeddings: Sequence[Sequence[float]],
    dimensions: int,
) -> None:
    if len(texts) != len(embeddings):
        raise EmbeddingError("embedding count does not match text count")
    if dimensions < 1:
        raise EmbeddingError("provider dimensions must be positive")
    for vector in embeddings:
        if len(vector) != dimensions:
            raise EmbeddingError("embedding dimensions do not match the provider contract")
