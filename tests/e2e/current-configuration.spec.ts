import { randomUUID } from 'node:crypto';
import { test, expect, log } from '../support/merged-fixtures';

// apiRequest resolves baseUrl from (in priority order) an explicit baseUrl,
// then Playwright's configured `use.baseURL` -- which is the frontend
// (BASE_URL, :3000), not the backend. Every direct-to-backend call in this
// file must pass baseUrl explicitly, matching health-api.spec.ts's existing
// pattern, or it silently hits the wrong server.
const API_URL = process.env.API_URL ?? 'http://localhost:8000';

// Story 1.3 (FR-3): the Settings drawer's "Currently configured" section
// reflects live .claude/ state -- rules, agents, and permission grants --
// fetched fresh every time the drawer opens. Setup goes through the real
// API directly (apiRequest), not the UI: seeding via /api/settings/apply and
// /api/permission-grants is what this app itself uses to write that state,
// and it's the fast, parallel-safe way to get there (data-factories.md) --
// the UI is reserved for what this test actually verifies, the summary view.
test.describe('Settings: view current configuration', () => {
  test('[P0] shows a rule, an agent, and a permission grant together', async ({ page, apiRequest }) => {
    const ruleSlug = `e2e-view-rule-${randomUUID().slice(0, 8)}`;
    const agentSlug = `e2e-view-agent-${randomUUID().slice(0, 8)}`;
    const grantTarget = `e2e-view-grant-${randomUUID().slice(0, 8)}.json`;

    await log.step('Seed a rule, an agent, and a grant via the real API');
    await apiRequest({
      method: 'POST',
      path: '/api/settings/apply',
      baseUrl: API_URL,
      body: {
        target_category: 'rule',
        file_path: `.claude/rules/${ruleSlug}.md`,
        content: `Seeded rule (${ruleSlug}).`,
        action: 'create',
      },
    });
    await apiRequest({
      method: 'POST',
      path: '/api/settings/apply',
      baseUrl: API_URL,
      body: {
        target_category: 'agent',
        file_path: `.claude/agents/${agentSlug}.md`,
        content: `---\nname: ${agentSlug}\ndescription: seeded for E2E\n---\n`,
        action: 'create',
      },
    });
    const { body: grant } = await apiRequest<{ id: string }>({
      method: 'POST',
      path: '/api/permission-grants',
      baseUrl: API_URL,
      body: { kind: 'file', target: grantTarget, scope: 'local' },
    });
    expect(grant.id).toBeTruthy();

    await log.step('Open Settings and verify all three appear');
    await page.goto('/');
    await page.getByRole('button', { name: 'Settings' }).click();

    await expect(page.getByText(`.claude/rules/${ruleSlug}.md`)).toBeVisible();
    await expect(page.getByText(`.claude/agents/${agentSlug}.md`)).toBeVisible();
    await expect(page.getByText(grantTarget)).toBeVisible();
    await expect(page.getByText('.claude/settings.local.json')).toBeVisible();
  });

  test('[P2] reflects an approved change without reopening the drawer', async ({ page, interceptNetworkCall }) => {
    const slug = `e2e-refresh-${randomUUID().slice(0, 8)}`;

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
              content: 'Seeded for the refresh check.',
              action: 'create',
            },
          ],
        },
      },
    });

    await page.goto('/');
    await page.getByRole('button', { name: 'Settings' }).click();
    await expect(page.getByText(slug, { exact: false })).not.toBeVisible();

    await page.getByPlaceholder(/always use pytest/i).fill('a rule for the refresh check');
    await page.getByRole('button', { name: 'Submit request' }).click();
    await proposeCall;
    await page.getByRole('button', { name: 'Approve & Apply' }).click();
    // getByText is case-insensitive substring matching by default, so a
    // non-exact 'Applied' also matches the "Proposal ready — not yet
    // applied" badge, which stays visible after approving too.
    await expect(page.getByText('Applied', { exact: true })).toBeVisible();

    // Still the same drawer instance -- never closed and reopened. The
    // applied card's own path span stays on screen too, so this matches
    // both -- .last() targets the summary row (renders after the cards).
    await expect(page.getByText(`.claude/rules/${slug}.md`).last()).toBeVisible();
  });
});
