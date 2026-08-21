import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.rag.chunker import DocumentChunker, PageText
from app.rag.embeddings import EmbeddingProvider, validate_embeddings


class ProcessingOutcome(StrEnum):
    READY = "READY"
    ALREADY_INDEXED = "ALREADY_INDEXED"


@dataclass(frozen=True, slots=True)
class IndexedChunk:
    page: int
    chunk_index: int
    text: str
    embedding: Sequence[float]


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    outcome: ProcessingOutcome
    checksum: str
    chunk_count: int


class DocumentTextExtractor(Protocol):
    def extract(self, pdf_bytes: bytes) -> list[PageText]: ...


class DocumentIndexRepository(Protocol):
    async def is_indexed(
        self,
        *,
        company_id: UUID,
        document_version_id: UUID,
        checksum: str,
    ) -> bool: ...

    async def replace_chunks(
        self,
        *,
        company_id: UUID,
        document_version_id: UUID,
        checksum: str,
        embedding_provider: str,
        embedding_model: str,
        chunks: Sequence[IndexedChunk],
    ) -> None: ...


class DocumentProcessor:
    """Idempotent extraction, chunking, embedding, and indexing pipeline."""

    def __init__(
        self,
        *,
        extractor: DocumentTextExtractor,
        chunker: DocumentChunker,
        embedding_provider: EmbeddingProvider,
        repository: DocumentIndexRepository,
    ) -> None:
        self._extractor = extractor
        self._chunker = chunker
        self._embedding_provider = embedding_provider
        self._repository = repository

    async def process(
        self,
        *,
        company_id: UUID,
        document_version_id: UUID,
        pdf_bytes: bytes,
    ) -> ProcessingResult:
        if not pdf_bytes:
            raise ValueError("document bytes must not be empty")
        checksum = hashlib.sha256(pdf_bytes).hexdigest()
        if await self._repository.is_indexed(
            company_id=company_id,
            document_version_id=document_version_id,
            checksum=checksum,
        ):
            return ProcessingResult(
                outcome=ProcessingOutcome.ALREADY_INDEXED,
                checksum=checksum,
                chunk_count=0,
            )

        pages = self._extractor.extract(pdf_bytes)
        chunks = self._chunker.chunk(pages)
        texts = [chunk.text for chunk in chunks]
        embeddings = await self._embedding_provider.embed(texts)
        validate_embeddings(
            texts=texts,
            embeddings=embeddings,
            dimensions=self._embedding_provider.dimensions,
        )
        indexed_chunks = [
            IndexedChunk(
                page=chunk.page,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                embedding=embedding,
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        await self._repository.replace_chunks(
            company_id=company_id,
            document_version_id=document_version_id,
            checksum=checksum,
            embedding_provider=self._embedding_provider.name,
            embedding_model=self._embedding_provider.model,
            chunks=indexed_chunks,
        )
        return ProcessingResult(
            outcome=ProcessingOutcome.READY,
            checksum=checksum,
            chunk_count=len(indexed_chunks),
        )
