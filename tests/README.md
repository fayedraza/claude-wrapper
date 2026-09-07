# Test suite

Playwright E2E/API tests for claude-wrapper (frontend + backend), plus a pointer to the backend's own pytest suite. This directory has its own `package.json` at the repo root, kept separate from `frontend/package.json` so test tooling never ships in the app bundle.

## Setup

```bash
# from the repo root
nvm use          # Node 24 (.nvmrc)
npm install
npx playwright install --with-deps chromium
```

Copy `.env.example` to `.env` if you need non-default values (`TEST_ENV`, `BASE_URL`, `API_URL`).

## Running tests

```bash
npm run test:e2e          # headless, auto-starts frontend (npm run dev) + backend (uvicorn) if not already running
npm run test:e2e:ui       # Playwright's interactive UI mode
npm run test:e2e:report   # open the last HTML report
```

Debug a single test: `npx playwright test -c tests/playwright.config.ts tests/e2e/health-api.spec.ts --debug`

Backend pytest suite (separate, standard Python layout — `cd backend` first):

```bash
make test              # uv run pytest
make test-cov          # with coverage report
make test-integration  # tests marked @pytest.mark.integration only
```

## Architecture

- `playwright.config.ts` — timeouts, reporters (HTML/JUnit/list), trace/screenshot/video-on-failure, `webServer` array that boots both dev servers locally.
- `global-setup.ts` — currently a documented no-op; see its comment for why (auth isn't wired up yet — no auth endpoint exists in this project).
- `support/merged-fixtures.ts` — the **only** place tests import `test`/`expect`/`log` from. Currently merges `apiRequest`, `recurse`, `interceptNetworkCall`, and `network-error-monitor` (auto-fails a test on any unhandled 4xx/5xx).
- `support/auth-provider.ts` + `auth-fixture.ts` — scaffolded and ready, **not yet merged** into `merged-fixtures.ts`. Wire them in once a real auth endpoint exists (see the TODOs in `auth-provider.ts`).
- `support/{fixtures,helpers,factories}/` — empty on purpose; each has a `README.md` explaining what belongs there once stories introduce real features/domain models to fixture, helper, or factory. Don't invent a factory for a shape that doesn't exist yet — see `confidence-gate.md` in the knowledge base.
- `e2e/` — one spec per concern. `health-api.spec.ts` is the API-sample reference (no browser); `home-page.spec.ts` is the UI-sample reference. Both import from `../support/merged-fixtures`, never `@playwright/test` directly.

## Best practices (enforced, not just documented)

A write-time hook (`.claude/hooks/tea-enforce.cjs`, registered in `.claude/settings.json`) blocks common test anti-patterns as you write them — `.only`/`.skip` left in, `page.waitForTimeout` as a sync mechanism, `page.route`/`request.<method>` where `apiRequest`/`interceptNetworkCall` apply, `console.log` in a spec, and more. Its rule table comes from the TEA `test-review` criteria registry (severity lives there, not in the hook). To turn a rule off deliberately, add it to `disabledRules` in `.tea/enforce-config.json` and explain why in the commit — never edit the hook script itself (it's a byte-for-byte copy the project doesn't own; `hookSha256` in that same config lets `--stop` warn if it drifts).

Beyond what the hook catches:

- **Selectors**: `data-testid` > ARIA role > text > CSS, in that order (`selector-resilience.md`).
- **Setup**: seed state via API/factories, never by driving the UI (`data-factories.md`).
- **Isolation**: no shared mutable state between tests; each test creates what it needs.
- **Network-first**: `interceptNetworkCall` is declared *before* `page.goto`, never after.

## CI integration

Not yet wired into a CI workflow — that's `bmad-testarch-ci`'s job, not this one. `playwright.config.ts` is already CI-aware (`forbidOnly`, retries, worker count keyed off `process.env.CI`), and the `webServer` array's `reuseExistingServer: !process.env.CI` means CI should start both dev servers explicitly in the workflow rather than relying on this config to do it.

## Troubleshooting

- **`Cannot find module 'dotenv'`** — `@seontechnologies/playwright-utils`'s `auth-session` module needs `dotenv` at runtime but only declares it as its own devDependency upstream. It's already added directly to the root `package.json`; if this recurs after a lockfile reset, re-add it.
- **A UI test fails immediately with an `auth-provider.ts` TODO error** — you (or a merge) added `authFixture` back into `merged-fixtures.ts`. Don't, until `auth-provider.ts`'s `manageAuthToken` TODO is resolved — see that file's header comment for why.
- **`npm run test:e2e` hangs waiting for a server** — the `webServer` array expects `frontend/` (`npm run dev`) and `backend/` (`uv run uvicorn gateway.main:app --port 8000`) to be startable from a clean checkout. Confirm both work standalone first.
- **Sample UI test fails on title/heading** — `home-page.spec.ts` asserts against the *stock* `create-next-app` scaffold. The moment `frontend/app/page.tsx` changes, update or replace this sample — it's a reference shape, not permanent coverage.
- **`make test-integration` exits with code 5** — that's pytest's "no tests collected" code, not a failure. No test is marked `@pytest.mark.integration` yet; correct until one exists.

## Knowledge base

The full TEA fragment set this scaffold was built from lives at `.claude/skills/bmad-testarch-framework/resources/knowledge/` — `playwright-utils-mandate.md`, `overview.md`, `fixtures-composition.md`, `auth-session.md`, `api-request.md`, `recurse.md`, `log.md`, `intercept-network-call.md`, `network-error-monitor.md`, `data-factories.md`, `confidence-gate.md`, `selector-resilience.md` among them.
