import { defineConfig, devices } from '@playwright/test'

// Playwright config for DocuCommit's end-to-end tests.
//
// `webServer` boots the whole stack before the tests run, so the suite is
// fully automated - no manual server startup needed:
//   1. the Flask backend on :5001, pointed at a throwaway sqlite db so the
//      dev database is never touched (and we dodge AirPlay on :5000)
//   2. the Vite dev server on :5173 using vite.e2e.config.js, which proxies
//      /api to the :5001 backend
//
// run with:  npx playwright test     (from the client/ directory)
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
      // fresh db each run so tests start from a known-clean state
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
