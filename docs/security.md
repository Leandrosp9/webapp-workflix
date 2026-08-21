# Security Baseline

## Trust boundaries

The browser is untrusted. Authentication, authorization, tenant selection, quiz correction, publish transitions, and document retrieval are backend responsibilities.

## Foundation controls

- Secrets and deployment-specific values come from environment variables.
- CORS is an explicit allowlist.
- Request payloads are validated before application services receive them.
- Production responses use stable error codes and never include Python tracebacks.
- Structured logs avoid passwords, tokens, API keys, prompts, and full document text.
- Each request has a correlation ID for safe diagnostics.
- Container services run with minimal privileges and expose health checks.

## Planned authentication controls

Phase 2 introduces secure password hashing, short-lived access tokens, rotating refresh tokens stored as hashes, role checks on backend entry points, login throttling, and revocation-aware logout.

## Multi-tenancy controls

- `company_id` is derived from the verified principal.
- Repositories require tenant context for company-owned aggregates.
- Cross-tenant access returns the same not-found behavior as missing data where appropriate.
- Tests create at least two companies and exercise reads and writes across the boundary.
- RAG retrieval applies tenant and authorization filters before ranking context.

## AI and documents

Uploaded content is data, not trusted instructions. RAG prompts explicitly treat document instructions as untrusted. AI observability records operational metadata without storing private prompts or document bodies by default.

