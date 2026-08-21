# Security Baseline

## Trust boundaries

The browser is untrusted. Authentication, authorization, tenant selection, quiz correction, publish transitions, and document retrieval are backend responsibilities.

## Foundation controls

- Secrets come from environment variables locally and an allowlisted AWS Secrets Manager JSON payload in staging.
- CORS is an explicit allowlist.
- Request payloads are validated before application services receive them.
- Production responses use stable error codes and never include Python tracebacks.
- Structured logs avoid passwords, tokens, API keys, prompts, and full document text.
- Each request has a correlation ID for safe diagnostics.
- Container services run with minimal privileges and expose health checks.

## Authentication controls

- Passwords use Argon2 through `pwdlib`.
- Access tokens are short-lived HS256 JWTs with issuer, audience, company, role, and token-type claims.
- Refresh tokens are opaque, stored only as SHA-256 hashes, rotated on every use, and revoked on logout.
- ADMIN and EMPLOYEE role checks execute on backend dependencies.
- Login responses do not reveal whether an email exists.

Login and refresh endpoints use fixed-window throttling. Staging uses one atomic Redis script so increment and expiry cannot diverge; local development uses an in-memory adapter. AI generation has a separate limit. Redis failure is fail-closed for protected requests and returns a stable `503` error; exceeded limits return `429` with `Retry-After`.

## Multi-tenancy controls

- `company_id` is derived from the verified principal.
- Repositories require tenant context for company-owned aggregates.
- Cross-tenant access returns the same not-found behavior as missing data where appropriate.
- Tests create at least two companies and exercise reads and writes across the boundary.
- RAG retrieval applies tenant and authorization filters before ranking context.

## AI and documents

PDF uploads require the PDF MIME type, a `%PDF-` signature, and the configured size limit. Every version receives a new company/document/version-prefixed object key and SHA-256 checksum; old bytes are not overwritten. Downloads and status reads re-authorize the user and assignment before accessing the latest version, and no public object URL is returned.

PyMuPDF extraction has a page cap, rejects password-protected or textless PDFs with safe codes, strips NUL bytes, and never logs document text. Retrieval requires the authenticated `company_id` and `user_id`, filters company, active principal, assignment, published training, requested document, and latest `READY` version before cosine ranking. PDF content is wrapped as untrusted evidence and the system prompt explicitly rejects instructions embedded in sources. Generated citations are validated against retrieved chunks before the API exposes document version, title, page, excerpt, and score.

The API never executes PDF work in its process. It commits the immutable version and tenant-scoped processing job in one database transaction. Workers claim with row locks and renewable ownership leases; an expired lease is recoverable by another replica. Bounded attempts, exponential retry, and dead-letter state prevent poison documents from looping forever. Stored job errors are allowlisted codes rather than exception messages or document content.

AI keys can come from the managed secret, generated output is schema-validated, and the RAG endpoint shares the protected AI rate-limit scope. Without `GEMINI_API_KEY`, extraction remains available but indexing and answers are not enabled.

## Staging secret handling

- `SECRETS_MANAGER_PROVIDER=aws` is the staging overlay default.
- The loader accepts only database, JWT, AI, object-storage, and Redis secret keys.
- Existing non-empty environment values are not overwritten.
- AWS access should use workload identity and least-privilege `GetSecretValue` access.
- The portable `env` mode exists for local smoke tests and is not the shared-staging default.
