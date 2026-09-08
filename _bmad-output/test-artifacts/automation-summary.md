---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-identify-targets']
lastStep: 'step-02-identify-targets'
lastSaved: '2026-09-08'
inputDocuments:
  - '_bmad-output/implementation-artifacts/spec-1-2-submit-settings-request-and-approve.md'
  - '_bmad-output/implementation-artifacts/spec-1-3-view-current-configuration.md'
  - '_bmad-output/implementation-artifacts/spec-1-4-permission-manager.md'
  - '.claude/skills/bmad-testarch-automate/resources/knowledge/test-levels-framework.md'
  - '.claude/skills/bmad-testarch-automate/resources/knowledge/test-priorities-matrix.md'
  - '.claude/skills/bmad-testarch-automate/resources/knowledge/test-quality.md'
  - '.claude/skills/bmad-testarch-automate/resources/knowledge/library-integration-mandate.md'
  - '.claude/skills/bmad-testarch-automate/resources/knowledge/playwright-utils-mandate.md'
  - '.claude/skills/bmad-testarch-automate/resources/knowledge/network-error-monitor.md'
  - '.claude/skills/bmad-testarch-automate/resources/knowledge/intercept-network-call.md'
  - '.claude/skills/bmad-testarch-automate/resources/knowledge/api-request.md'
  - '.claude/skills/bmad-testarch-automate/resources/knowledge/data-factories.md'
  - '.claude/skills/bmad-testarch-automate/resources/knowledge/confidence-gate.md'
---

# Test Automation Summary — Epic 1 E2E Coverage

## Step 1: Preflight & Context

**Detected stack:** `fullstack` (frontend: Next.js/React + Playwright already configured; backend: FastAPI/pytest already configured).

**Mode:** BMad-Integrated — Stories 1.2/1.3/1.4 specs loaded as acceptance-criteria source.

**Framework verified:** `tests/playwright.config.ts` exists; `tests/support/merged-fixtures.ts` composes `apiRequestFixture`, `recurseFixture`, `interceptFixture`, `networkErrorFixture` via `mergeTests` (playwright-utils already adopted, not being introduced here). `tea_use_playwright_utils: true` and the package is a dependency — mandate binds.

**Config flags:** `tea_use_playwright_utils: true` (binds), `tea_use_pactjs_utils: true` but **not relevant** — single fullstack app, no separate provider service, no microservices/contract-testing indicators found; skipped per its own relevance gate ("use when contract tests are written", not "add contract tests to this project"). `tea_pact_mcp` likewise not invoked. `tea_browser_automation: auto` — MCP Playwright tools connected earlier in-session for manual verification; falls back to source/spec analysis for target identification (sufficient here: the agent authored every endpoint and component under test in this same session and has already manually verified every flow live).

