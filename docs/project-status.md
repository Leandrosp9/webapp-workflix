# Status do Projeto Workflix

Last updated: 2026-08-25

## Release status

`PORTFOLIO RELEASE READY`

The functional scope is closed. Workflix is published and validated as a polished SaaS portfolio
project for GitHub, LinkedIn, recruiter reviews, and freelancer demonstrations.

## Completed product scope

- Responsive ADMIN and EMPLOYEE experiences with a premium dark interface and Workflix branding.
- Authentication, role-based access control, tenant isolation, rotating refresh tokens, and Argon2
  password hashing.
- Employee home, catalog, navigable player, progress, quizzes, learning paths, and automatically
  issued training/path certificates with CPF and public verification.
- ADMIN dashboard, training authoring, assignments, learning paths, analytics, and CSV/PDF exports.
- Gemini-assisted training and quiz generation behind a provider interface, with human review
  before persistence.
- ARTICLE, VIDEO, and versioned PDF workflows with a durable worker, private object storage,
  extraction, semantic retrieval, and grounded answers.
- Realistic NovaTech demo data for employees, trainings, progress, quizzes, paths, certificates,
  and analytics.
- Docker Compose development stack plus a published cloud portfolio environment.
- CI quality gates for backend, frontend, Playwright, formatting, and production build.

## Published environment

| Component             | Provider                | Status                                                         |
| --------------------- | ----------------------- | -------------------------------------------------------------- |
| Web application       | Cloudflare Pages        | [workflix.pages.dev](https://workflix.pages.dev)               |
| API                   | Northflank              | [Swagger UI](https://p01--backend--5ljdt6tvrrkz.code.run/docs) |
| Backend service       | Northflank              | Running with liveness and readiness checks                     |
| Document worker       | Northflank              | Running as a separate private worker                           |
| PostgreSQL + pgvector | Neon                    | Connected and ready                                            |
| Rate limiting         | Managed Redis           | Connected                                                      |
| PDF object storage    | Backblaze B2            | Private bucket with default encryption                         |
| AI authoring          | Google Gemini           | Configured through a protected secret                          |
| Runtime secrets       | Northflank secret group | Injected into backend and worker                               |

The backend health endpoints are
[health](https://p01--backend--5ljdt6tvrrkz.code.run/health) and
[readiness](https://p01--backend--5ljdt6tvrrkz.code.run/ready).

## Final validation

Validated on 2026-08-25:

- Backend: 45 Pytest tests passed.
- Python quality: Ruff lint and format checks passed.
- Frontend: 1 Vitest test passed; ESLint and Prettier checks passed.
- Production build: Vite passed with 1,746 modules transformed.
- Local E2E: 9 Playwright journeys passed, including learning completion, automatic certificate,
  PDF processing, account management, and responsive viewports.
- Public PDF flow: upload, Backblaze B2 persistence, durable-worker extraction, status polling, and
  cleanup passed.
- Gemini: a real training draft was generated successfully with `gemini-3.6-flash`.
- API: `/health` and `/ready` returned HTTP 200; direct SPA routes returned HTTP 200.
- Worker: the running replica logged `document_worker_started`.
- Database: migration-owned startup completed locally at Alembic head `20260825_0007`.
- Local Docker: frontend, backend, worker, and PostgreSQL containers are healthy; liveness and
  readiness return HTTP 200.

## Demonstration flow

The validated journey is:

1. ADMIN signs in, opens the dashboard, creates a training, generates training and quiz drafts,
   publishes, and assigns it.
2. EMPLOYEE signs in, opens the assigned training, progresses through the content, passes the quiz,
   completes the training, and views the certificate.
3. ADMIN returns to Analytics and confirms the employee completion.

Playwright mocks the external Gemini response only in the deterministic end-to-end authoring
journey. A separate live smoke test confirmed the deployed Gemini integration without persisting
its generated draft.

## Run locally

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: `http://localhost:5173`
- API documentation: `http://localhost:8000/docs`
- Liveness: `http://localhost:8000/health`
- Readiness: `http://localhost:8000/ready`

## Demo credentials

| Role          | Email                    | Password        |
| ------------- | ------------------------ | --------------- |
| Administrator | `admin@workflix.demo`    | `Workflix@2026` |
| Employee      | `employee@workflix.demo` | `Workflix@2026` |

These credentials belong only to the fictional portfolio dataset and must not be reused elsewhere.

## Real limitations

- The public environment uses entry-level hosting resources, so authentication and cold operations
  can take several seconds.
- Gemini and embeddings depend on provider availability and free-tier quota.
- Demo video trainings provide supporting content but do not bundle licensed video media.
- The seeded PDF training uses article fallback content; upload a source PDF to demonstrate binary
  extraction.
- A custom domain, production backup policy, external alert destination, and formal uptime SLA are
  outside this portfolio release.
- The public demo credentials are intentionally shared; the environment must not contain real
  company or personal data.

## Future roadmap

- Enterprise SSO and organization-managed identity.
- Advanced notification policies and delivery channels.
- Department, position, and manager-level administration.
- Extended audit reporting and production observability integrations.

These items are future product directions and are not presented as available features.
