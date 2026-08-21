from fastapi import APIRouter

from app.ai.dependencies import AIServiceDependency
from app.api.dependencies import AdminUser, SessionDependency
from app.schemas.ai import (
    GeneratedQuizResponse,
    GeneratedTrainingResponse,
    GenerateQuizRequest,
    GenerateTrainingRequest,
)
from app.services.ai_generation import generate_quiz, generate_training

router = APIRouter(prefix="/ai", tags=["AI generation"])


@router.post("/generate-training", response_model=GeneratedTrainingResponse)
async def generate_training_draft(
    payload: GenerateTrainingRequest,
    admin: AdminUser,
    ai: AIServiceDependency,
) -> GeneratedTrainingResponse:
    del admin
    return await generate_training(ai, payload)


@router.post("/generate-quiz", response_model=GeneratedQuizResponse)
async def generate_quiz_draft(
    payload: GenerateQuizRequest,
    admin: AdminUser,
    session: SessionDependency,
    ai: AIServiceDependency,
) -> GeneratedQuizResponse:
    return await generate_quiz(session, ai, admin.company_id, payload)
