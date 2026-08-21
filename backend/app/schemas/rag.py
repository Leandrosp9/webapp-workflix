from uuid import UUID

from pydantic import BaseModel, Field


class RAGAskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    limit: int | None = Field(default=None, ge=1, le=12)


class RAGSource(BaseModel):
    document_id: UUID
    document_version_id: UUID
    title: str
    page: int
    excerpt: str
    score: float


class RAGAnswerResponse(BaseModel):
    answer: str
    sources: list[RAGSource]
    provider: str
    model: str
