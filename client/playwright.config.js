import { defineConfig, devices } from '@playwright/test'

// playwright config. webServer starts the backend (:5001, throwaway db so we
// dodge airplay on :5000 and don't touch the dev db) and the vite dev server
// (:5173) before tests, so `npx playwright test` just works from client/.
export default defineConfig({
  testDir: './e2e',
  // e2e specs are named *.e2e.js (not *.spec.js) so vitest's default glob
  // doesn't try to run them as unit tests - vitest and playwright stay in
  // their own lanes without touching the shared vite.config.js.
  testMatch: '**/*.e2e.js',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: [
    {
      // fresh db each run
      command: 'rm -f instance/e2e.db && DATABASE_URL=sqlite:///e2e.db .venv/bin/flask --app app run --port 5001',
      cwd: '../Frank',
      url: 'http://127.0.0.1:5001/api/documents',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: 'npx vite --config vite.e2e.config.js',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
})
