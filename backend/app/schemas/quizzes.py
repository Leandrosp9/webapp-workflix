from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class QuizOptionEditor(BaseModel):
    id: UUID | None = None
    text: str = Field(min_length=1, max_length=350)
    is_correct: bool = False


class QuizQuestionEditor(BaseModel):
    id: UUID | None = None
    text: str = Field(min_length=3, max_length=500)
    explanation: str = Field(default="", max_length=700)
    options: list[QuizOptionEditor] = Field(min_length=2, max_length=8)

    @model_validator(mode="after")
    def one_correct_option(self) -> "QuizQuestionEditor":
        if sum(option.is_correct for option in self.options) != 1:
            raise ValueError("each question must have exactly one correct option")
        return self


class QuizEditor(BaseModel):
    id: UUID | None = None
    passing_score: int = Field(default=70, ge=0, le=100)
    questions: list[QuizQuestionEditor] = Field(min_length=1, max_length=50)


class QuizOptionPublic(BaseModel):
    id: UUID
    text: str


class QuizQuestionPublic(BaseModel):
    id: UUID
    text: str
    options: list[QuizOptionPublic]


class QuizPublic(BaseModel):
    id: UUID
    training_id: UUID
    passing_score: int
    questions: list[QuizQuestionPublic]


class QuizAnswer(BaseModel):
    question_id: UUID
    option_id: UUID


class QuizSubmission(BaseModel):
    answers: list[QuizAnswer] = Field(min_length=1, max_length=50)


class QuizAnswerResult(BaseModel):
    question_id: UUID
    selected_option_id: UUID
    correct_option_id: UUID
    is_correct: bool
    explanation: str


class QuizAttemptResponse(BaseModel):
    id: UUID
    score: int
    correct_answers: int
    total_questions: int
    passed: bool
    completed_at: datetime
    answers: list[QuizAnswerResult]
