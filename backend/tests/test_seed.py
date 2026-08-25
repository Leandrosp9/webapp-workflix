import asyncio

from app.models import Certificate, Company, LearningPath, Quiz, Training, TrainingType, User
from app.seed import seed_session
from sqlalchemy import func, select

from conftest import ApiContext, login


def test_demo_seed_is_idempotent_and_credentials_work(api: ApiContext) -> None:
    async def run_twice() -> tuple[int, int, int, int, int, int, int]:
        async with api.sessions() as session:
            await seed_session(session)
            await seed_session(session)
            return (
                int(await session.scalar(select(func.count(Company.id))) or 0),
                int(await session.scalar(select(func.count(User.id))) or 0),
                int(await session.scalar(select(func.count(Training.id))) or 0),
                int(await session.scalar(select(func.count(Quiz.id))) or 0),
                int(await session.scalar(select(func.count(LearningPath.id))) or 0),
                int(await session.scalar(select(func.count(Certificate.id))) or 0),
                int(
                    await session.scalar(
                        select(func.count(Training.id)).where(
                            Training.type == TrainingType.VIDEO,
                            Training.video_url.is_not(None),
                        )
                    )
                    or 0
                ),
            )

    companies, users, trainings, quizzes, paths, certificates, videos = asyncio.run(run_twice())
    assert (companies, users, trainings, quizzes) == (1, 6, 6, 6)
    assert (paths, certificates) == (2, 11)
    assert videos == 2
    assert login(api.client, "admin@workflix.demo", "Workflix@2026")["user"]["role"] == "ADMIN"
    employee = login(api.client, "employee@workflix.demo", "Workflix@2026")["user"]
    assert employee["role"] == "EMPLOYEE"
    assert employee["cpf"] == "90000000175"
    tokens = login(api.client, "employee@workflix.demo", "Workflix@2026")
    leaderboard = api.client.get(
        "/api/v1/employee/leaderboard",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert leaderboard.status_code == 200, leaderboard.text
    assert leaderboard.json()["entries"][0]["full_name"] == "Beatriz Souza"
    assert leaderboard.json()["current_user"]["full_name"] == "Lucas Andrade"
    assert leaderboard.json()["current_user"]["rank"] == 5
