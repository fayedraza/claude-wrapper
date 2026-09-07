// No-op placeholder. Two things kept this from doing anything useful yet:
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
async function globalSetup() {}

export default globalSetup;
