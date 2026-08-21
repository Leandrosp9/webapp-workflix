from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.ai.dependencies import AIServiceDependency
from app.api.dependencies import CurrentUser, SessionDependency
from app.api.rate_limits import AIRateLimit
from app.core.errors import AppError
from app.rag.embeddings import EmbeddingProvider
from app.rag.jobs import build_embedding_provider
from app.schemas.rag import RAGAnswerResponse, RAGAskRequest
from app.services.rag import RAGService

router = APIRouter(tags=["RAG"])


def get_rag_embedding_provider() -> EmbeddingProvider:
    provider = build_embedding_provider()
    if provider is None:
        raise AppError(
            code="RAG_NOT_CONFIGURED",
            message="Gemini embeddings are not configured. Set GEMINI_API_KEY to enable RAG.",
            status_code=503,
        )
    return provider


RAGEmbeddingDependency = Annotated[EmbeddingProvider, Depends(get_rag_embedding_provider)]


@router.post("/trainings/{training_id}/ask", response_model=RAGAnswerResponse)
async def ask_training_document(
    training_id: UUID,
    payload: RAGAskRequest,
    user: CurrentUser,
    session: SessionDependency,
    _rate_limit: AIRateLimit,
    embedding_provider: RAGEmbeddingDependency,
    ai_service: AIServiceDependency,
) -> RAGAnswerResponse:
    return await RAGService(
        session,
        ai_service=ai_service,
        embedding_provider=embedding_provider,
    ).ask(
        training_id=training_id,
        user=user,
        question=payload.question,
        limit=payload.limit,
    )
