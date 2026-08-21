# ADR 003: Provider-neutral cloud AI service

- Status: Accepted
- Date: 2026-08-21

## Context

Workflix requires cloud AI, controlled cost, structured output, fallback, and auditable usage without locking domain services to a vendor.

## Decision

All generation uses an `AIService` backed by an `AIProvider` interface. Gemini is the primary provider and Groq is an optional fallback. Models and provider selection come from environment configuration. Persistable output must pass Pydantic validation, and generated business content always requires human review.

## Consequences

Providers can evolve independently of domain workflows. The service must expose fallback use and preserve safe failure details for observability without leaking them to end users.

