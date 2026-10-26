import { defineConfig } from '@playwright/test'
import { resolve } from 'node:path'

const python = resolve('../../ai-services/.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
const launcher = resolve('../../ai-services/run_api.py')

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  timeout: 30000,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:15173',
    browserName: 'chromium',
    channel: process.env.PLAYWRIGHT_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined),
    viewport: { width: 1280, height: 900 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: `"${python}" -X utf8 "${launcher}" --port 18080`,
      url: 'http://127.0.0.1:18080/health',
      env: { PYTHONIOENCODING: 'utf-8' },
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command: 'npm run dev -- --port 15173',
      url: 'http://127.0.0.1:15173',
      env: { AI_API_TARGET: 'http://127.0.0.1:18080' },
      reuseExistingServer: false,
      timeout: 30000,
    },
  ],
})
