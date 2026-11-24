/**
 * News UI E2E — kiểm tra giao diện News không crash khi Backend News chưa tồn tại.
 *
 * Chạy được với chỉ Vite dev server: chặn request /api/v1/news* ở tầng browser để
 * mô phỏng backend chưa có, rồi xác minh UI hiển thị trạng thái lỗi hợp lý thay vì
 * crash hoặc hiển thị tin giả.
 *
 * Không ghi dữ liệu. Không cần backend, không cần tài khoản.
 *
 *   $env:PLAYWRIGHT_PATH="F:\SmartProp\frontend\vue.ui\node_modules\playwright"
 *   node e2e\news-ui.e2e.mjs
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

const BASE = process.env.SMARTPROP_NEWS_E2E_BASE || 'http://127.0.0.1:5173'
let failures = 0

function check(label, condition, detail = '') {
  if (condition) {
    console.log(`  PASS  ${label}`)
  } else {
    failures += 1
    console.log(`  FAIL  ${label}${detail ? ` — ${detail}` : ''}`)
  }
}

const browser = await chromium.launch({
  executablePath: process.env.PLAYWRIGHT_CHROMIUM || undefined,
})
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
const page = await context.newPage()

const consoleErrors = []
page.on('console', message => {
  if (message.type() === 'error') consoleErrors.push(message.text())
})
page.on('pageerror', error => consoleErrors.push(`pageerror: ${error.message}`))

// Mô phỏng Backend News chưa tồn tại: mọi request /api/v1/news* trả 404.
await context.route('**/api/v1/news**', route => route.fulfill({
  status: 404,
  contentType: 'application/json',
  body: JSON.stringify({ code: 'NOT_FOUND', message: 'Không tìm thấy tài nguyên' }),
}))

console.log('\n=== 1. Trang News tải được khi API lỗi ===')
await page.goto(`${BASE}/news`, { waitUntil: 'networkidle', timeout: 30000 })
const heading = await page.locator('h1').first().textContent().catch(() => '')
check('trang News render tiêu đề', Boolean(heading && heading.trim()), heading || 'không có h1')

console.log('\n=== 2. Hiển thị trạng thái lỗi, không crash ===')
const alert = page.locator('[role="alert"]').first()
const alertVisible = await alert.isVisible().catch(() => false)
check('có thông báo lỗi cho người dùng', alertVisible)
if (alertVisible) {
  const text = await alert.textContent()
  check('thông báo nói nguồn tin không khả dụng',
    /không khả dụng|thử lại/i.test(text || ''), (text || '').slice(0, 80))
}

console.log('\n=== 3. Có nút thử lại ===')
const retry = page.getByRole('button', { name: /thử lại/i }).first()
check('nút "Thử lại" hiện diện', await retry.isVisible().catch(() => false))

console.log('\n=== 4. Không hiển thị tin giả ===')
const cards = await page.locator('.news-card').count()
check('không có news card nào khi API lỗi', cards === 0, `tìm thấy ${cards} card`)

console.log('\n=== 5. Không có lỗi JS nghiêm trọng ===')
const fatal = consoleErrors.filter(text =>
  !/Failed to load resource|404|net::ERR/i.test(text))
check('không có pageerror', fatal.length === 0, fatal.slice(0, 2).join(' | '))

console.log('\n=== 6. Trang Home vẫn tải được ===')
await page.goto(`${BASE}/home`, { waitUntil: 'networkidle', timeout: 30000 })
const homeHeading = await page.locator('h1, h2').first().textContent().catch(() => '')
check('trang Home render', Boolean(homeHeading && homeHeading.trim()))

console.log('\n=== 7. Responsive mobile ===')
await page.setViewportSize({ width: 390, height: 844 })
await page.goto(`${BASE}/news`, { waitUntil: 'networkidle', timeout: 30000 })
const overflow = await page.evaluate(() =>
  document.documentElement.scrollWidth - document.documentElement.clientWidth)
check('không tràn ngang trên mobile', overflow <= 2, `overflow ${overflow}px`)

await browser.close()

console.log(`\n=== KET QUA: ${failures === 0 ? 'PASS' : `${failures} FAIL`} ===`)
process.exit(failures === 0 ? 0 : 1)
