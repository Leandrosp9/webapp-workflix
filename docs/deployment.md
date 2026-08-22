# Deployment

## Local Docker topology

`docker-compose.yml` defines:

- `frontend`: a static Nginx image that proxies `/api/` to the backend.
- `backend`: FastAPI, started only after PostgreSQL is healthy; Alembic and the idempotent NovaTech demo seed run before the server.
- `worker`: independently scalable document processor that starts after migrations and consumes leased PostgreSQL jobs.
- `postgres`: PostgreSQL with pgvector and a persistent named volume.

Host ports can be changed with `POSTGRES_PORT`, `BACKEND_PORT`, and `FRONTEND_PORT` without changing container-to-container addresses. PostgreSQL and the direct backend port bind to loopback; the frontend is the public ingress.

## Hardened staging topology

`docker-compose.staging.yml` overlays the local topology with:

- Redis-backed fixed-window limits for login, refresh, and AI generation;
- a private MinIO bucket exercising the same S3 adapter used with AWS S3 or Cloudflare R2;
- AWS Secrets Manager bootstrap before Pydantic validates application settings;
- disabled demo data by default and health-gated backend startup.

Prepare a private environment file and start both Compose files:

```bash
cp docker/staging.env.example docker/staging.env
docker compose --env-file docker/staging.env \
  -f docker-compose.yml \
  -f docker-compose.staging.yml \
  up --build -d
```

The overlay defaults to `SECRETS_MANAGER_PROVIDER=aws`. The workload needs `secretsmanager:GetSecretValue` for `AWS_SECRET_ID`, preferably through an instance, task, or pod identity rather than static AWS credentials. The secret must be a JSON object and only these keys are accepted:

```json
{
  "DATABASE_URL": "postgresql+psycopg://...",
  "JWT_SECRET": "at-least-32-random-characters",
  "GEMINI_API_KEY": "optional",
  "GROQ_API_KEY": "optional",
  "S3_ACCESS_KEY_ID": "optional-when-using-a-workload-role",
  "S3_SECRET_ACCESS_KEY": "optional-when-using-a-workload-role",
  "REDIS_URL": "redis://redis:6379/0"
}
```

An existing non-empty environment value wins over the managed value. Secret values are neither logged nor included in startup errors.

For a local staging smoke without AWS, explicitly set `SECRETS_MANAGER_PROVIDER=env`, `DATABASE_URL`, and `JWT_SECRET`. This fallback is not the recommended shared-staging posture.

MinIO in this overlay is single-node and appropriate for integration/staging validation, not production durability. Production should use managed S3/R2 or a supported redundant MinIO deployment, private network policies, lifecycle/backups, and `S3_SERVER_SIDE_ENCRYPTION=AES256` or `aws:kms` where supported.

## Environment

Copy `.env.example` to `.env` and replace every deployment secret. The included database password and JWT placeholder are suitable only for local development.

Document intelligence uses `RAG_EMBEDDING_MODEL=gemini-embedding-2`, a schema-fixed `RAG_EMBEDDING_DIMENSIONS=768`, `RAG_MAX_PDF_PAGES`, and `RAG_RETRIEVAL_LIMIT`. Hybrid OCR is controlled by `RAG_OCR_ENABLED`, `RAG_OCR_LANGUAGES`, `RAG_OCR_DPI`, `RAG_OCR_MIN_NATIVE_CHARS`, and `RAG_OCR_MAX_PAGES`. The backend image includes Portuguese and English Tesseract data. `GEMINI_API_KEY` enables both embeddings and grounded answer generation. Without the key, upload/extraction and OCR still succeed and the version remains `EXTRACTED` until an ADMIN requests reprocessing after configuration is available.

Worker behavior is controlled by `DOCUMENT_WORKER_POLL_SECONDS`, `DOCUMENT_JOB_LEASE_SECONDS`, `DOCUMENT_JOB_HEARTBEAT_SECONDS`, `DOCUMENT_JOB_MAX_ATTEMPTS`, `DOCUMENT_JOB_RETRY_BASE_SECONDS`, and `DOCUMENT_JOB_RETRY_MAX_SECONDS`. Keep the heartbeat shorter than the lease. Jobs are delivered at least once, so the extraction/indexing pipeline is intentionally idempotent.

Workers started outside the provided image need Tesseract 5, the configured language data, and a valid `TESSDATA_PREFIX`. Use `RAG_OCR_ENABLED=false` only as an explicit host-development fallback; scanned PDFs then fail with `PDF_NO_EXTRACTABLE_TEXT` instead of being partially indexed.

## Operational endpoints

- `GET /health`: process liveness without dependency details.
- `GET /ready`: database connectivity readiness without sensitive diagnostics.
- `GET /api/v1/system/health`: versioned application health for the web client.

## Production notes

- Terminate TLS at a managed load balancer or reverse proxy.
- Restrict direct database/Redis access and use workload identity with a managed secret store.
- Run migrations as an explicit release job when moving beyond a single-instance deployment.
- Back up PostgreSQL and object storage independently and test restoration.
- Keep `RATE_LIMIT_PROVIDER=redis`; the API fails closed with `503` if it cannot make a distributed limit decision.
- Use `FILE_STORAGE_PROVIDER=s3` or `r2` before horizontal scaling and keep the bucket private.
- Scale API and worker replicas independently. Keep worker lease/heartbeat settings consistent across replicas and alert on `DEAD_LETTER` jobs.
