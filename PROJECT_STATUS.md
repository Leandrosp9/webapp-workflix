# Workflix Project Status

Last updated: 2026-08-21

## Current phase

Focused MVP — implemented and validated end to end.

## Completed

- Foundation architecture, monorepo layout, ADRs, and tenant-boundary design.
- Premium responsive React/Vite product for ADMIN and EMPLOYEE.
- Login, employee home/catalog/player/quiz/result, admin dashboard/trainings/editor/users.
- Access/refresh/logout authentication, Argon2 password hashing, RBAC, and tenant isolation.
- Company, User, Training, TrainingAssignment, UserProgress, Quiz, Question, Option, and Attempt models.
- ARTICLE, VIDEO, and PDF workflows, including authorized local PDF storage.
- Backend-corrected quizzes and progress completion.
- Gemini REST structured generation with mock-only tests and human review before persistence.
- Idempotent NovaTech seed: six users, six trainings, six quizzes, assignments, and progress.
- FastAPI foundation with validated settings, CORS, structured logging, request IDs, safe errors, OpenAPI, liveness, and readiness.
- SQLAlchemy async infrastructure and two Alembic migrations.
- Preserved provider-neutral AI and future RAG module structure.
- Health-gated Docker Compose topology for frontend, backend, and PostgreSQL/pgvector.
- Backend/frontend tests, linting, formatting, production build, and GitHub Actions CI.
- Desktop and 390×844 browser verification against the real Docker stack.

## In progress

- No focused MVP implementation remains open.

## Pending

- V2: document extraction/versioning, acknowledgments, embeddings, pgvector RAG, and cited answers.
- V2+: learning paths, certificates, manager analytics, notifications, reports, and audit UI.
- Production hardening: external object storage, rate limiting, SSO, secrets manager, and deployment target.

## Known issues

- No external AI credentials are configured in the demo; Gemini authoring returns an explicit configuration error until `GEMINI_API_KEY` is set.
- The PDF demo training has article fallback content but no seeded binary; an ADMIN can upload the actual PDF through the editor.
- Video demo items use placeholder external URLs and are intended to be replaced with owned media.
- Local file storage and the default JWT secret are development-only.
- The validation machine already had port `5173` allocated, so the complete container smoke test used the supported `FRONTEND_PORT=5174` override. The documented default remains `5173`.

## Decisions

- Use a pragmatic modular monolith before considering independently deployed services.
- Enforce multi-tenancy in backend authorization and repository queries; never trust a client-provided `company_id`.
- Keep cloud AI and embedding providers behind application interfaces.
- Run every production schema change through Alembic; never use `create_all()` as a deployment mechanism.

## How to test

```bash
cp .env.example .env
docker compose up --build
```

Then open `http://localhost:5173`, `http://localhost:8000/health`, and `http://localhost:8000/docs`. If 5173 is occupied, use the documented `FRONTEND_PORT=5174` override.

For local quality checks, use the commands documented in `README.md`.

Validated on 2026-08-21:

- 22 backend tests passed;
- 1 frontend component/integration test passed;
- Ruff, ESLint, and Prettier checks passed;
- the frontend production build passed;
- migrations through `20260821_0002` were applied to PostgreSQL;
- PostgreSQL extensions `vector` and `pgcrypto` were present;
- frontend, backend, and PostgreSQL containers were healthy;
- authentication and both role experiences were exercised through Nginx;
- employee learning and quiz correction returned a passing result;
- the mobile dashboard had no horizontal overflow after responsive correction.
