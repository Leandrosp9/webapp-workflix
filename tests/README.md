# Cross-stack tests

This directory is reserved for Playwright end-to-end flows and deployment-level smoke tests. Backend unit/integration tests live in `backend/tests`; frontend component tests live beside the code in `frontend/src`.

Planned critical flows:

1. Employee login → catalog → training → quiz → completion.
2. Admin login → create → publish → assign content.
3. Two-company tenant isolation across HTTP and semantic retrieval.

