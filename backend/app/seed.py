import asyncio
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionFactory, engine
from app.models import (
    Company,
    Question,
    QuestionOption,
    Quiz,
    Role,
    Training,
    TrainingAssignment,
    TrainingStatus,
    TrainingType,
    User,
    UserProgress,
)

DEMO_PASSWORD = "Workflix@2026"  # noqa: S105 - intentional local demo credential

PEOPLE = [
    ("admin@workflix.demo", "Marina Costa", Role.ADMIN),
    ("employee@workflix.demo", "Lucas Andrade", Role.EMPLOYEE),
    ("beatriz.souza@workflix.demo", "Beatriz Souza", Role.EMPLOYEE),
    ("caio.martins@workflix.demo", "Caio Martins", Role.EMPLOYEE),
    ("daniela.lima@workflix.demo", "Daniela Lima", Role.EMPLOYEE),
    ("eduardo.rocha@workflix.demo", "Eduardo Rocha", Role.EMPLOYEE),
]

TRAININGS = [
    {
        "title": "Segurança da Informação: atitudes que protegem",
        "description": "Reconheça riscos digitais e adote hábitos seguros na rotina de trabalho.",
        "type": TrainingType.ARTICLE,
        "thumbnail_url": "/thumbnails/security.svg",
        "estimated_minutes": 18,
        "content": """# Segurança começa nas pequenas decisões

Informações de clientes, estratégias e credenciais fazem parte do patrimônio da NovaTech.
Proteger esses dados é responsabilidade de todas as pessoas.

## Três hábitos essenciais

1. Use senhas únicas e nunca compartilhe credenciais.
2. Confirme remetente, domínio e contexto antes de abrir links.
3. Bloqueie a tela sempre que se afastar do dispositivo.

## Diante de algo suspeito

Não investigue por conta própria. Preserve a mensagem, interrompa a interação e comunique
imediatamente pelo canal oficial de segurança.

## Checklist

- Mantenha o sistema atualizado.
- Use apenas ferramentas aprovadas.
- Armazene documentos no espaço corporativo.
- Na dúvida, pare e confirme.
""",
    },
    {
        "title": "LGPD na prática: dados com responsabilidade",
        "description": "Entenda como tratar dados pessoais de forma consciente em situações reais.",
        "type": TrainingType.VIDEO,
        "thumbnail_url": "/thumbnails/privacy.svg",
        "video_url": "https://example.com/workflix/lgpd-video-demo",
        "estimated_minutes": 14,
        "content": """# Dados pessoais merecem cuidado

Colete apenas o necessário para uma finalidade legítima, use os canais aprovados e respeite os
prazos de retenção definidos pela NovaTech.

Antes de compartilhar qualquer informação, confirme quem precisa recebê-la e qual é a finalidade.
Incidentes e dúvidas devem seguir o canal interno de privacidade.
""",
    },
    {
        "title": "Comunicação que conecta times",
        "description": "Torne mensagens, reuniões e feedbacks mais claros, objetivos e inclusivos.",
        "type": TrainingType.ARTICLE,
        "thumbnail_url": "/thumbnails/communication.svg",
        "estimated_minutes": 12,
        "content": """# Clareza é uma forma de cuidado

Comece pelo contexto, explique a decisão necessária e termine com responsáveis e prazo. Em
feedbacks, descreva comportamentos observáveis e o impacto gerado.

## Antes de enviar

- A pessoa tem contexto suficiente?
- A ação esperada está clara?
- O canal escolhido é adequado?
""",
    },
    {
        "title": "Liderança para ambientes híbridos",
        "description": (
            "Práticas simples para criar autonomia, confiança e alinhamento em times distribuídos."
        ),
        "type": TrainingType.VIDEO,
        "thumbnail_url": "/thumbnails/leadership.svg",
        "video_url": "https://example.com/workflix/leadership-video-demo",
        "estimated_minutes": 22,
        "content": """# Liderar é criar contexto

Ambientes híbridos funcionam quando resultados esperados, acordos de comunicação e critérios de
decisão são explícitos. Autonomia nasce da clareza, não da ausência de acompanhamento.
""",
    },
    {
        "title": "Ética e integridade nas decisões",
        "description": "Um guia direto para reconhecer conflitos e escolher o caminho responsável.",
        "type": TrainingType.PDF,
        "thumbnail_url": "/thumbnails/ethics.svg",
        "estimated_minutes": 16,
        "content": """# Integridade todos os dias

Considere o impacto sobre clientes, colegas e a reputação da NovaTech. Declare conflitos de
interesse, não ofereça vantagens indevidas e procure o canal de ética quando uma decisão parecer
ambígua.

Este item demonstra o formato PDF. O arquivo pode ser enviado pelo editor administrativo.
""",
    },
    {
        "title": "Fundamentos de IA responsável",
        "description": "Use inteligência artificial com criticidade, segurança e responsabilidade.",
        "type": TrainingType.ARTICLE,
        "thumbnail_url": "/thumbnails/ai.svg",
        "estimated_minutes": 20,
        "content": """# IA amplia capacidades — e exige julgamento

Nunca envie dados confidenciais para ferramentas não aprovadas. Revise fatos, fontes, linguagem e
possíveis vieses antes de usar uma saída gerada por IA.

## Regra de ouro

A responsabilidade pelo resultado final continua sendo humana. Use IA para apoiar o raciocínio,
não para substituir análise e prestação de contas.
""",
    },
]


