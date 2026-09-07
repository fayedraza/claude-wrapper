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
