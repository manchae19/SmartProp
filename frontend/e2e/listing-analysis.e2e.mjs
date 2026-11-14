// Browser E2E for the YOLOv8 listing integration.
// Runs against the isolated staging stack: Vite 15175 -> Backend 18080.
import { chromium } from 'playwright'

const BASE = process.env.STAGING_BASE || 'http://127.0.0.1:15175'
const EMAIL = 'mentor.demo@smartprop.local'
const PASSWORD = 'MentorDemo123!'

const checks = []
function check(name, ok, detail = '') {
  checks.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? ' :: ' + detail : ''}`)
}

const browser = await chromium.launch({ channel: process.env.ANALYSIS_BROWSER_CHANNEL || 'msedge' })
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
const errors = []
page.on('pageerror', (error) => errors.push(String(error)))
page.on('console', (message) => {
  if (message.type() === 'error') errors.push(message.text())
})
// Staging has no image bytes for the seeded listings, so their thumbnails 404.
// Those are data gaps, not page errors; only count errors raised on the listing page.
let collecting = false
page.on('response', (response) => {
  if (!collecting) return
  if (response.status() >= 500) errors.push(`${response.status()} ${response.url()}`)
})

try {
  // -- login ------------------------------------------------------------
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' })
  await page.fill('#email-input', EMAIL)
  await page.fill('#password-input', PASSWORD)
  await page.click('button[type="submit"]')
  await page.waitForTimeout(3500)
  check('login succeeds', !page.url().includes('/login'), page.url())

  // -- open the listing that has analysis --------------------------------
  const listingId = process.env.STAGING_LISTING_ID
  if (!listingId) {
    check('listing id provided', false, 'set STAGING_LISTING_ID')
  } else {
    await page.goto(`${BASE}/listing/${listingId}`, { waitUntil: 'networkidle' })
    // Discard errors raised by the home page's seeded thumbnails (no bytes in staging).
    errors.length = 0
    collecting = true
    await page.waitForTimeout(2500)

    const scanPanel = await page.locator('[data-sp-image-scan]').count()
    check('auto-scan panel present', scanPanel > 0, `count=${scanPanel}`)

    const analysisPanel = await page.locator('[data-sp-image-analysis]').count()
    check('yolo analysis panel present', analysisPanel > 0, `count=${analysisPanel}`)

    const heading = await page.locator('text=Phân tích nội dung ảnh').count()
    check('analysis heading shown', heading > 0)

    const labels = await page.locator('[data-analysis-labels] li').count()
    check('detected labels listed', labels > 0, `labels=${labels}`)

    const disclaimer = await page.locator('text=không phải xác nhận nội thất').count()
    check('non-certification disclaimer shown', disclaimer > 0)

    // Expand per-image detail.
    const toggle = page.locator('[data-analysis-toggle]')
    if (await toggle.count()) {
      await toggle.click()
      await page.waitForTimeout(400)
      const details = await page.locator('[data-analysis-details] li').count()
      check('per-image detail expands', details > 0, `items=${details}`)
    } else {
      check('per-image detail expands', false, 'no toggle')
    }

    await page.screenshot({ path: 'F:/SmartProp/.scratch/yolov8-listing-desktop.png', fullPage: true })

    // Mobile must not overflow.
    await page.setViewportSize({ width: 390, height: 844 })
    await page.waitForTimeout(600)
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)
    check('mobile no horizontal overflow', !overflow)
    await page.screenshot({ path: 'F:/SmartProp/.scratch/yolov8-listing-mobile.png', fullPage: true })
  }

  check('no page errors', errors.length === 0, errors.slice(0, 3).join(' | '))
} finally {
  await browser.close()
}

const failed = checks.filter((item) => !item.ok)
console.log(`\n${checks.length - failed.length}/${checks.length} checks passed`)
if (failed.length) process.exitCode = 1
