from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIRequest, AIResponse
from app.ai.service import AIService, AIServiceUnavailableError
from app.core.errors import AppError
from app.models import Training
from app.schemas.ai import (
    GeneratedQuiz,
    GeneratedQuizResponse,
    GeneratedTraining,
    GeneratedTrainingResponse,
    GenerateQuizRequest,
    GenerateTrainingRequest,
    GenerationMetadata,
)

TRAINING_SYSTEM_PROMPT = """You are an instructional designer for corporate learning.
Return Brazilian Portuguese content as valid JSON matching the supplied schema.
Use practical examples, short sections, inclusive language, and no fabricated laws or statistics."""

QUIZ_SYSTEM_PROMPT = """You design fair single-answer corporate quizzes in Brazilian Portuguese.
Return valid JSON matching the supplied schema. Every question must have exactly one correct option.
Wrong options must be plausible, and explanations must teach instead of merely repeat the answer."""


def metadata(response: AIResponse) -> GenerationMetadata:
    return GenerationMetadata(
        provider=response.provider,
        model=response.model,
        fallback_used=response.fallback_used,
    )


async def generate_training(
    service: AIService, payload: GenerateTrainingRequest
) -> GeneratedTrainingResponse:
    objectives = "\n".join(f"- {objective}" for objective in payload.learning_objectives)
    prompt = f"""Create an article training draft.
Topic: {payload.topic}
Audience: {payload.audience}
Target duration: {payload.estimated_minutes} minutes
Learning objectives:
{objectives}
The content field must be complete Markdown with an introduction, sections,
a practical checklist, and a recap."""
    try:
        draft, response = await service.generate_structured(
            AIRequest(
                feature="training_generation",
                prompt=prompt,
                system_prompt=TRAINING_SYSTEM_PROMPT,
                max_output_tokens=4096,
            ),
            GeneratedTraining,
        )
    except AIServiceUnavailableError as exc:
        raise AppError(
            code="AI_GENERATION_FAILED",
            message="The AI provider could not generate a valid training draft.",
            status_code=503,
        ) from exc
    return GeneratedTrainingResponse(draft=draft, generation=metadata(response))


async def generate_quiz(
    session: AsyncSession,
    service: AIService,
    company_id: UUID,
    payload: GenerateQuizRequest,
) -> GeneratedQuizResponse:
    try:
        training_id = UUID(payload.training_id)
    except ValueError as exc:
        raise AppError(
            code="VALIDATION_ERROR", message="training_id must be a UUID.", status_code=422
        ) from exc
    training = await session.scalar(
        select(Training).where(Training.id == training_id, Training.company_id == company_id)
    )
    if training is None:
        raise AppError(code="TRAINING_NOT_FOUND", message="Training not found.", status_code=404)
    prompt = f"""Create exactly {payload.question_count} questions for this training.
Use passing_score {payload.passing_score}.
Title: {training.title}
Description: {training.description}
Training content:
{training.content[:12000]}"""
    try:
        draft, response = await service.generate_structured(
            AIRequest(
                feature="quiz_generation",
                prompt=prompt,
                system_prompt=QUIZ_SYSTEM_PROMPT,
                max_output_tokens=4096,
            ),
            GeneratedQuiz,
        )
    except AIServiceUnavailableError as exc:
        raise AppError(
            code="AI_GENERATION_FAILED",
            message="The AI provider could not generate a valid quiz draft.",
            status_code=503,
        ) from exc
    if len(draft.questions) != payload.question_count:
        raise AppError(
            code="AI_GENERATION_FAILED",
            message="The AI provider returned an unexpected number of questions.",
            status_code=503,
        )
    draft.passing_score = payload.passing_score
    return GeneratedQuizResponse(draft=draft, generation=metadata(response))
