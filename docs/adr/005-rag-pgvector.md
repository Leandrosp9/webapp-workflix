# ADR 005: Page-aware RAG with pgvector

- Status: Accepted
- Date: 2026-08-21

## Context

Employees need source-aware answers over private company documents and semantic retrieval without local GPU requirements.

## Decision

Extract PDF text and page metadata with PyMuPDF, create paragraph-aware overlapping chunks, obtain embeddings through a cloud-provider interface, and store them in PostgreSQL using pgvector. Retrieval always applies tenant and permission filters before vector ranking.

## Consequences

Transactional metadata and vectors share one operational datastore at MVP scale. Embedding dimensions and indexes must be introduced with provider/model migrations, and larger scale may justify a dedicated vector service later.

