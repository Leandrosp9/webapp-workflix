# ADR 001: React and Vite frontend

- Status: Accepted
- Date: 2026-08-21

## Context

Workflix needs a responsive, strongly typed web application with excellent portfolio presentation and a modest operational footprint.

## Decision

Use React with TypeScript and Vite. React Router owns route composition, TanStack Query owns server state, React Hook Form and Zod own form state and validation, Tailwind CSS supplies utility styling, Lucide supplies accessible icons, and Framer Motion is reserved for purposeful microinteractions.

## Consequences

The stack is familiar, fast to iterate, and well supported. The team must enforce feature boundaries and avoid turning global state into an application data cache.

