# Workflix Project Status

Last updated: 2026-08-21

## Current phase

Document intelligence V1 — implemented and validated through extraction, indexing, retrieval, and cited answers.

## Completed

- Foundation architecture, monorepo layout, ADRs, and tenant-boundary design.
- Premium responsive React/Vite product for ADMIN and EMPLOYEE.
- Login, employee home/catalog/player/quiz/result, admin dashboard/trainings/editor/users.
- Access/refresh/logout authentication, Argon2 password hashing, RBAC, and tenant isolation.
- Company, User, Training, TrainingAssignment, UserProgress, Quiz, Question, Option, and Attempt models.
- ARTICLE, VIDEO, and PDF workflows, including immutable PDF versions and authorized object storage.
- Backend-corrected quizzes and progress completion.
- Gemini REST structured generation with mock-only tests and human review before persistence.
- Idempotent NovaTech seed: six users, six trainings, six quizzes, assignments, and progress.
- FastAPI foundation with validated settings, CORS, structured logging, request IDs, safe errors, OpenAPI, liveness, and readiness.
- SQLAlchemy async infrastructure and two Alembic migrations.
- PyMuPDF page extraction with persistent states, checksum metadata, failure codes, and ADMIN retry.
- Gemini embedding adapter, page-aware chunks, pgvector cosine retrieval, and HNSW index.
- Tenant/assignment-scoped PDF questions with grounded answers and page/version citations.
- Health-gated Docker Compose topology for frontend, backend, and PostgreSQL/pgvector.
- Hardened staging overlay with Redis rate limiting, private S3-compatible MinIO storage, and AWS Secrets Manager bootstrap.
- Backend/frontend tests, linting, formatting, production build, and GitHub Actions CI with Playwright.
- Automated employee, ADMIN, quiz/result, and 390×844 browser journeys against the real Docker stack.

## In progress

- Durable queue/worker extraction is the next reliability increment before multi-replica scale.

## Pending

- V2: document acknowledgments and OCR for image-only PDFs.
- V2+: learning paths, certificates, manager analytics, notifications, reports, and audit UI.
- Production target selection, SSO, workload-specific IAM policies, backup/restore drills, and edge/network controls.

## Known issues

- No external AI credentials are configured in the demo; extraction reaches `EXTRACTED`, while embedding/RAG and Gemini authoring return an explicit configuration error until `GEMINI_API_KEY` is set.
- The PDF demo training has article fallback content but no seeded binary; an ADMIN can upload the actual PDF through the editor.
- Video demo items use placeholder external URLs and are intended to be replaced with owned media.
- Local file storage, the in-memory limiter, and the default JWT secret are development-only.
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

- 34 backend tests passed;
- 1 frontend component/integration test passed;
- Ruff, ESLint, and Prettier checks passed;
- the frontend production build passed;
- migrations through `20260821_0003` were applied to PostgreSQL;
- PostgreSQL extensions `vector` and `pgcrypto` were present;
- frontend, backend, and PostgreSQL containers were healthy;
- the staging overlay started healthy with Redis and a private MinIO bucket;
- the 11th login request from one IP returned `429` and the limiter key was verified in Redis;
- PDF upload/download round-tripped byte-for-byte through MinIO under a tenant-scoped key;
- real two-page PDFs were versioned and extracted, page/chunk rows were persisted, and the latest version reached `READY` with a fake cloud boundary;
- the PostgreSQL repository returned one authorized page-7 vector result at cosine score `1.0000` and zero cross-tenant results; the smoke transaction was rolled back;
- 4 Playwright browser journeys passed locally, including PDF version/extraction; the original 3 role/responsive journeys also passed against the hardened staging stack;
- authentication and both role experiences were exercised through Nginx;
- employee learning and quiz correction returned a passing result;
- the mobile dashboard had no horizontal overflow after responsive correction.
