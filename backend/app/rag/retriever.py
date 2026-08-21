from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.rag.embeddings import EmbeddingProvider, EmbeddingTask, validate_embeddings


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    company_id: UUID
    user_id: UUID
    text: str
    limit: int = 6
    document_ids: tuple[UUID, ...] = ()

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("retrieval query must not be empty")
        if not 1 <= self.limit <= 20:
            raise ValueError("retrieval limit must be between 1 and 20")


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    document_id: UUID
    document_version_id: UUID
    title: str
    page: int
    text: str
    score: float


class VectorSearchRepository(Protocol):
    async def semantic_search(
        self,
        *,
        company_id: UUID,
        user_id: UUID,
        query_embedding: Sequence[float],
        limit: int,
        document_ids: tuple[UUID, ...],
    ) -> Sequence[RetrievedChunk]: ...


class Retriever:
    """Tenant and principal context are mandatory before vector ranking."""

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        repository: VectorSearchRepository,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._repository = repository

    async def retrieve(self, query: RetrievalQuery) -> list[RetrievedChunk]:
        embeddings = await self._embedding_provider.embed([query.text], task=EmbeddingTask.QUERY)
        validate_embeddings(
            texts=[query.text],
            embeddings=embeddings,
            dimensions=self._embedding_provider.dimensions,
        )
        results = await self._repository.semantic_search(
            company_id=query.company_id,
            user_id=query.user_id,
            query_embedding=embeddings[0],
            limit=query.limit,
            document_ids=query.document_ids,
        )
        return list(results)
