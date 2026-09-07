# Deferred Work

Findings surfaced incidentally during review that are pre-existing or out of scope for the story that surfaced them. Collected here for later focused attention.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-initialize-project-structure.md`
  summary: No test tooling (unit/component test runner) is set up yet for either frontend or backend.
  evidence: Story 1.1 is scaffolding-only per its spec boundaries; `bmad-testarch-framework` is planned to run immediately after this story lands, which will address this.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-initialize-project-structure.md`
  summary: The FastAPI gateway has no CORS middleware configured.
  evidence: `backend/gateway/main.py` only defines `/health`; the frontend will need to call the backend cross-origin once real endpoints exist, and no CORS policy has been decided or applied yet.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-initialize-project-structure.md`
  summary: The Redis service in `docker-compose.yml` has no `maxmemory`/eviction policy set.
  evidence: AD-9 requires AOF persistence (now configured), but with no memory cap Redis can grow unbounded under sustained load; this needs a deliberate policy choice once real read/write volume from the Engine is known, not a guess made at scaffold time.

- source_spec: `_bmad-output/test-artifacts/framework-setup-progress.md` (bmad-testarch-framework)
  summary: Two transitive vulnerabilities in `@seontechnologies/playwright-utils`'s own dependencies — `adm-zip` (high, no fix published) and `uuid` via `exceljs` (moderate) — both from its unused `file-utils` capability (CSV/XLSX/PDF/ZIP reading), which this project does not use.
  evidence: `npm audit` in the repo root; `npm audit fix` could not resolve either (no compatible upstream version). Dev-only dependency, not shipped to production, so not blocking, but worth revisiting if `file-utils` is ever adopted or when playwright-utils publishes a fix.

- source_spec: `_bmad-output/test-artifacts/framework-setup-progress.md` (bmad-testarch-framework)
  summary: `tests/support/auth-fixture.ts` and `auth-provider.ts` are scaffolded but not wired into `tests/support/merged-fixtures.ts` — no real auth endpoint exists yet, and merging them would break every UI test unconditionally (verified by running the suite).
  evidence: `@seontechnologies/playwright-utils@4.4.0`'s `createAuthFixtures()` overrides the base `context`/`page` fixture and unconditionally calls `authProvider.manageAuthToken()`, which throws until `auth-provider.ts`'s TODOs are resolved. Also note: that same package version's `configureAuthSession()` ignores the `authStoragePath` option (verified — wrote to a stray `.auth/` at the repo root instead), so re-verify the storage path before trusting it when wiring auth back in.
