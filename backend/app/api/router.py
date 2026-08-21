from fastapi import APIRouter

from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.quizzes import router as quizzes_router
from app.api.v1.rag import router as rag_router
from app.api.v1.system import router as system_router
from app.api.v1.trainings import router as trainings_router
from app.api.v1.users import router as users_router

api_router = APIRouter()
api_router.include_router(ai_router)
api_router.include_router(auth_router)
api_router.include_router(quizzes_router)
api_router.include_router(rag_router)
api_router.include_router(system_router)
api_router.include_router(trainings_router)
api_router.include_router(users_router)
