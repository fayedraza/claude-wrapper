import { test, expect, log } from '../support/merged-fixtures';

// API sample: no browser needed. See health-api.spec.ts vs home-page.spec.ts
// for the two reference shapes this scaffold ships (API-only vs UI).
test.describe('Backend health check', () => {
  test('[P0] GET /health returns ok', async ({ apiRequest }) => {
    // Given the gateway app is running
    // When GET /health is requested
    await log.step('Request backend health endpoint');

    const { status, body } = await apiRequest<{ status: string }>({
      method: 'GET',
      path: '/health',
      baseUrl: process.env.API_URL ?? 'http://localhost:8000',
    });

    // Then it returns 200 with the expected status body
    expect(status).toBe(200);
    expect(body.status).toBe('ok');
  });
});
