import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig, devices } from '@playwright/test';
import { E2E_CLAUDE_DIR } from './support/e2e-claude-dir';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:3000';
const API_URL = process.env.API_URL ?? 'http://localhost:8000';

export default defineConfig({
  testDir: './e2e',
  globalSetup: path.join(__dirname, 'global-setup.ts'),
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? '50%' : undefined,
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  reporter: [
    ['html', { outputFolder: '../playwright-report', open: 'never' }],
    ['junit', { outputFile: '../_bmad-output/test-artifacts/playwright-junit.xml' }],
    ['list'],
  ],
  use: {
    baseURL: BASE_URL,
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // Auto-starts both dev servers locally so `npm run test:e2e` is a single
  // command; in CI, start them explicitly in the workflow and this becomes a
  // no-op health check via `reuseExistingServer`.
  webServer: [
    {
      command: 'npm run dev',
      cwd: path.join(__dirname, '../frontend'),
      url: BASE_URL,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: 'uv run uvicorn gateway.main:app --port 8000',
      cwd: path.join(__dirname, '../backend'),
      url: `${API_URL}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      // Isolates the E2E-run backend from this repo's own real .claude/ --
      // see e2e-claude-dir.ts for why this is required, not optional.
      env: { CLAUDE_WRAPPER_CLAUDE_DIR: E2E_CLAUDE_DIR },
    },
  ],
});
