# Docker assets

The root `docker-compose.yml` is the supported local topology. Service-specific Dockerfiles remain with the service they build so their context and runtime contract stay discoverable.

Future deployment-only assets, database initialization scripts, and observability configuration belong here. Database schema changes always remain in Alembic migrations.

