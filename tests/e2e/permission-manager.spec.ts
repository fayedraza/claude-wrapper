import { randomUUID } from 'node:crypto';
import { test, expect, log } from '../support/merged-fixtures';

// Story 1.4 (FR-6 + the standing half of FR-5): view, add, move, and revoke
// permission grants across both local (.claude/settings.local.json) and team
// (.claude/settings.json) scope. All real -- no network stubbing here, every
// call is a genuine round trip to the real backend.
//
// Row scoping: locate a specific grant row via the unique target text's own
// immediate parent (`xpath=..`), not `page.locator('div', { has: ... })`.
// The latter also matches the outer "Granted" list container -- every row's
// target text is technically a descendant of it too -- and `.first()`
// resolves to that outer container in document order, not the specific row.
// Confirmed by running it: with more than one grant present (state
// accumulates across this whole file, one shared backend), that container
// scope made `getByRole('button', { name: 'Revoke' })` match every
// accumulated row's button, not just this test's own.
test.describe('Permission Manager', () => {
  test('[P0] adding a local grant shows it here and in Settings’ summary', async ({ page }) => {
    const target = `e2e-add-local-${randomUUID().slice(0, 8)}.json`;

    await log.step('Add a personal grant via the Permission Manager');
    await page.goto('/');
    await page.getByRole('button', { name: 'Permissions' }).click();
    await page.getByRole('textbox', { name: 'Grant target' }).fill(target);
    // "Personal (not shared)" is already the default scope.
    await page.getByRole('button', { name: 'Add grant' }).click();

    const targetSpan = page.getByText(target, { exact: true });
    await expect(targetSpan).toBeVisible();
    const row = targetSpan.locator('xpath=..');
    await expect(row.getByText('Local', { exact: true })).toBeVisible();

    await log.step('Confirm the same grant appears in Settings’ "Currently configured"');
    await page.getByRole('button', { name: 'Close permissions' }).first().click();
    await page.getByRole('button', { name: 'Settings' }).click();
    const summarySpan = page.getByText(target, { exact: true });
    await expect(summarySpan).toBeVisible();
    // Other local-scoped grants accumulate across this shared-backend test
    // file, so a bare path-text query would also match their rows.
    await expect(summarySpan.locator('xpath=..').getByText('.claude/settings.local.json')).toBeVisible();
  });

  test('[P0] adding a team grant renders a distinct "Team" banner', async ({ page }) => {
    const target = `e2e-add-team-${randomUUID().slice(0, 8)}.json`;

    await page.goto('/');
    await page.getByRole('button', { name: 'Permissions' }).click();
    await page.getByRole('textbox', { name: 'Grant target' }).fill(target);
    await page.getByRole('combobox', { name: 'Save to' }).selectOption('team');
    await page.getByRole('button', { name: 'Add grant' }).click();

    const targetSpan = page.getByText(target, { exact: true });
    await expect(targetSpan).toBeVisible();
    const row = targetSpan.locator('xpath=..');
    await expect(row.getByText('Team', { exact: true })).toBeVisible();

    await log.step('Confirm it shows under settings.json, not settings.local.json');
    await page.getByRole('button', { name: 'Close permissions' }).first().click();
    await page.getByRole('button', { name: 'Settings' }).click();
    const summarySpan = page.getByText(target, { exact: true });
    await expect(summarySpan).toBeVisible();
    await expect(summarySpan.locator('xpath=..').getByText('.claude/settings.json', { exact: true })).toBeVisible();
  });

  test('[P1] moving a grant to Team relocates it, same identity', async ({ page }) => {
    const target = `e2e-move-${randomUUID().slice(0, 8)}.json`;

    await page.goto('/');
    await page.getByRole('button', { name: 'Permissions' }).click();
    await page.getByRole('textbox', { name: 'Grant target' }).fill(target);
    await page.getByRole('button', { name: 'Add grant' }).click();

    const targetSpan = page.getByText(target, { exact: true });
    await expect(targetSpan).toBeVisible();
    const row = targetSpan.locator('xpath=..');
    await row.getByRole('button', { name: 'Move to Team' }).click();

    // Same row, now banner reads Team and the action flips to move back.
    await expect(row.getByText('Team', { exact: true })).toBeVisible();
    await expect(row.getByRole('button', { name: 'Move to Local' })).toBeVisible();
  });

  test('[P0] revoking a grant removes it from the list', async ({ page }) => {
    const target = `e2e-revoke-${randomUUID().slice(0, 8)}.json`;

    await page.goto('/');
    await page.getByRole('button', { name: 'Permissions' }).click();
    await page.getByRole('textbox', { name: 'Grant target' }).fill(target);
    await page.getByRole('button', { name: 'Add grant' }).click();

    const targetSpan = page.getByText(target, { exact: true });
    await expect(targetSpan).toBeVisible();
    await targetSpan.locator('xpath=..').getByRole('button', { name: 'Revoke' }).click();

    await expect(page.getByText(target, { exact: true })).not.toBeVisible();
  });

  test(
    '[P2] revoking an already-revoked grant (stale second tab) shows an error and re-syncs',
    { annotation: [{ type: 'skipNetworkMonitoring' }] },
    async ({ page, context }) => {
      const target = `e2e-stale-revoke-${randomUUID().slice(0, 8)}.json`;

      await log.step('Add a grant, visible in two tabs');
      await page.goto('/');
      await page.getByRole('button', { name: 'Permissions' }).click();
      await page.getByRole('textbox', { name: 'Grant target' }).fill(target);
      await page.getByRole('button', { name: 'Add grant' }).click();
      await expect(page.getByText(target, { exact: true })).toBeVisible();

      const page2 = await context.newPage();
      await page2.goto('/');
      await page2.getByRole('button', { name: 'Permissions' }).click();
      await expect(page2.getByText(target, { exact: true })).toBeVisible();

      await log.step('Tab 1 revokes it for real');
      await page.getByText(target, { exact: true }).locator('xpath=..').getByRole('button', { name: 'Revoke' }).click();
      await expect(page.getByText(target, { exact: true })).not.toBeVisible();

      await log.step('Tab 2, unaware, tries to revoke its own stale row');
      await page2.getByText(target, { exact: true }).locator('xpath=..').getByRole('button', { name: 'Revoke' }).click();

      // I/O matrix: error shown, list re-fetches -- the stale row disappears
      // once tab 2 learns the true (already-revoked) state. Scoped to the
      // open dialog: Next.js's own route announcer is also role="alert"
      // (empty, page-wide, framework-injected), so an unscoped query is
      // ambiguous under strict mode.
      await expect(page2.getByRole('dialog').getByRole('alert')).toBeVisible();
      await expect(page2.getByText(target, { exact: true })).not.toBeVisible();

      await page2.close();
    },
  );
});

