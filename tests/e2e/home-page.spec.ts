import { test, expect } from '../support/merged-fixtures';

// UI sample against the default (unmodified) create-next-app scaffold from
// Story 1.1 — frontend/app/page.tsx. No interceptNetworkCall here: this page
// makes no API calls yet, so there's nothing to intercept. Replace this test
// once the first real page ships.
test.describe('Frontend scaffold', () => {
  test('[P0] home page loads and renders the default Next.js scaffold', async ({ page }) => {
    // Given the frontend dev server is running
    // When the home page is opened
    await page.goto('/');

    // Then it renders the default scaffold (title + heading)
    await expect(page).toHaveTitle('Create Next App');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });
});