async def upsert_users(session: AsyncSession, company: Company) -> dict[str, User]:
    result: dict[str, User] = {}
    for email, full_name, role in PEOPLE:
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                company_id=company.id,
                email=email,
                full_name=full_name,
                password_hash=hash_password(DEMO_PASSWORD),
                role=role,
            )
            session.add(user)
            await session.flush()
        else:
            user.company_id = company.id
            user.full_name = full_name
            user.password_hash = hash_password(DEMO_PASSWORD)
            user.role = role
            user.is_active = True
        result[email] = user
    return result


async def upsert_trainings(session: AsyncSession, company: Company, admin: User) -> list[Training]:
    result: list[Training] = []
    for definition in TRAININGS:
        training = await session.scalar(
            select(Training).where(
                Training.company_id == company.id,
                Training.title == definition["title"],
            )
        )
        values = {
            **definition,
            "status": TrainingStatus.PUBLISHED,
            "company_id": company.id,
            "created_by": admin.id,
        }
        if training is None:
            training = Training(**values)
            session.add(training)
            await session.flush()
        else:
            for field, value in values.items():
                setattr(training, field, value)
        result.append(training)
    return result


async def ensure_quiz(session: AsyncSession, company: Company, training: Training) -> None:
    if await session.scalar(select(Quiz.id).where(Quiz.training_id == training.id)):
        return
    quiz = Quiz(
        company_id=company.id,
        training_id=training.id,
        passing_score=70,
        questions=[
            Question(
                text="Qual atitude representa a melhor aplicação deste conteúdo?",
                explanation="A opção correta prioriza os canais oficiais e uma decisão consciente.",
                position=0,
                options=[
                    QuestionOption(
                        text="Aplicar a orientação e confirmar dúvidas pelo canal oficial.",
                        is_correct=True,
                        position=0,
                    ),
                    QuestionOption(
                        text="Ignorar a orientação quando a rotina estiver corrida.",
                        is_correct=False,
                        position=1,
                    ),
                    QuestionOption(
                        text="Compartilhar informações sem verificar o contexto.",
                        is_correct=False,
                        position=2,
                    ),
                ],
            ),
            Question(
                text="O que fazer quando surgir uma situação ambígua?",
                explanation="Interromper e confirmar evita decisões precipitadas e reduz riscos.",
                position=1,
                options=[
                    QuestionOption(
                        text="Decidir rapidamente sem registrar o contexto.",
                        is_correct=False,
                        position=0,
                    ),
                    QuestionOption(
                        text="Parar, registrar o contexto e buscar orientação.",
                        is_correct=True,
                        position=1,
                    ),
                    QuestionOption(
                        text="Repassar o problema para qualquer pessoa disponível.",
                        is_correct=False,
                        position=2,
                    ),
                ],
            ),
        ],
    )
    session.add(quiz)


async def seed_session(session: AsyncSession) -> None:
    company = await session.scalar(select(Company).where(Company.slug == "novatech"))
    if company is None:
        company = Company(name="NovaTech", slug="novatech")
        session.add(company)
        await session.flush()
    users = await upsert_users(session, company)
    trainings = await upsert_trainings(session, company, users["admin@workflix.demo"])
    employees = [user for user in users.values() if user.role == Role.EMPLOYEE]
    for training_index, training in enumerate(trainings):
        await ensure_quiz(session, company, training)
        for employee_index, employee in enumerate(employees):
            if employee_index > 1 and (training_index + employee_index) % 3 == 0:
                continue
            assignment = await session.scalar(
                select(TrainingAssignment).where(
                    TrainingAssignment.training_id == training.id,
                    TrainingAssignment.employee_id == employee.id,
                )
            )
            if assignment is None:
                session.add(
                    TrainingAssignment(
                        company_id=company.id,
                        training_id=training.id,
                        employee_id=employee.id,
                        due_date=date(2026, 9, 30) if training_index < 2 else None,
                    )
                )
    demo_employee = users["employee@workflix.demo"]
    progress_values = {trainings[0].id: 45, trainings[1].id: 100}
    for training_id, percent in progress_values.items():
        progress = await session.scalar(
            select(UserProgress).where(
                UserProgress.user_id == demo_employee.id,
                UserProgress.training_id == training_id,
            )
        )
        now = datetime.now(UTC)
        if progress is None:
            session.add(
                UserProgress(
                    company_id=company.id,
                    user_id=demo_employee.id,
                    training_id=training_id,
                    progress_percent=percent,
                    started_at=now,
                    completed_at=now if percent == 100 else None,
                )
            )
    await session.commit()


async def seed() -> None:
    if not get_settings().demo_mode:
        return
    async with SessionFactory() as session:
        await seed_session(session)


if __name__ == "__main__":
    asyncio.run(seed())
    asyncio.run(engine.dispose())
