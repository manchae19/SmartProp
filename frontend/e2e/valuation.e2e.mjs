/**
 * SmartProp Valuation UI E2E — real FastAPI V6/V1.3, real React.
 * Requires: FastAPI :8000 (V6 + V1.3 artifacts) and React :5173.
 * No database writes, no auth.
 *
 * Run:
 *   $env:PLAYWRIGHT_PATH="F:\SmartProp\frontend\vue.ui\node_modules\playwright"
 *   node e2e/valuation.e2e.mjs
 */
import { createRequire } from 'node:module'
const require = createRequire(import.meta.url)
let chromium
try {
  ;({ chromium } = require('playwright'))
} catch {
  const explicit = process.env.PLAYWRIGHT_PATH
  if (!explicit) throw new Error('Playwright not found. Set PLAYWRIGHT_PATH to the playwright package directory.')
  ;({ chromium } = require(explicit))
}

const BASE = process.env.SMARTPROP_VALUATION_E2E_BASE || 'http://127.0.0.1:5173'
let failures = 0
function pass(condition, label, detail = '') {
  console.log(`${condition ? 'PASS' : 'FAIL'}  ${label}${detail ? '  ' + detail : ''}`)
  if (!condition) failures++
}

async function launch() {
  try { return await chromium.launch() } catch { return chromium.launch({ channel: 'msedge' }) }
}

async function fillValuation(page) {
  await page.goto(BASE + '/valuation', { waitUntil: 'networkidle' })
  await page.waitForTimeout(1200)
  const selects = page.locator('select')
  await selects.nth(0).selectOption({ label: 'Nhà ở' })
  await page.waitForTimeout(500)
  await selects.nth(1).selectOption({ label: 'Hải Châu' })
  const numbers = page.locator('input[type="number"]')
  await numbers.nth(0).fill('100')
  // Optional fields are populated to exercise the same 100m²/villa input used in the audit.
  const labels = await page.locator('label').allInnerTexts()
  const roomLabel = page.locator('label', { hasText: 'Phòng ngủ' }).locator('input[type="number"]')
  if (await roomLabel.count()) await roomLabel.first().fill('4')
  const floorLabel = page.locator('label', { hasText: 'Số tầng nhà' }).locator('input[type="number"]')
  if (await floorLabel.count()) await floorLabel.first().fill('3')
  const accessLabel = page.locator('label', { hasText: 'Lối vào' }).locator('select')
  if (await accessLabel.count()) await accessLabel.first().selectOption('frontage')
  const subtypeLabel = page.locator('label', { hasText: 'Loại nhà chi tiết' }).locator('select')
  if (await subtypeLabel.count()) await subtypeLabel.first().selectOption('villa')
  return labels
}

async function quickAddress(browser) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })
  const errors = []
  page.on('pageerror', (e) => errors.push('pageerror:' + e.message))
  await page.goto(BASE + '/valuation', { waitUntil: 'networkidle' })
  await page.waitForTimeout(1200)
  const input = page.locator('[data-testid="valuation-quick-address-input"]')
  pass(await input.count() === 1, 'LIVE valuation quick-address input is present')
  await input.fill('120 Bạch Đằng, Phường Hải Châu 1, Quận Hải Châu')
  await page.locator('[data-testid="valuation-quick-address-apply"]').click()
  await page.waitForTimeout(500)
  const feedback = await page.locator('[data-testid="valuation-quick-address-feedback"]').innerText()
  pass(feedback.includes('Hải Châu'), 'LIVE quick-address fills district/ward', feedback)
  pass((await page.locator('select').nth(1).inputValue()) === 'Hải Châu', 'LIVE quick-address selects Hải Châu')
  pass((await page.getByLabel(/Phường\/xã/).inputValue()) === 'Hải Châu 1', 'LIVE quick-address fills legacy ward')
  pass(errors.length === 0, 'LIVE quick-address has no page errors', errors.slice(0, 2).join(' | '))
  await page.close()
}

