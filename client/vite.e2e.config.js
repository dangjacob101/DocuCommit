import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// vite config just for the e2e tests. proxies /api to :5001 since we run the
// e2e backend there (macos airplay grabs :5000). doesn't touch normal `npm run dev`.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:5001',
    },
  },
})
