# ADR 002: Modular FastAPI monolith

- Status: Accepted
- Date: 2026-08-21

## Context

The product spans many related domains but starts with a small team and needs reliable transactions and simple deployment.

## Decision

Use FastAPI, Pydantic, SQLAlchemy 2.x, and Alembic in a modular monolith. HTTP routers call application services; services own workflows; repositories isolate persistence where useful; domain modules remain independently testable.

## Consequences

Deployment and local development stay simple. Clear module contracts are required so high-load document or AI work can later move to workers or services without rewriting domain rules.