// Not covered here, and deliberately so, both confirmed by actually running
// the attempt rather than assumed:
//
// - Add-grant client-side validation (empty/whitespace target). The Add
//   button stays disabled whenever `target.trim()` is empty
//   (PermissionManagerDrawer.tsx), so the backend's 400 rejection is
//   genuinely unreachable through real UI interaction -- it's already
//   covered at the right level by
//   backend/tests/brain/settings_router/test_grants.py, which calls the
//   validation path directly. Forcing it here would mean bypassing the DOM
//   the way no real user can, which is exactly what the Duplicate Coverage
//   Guard (test-levels-framework.md) says not to do.
//
// - "Opening Permissions closes Settings" as a *click-driven* scenario.
//   Attempted and dropped: each drawer renders `fixed inset-0 z-50`
//   (frontend/app/page.tsx), a full-screen backdrop with no counterpart
//   z-index on the header, so while either drawer is open its own backdrop
//   physically covers the *other* drawer's header trigger and blocks the
//   click before React ever runs (confirmed by a real timeout: "subtree
//   intercepts pointer events"). The mutual-exclusion state logic added
//   during Story 1.4's review (opening one drawer sets the other's state to
//   closed) is real and harmless, but it has no click-reachable path to
//   exercise in the first place -- a user must close the open drawer
//   (Escape, backdrop click, or the × button) before the other trigger
//   becomes clickable at all, at which point there is nothing left to be
//   "mutually exclusive" with. Worth knowing, not worth a fabricated test.
