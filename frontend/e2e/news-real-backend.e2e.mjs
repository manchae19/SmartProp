/**
 * News E2E với Backend THẬT (Spring Boot + MySQL cô lập).
 *
 * Khác với news-ui.e2e.mjs (chặn API), test này gọi backend thật và xác minh dữ liệu
 * từ MySQL. Fixture do nhóm tự tạo — không phải bài báo thật.
 *
 *   $env:PLAYWRIGHT_PATH="F:\SmartProp\frontend\vue.ui\node_modules\playwright"
 *   $env:PLAYWRIGHT_CHROMIUM="<chrome.exe>"
 *   $env:SMARTPROP_NEWS_E2E_BASE="http://127.0.0.1:5173"
 *   node e2e\news-real-backend.e2e.mjs
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
const API = process.env.SMARTPROP_NEWS_API || 'http://127.0.0.1:18080'
let failures = 0

function check(label, condition, detail = '') {
  if (condition) console.log(`  PASS  ${label}`)
  else {
    failures += 1
    console.log(`  FAIL  ${label}${detail ? ` — ${detail}` : ''}`)
  }
}

// ---------- API contract (backend thật) ----------
console.log('\n=== 1. Backend API contract ===')
const listRes = await fetch(`${API}/api/v1/news?size=5`)
const list = await listRes.json()
check('GET /news trả 200', listRes.status === 200)
check('có items', Array.isArray(list.items) && list.items.length > 0)
check('totalElements = 33', list.totalElements === 33, `thực tế ${list.totalElements}`)
check('totalPages = 7', list.totalPages === 7, `thực tế ${list.totalPages}`)
check('page = 0', list.page === 0)
check('size = 5', list.size === 5)

const article = list.items[0]
check('article có id', typeof article.id === 'string')
check('article có title', typeof article.title === 'string' && article.title.length > 0)
check('article có category', typeof article.category === 'string')
check('article có articleUrl', typeof article.articleUrl === 'string')
check('article có sourceName', typeof article.sourceName === 'string')
check('article có publishedAt', typeof article.publishedAt === 'string')
check('article có fetchedAt', typeof article.fetchedAt === 'string')
check('locationTags có dấu Đà Nẵng',
  typeof article.locationTags === 'string' && article.locationTags.includes('Đà Nẵng'),
  article.locationTags)

console.log('\n=== 2. Sources là array ===')
const sourcesRes = await fetch(`${API}/api/v1/news/sources`)
const sources = await sourcesRes.json()
check('GET /sources trả 200', sourcesRes.status === 200)
check('response là array', Array.isArray(sources), typeof sources)
check('có 3 nguồn APPROVED+enabled', sources.length === 3, `thực tế ${sources.length}`)
check('source có name/count/status',
  sources[0] && typeof sources[0].name === 'string'
  && typeof sources[0].count === 'number'
  && typeof sources[0].status === 'string')

console.log('\n=== 3. Featured ===')
const featuredRes = await fetch(`${API}/api/v1/news/featured`)
const featured = await featuredRes.json()
check('GET /featured trả 200', featuredRes.status === 200)
check('có bài nổi bật', featured.items.length > 0)

console.log('\n=== 4. Category grouping ===')
const planningRes = await fetch(
  `${API}/api/v1/news?category=${encodeURIComponent('Quy hoạch & hạ tầng')}`)
const planning = await planningRes.json()
check('Quy hoạch & hạ tầng gồm PLANNING + INFRASTRUCTURE',
  planning.totalElements === 13, `thực tế ${planning.totalElements}`)

const daNangRes = await fetch(
  `${API}/api/v1/news?category=${encodeURIComponent('Tin tức Đà Nẵng')}`)
const daNang = await daNangRes.json()
check('Tin tức Đà Nẵng lọc theo region', daNang.totalElements > 0,
  `thực tế ${daNang.totalElements}`)

console.log('\n=== 5. Sorting ===')
const newestRes = await fetch(`${API}/api/v1/news?sort=newest&size=3`)
const newest = await newestRes.json()
const oldestRes = await fetch(`${API}/api/v1/news?sort=oldest&size=3`)
const oldest = await oldestRes.json()
check('newest và oldest khác nhau',
  newest.items[0].id !== oldest.items[0].id)
check('oldest bắt đầu từ bài cũ hơn',
  new Date(oldest.items[0].publishedAt) < new Date(newest.items[0].publishedAt))

console.log('\n=== 6. Summary permission ===')
const noSummaryRes = await fetch(`${API}/api/v1/news?q=${encodeURIComponent('Chính sách')}`)
const noSummary = await noSummaryRes.json()
check('tìm thấy bài từ nguồn không cho summary', noSummary.totalElements === 3)
check('summary bị null', noSummary.items[0].summary === null,
  String(noSummary.items[0].summary))

const forbiddenSearchRes = await fetch(`${API}/api/v1/news?q=${encodeURIComponent('BỊ CẤM')}`)
const forbiddenSearch = await forbiddenSearchRes.json()
check('search không khớp summary bị cấm', forbiddenSearch.totalElements === 0,
  `thực tế ${forbiddenSearch.totalElements}`)

console.log('\n=== 7. Hidden và nguồn không hợp lệ không lộ ===')
const hiddenRes = await fetch(`${API}/api/v1/news?q=${encodeURIComponent('bị ẩn')}`)
const hidden = await hiddenRes.json()
check('bài HIDDEN không xuất hiện', hidden.totalElements === 0)

const disabledRes = await fetch(`${API}/api/v1/news?q=${encodeURIComponent('đang tắt')}`)
const disabled = await disabledRes.json()
check('bài từ nguồn tắt không xuất hiện', disabled.totalElements === 0)

const pendingRes = await fetch(`${API}/api/v1/news?q=${encodeURIComponent('chờ duyệt')}`)
const pending = await pendingRes.json()
check('bài từ nguồn chưa duyệt không xuất hiện', pending.totalElements === 0)

console.log('\n=== 8. Ingestion bị khóa ===')
const syncRes = await fetch(`${API}/api/v1/admin/news/sources`, { method: 'GET' })
check('admin endpoint yêu cầu auth (401)', syncRes.status === 401,
  `thực tế ${syncRes.status}`)

// ---------- Browser E2E ----------
console.log('\n=== 9. Browser: News page với backend thật ===')
const browser = await chromium.launch({
  executablePath: process.env.PLAYWRIGHT_CHROMIUM || undefined,
})
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
const page = await context.newPage()
const pageErrors = []
page.on('pageerror', e => pageErrors.push(e.message))

// Chỉ chặn API của backend khác (không chặn News) để trang tải được.
await context.route('**/api/v1/**', async route => {
  const url = route.request().url()
  if (url.includes('/api/v1/news')) return route.continue()
  return route.fulfill({
    status: 503, contentType: 'application/json',
    body: JSON.stringify({ code: 'FEATURE_UNAVAILABLE', message: 'Tạm không khả dụng' }),
  })
})

await page.goto(`${BASE}/news`, { waitUntil: 'networkidle', timeout: 45000 })
const heading = await page.locator('h1').first().textContent().catch(() => '')
check('trang News render', Boolean(heading && heading.trim()))

const cards = await page.locator('.news-card').count()
check('có news card từ backend thật', cards > 0, `thực tế ${cards}`)

const firstTitle = await page.locator('.news-card h3').first().textContent().catch(() => '')
check('card có tiêu đề', Boolean(firstTitle && firstTitle.trim()))

const badge = await page.locator('.news-card-badges').first().textContent().catch(() => '')
check('badge Đà Nẵng hiển thị', badge.includes('Đà Nẵng'), badge)

const fatal = pageErrors.filter(e => !/Failed to load resource|503|net::ERR/i.test(e))
check('không có pageerror', fatal.length === 0, fatal.slice(0, 2).join(' | '))

console.log('\n=== 10. Responsive ===')
await page.setViewportSize({ width: 390, height: 844 })
await page.goto(`${BASE}/news`, { waitUntil: 'networkidle', timeout: 45000 })
const overflow = await page.evaluate(() =>
  document.documentElement.scrollWidth - document.documentElement.clientWidth)
check('không tràn ngang mobile', overflow <= 2, `overflow ${overflow}px`)

await browser.close()

console.log(`\n=== KET QUA: ${failures === 0 ? 'PASS' : `${failures} FAIL`} ===`)
console.log('REAL_BACKEND_E2E: Spring Boot + MySQL cô lập')
console.log('FIXTURE_DATA: 40 bài tự tạo, không phải bài báo thật')
console.log('LIVE_RSS_INGESTION: LOCKED')
process.exit(failures === 0 ? 0 : 1)
