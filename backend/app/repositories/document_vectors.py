from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentVersion,
    Role,
    Training,
    TrainingAssignment,
    TrainingStatus,
    User,
)
from app.rag.retriever import RetrievedChunk


class SqlAlchemyVectorSearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def semantic_search(
        self,
        *,
        company_id: UUID,
        user_id: UUID,
        query_embedding: Sequence[float],
        limit: int,
        document_ids: tuple[UUID, ...],
    ) -> Sequence[RetrievedChunk]:
        role = await self._session.scalar(
            select(User.role).where(
                User.id == user_id,
                User.company_id == company_id,
                User.is_active.is_(True),
            )
        )
        if role is None:
            return []

        other_version = aliased(DocumentVersion)
        latest_version_number = (
            select(func.max(other_version.version_number))
            .where(
                other_version.document_id == Document.id,
                other_version.company_id == company_id,
            )
            .correlate(Document)
            .scalar_subquery()
        )
        distance = DocumentChunk.embedding.cosine_distance(list(query_embedding))
        statement = (
            select(
                Document.id,
                DocumentVersion.id,
                Document.title,
                DocumentChunk.page_number,
                DocumentChunk.text,
                distance.label("distance"),
            )
            .join(DocumentVersion, DocumentVersion.id == DocumentChunk.document_version_id)
            .join(Document, Document.id == DocumentVersion.document_id)
            .join(Training, Training.id == Document.training_id)
            .where(
                DocumentChunk.company_id == company_id,
                DocumentVersion.company_id == company_id,
                Document.company_id == company_id,
                Training.company_id == company_id,
                DocumentVersion.status == DocumentStatus.READY,
                DocumentVersion.version_number == latest_version_number,
            )
        )
        if role == Role.EMPLOYEE:
            statement = statement.join(
                TrainingAssignment,
                TrainingAssignment.training_id == Training.id,
            ).where(
                TrainingAssignment.company_id == company_id,
                TrainingAssignment.employee_id == user_id,
                Training.status == TrainingStatus.PUBLISHED,
            )
        if document_ids:
            statement = statement.where(Document.id.in_(document_ids))
        rows = (await self._session.execute(statement.order_by(distance).limit(limit))).all()
        return [
            RetrievedChunk(
                document_id=document_id,
                document_version_id=version_id,
                title=title,
                page=page_number,
                text=text,
                score=max(-1.0, min(1.0, 1.0 - float(vector_distance))),
            )
            for document_id, version_id, title, page_number, text, vector_distance in rows
        ]
