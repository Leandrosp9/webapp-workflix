# Cross-stack tests

This directory is reserved for Playwright end-to-end flows and deployment-level smoke tests. Backend unit/integration tests live in `backend/tests`; frontend component tests live beside the code in `frontend/src`.

Automated critical flows:

1. Employee login → catalog → training → quiz → completion.
2. Admin login → create → publish → assign content.
3. Admin PDF upload → durable extraction → observable version state.
4. Employee PDF player → version-specific acknowledgement contract.
5. Mobile employee experience → no horizontal overflow.

Two-company tenant isolation, stale-version rejection, acknowledgement persistence, and semantic-retrieval authorization are exercised in the backend integration suite, where database state can be isolated and cleaned deterministically.
