import { mergeTests } from '@playwright/test';
import { log } from '@seontechnologies/playwright-utils';
import { test as apiRequestFixture } from '@seontechnologies/playwright-utils/api-request/fixtures';
import { test as recurseFixture } from '@seontechnologies/playwright-utils/recurse/fixtures';
// Browser-only utilities — this project is fullstack (frontend + backend).
import { test as interceptFixture } from '@seontechnologies/playwright-utils/intercept-network-call/fixtures';
import { test as networkErrorFixture } from '@seontechnologies/playwright-utils/network-error-monitor/fixtures';

// NOT merged yet: './auth-fixture' (createAuthFixtures()). Verified by running
// the suite — createAuthFixtures() overrides Playwright's base `context`
// (and therefore `page`) fixture and unconditionally calls
// authProvider.manageAuthToken() for every test that touches `page`/`context`,
// regardless of whether that test needs auth (see
// @seontechnologies/playwright-utils's auth-session/fixtures.ts `context`
// fixture). With no real auth endpoint yet, manageAuthToken() only throws
// (see ./auth-provider.ts), so merging it here would fail every UI test
// unconditionally, not just ones that use `authToken`. auth-fixture.ts and
// auth-provider.ts are fully scaffolded and ready — merge authFixture back in
// here once a real auth endpoint exists and auth-provider.ts's TODOs are
// resolved.
export const test = mergeTests(apiRequestFixture, recurseFixture, interceptFixture, networkErrorFixture);

export { expect } from '@playwright/test';
export { log };
