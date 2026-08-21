from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import AdminUser, EmployeeUser, SessionDependency
from app.schemas.quizzes import QuizAttemptResponse, QuizEditor, QuizPublic, QuizSubmission
from app.services.quizzes import QuizService

router = APIRouter(tags=["Quizzes"])


@router.put("/trainings/{training_id}/quiz", response_model=QuizEditor)
async def replace_quiz(
    training_id: UUID,
    payload: QuizEditor,
    admin: AdminUser,
    session: SessionDependency,
) -> QuizEditor:
    return await QuizService(session).replace(training_id, admin.company_id, payload)


@router.get("/trainings/{training_id}/quiz", response_model=QuizEditor)
async def get_quiz_editor(
    training_id: UUID, admin: AdminUser, session: SessionDependency
) -> QuizEditor:
    return await QuizService(session).get_editor(training_id, admin.company_id)


@router.get("/employee/trainings/{training_id}/quiz", response_model=QuizPublic)
async def get_employee_quiz(
    training_id: UUID, employee: EmployeeUser, session: SessionDependency
) -> QuizPublic:
    return await QuizService(session).get_public(training_id, employee.company_id, employee.id)


@router.post(
    "/employee/trainings/{training_id}/quiz/attempts",
    response_model=QuizAttemptResponse,
)
async def submit_quiz(
    training_id: UUID,
    payload: QuizSubmission,
    employee: EmployeeUser,
    session: SessionDependency,
) -> QuizAttemptResponse:
    return await QuizService(session).submit(training_id, employee.company_id, employee.id, payload)
