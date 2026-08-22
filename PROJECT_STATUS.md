# Workflix Project Status

Last updated: 2026-08-22

## Current phase

Document intelligence V2 — implemented through durable hybrid OCR processing and version-specific acknowledgement evidence, on top of extraction, indexing, retrieval, and cited answers.

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
- SQLAlchemy async infrastructure and five Alembic migrations.
- Hybrid PyMuPDF/Tesseract page extraction with provenance, OCR budgets, persistent states, checksum metadata, failure codes, and ADMIN retry.
- Gemini embedding adapter, page-aware chunks, pgvector cosine retrieval, and HNSW index.
- Tenant/assignment-scoped PDF questions with grounded answers and page/version citations.
- Durable PostgreSQL job queue with atomic enqueue, leased multi-worker claims, heartbeat renewal, bounded exponential retry, dead-letter handling, and ADMIN requeue.
- Immutable, idempotent employee acknowledgement evidence per PDF version/checksum with stale-version protection and ADMIN current/history reporting.
- Health-gated Docker Compose topology for frontend, backend, and PostgreSQL/pgvector.
- Hardened staging overlay with Redis rate limiting, private S3-compatible MinIO storage, and AWS Secrets Manager bootstrap.
- Backend/frontend tests, linting, formatting, production build, and GitHub Actions CI with Playwright.
- Automated employee, ADMIN, quiz/result, and 390×844 browser journeys against the real Docker stack.

## Pending

- V2+: learning paths, certificates, manager analytics, notifications, richer exports, and general audit UI.
- Production target selection, SSO, workload-specific IAM policies, backup/restore drills, and edge/network controls.

## Known issues

- Embedding/RAG and Gemini authoring depend on the configured API key, model availability, and provider quota; extraction and OCR do not consume Gemini.
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

Validated on 2026-08-22:

- 41 backend tests passed;
- 1 frontend component/integration test passed;
- Ruff, ESLint, and Prettier checks passed;
- the frontend production build passed;
- migration `20260822_0005` was generated offline and applied to PostgreSQL;
- PostgreSQL extensions `vector` and `pgcrypto` were present;
- frontend, backend, document worker, and PostgreSQL containers were healthy;
- the staging overlay started healthy with Redis and a private MinIO bucket;
- the 11th login request from one IP returned `429` and the limiter key was verified in Redis;
- PDF upload/download round-tripped byte-for-byte through MinIO under a tenant-scoped key;
- real two-page PDFs were versioned and extracted, page/chunk rows were persisted, and the latest version reached `READY` with a fake cloud boundary;
- the PostgreSQL repository returned one authorized page-7 vector result at cosine score `1.0000` and zero cross-tenant results; the smoke transaction was rolled back;
- 5 Playwright browser journeys passed locally, including PDF version/extraction and version acknowledgement; the original role/responsive journeys also passed against the hardened staging stack;
- the PDF browser journey was consumed by the separate worker and completed from a persisted PostgreSQL job;
- authentication and both role experiences were exercised through Nginx;
- employee learning and quiz correction returned a passing result;
- the mobile dashboard had no horizontal overflow after responsive correction.
- hybrid OCR uses fake providers in tests so no local Tesseract or Gemini quota is consumed;
- acknowledgement tests cover idempotency, tenant isolation, stale versions, version rollover, checksums, ADMIN counts, and protected deletion.
- a real image-only PDF was recognized inside the worker with Tesseract 5.5 using the installed `por+eng` language data.
