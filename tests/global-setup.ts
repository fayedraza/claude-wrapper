// Auth wiring is still a no-op here. Two things kept it from doing anything
// useful yet:
//
// 1. auth-fixture.ts's authFixture is not merged into merged-fixtures.ts (see
//    that file's comment) because createAuthFixtures() overrides Playwright's
//    base `context`/`page` fixtures and unconditionally calls
//    authProvider.manageAuthToken() for every test, which throws until a real
//    auth endpoint exists.
// 2. Verified by running it: @seontechnologies/playwright-utils@4.4.0's own
//    configureAuthSession() ignores the `authStoragePath` option when
//    creating the storage directory — it recomputes the path via its
//    internal getStorageDir() with no arguments, so it wrote to a stray
//    `.auth/` at the repo root instead of the configured tests/.auth-sessions/.
//    This is an upstream bug, not a wiring mistake on our side.
//
// Wire authStorageInit() + configureAuthSession() + setAuthProvider() back in
// here once a real auth endpoint exists (see tests/support/auth-provider.ts)
// and re-verify the storage path lands where configured before trusting it.
//
// Epic 1 E2E setup added the one thing this file does today: clear the
// isolated E2E .claude/ directory (see e2e-claude-dir.ts) once per full run,
// so permission grants/rules left behind by a previous local
// `npm run test:e2e` invocation never leak into the next one. Order relative
// to webServer startup doesn't matter -- the backend never caches `.claude/`
// state (a hard invariant across all of Epic 1), so it picks up the newly-
// empty directory on its very next request regardless of whether this ran
// before or after the server came up.
import { rm } from 'node:fs/promises';
import { E2E_CLAUDE_DIR } from './support/e2e-claude-dir';

async function globalSetup() {
  await rm(E2E_CLAUDE_DIR, { recursive: true, force: true });
}

export default globalSetup;
