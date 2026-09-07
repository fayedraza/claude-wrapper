import { test, expect } from '../support/merged-fixtures';

// UI sample against the real app shell (frontend/app/page.tsx, Story 1.2) --
// replaced the Story 1.1 stock create-next-app scaffold this sample
// originally covered. No interceptNetworkCall: opening the drawer makes no
// network call by itself (only Submit does).
test.describe('App shell', () => {
  test('[P0] home page loads and the Settings entry point opens the drawer', async ({ page }) => {
    // Given the frontend dev server is running
    // When the home page is opened
    await page.goto('/');

    // Then it renders the real app shell
    await expect(page).toHaveTitle('Claude Wrapper');
    await expect(page.getByRole('button', { name: 'Settings' })).toBeVisible();

    // And opening Settings shows the request drawer (FR-1 entry point)
    await page.getByRole('button', { name: 'Settings' }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByPlaceholder(/always use pytest/i)).toBeVisible();
  });
});
