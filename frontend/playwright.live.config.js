import { defineConfig } from '@playwright/test'

// Only the private-MySQL launcher may opt in; direct runs must not target a personal DB.
if (process.env.SMARTPROP_BROWSER_HISTORY_TEST !== 'isolated'
    || !/^jdbc:mysql:\/\/127\.0\.0\.1:13317\/smartprop_history_[a-z0-9]+\?/.test(process.env.SMARTPROP_HISTORY_TEST_URL || '')
    || !process.env.SMARTPROP_BROWSER_HISTORY_REPORT) {
  throw new Error('Run backend/scripts/check-history-mysql.py --browser from the repository root.')
}

export default defineConfig({
  testDir: './e2e-live',
  workers: 1,
  retries: 0,
  timeout: 60000,
  reporter: [['list'], ['json', { outputFile: process.env.SMARTPROP_BROWSER_HISTORY_REPORT }]],
  use: {
    baseURL: 'http://127.0.0.1:15174',
    browserName: 'chromium',
    channel: process.env.PLAYWRIGHT_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined),
    viewport: { width: 1280, height: 900 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npm run dev -- --port 15174',
    url: 'http://127.0.0.1:15174',
    reuseExistingServer: false,
    timeout: 30000,
    env: {
      AI_API_TARGET: 'http://127.0.0.1:18081',
      BE_API_TARGET: 'http://127.0.0.1:18082',
      VITE_API_BASE_URL: '/api/v1',
      VITE_ENABLE_REFRESH: 'false',
    },
  },
})
