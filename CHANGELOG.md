# Changelog

All notable development changes are recorded here. This project follows the spirit of Keep a Changelog and uses semantic versioning once releases begin.

## [Unreleased]

No unreleased product changes. The portfolio scope is closed.

## [0.1.0] - 2026-08-22

### Added

- Focused Workflix MVP for ADMIN and EMPLOYEE roles.
- Secure JWT authentication with refresh rotation, logout, Argon2 passwords, RBAC, and tenant isolation.
- Company, user, training, assignment, progress, quiz, question, option, and attempt persistence.
- ARTICLE, VIDEO, and PDF content with draft/published lifecycle and protected PDF storage.
- Employee home, catalog, player, quiz, and result interfaces.
- Admin analytics, training/quiz editor, assignments, PDF upload, and employee management.
- Gemini structured training/quiz generation with Pydantic validation and mock-only tests.
- Idempotent NovaTech demo seed and six local SVG cover assets.
- MVP schema migration `20260821_0002` and end-to-end Docker validation.
- Playwright employee, ADMIN, quiz/result, and mobile journeys executed against Docker in CI.
- Redis-backed rate limiting for authentication and AI generation with atomic fixed windows.
- Local and S3-compatible object-storage adapters with tenant-scoped private PDF keys.
- AWS Secrets Manager bootstrap with an explicit allowlist and environment precedence.
- Hardened staging Compose overlay with Redis, MinIO, private bucket bootstrap, and pinned images.
- Immutable PDF document/version records with unique private object keys and SHA-256 checksums.
- PyMuPDF page extraction, persistent processing states, safe failure codes, and ADMIN retry.
- Gemini `gemini-embedding-2` adapter with task-specific query/document prefixes.
- 768-dimensional pgvector chunks, HNSW cosine index, latest-version retrieval, and tenant/assignment filters.
- Employee document questions with grounded Gemini answers, page/version sources, and prompt-injection isolation.
- Durable PostgreSQL document jobs, independent worker containers, leased claims, heartbeats, exponential retry, dead-letter handling, and atomic upload enqueue.
- Gemini generation default updated to `gemini-3.6-flash`, with test configuration explicitly blocking real provider credentials.
- Hybrid OCR, immutable PDF acknowledgements, ordered learning paths, verifiable certificates, management analytics, and safe CSV exports.
- Portfolio-ready responsive polish, realistic role-specific demo data, loading skeletons, action feedback, and screenshot assets.
- Automated ADMIN AI authoring → publish → assignment → EMPLOYEE quiz/completion → ADMIN analytics demonstration flow.

- Product, architecture, database, security, and deployment documentation.
- Architecture decision records for the frontend, backend, AI, multi-tenancy, and RAG foundations.
- Phase 1 monorepo and environment contract.
- Responsive Workflix foundation experience with live API health state.
- FastAPI configuration, JSON logging, request correlation, error envelopes, and health/readiness probes.
- SQLAlchemy/Alembic foundation with PostgreSQL `vector` and `pgcrypto` extensions.
- Cloud AI contracts, explicit fallback orchestration, provider registry, and policy-disabled Ollama adapter.
- Page-aware RAG chunking, embedding and retrieval contracts, and idempotent document processing.
- Docker Compose topology, multi-stage images, CI pipeline, and foundation test suites.
