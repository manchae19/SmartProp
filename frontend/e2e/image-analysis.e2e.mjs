// Browser E2E for the YOLOv8 image-analysis demo.
// Runs against a live Vite dev server and the real vision service; no mocks.
import { chromium } from 'playwright'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const BASE = process.env.ANALYSIS_BASE || 'http://127.0.0.1:15174'
const SAMPLE = process.env.ANALYSIS_SAMPLE ||
  'F:/SmartProp/.scratch/yolov8-samples/0cc1acd26e2d4f8ea49160bacb9c8666.jpg'

const checks = []
function check(name, ok, detail = '') {
  checks.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? ' :: ' + detail : ''}`)
}

const browser = await chromium.launch({
  // Reuse an installed browser instead of downloading another Chromium build.
  channel: process.env.ANALYSIS_BROWSER_CHANNEL || 'msedge',
})
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
const errors = []
page.on('pageerror', (error) => errors.push(String(error)))
page.on('console', (message) => {
  if (message.type() === 'error') errors.push(message.text())
})

try {
  await page.goto(`${BASE}/image-analysis`, { waitUntil: 'networkidle' })
  check('page loads', true)
  check('heading present', await page.locator('h1').first().isVisible())
  check('file input present', await page.locator('#analysis-image').count() === 1)
  check('analyze button disabled before file', await page.locator('button:has-text("Phân tích ảnh")').isDisabled())
  check('supported class hint shown', (await page.locator('text=Giường, ghế sofa').count()) > 0)
  check('unsupported hint shown', (await page.locator('text=Không nhận diện được').count()) > 0)

  await page.setInputFiles('#analysis-image', SAMPLE)
  await page.waitForTimeout(400)
  check('preview image appears', await page.locator('img[alt="Ảnh đang phân tích"]').isVisible())
  check('analyze button enabled after file', await page.locator('button:has-text("Phân tích ảnh")').isEnabled())

  await page.locator('button:has-text("Phân tích ảnh")').click()
  await page.waitForSelector('text=đối tượng', { timeout: 60000 })
  await page.waitForTimeout(1200)

  const badge = await page.locator('span:has-text("đối tượng")').first().textContent()
  const count = Number((badge || '').match(/(\d+)/)?.[1] || 0)
  check('detection count badge', count > 0, `badge="${badge}"`)

  const boxes = await page.locator('div[style*="border: 2px solid"]').count()
  check('bounding boxes rendered', boxes > 0, `boxes=${boxes}`)

  const rows = await page.locator('table[data-detection-table] tbody tr').count()
  check('detection table rows', rows === count, `rows=${rows} count=${count}`)

  const timing = await page.locator('text=Thời gian suy luận').count()
  check('timing shown', timing > 0)

  const model = await page.locator('text=Model yolov8n').count()
  check('model version shown', model > 0)

  // Toggle the overlay off and confirm the boxes disappear.
  await page.locator('input[data-overlay-toggle]').uncheck()
  await page.waitForTimeout(300)
  const boxesHidden = await page.locator('div[style*="border: 2px solid"]').count()
  check('overlay toggle hides boxes', boxesHidden === 0, `boxes=${boxesHidden}`)
  await page.locator('input[data-overlay-toggle]').check()

  await page.screenshot({ path: 'F:/SmartProp/.scratch/yolov8-ui-desktop.png', fullPage: true })

  // Mobile layout must not overflow horizontally.
  await page.setViewportSize({ width: 390, height: 844 })
  await page.waitForTimeout(500)
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)
  check('mobile no horizontal overflow', !overflow)
  await page.screenshot({ path: 'F:/SmartProp/.scratch/yolov8-ui-mobile.png', fullPage: true })

  check('no page errors', errors.length === 0, errors.slice(0, 3).join(' | '))
} finally {
  await browser.close()
}

const failed = checks.filter((item) => !item.ok)
console.log(`\n${checks.length - failed.length}/${checks.length} checks passed`)
if (failed.length) process.exitCode = 1
