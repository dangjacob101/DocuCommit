import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Backend URL is configurable so Mac users can dodge AirPlay Receiver on :5000.
// Override via VITE_API_TARGET in client/.env.local (e.g. http://localhost:5001).
// See SETUP.md.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:5000'

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': apiTarget,
      },
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/test/setup.js',
    },
  }
})