**Genuine architectural gap found and fixed before writing any test**: `backend/gateway/main.py`'s `get_claude_dir()` was hardcoded to this repo's own real `.claude/` directory, with no override path for a live (non-`TestClient`) server process — confirmed by reproduction (a manual browser check wrote a real grant into the actual repo's `.claude/settings.local.json`; `.claude/settings.json` is git-tracked, not gitignored, so a "team"-scope grant or a Settings Router write would have corrupted real repo state on every E2E run). Fixed by adding `CLAUDE_WRAPPER_CLAUDE_DIR` env-var override (human-approved), covered by `backend/tests/api/test_claude_dir_config.py`. E2E `global-setup.ts` must launch the backend with this var pointed at an isolated temp directory.

## Step 2: Identify Targets & Coverage Plan

**Existing E2E coverage** (`tests/e2e/`): 2 scaffold samples only (`home-page.spec.ts` — shell loads, Settings opens; `health-api.spec.ts` — `/health` responds). Neither exercises a real Epic 1 feature flow. No ATDD outputs exist to avoid duplicating.

**Duplicate Coverage Guard applied**: backend pytest (140 tests) already covers every API contract, validation rule, and edge case at the integration level for all 4 stories. New E2E tests therefore focus exclusively on **user journeys through the UI** — they do not re-assert backend logic pytest already owns; browser tests get API-level assertions (status codes, body shape) only incidentally, as confirmation the real backend responded, not as their primary subject.

### Coverage Plan

| # | Target (user journey) | Level | Priority | Story | Network handling |
|---|---|---|---|---|---|
| 1 | Submit a natural-language request → review proposed change → approve → applied | E2E | P0 | 1.2 | `interceptNetworkCall` stubs `/api/settings/propose` only (real LLM call is costly + non-deterministic); `/api/settings/apply` and the resulting file write are real |
| 2 | Reject a proposed change (no write happens) | E2E | P1 | 1.2 | Real (no network call on reject, by design) |
| 3 | Settings propose fails (502) → error shown, drawer still usable | E2E | P1 | 1.2 | Stubbed 502 via `interceptNetworkCall`; opts out of `network-error-monitor` |
| 4 | View "Currently configured" showing a rule + agent + grant together | E2E | P0 | 1.3 | Real (seeds via real `add_grant`-backed API call, not UI, per data-factories "API for setup") |
| 5 | Add a personal (local) permission grant; appears in Permission Manager and Settings' summary | E2E | P0 | 1.4 | Real |
| 6 | Add a team-scoped grant; "Team" banner renders distinctly from "Local" | E2E | P0 | 1.4 | Real |
| 7 | Move a grant between scopes | E2E | P1 | 1.4 | Real |
| 8 | Revoke a grant | E2E | P0 | 1.4 | Real |
| 9 | Add-grant validation error (empty target) → error shown | E2E | P1 | 1.4 | Real; opts out of `network-error-monitor` (expects 400) |
| 10 | Revoke unknown id → error shown, list re-fetches | E2E | P2 | 1.4 | Real; opts out of `network-error-monitor` (expects 404) |
| 11 | Opening Permissions closes Settings and vice versa (mutual exclusion) | E2E | P1 | 1.4 | Real, no network assertions |

**Justification for scope**: critical-paths coverage, not comprehensive — one E2E test per primary happy path (P0) plus the highest-value error/edge paths already known to be real, reachable behavior (not speculative), matching this project's existing "1 backend regression = 1 test" discipline. Deferred to backend pytest (already covers, not duplicated here): scope-merge idempotency, malformed-JSON tolerance, chmod-based permission-failure propagation, grant-preservation-on-unrelated-write. `data-factories.md`'s guidance on unique/parallel-safe data applies to grant `target` strings (each test uses a distinct path/name, not shared literals, so parallel workers never collide on the same `.claude/` file within a shared temp dir per worker — see `global-setup.ts`).

**Pact/contract testing**: not applicable, not generated — no consumer/provider boundary exists in this architecture (confirmed during Step 1).

## Step 3: Generation

**Execution mode: `sequential`, deliberately, not the resolved `agent-team`/`subagent` default.** Given the small, well-scoped target list (11 planned scenarios, one dropped) and that the agent authored every endpoint and component under test in this same session, dispatching parallel subagents would mean re-deriving already-loaded context at real cost for no quality gain — contrary to this session's own guidance against over-spawning agents. Documented here as the explicit deviation the skill's sequential fallback anticipates.

**Worker A (API test generation) and Worker B-backend (backend test generation) deliberately skipped, not just "not run".** Both would duplicate coverage the existing 140-test pytest suite already owns at the correct level (Duplicate Coverage Guard, `test-levels-framework.md`) — new endpoints, validation rules, and edge cases for all 4 Epic 1 stories are already asserted there. Generating a second set of Playwright-level "API tests" for the same contracts would be pure duplication, not defense-in-depth.

**Worker B (E2E) — 11 planned scenarios, 10 written, 1 dropped after being genuinely attempted:**

| # | File | Test | Result |
|---|---|---|---|
| 1 | `settings-request.spec.ts` | Approve a proposed rule, writes to disk | ✅ |
| 2 | `settings-request.spec.ts` | Reject a proposed change | ✅ |
| 3 | `settings-request.spec.ts` | Propose fails (502), drawer stays usable | ✅ |
| 4 | `current-configuration.spec.ts` | Rule + agent + grant together | ✅ |
| 5 | `current-configuration.spec.ts` | Reflects an approve without reopening | ✅ |
| 6 | `permission-manager.spec.ts` | Add a local grant, seen in both surfaces | ✅ |
| 7 | `permission-manager.spec.ts` | Add a team grant, distinct banner | ✅ |
| 8 | `permission-manager.spec.ts` | Move a grant between scopes | ✅ |
| 9 | `permission-manager.spec.ts` | Revoke a grant | ✅ |
| 10 | `permission-manager.spec.ts` | Stale second-tab revoke (real 2-tab race) | ✅ |
| 11 | ~~"empty target validation"~~ | dropped | Not reachable — Add button stays disabled while `target.trim()` is empty; already covered by `test_grants.py` at the right level |
| 12 | ~~"opening Permissions closes Settings" (click-driven)~~ | dropped | Not reachable — each drawer is `fixed inset-0 z-50` with no counterpart z-index on the header, so the open drawer's own backdrop physically blocks clicking the other trigger; confirmed by a real timeout, not assumed |

**Playwright Utils mandate compliance**: every spec imports `test`/`expect`/`log` from `../support/merged-fixtures`, never `@playwright/test` directly. `interceptNetworkCall` stubs the one LLM-backed call (`/api/settings/propose`); every other call is real. Two tests carry `{ annotation: [{ type: 'skipNetworkMonitoring' }] }` for their one intentionally-erroring call each (never the whole file). No `page.waitForTimeout`, no `console.log`, no raw `request.*` on application endpoints — `apiRequest` used for direct-to-backend seeding in `current-configuration.spec.ts` (with an explicit `baseUrl`, since `apiRequest`'s default resolves to Playwright's own configured `use.baseURL`, the frontend on :3000, not the backend on :8000 — confirmed by a real failure before fixing it).

**Genuine architectural/test bugs found and fixed while writing these tests (not assumed, each reproduced):**
1. `get_claude_dir()` had no live-process override at all (see Step 1) — fixed with human sign-off before any test ran against a real server.
2. The override directory's *basename* must be exactly `.claude` — `apply.py`'s path validation checks `file_path` against `claude_dir.name`, and every `file_path` in this app is hardcoded to the literal `.claude/...` prefix. An override directory named anything else (tried first: `.e2e-claude-dir`) makes every `apply_action()` call fail with a 400. Reproduced via a real failing test before the fix.
3. `playwright.config.ts`'s backend `webServer` entry never passed the new env var through at all — without wiring it there (not just in `backend/gateway/main.py`), a real E2E run (local or CI) would still default to this repo's own `.claude/`. Confirmed the `env` option merges with, not replaces, the inherited environment (verified empirically: `uv`/PATH still resolved) before trusting it.
4. `getByText('Applied')` (non-exact) is a false-positive match against "Proposal ready — **not yet applied**" — `getByText` is case-insensitive substring matching by default. Two occurrences fixed.
5. Backend state accumulates across the whole spec file (one shared server process, no per-test reset) — several generic chip/text assertions (`'rule'`, `.claude/settings.local.json`, `Applied`) collided with earlier tests' own rows once more than one existed. Fixed by scoping to the specific element's own row/header via its unique target text's immediate parent, not a `div:has(text)` filter (which resolves to the *outer list container*, not the specific row, in document order).

**Verification**: all 12 real tests pass both sequentially (`--workers=1`) and under real parallel execution (6 workers, `fullyParallel: true`) — run twice, not assumed. Backend pytest (140 tests) and frontend build/lint re-verified clean afterward. Confirmed the real repo's own `.claude/settings.local.json` and `.claude/settings.json` were untouched by the entire exercise.

## Step 4+: aggregation/reporting handled directly in the final chat summary rather than the schema-driven `step-03c-aggregate.md` onward (that machinery assumes subagent JSON outputs this run deliberately didn't produce — see Step 3's execution-mode note).
