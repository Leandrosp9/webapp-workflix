# Deployment

## Local Docker topology

`docker-compose.yml` defines:

- `frontend`: a static Nginx image that proxies `/api/` to the backend.
- `backend`: FastAPI, started only after PostgreSQL is healthy; Alembic runs before the server.
- `postgres`: PostgreSQL with pgvector and a persistent named volume.

## Environment

Copy `.env.example` to `.env` and replace every deployment secret. The included database password and JWT placeholder are suitable only for local development.

## Operational endpoints

- `GET /health`: process liveness without dependency details.
- `GET /ready`: database connectivity readiness without sensitive diagnostics.
- `GET /api/v1/system/health`: versioned application health for the web client.

## Production notes

- Terminate TLS at a managed load balancer or reverse proxy.
- Restrict direct database access and use a managed secret store.
- Run migrations as an explicit release job when moving beyond a single-instance deployment.
- Back up PostgreSQL and object storage independently and test restoration.
- Replace local file storage with an object storage implementation before horizontal scaling.

