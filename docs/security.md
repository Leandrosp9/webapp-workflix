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

PDF uploads require the PDF MIME type, a `%PDF-` signature, and the configured size limit. Objects use company/training-prefixed keys in local or private S3-compatible storage. Downloads re-authorize the current user and assignment before retrieving bytes; no public object URL is returned. AI keys can come from the managed secret, Gemini drafts are schema-validated, and generated content requires an ADMIN to save or publish it. PDF extraction and RAG remain future scope.

## Staging secret handling

- `SECRETS_MANAGER_PROVIDER=aws` is the staging overlay default.
- The loader accepts only database, JWT, AI, object-storage, and Redis secret keys.
- Existing non-empty environment values are not overwritten.
- AWS access should use workload identity and least-privilege `GetSecretValue` access.
- The portable `env` mode exists for local smoke tests and is not the shared-staging default.
