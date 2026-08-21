from typing import Literal

from pydantic import BaseModel, Field, model_validator


class GenerateTrainingRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=300)
    audience: str = Field(min_length=2, max_length=200)
    learning_objectives: list[str] = Field(min_length=1, max_length=8)
    estimated_minutes: int = Field(default=15, ge=3, le=180)


class GeneratedTraining(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=600)
    content: str = Field(min_length=100)
    estimated_minutes: int = Field(ge=3, le=180)


class GenerateQuizRequest(BaseModel):
    training_id: str
    question_count: int = Field(default=5, ge=1, le=15)
    passing_score: int = Field(default=70, ge=0, le=100)


class GeneratedOption(BaseModel):
    text: str = Field(min_length=1, max_length=350)
    is_correct: bool


class GeneratedQuestion(BaseModel):
    text: str = Field(min_length=3, max_length=500)
    explanation: str = Field(min_length=3, max_length=700)
    options: list[GeneratedOption] = Field(min_length=2, max_length=5)

    @model_validator(mode="after")
    def exactly_one_correct(self) -> "GeneratedQuestion":
        if sum(option.is_correct for option in self.options) != 1:
            raise ValueError("exactly one option must be correct")
        return self


class GeneratedQuiz(BaseModel):
    passing_score: int = Field(ge=0, le=100)
    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=15)


class GenerationMetadata(BaseModel):
    provider: Literal["gemini", "groq"] | str
    model: str
    fallback_used: bool


class GeneratedTrainingResponse(BaseModel):
    draft: GeneratedTraining
    generation: GenerationMetadata


class GeneratedQuizResponse(BaseModel):
    draft: GeneratedQuiz
    generation: GenerationMetadata
