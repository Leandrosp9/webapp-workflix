import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import (
    DocumentChunk,
    DocumentPage,
    DocumentStatus,
    DocumentVersion,
)
from app.rag.chunker import DocumentChunker
from app.rag.embeddings import EmbeddingError, EmbeddingProvider, EmbeddingTask
from app.rag.extractor import PDFExtractionError, PyMuPDFExtractor
from app.rag.providers import GeminiEmbeddingProvider
from app.storage import ObjectNotFoundError, ObjectStorage, StorageError

logger = get_logger(__name__)


@dataclass(frozen=True)
class DocumentProcessingOutcome:
    completed: bool
    retryable: bool = False
    error_code: str | None = None


def build_embedding_provider() -> EmbeddingProvider | None:
    settings = get_settings()
    key = settings.gemini_api_key
    if key is None or not key.get_secret_value():
        return None
    return GeminiEmbeddingProvider(
        api_key=key.get_secret_value(),
        model=settings.rag_embedding_model,
        dimensions=settings.rag_embedding_dimensions,
    )


class DocumentProcessingService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        storage: ObjectStorage,
        embedding_provider: EmbeddingProvider | None,
    ) -> None:
        settings = get_settings()
        self._session = session
        self._storage = storage
        self._embedding_provider = embedding_provider
        self._extractor = PyMuPDFExtractor(max_pages=settings.rag_max_pdf_pages)
        self._chunker = DocumentChunker()

    async def process(self, version_id: UUID) -> DocumentProcessingOutcome:
        version = await self._session.scalar(
            select(DocumentVersion)
            .options(selectinload(DocumentVersion.document))
            .where(DocumentVersion.id == version_id)
            .with_for_update()
        )
        if version is None:
            logger.warning("document_version_missing", extra={"version_id": str(version_id)})
            await self._session.rollback()
            return DocumentProcessingOutcome(completed=True)
        if version.status == DocumentStatus.READY:
            await self._session.rollback()
            return DocumentProcessingOutcome(completed=True)

        try:
            version.status = DocumentStatus.EXTRACTING
            version.error_code = None
            await self._session.commit()

            stored = await self._storage.get(version.object_key)
            pages = await asyncio.to_thread(self._extractor.extract, stored.data)
            await self._session.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.company_id == version.company_id,
                    DocumentChunk.document_version_id == version.id,
                )
            )
            await self._session.execute(
                delete(DocumentPage).where(
                    DocumentPage.company_id == version.company_id,
                    DocumentPage.document_version_id == version.id,
                )
            )
            self._session.add_all(
                [
                    DocumentPage(
                        company_id=version.company_id,
                        document_version_id=version.id,
                        page_number=page.page,
                        text=page.text,
                    )
                    for page in pages
                ]
            )
            version.page_count = len(pages)
            version.chunk_count = 0
            version.status = DocumentStatus.EXTRACTED
            version.processed_at = datetime.now(UTC)
            await self._session.commit()

            if self._embedding_provider is None:
                return DocumentProcessingOutcome(completed=True)

            chunks = self._chunker.chunk(pages)
            if not chunks:
                raise PDFExtractionError("PDF_NO_EXTRACTABLE_TEXT")
            version.status = DocumentStatus.INDEXING
            await self._session.commit()
            texts = [chunk.text for chunk in chunks]
            title = version.document.title
            embeddings = await self._embedding_provider.embed(
                texts,
                task=EmbeddingTask.DOCUMENT,
                titles=[title] * len(texts),
            )
            self._session.add_all(
                [
                    DocumentChunk(
                        company_id=version.company_id,
                        document_version_id=version.id,
                        page_number=chunk.page,
                        chunk_index=chunk.chunk_index,
                        text=chunk.text,
                        embedding=embedding,
                        embedding_provider=self._embedding_provider.name,
                        embedding_model=self._embedding_provider.model,
                    )
                    for chunk, embedding in zip(chunks, embeddings, strict=True)
                ]
            )
            version.chunk_count = len(chunks)
            version.status = DocumentStatus.READY
            version.processed_at = datetime.now(UTC)
            await self._session.commit()
            return DocumentProcessingOutcome(completed=True)
        except Exception as exc:
            await self._session.rollback()
            error_code, retryable = await self._mark_failed(version_id, exc)
            return DocumentProcessingOutcome(
                completed=False,
                retryable=retryable,
                error_code=error_code,
            )

    async def _mark_failed(self, version_id: UUID, exc: Exception) -> tuple[str, bool]:
        version = await self._session.get(DocumentVersion, version_id)
        if version is None:
            return "DOCUMENT_VERSION_NOT_FOUND", False
        if isinstance(exc, PDFExtractionError):
            error_code = exc.code
            retryable = False
        elif isinstance(exc, ObjectNotFoundError):
            error_code = "DOCUMENT_OBJECT_NOT_FOUND"
            retryable = True
        elif isinstance(exc, StorageError):
            error_code = "STORAGE_UNAVAILABLE"
            retryable = True
        elif isinstance(exc, EmbeddingError):
            error_code = "EMBEDDING_FAILED"
            retryable = True
        else:
            error_code = "PROCESSING_FAILED"
            retryable = True
        version.status = DocumentStatus.FAILED
        version.error_code = error_code
        version.processed_at = datetime.now(UTC)
        await self._session.commit()
        logger.warning(
            "document_processing_failed",
            extra={
                "version_id": str(version_id),
                "error_code": error_code,
                "error_type": type(exc).__name__,
            },
        )
        return error_code, retryable
