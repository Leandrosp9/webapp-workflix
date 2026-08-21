# Workflix Project Status

Last updated: 2026-08-21

## Current phase

Phase 1 — Foundation is complete. The next implementation phase is Phase 2 — Authentication and Multi-Tenancy.

## Completed

- Phase 0 workspace discovery: the initial directory was empty and not yet a Git repository.
- Initial product and technical architecture.
- Monorepo layout decision for frontend, backend, documentation, and deployment assets.
- Initial relational model and tenant-boundary design.
- Architecture decision records for the major foundational choices.
- Responsive React/Vite foundation with typed health state and production Nginx image.
- FastAPI foundation with validated settings, CORS, structured logging, request IDs, safe errors, OpenAPI, liveness, and readiness.
- SQLAlchemy session infrastructure and Alembic baseline enabling `vector` and `pgcrypto`.
- Provider-neutral AI/RAG module structure, explicit fallback, cloud-only Ollama guardrail, page-aware chunking, tenant-bound retrieval contracts, and idempotent document processing.
- Health-gated Docker Compose topology for frontend, backend, and PostgreSQL/pgvector.
- Backend/frontend tests, linting, formatting, production build, and GitHub Actions CI.
- Professional English README, banner, architecture documentation, database design, security baseline, deployment notes, and ADRs.

## In progress

- No Phase 1 implementation remains open.

## Pending

- Phase 2: authentication, Company, User, refresh tokens, RBAC, and tested tenant isolation.
- Phase 3: complete visual system, public landing page, login, and authenticated shell.
- Phases 4–15 as described in the product roadmap.

## Known issues

- No external AI credentials are configured; no AI call is required in Phase 1.
- The foundation deliberately has no business tables yet. The first domain migration belongs to Phase 2 and will introduce companies, users, roles, departments, and positions together with their invariants.
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

Then open `http://localhost:5173`, `http://localhost:8000/health`, and `http://localhost:8000/docs`.

For local quality checks, use the commands documented in `README.md`.

Validated on 2026-08-21:

- 10 backend tests passed;
- 1 frontend component/integration test passed;
- Ruff, ESLint, and Prettier checks passed;
- the frontend production build passed;
- migration `20260821_0001` was applied;
- PostgreSQL extensions `vector` and `pgcrypto` were present;
- frontend, backend, and PostgreSQL containers were healthy;
- `/health`, `/ready`, and the frontend returned successful responses.
