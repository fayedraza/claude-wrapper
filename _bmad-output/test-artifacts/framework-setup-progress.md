---
stepsCompleted: ['step-01-preflight', 'step-02-select-framework', 'step-03-scaffold-framework', 'step-04-docs-and-scripts', 'step-05-validate-and-summary']
lastStep: 'step-05-validate-and-summary'
lastSaved: '2026-09-07'
---

## Step 1: Preflight Checks

**Detected stack:** `fullstack`

- Frontend: Next.js 16.3.4 app (`frontend/`) — React 19.2.8, TypeScript, Tailwind CSS v4, Turbopack, ESLint 9. No E2E framework installed yet.
- Backend: FastAPI 0.141.x app (`backend/`) — uv-managed, Python >=3.12, pinned deps (fastapi 0.141.1, starlette>=1.0.1, langgraph 1.2.11, fastmcp>=3.4.5,<3.5.0, pydantic 2.13.5, redis 8.1.0, uvicorn[standard]>=0.34.0). No test framework config present (no conftest.py, no existing pytest suite).
- No mobile indicators found.

**Prerequisites:** pass — no conflicting E2E/test framework config found for either stack.

**Context docs found:** `_bmad-output/planning-artifacts/architecture/architecture-claude-wrapper-2026-08-30/` (Architecture spine).

## Step 2: Framework Selection

**Selected:** Playwright (frontend/E2E + component) + pytest (backend).

- **Playwright** — chosen over Cypress: heavy API+UI integration expected (live WebSocket/SSE telemetry, DAG canvas, streaming agent reasoning per the UX design), and CI parallelism/speed matters as coverage accumulates across 5 epics.
- **pytest** — Python/FastAPI backend, pytest is the language default.
- `config.test_framework` was `auto`; no override applied.

## Step 3: Scaffold Framework

**Contract testing (Pact) relevance gate:** did not open. Frontend calls only its own backend, same repo, same deploy — no consumer-provider boundary per `pactjs-utils-mandate.md`. No Pact artifacts scaffolded.

**Execution mode:** sequential (direct execution, not subagent/agent-team) — chosen for exactness given the volume of precisely-specified file shapes.

**playwright-utils:** installed at user's confirmation (`@seontechnologies/playwright-utils@4.4.0`, `@playwright/test@1.63.0`, both pinned exact per project convention). `dotenv@17.4.2` also added directly — required at runtime by playwright-utils's `auth-session` module but only declared as *its own* devDependency upstream, so it never installs transitively (verified: `npm install` alone threw `Cannot find module 'dotenv'` until added directly).

**Structure created:**

