import asyncio
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionFactory, engine
from app.models import (
    Certificate,
    Company,
    LearningPath,
    LearningPathAssignment,
    LearningPathItem,
    LearningPathStatus,
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
from app.services.certificates import CertificateService

DEMO_PASSWORD = "Workflix@2026"  # noqa: S105 - intentional local demo credential

PEOPLE = [
    ("admin@workflix.demo", "Marina Costa", Role.ADMIN, None),
    ("employee@workflix.demo", "Lucas Andrade", Role.EMPLOYEE, "90000000175"),
    ("beatriz.souza@workflix.demo", "Beatriz Souza", Role.EMPLOYEE, "90000000256"),
    ("caio.martins@workflix.demo", "Caio Martins", Role.EMPLOYEE, "90000000337"),
    ("daniela.lima@workflix.demo", "Daniela Lima", Role.EMPLOYEE, "90000000418"),
    ("eduardo.rocha@workflix.demo", "Eduardo Rocha", Role.EMPLOYEE, "90000000507"),
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
        "video_url": "https://www.youtube.com/watch?v=jVuQjczLvRI",
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
        "video_url": "https://www.youtube.com/watch?v=Vnc9CFhfyIM",
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

QUIZ_QUESTIONS = {
    "Segurança da Informação: atitudes que protegem": [
        {
            "text": (
                "Você recebe um e-mail urgente pedindo acesso a uma planilha restrita. O que fazer?"
            ),
            "explanation": (
                "Interromper a interação e validar o pedido pelo canal oficial reduz o risco "
                "de phishing."
            ),
            "options": [
                ("Confirmar o pedido por um canal oficial antes de agir.", True),
                ("Liberar o acesso porque a mensagem parece urgente.", False),
                ("Encaminhar a mensagem para colegas sem contexto.", False),
            ],
        },
        {
            "text": "Qual prática protege melhor uma conta corporativa?",
            "explanation": (
                "Senhas únicas e autenticação multifator reduzem o impacto de credenciais vazadas."
            ),
            "options": [
                ("Reutilizar uma senha forte em todos os sistemas.", False),
                ("Usar senha única e autenticação multifator.", True),
                ("Compartilhar a senha com o time em um documento.", False),
            ],
        },
    ],
    "LGPD na prática: dados com responsabilidade": [
        {
            "text": "Ao criar um formulário interno, quais dados pessoais devem ser solicitados?",
            "explanation": (
                "A minimização orienta a coleta apenas dos dados necessários para uma "
                "finalidade legítima."
            ),
            "options": [
                ("Somente os dados necessários para a finalidade informada.", True),
                ("Todos os dados disponíveis para uso futuro.", False),
                ("Dados adicionais sem explicar a finalidade.", False),
            ],
        },
        {
            "text": "Antes de compartilhar dados de um cliente, qual é a melhor decisão?",
            "explanation": (
                "Necessidade, finalidade e canal aprovado devem ser confirmados antes do "
                "compartilhamento."
            ),
            "options": [
                ("Enviar para agilizar e registrar depois.", False),
                ("Confirmar necessidade, destinatário e canal aprovado.", True),
                ("Copiar toda a equipe para dar transparência.", False),
            ],
        },
    ],
    "Comunicação que conecta times": [
        {
            "text": "O que torna uma mensagem de trabalho mais acionável?",
            "explanation": (
                "Contexto, decisão, responsável e prazo reduzem ambiguidades e retrabalho."
            ),
            "options": [
                ("Contexto, ação esperada, responsável e prazo.", True),
                ("Uma mensagem curta sem explicar o objetivo.", False),
                ("Muitos detalhes sem indicar a próxima ação.", False),
            ],
        },
        {
            "text": "Como oferecer um feedback útil?",
            "explanation": (
                "Feedbacks objetivos descrevem comportamento observável, impacto e próximo passo."
            ),
            "options": [
                ("Avaliar a personalidade da pessoa.", False),
                ("Descrever comportamento, impacto e acordo futuro.", True),
                ("Esperar meses para reunir vários problemas.", False),
            ],
        },
    ],
    "Liderança para ambientes híbridos": [
        {
            "text": "O que favorece autonomia em um time distribuído?",
            "explanation": (
                "Resultados esperados e critérios de decisão explícitos permitem autonomia "
                "com alinhamento."
            ),
            "options": [
                ("Centralizar todas as decisões na liderança.", False),
                ("Explicitar resultados, acordos e critérios de decisão.", True),
                ("Aumentar a quantidade de reuniões sem pauta.", False),
            ],
        },
        {
            "text": "Como acompanhar o trabalho híbrido de forma saudável?",
            "explanation": (
                "O acompanhamento deve observar entregas e remover impedimentos, não vigiar "
                "presença."
            ),
            "options": [
                ("Medir disponibilidade minuto a minuto.", False),
                ("Acompanhar resultados e remover impedimentos.", True),
                ("Evitar conversas de alinhamento.", False),
            ],
        },
    ],
    "Ética e integridade nas decisões": [
        {
            "text": "Como agir diante de um possível conflito de interesses?",
            "explanation": (
                "Declarar o conflito e buscar orientação preserva a imparcialidade da decisão."
            ),
            "options": [
                ("Declarar o conflito e consultar o canal responsável.", True),
                ("Prosseguir sem registrar para evitar atrasos.", False),
                ("Transferir a decisão sem explicar o motivo.", False),
            ],
        },
        {
            "text": (
                "Um fornecedor oferece uma vantagem pessoal durante uma negociação. O que fazer?"
            ),
            "explanation": (
                "Vantagens indevidas devem ser recusadas e comunicadas conforme a política "
                "de integridade."
            ),
            "options": [
                ("Aceitar se o valor parecer baixo.", False),
                ("Recusar e comunicar pelo canal de integridade.", True),
                ("Dividir a vantagem com a equipe.", False),
            ],
        },
    ],
    "Fundamentos de IA responsável": [
        {
            "text": "Qual cuidado vem antes de enviar conteúdo a uma ferramenta de IA?",
            "explanation": (
                "Dados confidenciais só podem ser usados em ferramentas e fluxos formalmente "
                "aprovados."
            ),
            "options": [
                ("Remover o título do documento e enviar o restante.", False),
                ("Confirmar aprovação da ferramenta e proteção dos dados.", True),
                ("Enviar primeiro e verificar a política depois.", False),
            ],
        },
        {
            "text": "Quem responde pelo uso final de uma saída gerada por IA?",
            "explanation": (
                "A revisão de fatos, fontes, linguagem e vieses permanece uma responsabilidade "
                "humana."
            ),
            "options": [
                ("A pessoa que revisa e utiliza o resultado.", True),
                ("Somente o fornecedor do modelo.", False),
                ("Ninguém, porque a saída é automática.", False),
            ],
        },
    ],
}


async def upsert_users(session: AsyncSession, company: Company) -> dict[str, User]:
    result: dict[str, User] = {}
    for email, full_name, role, cpf in PEOPLE:
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                company_id=company.id,
                email=email,
                full_name=full_name,
                cpf=cpf,
                password_hash=hash_password(DEMO_PASSWORD),
                role=role,
            )
            session.add(user)
            await session.flush()
        else:
            user.company_id = company.id
            user.full_name = full_name
            user.cpf = cpf
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
    definitions = QUIZ_QUESTIONS[training.title]
    quiz = Quiz(
        company_id=company.id,
        training_id=training.id,
        passing_score=70,
        questions=[
            Question(
                text=definition["text"],
                explanation=definition["explanation"],
                position=question_position,
                options=[
                    QuestionOption(
                        text=option_text,
                        is_correct=is_correct,
                        position=option_position,
                    )
                    for option_position, (option_text, is_correct) in enumerate(
                        definition["options"]
                    )
                ],
            )
            for question_position, definition in enumerate(definitions)
        ],
    )
    session.add(quiz)


async def ensure_learning_path(
    session: AsyncSession,
    *,
    company: Company,
    admin: User,
    title: str,
    description: str,
    trainings: list[Training],
    employees: list[User],
) -> LearningPath:
    learning_path = await session.scalar(
        select(LearningPath).where(
            LearningPath.company_id == company.id, LearningPath.title == title
        )
    )
    if learning_path is None:
        learning_path = LearningPath(
            company_id=company.id,
            created_by=admin.id,
            title=title,
            description=description,
            status=LearningPathStatus.PUBLISHED,
        )
        session.add(learning_path)
        await session.flush()
        for position, training in enumerate(trainings):
            session.add(
                LearningPathItem(
                    company_id=company.id,
                    learning_path_id=learning_path.id,
                    training_id=training.id,
                    position=position,
                    required=True,
                )
            )
    for employee in employees:
        assigned = await session.scalar(
            select(LearningPathAssignment.id).where(
                LearningPathAssignment.learning_path_id == learning_path.id,
                LearningPathAssignment.employee_id == employee.id,
            )
        )
        if assigned is None:
            session.add(
                LearningPathAssignment(
                    company_id=company.id,
                    learning_path_id=learning_path.id,
                    employee_id=employee.id,
                    due_date=date(2026, 10, 31),
                )
            )
    return learning_path


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
    progress_plan = {
        "employee@workflix.demo": {0: 45, 1: 100},
        "beatriz.souza@workflix.demo": {0: 100, 1: 100, 2: 65, 3: 100, 4: 20},
        "caio.martins@workflix.demo": {0: 100, 2: 100, 3: 40},
        "daniela.lima@workflix.demo": {1: 100, 2: 35, 4: 100},
        "eduardo.rocha@workflix.demo": {0: 100, 1: 75, 3: 100, 4: 25},
    }
    now = datetime.now(UTC)
    for employee_offset, (email, values) in enumerate(progress_plan.items(), start=1):
        employee = users[email]
        for training_index, percent in values.items():
            training = trainings[training_index]
            started_at = now - timedelta(days=employee_offset * 3 + training_index)
            progress = await session.scalar(
                select(UserProgress).where(
                    UserProgress.user_id == employee.id,
                    UserProgress.training_id == training.id,
                )
            )
            if progress is None:
                progress = UserProgress(
                    company_id=company.id,
                    user_id=employee.id,
                    training_id=training.id,
                )
                session.add(progress)
            progress.progress_percent = percent
            progress.started_at = started_at
            progress.completed_at = started_at + timedelta(days=2) if percent == 100 else None
    await session.flush()
    certificate_service = CertificateService(session)
    for email, values in progress_plan.items():
        employee = users[email]
        for training_index, percent in values.items():
            if percent == 100:
                await certificate_service.issue_training(
                    company_id=company.id,
                    user_id=employee.id,
                    training_id=trainings[training_index].id,
                )
    await ensure_learning_path(
        session,
        company=company,
        admin=users["admin@workflix.demo"],
        title="Jornada Essencial NovaTech",
        description="Segurança, privacidade e comunicação para uma rotina de trabalho consciente.",
        trainings=trainings[:3],
        employees=employees[:2],
    )
    privacy_path = await ensure_learning_path(
        session,
        company=company,
        admin=users["admin@workflix.demo"],
        title="Privacidade na prática",
        description="Uma jornada objetiva para aplicar a LGPD nas decisões do dia a dia.",
        trainings=[trainings[1]],
        employees=[demo_employee],
    )
    await session.flush()
    await certificate_service.issue_eligible(
        company_id=company.id,
        user_id=demo_employee.id,
        learning_path_ids=[privacy_path.id],
    )
    for employee in employees:
        existing_certificates = (
            await session.scalars(
                select(Certificate).where(
                    Certificate.company_id == company.id,
                    Certificate.user_id == employee.id,
                    Certificate.user_cpf.is_(None),
                )
            )
        ).all()
        for certificate in existing_certificates:
            certificate.user_cpf = employee.cpf
    await session.commit()


async def seed() -> None:
    if not get_settings().demo_mode:
        return
    async with SessionFactory() as session:
        await seed_session(session)


if __name__ == "__main__":
    asyncio.run(seed())
    asyncio.run(engine.dispose())
