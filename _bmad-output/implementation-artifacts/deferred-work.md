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

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-view-current-configuration.md`
  summary: Permission grants have no defined on-disk schema anywhere in the docs (PRD FR-4/5/6 and ARCHITECTURE-SPINE.md AD-6 describe only behavior, no field names) — Story 1.3 deliberately shows an empty grants list rather than inventing one. Story 1.4 must define the real schema.
  evidence: Confirmed by direct investigation across PRD/architecture/UX docs during Story 1.3 planning — nothing concrete exists. Story 1.3 only checks for a `permissionGrants` key in `settings.json`/`settings.local.json` (chosen specifically to not collide with Claude Code's own reserved `permissions` key, since this repo's `.claude/settings.json` is the same file real Claude Code reads and already has a `hooks` block it enforces) and shows nothing when absent. **Story 1.4 should write real grant data under that same `permissionGrants` key** so Story 1.3's reader picks it up automatically — verify that assumption holds once 1.4 is implemented, don't take it on faith. Specific open design question for 1.4: should a grant be a flat per-file toggle, or per-action like real Claude Code's own permission rules (`Read(pattern)`, `Edit(pattern)`, `Bash(pattern)`, etc.)? Raised by the human during Story 1.3 planning — FR-4's "itemized checklist of every file and MCP server" doesn't settle it either way. **Raised again via PR #4 review comment:** `ConfigKind` (`backend/brain/settings_router/models.py`) is currently only `rule`/`agent`/`mcp`, and `_permission_grant_items()` renders every `permissionGrants` entry as `kind="mcp"` regardless of whether it's a file grant or an MCP server grant. Story 1.4's own AC treats files and MCP servers as two distinct grant types — once its schema lands, add a separate `file` `ConfigKind` rather than continuing to lump both under `mcp`.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-view-current-configuration.md`
  summary: `_permission_grant_items()` concatenates grants from `settings.json` and `settings.local.json` with no de-duplication or precedence handling — the same grant appearing in both would render as two indistinguishable rows instead of reflecting a local-overrides-team precedence.
  evidence: `backend/brain/settings_router/summary.py`; can't be meaningfully fixed without knowing what "the same grant" means (identity/equality semantics), which isn't defined anywhere since no grant schema exists yet (see the entry above) — Story 1.4's territory once the real schema lands.
  RESOLVED (post-Story-1.4, PR #7): moot as of this fix — `_permission_grant_items()` no longer reads `settings.json` at all; `permissionGrants` is scoped to `settings.local.json` only, matching `grants.py`'s `list_grants()` exactly, so there is only ever one file to reconcile. Prompted by the human asking what happens if someone hand-edits a `permissionGrants` array directly into `settings.json` — confirmed it's a real, reachable case (not just unreachable dead code), so rather than defining precedence semantics for two locations, the second location was removed. A hand-edited `settings.json` entry is now invisible everywhere in the app, not merely unmanaged.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-view-current-configuration.md`
  summary: No pagination/size bound on the `GET /api/settings/current` response — a large `rules/`/`agents/` directory or many permission grants returns everything unbounded, with no truncation or "show more" in the drawer.
  evidence: `backend/brain/settings_router/summary.py`, `frontend/components/settings/SettingsDrawer.tsx`; low risk at current scale (a single developer's local `.claude/`), same category as the existing deferred "no upper bound on SettingsRouterOutput.updates" item from Story 1.2.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-view-current-configuration.md`
  summary: None of `frontend/lib/settings-api.ts`'s three client functions (`proposeSettingsChange`, `applySettingsChange`, `getCurrentConfiguration`) set a fetch timeout — a hung backend leaves the caller waiting indefinitely with no way to recover.
  evidence: Systemic, not unique to this story's new `getCurrentConfiguration()` — applies equally to the two functions Story 1.2 already shipped. Worth fixing once, consistently, across all three rather than patching one in isolation.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-view-current-configuration.md`
  summary: The new "Currently configured" fetch-on-open and refresh-after-apply logic in `SettingsDrawer.tsx` has no automated test coverage.
  evidence: Same root cause as the already-logged Story 1.2 "Reject row" gap — no frontend component-test framework exists yet in this project, deliberately deferred to `bmad-testarch-automate` running after Epic 1 completes.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-view-current-configuration.md`
  summary: `_grant_text()`'s fallback silently degrades any permission-grant entry shaped differently than expected to the generic string `"Permission grant"`, with no logging to notice when real Story 1.4 data starts falling into that bucket unexpectedly.
  evidence: `backend/brain/settings_router/summary.py`; adding logging now would be inventing infrastructure — no logging convention exists anywhere else in this backend yet. Revisit alongside Story 1.4, once real grant data exists to actually fall into this fallback.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-3-view-current-configuration.md`
  summary: Pre-existing bug (not part of this story's diff, confirmed out of scope by the reviewer that found it): `_read_claude_dir_context()` in `backend/brain/settings_router/router.py` (Story 1.2, used by `/api/settings/propose`) walks `.claude/` via `claude_dir.rglob("*")`, which silently swallows `PermissionError` while scanning a directory — the exact same class of bug this story's review found and fixed in `summary.py` (there, fixed by switching to `iterdir()`). A permission-denied subdirectory under `.claude/` would be silently omitted from the LLM's classification context instead of surfacing an error.
  evidence: Verified directly: `Path.rglob("*")` over a `chmod 000` subdirectory returns without raising, simply omitting its contents. Worth fixing the same way (`iterdir()`-based traversal) when `router.py` is next touched.

- source_spec: none
  summary: Not adopting `bmad-loop` (the autonomous multi-session dev/review orchestrator) for now — staying with the interactive `bmad-build` flow used for Stories 1.1–1.3.
  evidence: Investigated what setup would actually involve: a separate `uv tool install` from GitHub, `bmad-loop init`/`validate`, and a hard prerequisite this project doesn't have yet (`sprint-status.yaml`, which needs `bmad-sprint-planning` to have run). More importantly, spawned dev/review sessions run under a "never-ask" automation rule — the kind of live judgment calls made interactively this session (model choice, permission-grant schema handling, etc.) would either need to be pre-decided in the spec/policy or would trigger a CRITICAL escalation pausing the whole run for a separate `/bmad-loop-resolve` session. The human explicitly declined the tradeoff (less steering per story in exchange for unattended throughput) after this was explained. Revisit once specs/policy are stable enough that escalations would be rare, or if throughput becomes the binding constraint instead of judgment calls.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-permission-manager.md`
  summary: `grants.py`'s read-modify-write of `settings.local.json` (`add_grant`/`revoke_grant`) has no file locking or atomic write (temp-file-plus-rename) — two concurrent writers (or a race with Claude Code itself writing the file) can clobber each other's changes.
  evidence: Confirmed by review: `_write_settings_local()` does a plain `write_text()` after a plain `read_text()`, no lock acquired in between. Matches the existing pattern in `apply.py`'s `apply_action()` (also no locking), so this isn't a regression specific to this story, and the app is designed for a single local user — but worth a real fix (e.g. `filelock`) if concurrent access ever becomes plausible.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-permission-manager.md`
  summary: Grant deduplication in `add_grant()` compares `target` via raw string equality after only trimming whitespace — no path normalization, so `src/a.json` and `./src/a.json` (or different path separators) are treated as distinct grants for the same real resource.
  evidence: `backend/brain/settings_router/grants.py`'s `add_grant()` loop: `existing.target == trimmed`. Targets are documented as opaque identifiers (Design Notes) so this may be intentional, but it means a user can end up with duplicate-looking grants that "mean" the same file if they type the path differently each time.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-permission-manager.md`
  summary: `_parse_grants()` silently drops any `permissionGrants` entry that fails to validate against the real `PermissionGrant` schema, and the next `add_grant`/`revoke_grant` call re-serializes only the surviving entries — so a legacy/hand-authored freeform grant (the kind Story 1.3's summary reader still displays via its text/description/name fallback) is permanently deleted the next time the new UI adds or revokes anything.
  evidence: `backend/brain/settings_router/grants.py`: `_parse_grants()` skips non-conforming dicts via `try/except ValueError: continue`, and both `add_grant`/`revoke_grant` write back `[g.model_dump() for g in grants]` — only ever the parsed survivors. Confirmed by reading the code path; not reproduced against real data since no legacy freeform grants exist in this repo today.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-permission-manager.md`
  summary: `revoke_grant()` treats an unknown or already-revoked id as an error (404), while `add_grant()` for the same kind+target is explicitly idempotent (200, no error) — a client that retries a `DELETE` after a dropped response (the first request actually succeeded server-side) gets an unexpected 404 instead of a no-op success.
  evidence: `backend/brain/settings_router/grants.py`: `revoke_grant()` raises `PermissionGrantNotFoundError` whenever the id isn't found, with no distinction between "never existed" and "already revoked by a previous, unacknowledged call." Surfaced by review; no test exercises the retry-after-timeout scenario specifically. Worth a deliberate decision (make revoke idempotent too, or document the asymmetry) rather than inheriting it by default.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-permission-manager.md`
  summary: `PermissionGrant.target` (the Pydantic model used on the *read* path, via `model_validate` in `_parse_grants()`) has no length or emptiness constraint, unlike `add_grant()`'s own trim/length validation on the *write* path — a hand-edited `settings.local.json` with an empty-string or oversized target would be parsed and returned as-is by `list_grants()`/`GET`.
  evidence: `backend/brain/settings_router/models.py`: `PermissionGrant.target: str = Field(description=...)` carries no `min_length`/`max_length`. `add_grant()`'s own checks (`grants.py`) only run on the write path, so they don't protect reads of externally-edited data.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-permission-manager.md`
  summary: No upper bound exists on how many grants a single `settings.local.json` can accumulate — `add_grant()` has no total-count cap.
  evidence: Surfaced by review; low real risk for a single-local-user tool, but nothing currently prevents unbounded growth of the `permissionGrants` list from a buggy or looping client.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-permission-manager.md`
  summary: The new Permission Manager frontend (`PermissionManagerDrawer.tsx`, `PermissionGrantRow.tsx`, `permission-grants-api.ts`) ships with zero automated tests, same as `SettingsDrawer.tsx` before it.
  evidence: Confirmed via the verification-gap reviewer: no test runner, config, or `*.test.*`/`*.spec.*` file exists anywhere under `frontend/` (matches the pre-existing gap already logged against Story 1.2's Reject-button row). Not a regression this story introduced, but this story doubles the untested UI surface area — worth prioritizing once `bmad-testarch-automate` runs after Epic 1, per the existing plan.

- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-permission-manager.md`
  summary: Architectural clarification for whoever builds `backend/engine/` (not yet built — empty stub): Story 1.4's `permissionGrants` records are inert as far as Claude Code's own permission engine is concerned, and that's correct, not a gap to close later by "integrating" with it — this app's agents are not literal `claude` CLI subprocesses.
  evidence: Investigated after the human asked whether grants should also be written into Claude Code's real, documented `permissions.allow`/`ask`/`deny` (`Read(pattern)`/`Edit(pattern)`/`Bash(pattern)`) and `allowedMcpServers`/`enabledMcpjsonServers` keys — confirmed those genuinely array-merge across `settings.json`/`settings.local.json` per Claude Code's own docs (code.claude.com/docs/en/settings, /permissions, /mcp). But a second investigation of this project's own docs/code found: the only implemented execution code (`backend/brain/settings_router/router.py`) calls the raw Anthropic SDK directly (`anthropic.Anthropic()`, `.messages.parse()`), no `claude-agent-sdk` dependency exists anywhere in `pyproject.toml`, and the planned main agent loop (`backend/engine/`, currently an empty stub) is described in the architecture docs as an "Anthropic token stream" orchestrated by LangGraph — never as a spawned `claude` CLI process. "Spawned FastMCP processes" (AD-6) are the MCP tool-*servers* an agent calls out to, not the agent-loop process itself. ARCHITECTURE-SPINE.md AD-6 states directly: "The Permission Manager's approve/revoke flow (FR-4/5/6) is the entire v1 trust boundary" — i.e. this app's own backend (the not-yet-built Engine) is expected to check grants itself before letting an agent touch a resource; delegating to Claude Code's settings.json permission system is a non-sequitur here since Claude Code's own engine never runs these agents. Whoever builds the Engine's tool-execution/permission-check layer should read `grants.py`'s `permissionGrants` records directly (or whatever schema they evolve into) rather than looking for a Claude-Code-native enforcement path that doesn't apply to this app's architecture.
