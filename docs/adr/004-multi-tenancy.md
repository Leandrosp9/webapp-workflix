# ADR 004: Shared schema with explicit tenant keys

- Status: Accepted
- Date: 2026-08-21

## Context

The initial SaaS needs strong company isolation without the deployment and migration overhead of one database or schema per customer.

## Decision

Use a shared PostgreSQL schema with non-null `company_id` ownership on tenant aggregates. Tenant context is derived from the authenticated principal and required by repository queries. Composite uniqueness and indexes include `company_id` where business identity is tenant-local.

## Consequences

The model is economical and easy to operate, but missing tenant filters are security defects. Cross-company integration tests are mandatory. PostgreSQL row-level security remains a possible defense-in-depth addition after repository behavior is stable.

