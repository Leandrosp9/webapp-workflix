import asyncio
import json
from collections.abc import AsyncIterator

from app.ai.base import AIProvider, AIRequest, AIResponse
from app.ai.dependencies import get_ai_service
from app.ai.service import AIService
from app.main import app
from app.models import Role

from conftest import ApiContext, create_company_user, login


class StructuredFakeProvider(AIProvider):
    name = "gemini"
    model = "gemini-test"

    def __init__(self) -> None:
        self.requests: list[AIRequest] = []

    async def generate_text(self, request: AIRequest) -> AIResponse:
        self.requests.append(request)
        if request.feature == "training_generation":
            output = {
                "title": "Segurança no trabalho remoto",
                "description": "Boas práticas para proteger informações fora do escritório.",
                "content": "# Introdução\n\n" + "Conteúdo prático e seguro. " * 10,
                "estimated_minutes": 15,
            }
        else:
            output = {
                "passing_score": 10,
                "questions": [
                    {
                        "text": "Qual é a prática correta?",
                        "explanation": "Use sempre os canais oficiais.",
                        "options": [
                            {"text": "Usar o canal oficial", "is_correct": True},
                            {"text": "Compartilhar credenciais", "is_correct": False},
                        ],
                    }
                ],
            }
        return AIResponse(text=json.dumps(output), provider=self.name, model=self.model)

    async def _stream(self, request: AIRequest) -> AsyncIterator[str]:
        response = await self.generate_text(request)
        yield response.text

    def stream(self, request: AIRequest) -> AsyncIterator[str]:
        return self._stream(request)


def authorization(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_generates_structured_training_and_quiz_without_real_call(
    api: ApiContext,
) -> None:
    _, admin = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="AI Company",
            email="admin@ai-company.example.com",
            role=Role.ADMIN,
        )
    )
    token = login(api.client, admin.email)["access_token"]
    fake = StructuredFakeProvider()
    app.dependency_overrides[get_ai_service] = lambda: AIService(fake)
    generated_training = api.client.post(
        "/api/v1/ai/generate-training",
        json={
            "topic": "Trabalho remoto seguro",
            "audience": "Todos os colaboradores",
            "learning_objectives": ["Reconhecer riscos", "Usar canais oficiais"],
            "estimated_minutes": 15,
        },
        headers=authorization(token),
    )
    assert generated_training.status_code == 200, generated_training.text
    assert generated_training.json()["draft"]["title"] == "Segurança no trabalho remoto"
    assert generated_training.json()["generation"]["provider"] == "gemini"

    training = api.client.post(
        "/api/v1/trainings",
        json={
            "title": "Remote security",
            "description": "Secure practices for distributed work.",
            "type": "ARTICLE",
            "content": "Use official channels and protect sensitive information.",
            "estimated_minutes": 15,
            "status": "DRAFT",
        },
        headers=authorization(token),
    ).json()
    generated_quiz = api.client.post(
        "/api/v1/ai/generate-quiz",
        json={"training_id": training["id"], "question_count": 1, "passing_score": 80},
        headers=authorization(token),
    )
    assert generated_quiz.status_code == 200, generated_quiz.text
    assert generated_quiz.json()["draft"]["passing_score"] == 80
    assert len(generated_quiz.json()["draft"]["questions"]) == 1
    assert len(fake.requests) == 2
    assert all(request.response_schema for request in fake.requests)


def test_employee_cannot_use_ai_generation(api: ApiContext) -> None:
    _, employee = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="No AI Company",
            email="employee@no-ai.example.com",
            role=Role.EMPLOYEE,
        )
    )
    token = login(api.client, employee.email)["access_token"]
    fake = StructuredFakeProvider()
    app.dependency_overrides[get_ai_service] = lambda: AIService(fake)
    response = api.client.post(
        "/api/v1/ai/generate-training",
        json={
            "topic": "Security",
            "audience": "Employees",
            "learning_objectives": ["Be safer"],
        },
        headers=authorization(token),
    )
    assert response.status_code == 403
    assert fake.requests == []
