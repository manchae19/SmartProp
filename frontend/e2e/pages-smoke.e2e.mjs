/**
 * Smoke E2E — kiểm tra các trang chính render được và không có lỗi JS nghiêm trọng.
 *
 * Chạy với chỉ Vite dev server. Không ghi dữ liệu, không cần tài khoản.
 *
 *   $env:PLAYWRIGHT_PATH="F:\SmartProp\frontend\vue.ui\node_modules\playwright"
 *   $env:PLAYWRIGHT_CHROMIUM="<path to chrome.exe>"
 *   node e2e\pages-smoke.e2e.mjs
 */
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
let chromium
try {
  ;({ chromium } = require('playwright'))
} catch {
  const explicit = process.env.PLAYWRIGHT_PATH
  if (!explicit) throw new Error('Playwright not found. Set PLAYWRIGHT_PATH.')
  ;({ chromium } = require(explicit))
}

const BASE = process.env.SMARTPROP_SMOKE_BASE || 'http://127.0.0.1:5173'
let failures = 0

function check(label, condition, detail = '') {
  if (condition) console.log(`  PASS  ${label}`)
  else {
    failures += 1
    console.log(`  FAIL  ${label}${detail ? ` — ${detail}` : ''}`)
  }
}

const browser = await chromium.launch({
  executablePath: process.env.PLAYWRIGHT_CHROMIUM || undefined,
})
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
const page = await context.newPage()

// Backend không chạy: mọi /api/v1/* trả 503 để kiểm tra UI chịu được lỗi.
await context.route('**/api/v1/**', route => route.fulfill({
  status: 503,
  contentType: 'application/json',
  body: JSON.stringify({ code: 'FEATURE_UNAVAILABLE', message: 'Tạm không khả dụng' }),
}))

const PAGES = [
  ['/home', 'Home'],
  ['/listings', 'Listings'],
  ['/market', 'Market'],
  ['/market-analytics', 'Market Analytics'],
  ['/news', 'News'],
  ['/projects', 'Projects'],
  ['/map', 'Map'],
  ['/valuation', 'Valuation'],
]

console.log('\n=== Các trang chính render được khi API lỗi ===')
for (const [path, label] of PAGES) {
  const errors = []
  const onError = error => errors.push(error.message)
  page.on('pageerror', onError)
  try {
    await page.goto(`${BASE}${path}`, { waitUntil: 'networkidle', timeout: 30000 })
    const body = await page.locator('body').textContent()
    const hasContent = Boolean(body && body.trim().length > 50)
    const fatal = errors.filter(e => !/Failed to load resource|503|net::ERR/i.test(e))
    check(`${label} (${path})`, hasContent && fatal.length === 0,
      fatal.slice(0, 1).join(' | ') || (hasContent ? '' : 'trang trống'))
  } catch (e) {
    check(`${label} (${path})`, false, e.message.slice(0, 80))
  } finally {
    page.off('pageerror', onError)
  }
}

console.log('\n=== Responsive ===')
for (const [width, height, name] of [[390, 844, 'mobile'], [768, 1024, 'tablet'], [1440, 900, 'desktop']]) {
  await page.setViewportSize({ width, height })
  await page.goto(`${BASE}/home`, { waitUntil: 'networkidle', timeout: 30000 })
  const overflow = await page.evaluate(() =>
    document.documentElement.scrollWidth - document.documentElement.clientWidth)
  check(`${name} (${width}px) không tràn ngang`, overflow <= 2, `overflow ${overflow}px`)
}

await browser.close()
console.log(`\n=== KET QUA: ${failures === 0 ? 'PASS' : `${failures} FAIL`} ===`)
process.exit(failures === 0 ? 0 : 1)
