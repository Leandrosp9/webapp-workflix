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

## Authentication controls

- Passwords use Argon2 through `pwdlib`.
- Access tokens are short-lived HS256 JWTs with issuer, audience, company, role, and token-type claims.
- Refresh tokens are opaque, stored only as SHA-256 hashes, rotated on every use, and revoked on logout.
- ADMIN and EMPLOYEE role checks execute on backend dependencies.
- Login responses do not reveal whether an email exists.

Login throttling is a required production-hardening item and is not implemented in the local MVP.

## Multi-tenancy controls

- `company_id` is derived from the verified principal.
- Repositories require tenant context for company-owned aggregates.
- Cross-tenant access returns the same not-found behavior as missing data where appropriate.
- Tests create at least two companies and exercise reads and writes across the boundary.
- RAG retrieval applies tenant and authorization filters before ranking context.

## AI and documents

PDF uploads require the PDF MIME type, a `%PDF-` signature, and the configured size limit. Downloads re-authorize the current user and assignment. AI keys stay in environment variables, Gemini drafts are schema-validated, and generated content requires an ADMIN to save or publish it. RAG is future scope.
