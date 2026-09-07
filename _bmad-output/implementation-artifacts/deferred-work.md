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

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-submit-settings-request-and-approve.md`
  summary: The "Reject" row of this story's I/O matrix (Settings drawer Reject button discards the card with no network call) has no automated test — only a one-off manual headless-browser check during implementation.
  evidence: No frontend component-test framework exists yet in this project (confirmed: `find frontend -iname "*.test.*" -o -iname "*.spec.*"` returns nothing); it's deliberately deferred to `bmad-testarch-automate` running after Epic 1 completes, per the human's decision this session. Every other row in this story's matrix is covered by a real, passing backend test — this is the one row that structurally can't be, without pulling in component-test tooling ahead of that plan.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-submit-settings-request-and-approve.md`
  summary: `apply_action()` doesn't re-validate on-disk state against `action.action` before writing — "create" silently overwrites a file that came to exist between propose and apply, "update"/"revoke" silently succeed even if the file never existed by then.
  evidence: `backend/brain/settings_router/apply.py`; a time-of-check-to-time-of-use gap between when a proposal is previewed and when the human approves it. Not a violation of the story's AC (the previewed content is still written correctly), but a real robustness gap under concurrent `.claude/` modification. Low urgency for a local single-developer tool.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-submit-settings-request-and-approve.md`
  summary: `apply_action()` writes via a direct `target.write_text(...)`, not an atomic write (temp file + rename) — a crash or interruption mid-write could leave a corrupted `.claude/` config file.
  evidence: `backend/brain/settings_router/apply.py`; this is the app's one deliberately safety-gated mutation path, which makes atomicity more valuable here than average, but the failure window is narrow and self-recoverable (re-submit the request).

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-submit-settings-request-and-approve.md`
  summary: `_read_claude_dir_context()`'s directory walk isn't guarded against `.claude/` being removed between its `exists()` check and the `rglob()` walk (TOCTOU) — would raise an unhandled `FileNotFoundError` mid-scan.
  evidence: `backend/brain/settings_router/router.py`; requires something else concurrently deleting `.claude/` mid-request, implausible for a local single-developer tool. Cheap to guard (`try/except FileNotFoundError`) if ever revisited alongside other robustness work.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-submit-settings-request-and-approve.md`
  summary: `SettingAction`/`SettingsRouterOutput`/`TargetCategory` are hand-duplicated between `backend/brain/settings_router/models.py` and `frontend/lib/settings-api.ts` with nothing (codegen, schema export, contract test) enforcing they stay in sync as the app evolves.
  evidence: Both sides currently match (verified in this review), but every future change to the schema requires manually updating both files with no test catching drift. Worth an OpenAPI-schema-driven codegen step once the API surface stabilizes past this first endpoint.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-submit-settings-request-and-approve.md`
  summary: No upper bound on `SettingsRouterOutput.updates` length or per-action `content` size on the write side, unlike the read side (`_MAX_CHARS_PER_FILE`/`_MAX_CONTEXT_CHARS` bound what's fed to the classifier).
  evidence: `backend/brain/settings_router/router.py`/`models.py`; low risk at current scale (a single developer's plain-language request), but worth a bound before this becomes a shared/multi-user surface.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-submit-settings-request-and-approve.md`
  summary: No audit trail (who/when/which path/old vs. new content) around `apply_action`'s writes, despite it being the sole approval-gated mutation point in the app.
  evidence: `backend/brain/settings_router/apply.py`; the product's core pitch is safe, reviewable config changes, which an audit log would reinforce. Not required by this story's AC.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-submit-settings-request-and-approve.md`
  summary: Closing the Settings drawer (Escape, backdrop click, or the × button) discards any pending/undecided proposed-change cards with no confirmation.
  evidence: `frontend/components/settings/SettingsDrawer.tsx`; an accidental close loses a reviewed-but-not-yet-approved proposal, forcing a re-submit and re-wait on the LLM call. UX polish, not a correctness or safety issue (no file was written).

- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-submit-settings-request-and-approve.md`
  summary: `ProposedChangeCard`'s content preview has no truncation/max-height/collapse control, and "update" actions show only the new full content with no diff against the existing file.
  evidence: `frontend/components/settings/ProposedChangeCard.tsx`; a large generated file would blow out the card, and for updates there's no way to see exactly what's changing versus what already exists — both reduce how well the approval step actually conveys the change, though neither violates this story's AC.
