from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models import (
    Question,
    QuestionOption,
    Quiz,
    QuizAttempt,
    Training,
    TrainingAssignment,
    TrainingStatus,
    UserProgress,
)
from app.schemas.quizzes import (
    QuizAnswerResult,
    QuizAttemptResponse,
    QuizEditor,
    QuizOptionEditor,
    QuizOptionPublic,
    QuizPublic,
    QuizQuestionEditor,
    QuizQuestionPublic,
    QuizSubmission,
)


class QuizService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _training(self, training_id: UUID, company_id: UUID) -> Training:
        training = await self._session.scalar(
            select(Training).where(Training.id == training_id, Training.company_id == company_id)
        )
        if training is None:
            raise AppError(
                code="TRAINING_NOT_FOUND", message="Training not found.", status_code=404
            )
        return training

    async def _quiz(self, training_id: UUID, company_id: UUID) -> Quiz:
        quiz = await self._session.scalar(
            select(Quiz)
            .options(selectinload(Quiz.questions).selectinload(Question.options))
            .where(Quiz.training_id == training_id, Quiz.company_id == company_id)
        )
        if quiz is None:
            raise AppError(code="QUIZ_NOT_FOUND", message="Quiz not found.", status_code=404)
        return quiz

    @staticmethod
    def _editor(quiz: Quiz) -> QuizEditor:
        return QuizEditor(
            id=quiz.id,
            passing_score=quiz.passing_score,
            questions=[
                QuizQuestionEditor(
                    id=question.id,
                    text=question.text,
                    explanation=question.explanation,
                    options=[
                        QuizOptionEditor(
                            id=option.id,
                            text=option.text,
                            is_correct=option.is_correct,
                        )
                        for option in question.options
                    ],
                )
                for question in quiz.questions
            ],
        )

    async def replace(self, training_id: UUID, company_id: UUID, payload: QuizEditor) -> QuizEditor:
        await self._training(training_id, company_id)
        existing = await self._session.scalar(
            select(Quiz).where(Quiz.training_id == training_id, Quiz.company_id == company_id)
        )
        if existing is not None:
            await self._session.delete(existing)
            await self._session.flush()
        quiz = Quiz(
            company_id=company_id,
            training_id=training_id,
            passing_score=payload.passing_score,
            questions=[
                Question(
                    text=question.text.strip(),
                    explanation=question.explanation.strip(),
                    position=question_position,
                    options=[
                        QuestionOption(
                            text=option.text.strip(),
                            is_correct=option.is_correct,
                            position=option_position,
                        )
                        for option_position, option in enumerate(question.options)
                    ],
                )
                for question_position, question in enumerate(payload.questions)
            ],
        )
        self._session.add(quiz)
        await self._session.commit()
        return self._editor(await self._quiz(training_id, company_id))

    async def get_editor(self, training_id: UUID, company_id: UUID) -> QuizEditor:
        await self._training(training_id, company_id)
        return self._editor(await self._quiz(training_id, company_id))

    async def get_public(
        self, training_id: UUID, company_id: UUID, employee_id: UUID
    ) -> QuizPublic:
        quiz = await self._employee_quiz(training_id, company_id, employee_id)
        return QuizPublic(
            id=quiz.id,
            training_id=quiz.training_id,
            passing_score=quiz.passing_score,
            questions=[
                QuizQuestionPublic(
                    id=question.id,
                    text=question.text,
                    options=[
                        QuizOptionPublic(id=option.id, text=option.text)
                        for option in question.options
                    ],
                )
                for question in quiz.questions
            ],
        )

    async def _employee_quiz(self, training_id: UUID, company_id: UUID, employee_id: UUID) -> Quiz:
        assigned = await self._session.scalar(
            select(TrainingAssignment.id)
            .join(Training, Training.id == TrainingAssignment.training_id)
            .where(
                TrainingAssignment.training_id == training_id,
                TrainingAssignment.company_id == company_id,
                TrainingAssignment.employee_id == employee_id,
                Training.company_id == company_id,
                Training.status == TrainingStatus.PUBLISHED,
            )
        )
        if assigned is None:
            raise AppError(
                code="TRAINING_NOT_FOUND", message="Training not found.", status_code=404
            )
        return await self._quiz(training_id, company_id)

    async def submit(
        self,
        training_id: UUID,
        company_id: UUID,
        employee_id: UUID,
        payload: QuizSubmission,
    ) -> QuizAttemptResponse:
        quiz = await self._employee_quiz(training_id, company_id, employee_id)
        answers = {answer.question_id: answer.option_id for answer in payload.answers}
        question_ids = {question.id for question in quiz.questions}
        if len(answers) != len(payload.answers) or set(answers) != question_ids:
            raise AppError(
                code="INVALID_QUIZ_SUBMISSION",
                message="Submit exactly one answer for every question.",
                status_code=422,
            )
        results: list[QuizAnswerResult] = []
        correct_count = 0
        for question in quiz.questions:
            selected_id = answers[question.id]
            option_ids = {option.id for option in question.options}
            if selected_id not in option_ids:
                raise AppError(
                    code="INVALID_QUIZ_SUBMISSION",
                    message="An answer option does not belong to its question.",
                    status_code=422,
                )
            correct_option = next(option for option in question.options if option.is_correct)
            is_correct = selected_id == correct_option.id
            correct_count += int(is_correct)
            results.append(
                QuizAnswerResult(
                    question_id=question.id,
                    selected_option_id=selected_id,
                    correct_option_id=correct_option.id,
                    is_correct=is_correct,
                    explanation=question.explanation,
                )
            )
        total = len(quiz.questions)
        score = round(correct_count / total * 100)
        passed = score >= quiz.passing_score
        attempt = QuizAttempt(
            company_id=company_id,
            quiz_id=quiz.id,
            user_id=employee_id,
            score=score,
            correct_answers=correct_count,
            total_questions=total,
            passed=passed,
        )
        self._session.add(attempt)
        if passed:
            await self._complete_training(training_id, company_id, employee_id)
        await self._session.commit()
        await self._session.refresh(attempt)
        return QuizAttemptResponse(
            id=attempt.id,
            score=attempt.score,
            correct_answers=attempt.correct_answers,
            total_questions=attempt.total_questions,
            passed=attempt.passed,
            completed_at=attempt.completed_at,
            answers=results,
        )

    async def _complete_training(
        self, training_id: UUID, company_id: UUID, employee_id: UUID
    ) -> None:
        progress = await self._session.scalar(
            select(UserProgress).where(
                UserProgress.training_id == training_id,
                UserProgress.company_id == company_id,
                UserProgress.user_id == employee_id,
            )
        )
        now = datetime.now(UTC)
        if progress is None:
            self._session.add(
                UserProgress(
                    training_id=training_id,
                    company_id=company_id,
                    user_id=employee_id,
                    progress_percent=100,
                    started_at=now,
                    completed_at=now,
                )
            )
        else:
            progress.progress_percent = 100
            progress.started_at = progress.started_at or now
            progress.completed_at = progress.completed_at or now