- Root `package.json` (new) — dedicated to the Playwright suite, kept separate from `frontend/package.json` so test tooling never ships in the app bundle. `.nvmrc` (Node 24, current LTS per the fragment's own guidance), `.env.example` (`TEST_ENV`, `BASE_URL`, `API_URL`).
- `tests/playwright.config.ts` — timeouts (action 15s/nav 30s/test 60s), `trace: 'retain-on-failure'` (closest real Playwright API value; "retain-on-failure-and-retries" isn't a literal trace mode), screenshot only-on-failure, video retain-on-failure, HTML+JUnit+list reporters, CI-tuned parallelism, `webServer` array auto-starting both the frontend dev server and the backend uvicorn server so `npm run test:e2e` is a single command locally.
- `tests/e2e/` — `health-api.spec.ts` (API sample, backend `/health`), `home-page.spec.ts` (UI sample, the default Next.js scaffold page — selectors read from the actual `frontend/app/page.tsx`, not guessed).
- `tests/support/merged-fixtures.ts` — `apiRequest`, `recurse`, `interceptNetworkCall`, `network-error-monitor` merged. `authFixture` deliberately **not** merged (see Deviations below).
- `tests/support/auth-provider.ts` + `auth-fixture.ts` — fully scaffolded per the mandate's six-member `AuthProvider` contract, with `manageAuthToken` and cookie names marked `TODO` (no auth endpoint exists yet).
- `tests/support/{fixtures,helpers,factories}/README.md` — placeholders explaining why each is empty (no domain models yet); `page-objects/` skipped entirely (optional, nothing to model).
- `backend/tests/` — `conftest.py` (TestClient fixture), `api/test_health.py` (sample), `unit/README.md`, `integration/README.md` placeholders. `pyproject.toml` gained `[tool.pytest.ini_options]` and a `pytest`/`httpx` dev dependency group via `uv add --dev`.

**Verification (actually run, not assumed):**

- `uv run pytest -v` (backend) — 1 passed.
- `npm run test:e2e` (root) — 2 passed, after fixing two real defects surfaced by running it (see Deviations).
- `npm run build` (frontend) — still succeeds after the `turbopack.root` fix.

**Deviations / real defects found by running the scaffold (not by inspection):**

1. **`dotenv` missing at install time** — `@seontechnologies/playwright-utils`'s `auth-session` module requires `dotenv` at runtime but only lists it as its own devDependency upstream. Fixed by adding `dotenv` directly to the root `package.json`.
2. **`createAuthFixtures()` breaks every test unconditionally without a real auth backend** — its `context` fixture (which `page` depends on) unconditionally calls `authProvider.manageAuthToken()` for *every* test that touches `page`/`context`, not just ones using `authToken`. Confirmed by running the suite: both sample tests failed with the provider's TODO error. Fixed by not merging `authFixture` into `merged-fixtures.ts` yet — `auth-fixture.ts`/`auth-provider.ts` remain fully scaffolded and documented for when a real auth endpoint exists.
3. **`configureAuthSession()`'s `authStoragePath` option is ignored** — verified the installed package (`4.4.0`) recomputes its storage directory via an internal no-argument call, so it wrote to a stray `.auth/` at the repo root instead of the configured `tests/.auth-sessions/`. Since the auth fixture isn't wired in yet anyway, `tests/global-setup.ts` was simplified to a documented no-op rather than carrying a call known not to do what it says.
4. **Two transitive vulnerabilities** in `@seontechnologies/playwright-utils`'s own dependencies (`adm-zip` — high, no fix available; `uuid` — moderate, via `exceljs`), both from its unused `file-utils` capability. `npm audit fix` could not resolve them (no compatible version published upstream). Logged to `deferred-work.md` rather than blocking — dev-only exposure, not shipped to production.
5. **Data factories skipped** — no domain models exist yet (Story 1.1 ships only `/health` and the default page); `data-factories.md`/`confidence-gate.md` both say a factory guessing field validity rules is fabrication, not scaffolding. `@faker-js/faker` intentionally not installed. Documented in `tests/support/factories/README.md`.

## Step 4: Documentation & Scripts

- `tests/README.md` written (setup, running tests, architecture, best practices, CI notes, knowledge-base references).
- `package.json` scripts: `test:e2e`, `test:e2e:ui`, `test:e2e:report` (already present from step 3).
- Backend: `backend/Makefile` (`test`, `test-cov`, `test-integration`) — all three run for real; `test-integration` currently exits 5 (pytest's "no tests collected" code) since no test is marked `@pytest.mark.integration` yet, which is correct, not a bug. Added `pytest-cov` dev dependency and registered the `integration` marker in `pyproject.toml`.
- **Write-time enforcement hook installed** (Claude Code supports tool hooks): `.claude/hooks/tea-enforce.cjs` copied byte-for-byte from the skill resource (diff-verified identical), `.tea/enforce-config.json` written with `testGlobs` scoped to actual paths (`tests/**/*.spec.{ts,js}` for Playwright, `backend/tests/**/test_*.py` + `backend/**/*_test.py` for pytest — not the generic table example, since pytest lives under `backend/` here while `tests/` at repo root is the Playwright suite), `pactConfigGlobs`/`excludeGlobs` empty (no Pact, no k6), `hookSha256` set from `shasum -a 256`. `.claude/settings.json` created (didn't previously exist) registering `PreToolUse`/`PostToolUse`/`Stop`. **Functionally verified, not just installed**: piped a synthetic `Write` payload containing `test.only(...)` and `page.waitForTimeout(...)` through `--pre` and confirmed it blocked with exit code 2 and the expected criteria-registry citations (C2, H1); confirmed it exits 0 (fails open) on a malformed/empty payload.

## Step 5: Validate & Summarize

**Checked against `checklist.md`; fixed two real gaps it surfaced:**

- Added Given/When/Then comments to both Playwright samples (backend's pytest sample already had them — now consistent).
- Added a Troubleshooting section to `tests/README.md` (was missing).

**Verified rather than assumed, beyond what step 3/4 already covered:**

- Deliberately ran a failing test and confirmed screenshot, video, and trace all actually get captured on failure (then deleted the smoke test and its artifacts).

**Checklist items deliberately not satisfied, with reasons (not oversights):**

- *No data factory created* — no domain models exist yet in this project (Story 1.1 ships only `/health` and the default page). `data-factories.md` and `confidence-gate.md` both treat a factory that guesses field validity rules as fabrication, not scaffolding. Documented in `tests/support/factories/README.md`.
- *`authStorageInit()`/`configureAuthSession()` not wired into `global-setup.ts`* — verified this package version's `configureAuthSession()` ignores the custom storage path (wrote to a stray `.auth/` at repo root instead of the configured path). Re-verify before wiring back in.
- *`authFixture` not merged into `merged-fixtures.ts`* — verified it breaks every UI test unconditionally without a real auth provider (see Step 3 Deviations #2).
- *No `interceptNetworkCall` in the UI sample* — the actual scaffolded page (`frontend/app/page.tsx`, read directly, not guessed) makes zero API calls, so there's nothing to intercept.
- *TODOs left in `auth-provider.ts`* — the generic checklist's "no TODO/FIXME" rule is superseded here by step-03's own explicit instruction to leave `manageAuthToken` and cookie names as marked TODOs when the auth endpoint is unknown, and report them (done, here and in the completion summary).
- *`tests/support/fixtures/index.ts` and `tests/support/fixtures/factories/` (checklist's generic layout)* — superseded by `playwright-utils-mandate.md`'s explicit, more specific instruction that the fixture index lives at `{test_dir}/support/merged-fixtures.ts`. Followed the mandate over the generic checklist template.

**Completion criteria:** all satisfied except the deliberate, documented items above. Sample tests genuinely pass (`npm run test:e2e`, `uv run pytest` — both actually run, not assumed), documentation is complete and accurate to what was actually built, no unexplained placeholder text remains.
