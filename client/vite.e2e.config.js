import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// E2E-only Vite config used by the Playwright harness.
//
// it proxies /api to the test backend on :5001 instead of the usual :5000.
// we run the e2e backend on 5001 because macOS binds AirPlay Receiver to
// :5000 by default, which would otherwise shadow Flask. this file does NOT
// affect normal `npm run dev` (that still uses vite.config.js / :5000).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:5001',
    },
  },
})