async function desktop(browser) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })
  const errors = []
  page.on('pageerror', (e) => errors.push('pageerror:' + e.message))
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console:' + m.text().slice(0, 160)) })
  await fillValuation(page)
  await page.getByRole('button', { name: 'Ước tính giá rao' }).click()
  await page.waitForSelector('[data-testid="valuation-result"]', { timeout: 30000 })
  const price = await page.locator('[data-testid="estimated-price"]').innerText()
  pass(/\d/.test(price), 'LIVE V6 result renders a price', price)
  pass(await page.locator('[data-testid="v6-band"]').count() === 1, 'LIVE V6 explains no price band')
  pass((await page.locator('[data-testid="v6-governance"]').innerText()).includes('development validation'), 'LIVE V6 states evaluation source/limits')
  const v6Shap = page.locator('[data-testid="v6-shap"]')
  pass(await v6Shap.count() === 1, 'LIVE V6 SHAP block is present')
  const v6Text = await v6Shap.innerText()
  pass(v6Text.includes('Loại nhà: Biệt thự'), 'LIVE V6 raw subtype label is localized')
  pass(v6Text.includes('không phải quan hệ nhân quả'), 'LIVE V6 SHAP is labelled non-causal')
  pass(v6Text.includes('không áp dụng cho input') || v6Text.includes('Lối vào'), 'LIVE V6 marks access context', v6Text.slice(0, 120))

  await page.getByRole('button', { name: 'Xem dự đoán V1.3' }).click()
  await page.waitForSelector('[data-testid="v1-3-result"]', { timeout: 30000 })
  const v13 = await page.locator('[data-testid="v1-3-result"]').innerText()
  pass(v13.includes('v1.3'), 'LIVE V1.3 result declares version')
  pass(/KB|B/.test(v13) || /Khoảng giá/.test(v13), 'LIVE V1.3 renders price band', v13.slice(0, 120))
  const v13Governance = await page.locator('[data-testid="v1-3-governance"]').innerText()
  pass(v13Governance.includes('dev-test 4.403') && v13Governance.includes('không phải blind'), 'LIVE V1.3 states evaluation source/limits', v13Governance)
  const assumptions = page.locator('[data-testid="v1-3-assumptions"]')
  pass(await assumptions.count() === 1, 'LIVE V1.3 exposes adapter assumptions')
  const assumptionText = await assumptions.innerText()
  pass(assumptionText.includes('suy ra từ lối vào'), 'LIVE V1.3 does not present synthetic road/frontage as measured')
  const missing = await page.locator('[data-testid="v1-3-missing"]').innerText()
  pass(/Tên tuyến đường|Dự án|Số phòng tắm/.test(missing), 'LIVE V1.3 lists missing features', missing)
  const v13Shap = page.locator('[data-testid="v1-3-shap"]')
  pass(await v13Shap.count() === 1, 'LIVE V1.3 SHAP block is present')
  const v13Text = await v13Shap.innerText()
  pass(v13Text.includes('không phải quan hệ nhân quả'), 'LIVE V1.3 SHAP is labelled non-causal')
  pass(/đang thiếu|không có trong input|Giá trị/.test(v13Text) || v13Text.includes('Giải thích'), 'LIVE V1.3 SHAP renders labels', v13Text.slice(0, 160))
  pass(errors.filter((e) => e.startsWith('pageerror:')).length === 0, 'LIVE desktop has no page errors', errors.slice(0, 2).join(' | '))
  await page.close()
}

async function mobile(browser) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } })
  const errors = []
  page.on('pageerror', (e) => errors.push('pageerror:' + e.message))
  await page.goto(BASE + '/valuation', { waitUntil: 'networkidle' })
  await page.waitForTimeout(1000)
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  pass(overflow <= 2, 'LIVE mobile /valuation has no horizontal overflow', `overflow=${overflow}px`)
  pass(await page.getByRole('button', { name: 'Ước tính giá rao' }).count() === 1, 'LIVE mobile valuation form is usable')
  pass(errors.length === 0, 'LIVE mobile has no page errors')
  await page.close()
}

const browser = await launch()
try {
  await quickAddress(browser)
  await desktop(browser)
  await mobile(browser)
} finally {
  await browser.close()
}
console.log('VALUATION_E2E_RESULT=' + (failures === 0 ? 'ALL_PASS' : 'FAILURES=' + failures))
process.exit(failures === 0 ? 0 : 1)
