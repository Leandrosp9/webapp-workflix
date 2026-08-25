import asyncio
from uuid import uuid4

from app.core.security import hash_password
from app.models import Role, User

from conftest import ApiContext, create_company_user, login


async def add_employee(api: ApiContext, company_id) -> User:
    async with api.sessions() as session:
        employee = User(
            company_id=company_id,
            email="learner@quiz.example.com",
            full_name="Quiz Learner",
            cpf="90000000760",
            password_hash=hash_password("StrongDemo@2026"),
            role=Role.EMPLOYEE,
        )
        session.add(employee)
        await session.commit()
        return employee


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_quiz_answers_are_hidden_and_scored_on_backend(api: ApiContext) -> None:
    company, admin = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Quiz Company",
            email="admin@quiz.example.com",
            role=Role.ADMIN,
        )
    )
    employee = asyncio.run(add_employee(api, company.id))
    admin_token = login(api.client, admin.email)["access_token"]
    employee_token = login(api.client, employee.email)["access_token"]
    training = api.client.post(
        "/api/v1/trainings",
        json={
            "title": "Privacy basics",
            "description": "Learn the fundamentals of privacy at work.",
            "type": "ARTICLE",
            "content": "Only collect data that the business needs.",
            "estimated_minutes": 8,
            "status": "PUBLISHED",
        },
        headers=headers(admin_token),
    ).json()
    api.client.post(
        f"/api/v1/trainings/{training['id']}/assignments",
        json={"employee_ids": [str(employee.id)]},
        headers=headers(admin_token),
    )
    editor_payload = {
        "passing_score": 70,
        "questions": [
            {
                "text": "What is data minimization?",
                "explanation": "Collect only what is necessary.",
                "options": [
                    {"text": "Collect everything", "is_correct": False},
                    {"text": "Collect only necessary data", "is_correct": True},
                ],
            },
            {
                "text": "What should you do with suspicious requests?",
                "explanation": "Report them through the official channel.",
                "options": [
                    {"text": "Ignore them", "is_correct": False},
                    {"text": "Report them", "is_correct": True},
                ],
            },
        ],
    }
    saved = api.client.put(
        f"/api/v1/trainings/{training['id']}/quiz",
        json=editor_payload,
        headers=headers(admin_token),
    )
    assert saved.status_code == 200, saved.text
    saved_quiz = saved.json()

    public = api.client.get(
        f"/api/v1/employee/trainings/{training['id']}/quiz",
        headers=headers(employee_token),
    )
    assert public.status_code == 200
    assert "is_correct" not in public.text
    assert "explanation" not in public.text

    answers = [
        {
            "question_id": question["id"],
            "option_id": question["options"][1]["id"],
        }
        for question in saved_quiz["questions"]
    ]
    result = api.client.post(
        f"/api/v1/employee/trainings/{training['id']}/quiz/attempts",
        json={"answers": answers},
        headers=headers(employee_token),
    )
    assert result.status_code == 200, result.text
    assert result.json()["score"] == 100
    assert result.json()["passed"] is True
    assert all(answer["is_correct"] for answer in result.json()["answers"])

    detail = api.client.get(
        f"/api/v1/employee/trainings/{training['id']}",
        headers=headers(employee_token),
    )
    assert detail.json()["progress_percent"] == 100


def test_quiz_rejects_option_from_another_question(api: ApiContext) -> None:
    company, admin = asyncio.run(
        create_company_user(
            api.sessions,
            company_name="Quiz Validation",
            email="admin@quiz-validation.example.com",
            role=Role.ADMIN,
        )
    )
    employee = asyncio.run(add_employee(api, company.id))
    admin_token = login(api.client, admin.email)["access_token"]
    employee_token = login(api.client, employee.email)["access_token"]
    training_id = api.client.post(
        "/api/v1/trainings",
        json={
            "title": "Validation training",
            "description": "A training used to validate quiz submissions.",
            "type": "ARTICLE",
            "content": "Validation matters.",
            "estimated_minutes": 5,
            "status": "PUBLISHED",
        },
        headers=headers(admin_token),
    ).json()["id"]
    api.client.post(
        f"/api/v1/trainings/{training_id}/assignments",
        json={"employee_ids": [str(employee.id)]},
        headers=headers(admin_token),
    )
    quiz = api.client.put(
        f"/api/v1/trainings/{training_id}/quiz",
        json={
            "questions": [
                {
                    "text": "Choose the safe answer",
                    "options": [
                        {"text": "Safe", "is_correct": True},
                        {"text": "Unsafe", "is_correct": False},
                    ],
                }
            ]
        },
        headers=headers(admin_token),
    ).json()
    invalid = api.client.post(
        f"/api/v1/employee/trainings/{training_id}/quiz/attempts",
        json={
            "answers": [
                {
                    "question_id": quiz["questions"][0]["id"],
                    "option_id": str(uuid4()),
                }
            ]
        },
        headers=headers(employee_token),
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "INVALID_QUIZ_SUBMISSION"
