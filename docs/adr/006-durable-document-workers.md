# ADR 006: Durable PostgreSQL document workers

## Status

Accepted — 2026-08-21

## Context

PDF extraction and indexing outlive an HTTP request and must continue safely when API replicas restart or scale horizontally. FastAPI background tasks are process-local, have no durable acknowledgment, and cannot coordinate ownership across replicas.

## Decision

Persist one `document_processing_jobs` row per document version in PostgreSQL. Create that row in the same transaction as the immutable version. Independent worker containers claim eligible rows with `FOR UPDATE SKIP LOCKED`, record a bounded ownership lease, and renew it while processing.

Delivery is at least once. Extraction and indexing therefore remain idempotent: a retry replaces pages and chunks for the same immutable version. Transient storage, embedding, and unexpected processing failures retry with capped exponential backoff. Permanent PDF validation failures and exhausted attempts enter `DEAD_LETTER`; the existing ADMIN action explicitly requeues them with a fresh attempt budget.

## Consequences

- API and worker replicas scale independently without process-local job loss.
- PostgreSQL is both the domain transaction boundary and queue durability boundary, avoiding a dual-write between the version and an external broker.
- Queue throughput is intentionally optimized for document workloads rather than very high event volume.
- Worker metrics and alerts should track queue age, lease expiry, retries, and dead-letter count.
- If volume later exceeds PostgreSQL queue goals, the worker contract can move behind a managed broker without changing document-processing rules.
