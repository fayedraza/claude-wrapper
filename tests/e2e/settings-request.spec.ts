import { randomUUID } from 'node:crypto';
import { test, expect, log } from '../support/merged-fixtures';

// Story 1.2 (FR-1/FR-2): submit a natural-language settings request, review
// the proposed change, then approve or reject it. The real LLM call
// (/api/settings/propose) is stubbed via interceptNetworkCall -- a live
// Anthropic call here would be costly, non-deterministic, and orthogonal to
// what this suite verifies (the frontend<->backend<->file-write path).
// /api/settings/apply and the resulting file write stay real.
test.describe('Settings: submit and approve a request', () => {
  test('[P0] approving a proposed rule writes it to disk', async ({ page, interceptNetworkCall }) => {
    const slug = `e2e-rule-${randomUUID().slice(0, 8)}`;
    const ruleContent = `Always use pytest for tests. (${slug})`;

    const proposeCall = interceptNetworkCall({
      url: '**/api/settings/propose',
      fulfillResponse: {
        status: 200,
        body: {
          user_summary: 'Adds a rule about always using pytest.',
          updates: [
            {
              target_category: 'rule',
              file_path: `.claude/rules/${slug}.md`,
              content: ruleContent,
              action: 'create',
            },
          ],
        },
      },
    });

    await log.step('Open Settings and submit a request');
    await page.goto('/');
    await page.getByRole('button', { name: 'Settings' }).click();
    await page.getByPlaceholder(/always use pytest/i).fill('always use pytest for tests');
    await page.getByRole('button', { name: 'Submit request' }).click();
    await proposeCall;

    await log.step('Review and approve the proposed card');
    // Backend state accumulates across the whole test file (one shared
    // server), so a bare chip-text query risks matching an earlier test's
    // row too. Scope to this card's own header (the file_path span's direct
    // parent) so the category/action chip checks stay unambiguous.
    const filePathSpan = page.getByText(`.claude/rules/${slug}.md`);
    await expect(filePathSpan).toBeVisible();
    const cardHeader = filePathSpan.locator('xpath=..');
    await expect(cardHeader.getByText('rule', { exact: true })).toBeVisible();
    await expect(cardHeader.getByText('create', { exact: true })).toBeVisible();

    await page.getByRole('button', { name: 'Approve & Apply' }).click();
    // getByText is case-insensitive substring matching by default, so a
    // non-exact 'Applied' also matches the "Proposal ready — not yet
    // applied" badge, which stays visible after approving too.
    await expect(page.getByText('Applied', { exact: true })).toBeVisible();

    await log.step('Confirm it now shows in "Currently configured"');
    // The applied card's own path span (`.claude/rules/${slug}.md`) stays on
    // screen too, so this matches both -- .last() targets the summary row,
    // which renders after the card list in DOM order.
    await expect(page.getByText(`.claude/rules/${slug}.md`).last()).toBeVisible();
  });

  test('[P1] rejecting a proposed change discards it without writing', async ({ page, interceptNetworkCall }) => {
    const slug = `e2e-rejected-${randomUUID().slice(0, 8)}`;

    const proposeCall = interceptNetworkCall({
      url: '**/api/settings/propose',
      fulfillResponse: {
        status: 200,
        body: {
          user_summary: 'Adds a rule.',
          updates: [
            {
              target_category: 'rule',
              file_path: `.claude/rules/${slug}.md`,
              content: 'Never gets written.',
              action: 'create',
            },
          ],
        },
      },
    });

    await page.goto('/');
    await page.getByRole('button', { name: 'Settings' }).click();
    await page.getByPlaceholder(/always use pytest/i).fill('a rule that will be rejected');
    await page.getByRole('button', { name: 'Submit request' }).click();
    await proposeCall;

    await expect(page.getByText(`.claude/rules/${slug}.md`)).toBeVisible();
    await page.getByRole('button', { name: 'Reject' }).click();

    // FR-2: rejecting makes no network call and writes nothing -- the card
    // just disappears, and the rejected rule never shows up as configured.
    await expect(page.getByText(`.claude/rules/${slug}.md`)).not.toBeVisible();
    await expect(page.getByText(slug, { exact: false })).not.toBeVisible();
  });

  test(
    '[P1] a failed propose call shows an error and leaves the drawer usable',
    { annotation: [{ type: 'skipNetworkMonitoring' }] },
    async ({ page, interceptNetworkCall }) => {
      const proposeCall = interceptNetworkCall({
        url: '**/api/settings/propose',
        fulfillResponse: {
          status: 502,
          body: { error_code: 'settings.llm_error', message: 'Simulated LLM failure', node_id: null },
        },
      });

      await page.goto('/');
      await page.getByRole('button', { name: 'Settings' }).click();
      await page.getByPlaceholder(/always use pytest/i).fill('this request will fail');
      await page.getByRole('button', { name: 'Submit request' }).click();
      await proposeCall;

      // Next.js's own route announcer is also role="alert" (empty, framework-
      // injected) -- scope past it by matching the actual error text.
      await expect(page.getByText('Simulated LLM failure')).toBeVisible();

      // Drawer is still usable: the textarea and submit button still work.
      await page.getByPlaceholder(/always use pytest/i).fill('a different request');
      await expect(page.getByRole('button', { name: 'Submit request' })).toBeEnabled();
    },
  );
});
