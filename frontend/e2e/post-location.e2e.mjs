/**
 * Property Quick Address E2E — real geocoding + manual map confirmation.
 * Requires staging backend :8080, React :5173, and a publisher staging account.
 * Does not save a listing or write to MySQL.
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

const BASE = process.env.SMARTPROP_POST_E2E_BASE || 'http://127.0.0.1:5173'
const EMAIL = process.env.SMARTPROP_CHAT_E2E_EMAIL || ''
const PASSWORD = process.env.SMARTPROP_CHAT_E2E_PASSWORD || ''
let failures = 0
function pass(condition, label, detail = '') {
  console.log(`${condition ? 'PASS' : 'FAIL'}  ${label}${detail ? '  ' + detail : ''}`)
  if (!condition) failures++
}

async function launch() {
  try { return await chromium.launch() } catch { return chromium.launch({ channel: 'msedge' }) }
}

async function login(page) {
  await page.goto(BASE + '/login', { waitUntil: 'networkidle' })
  await page.fill('#email-input', EMAIL)
  await page.fill('#password-input', PASSWORD)
  await page.press('#password-input', 'Enter')
  await page.waitForTimeout(2200)
  for (const name of ['Đã hiểu', 'Đóng']) {
    const button = page.getByRole('button', { name })
    if (await button.count()) await button.first().click().catch(() => {})
  }
}

async function openStep2(page, editId = '') {
  await login(page)
  await page.evaluate((id) => {
    history.pushState({}, '', '/post/step-2' + (id ? '?edit=' + encodeURIComponent(id) : ''))
    window.dispatchEvent(new PopStateEvent('popstate'))
  }, editId)
  await page.waitForTimeout(2000)
}

async function main(browser) {
  if (!EMAIL || !PASSWORD) {
    console.log('SKIP  property quick-address  set SMARTPROP_CHAT_E2E_EMAIL/PASSWORD')
    return
  }
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })
  const errors = []
  page.on('pageerror', (e) => errors.push('pageerror:' + e.message))
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console:' + m.text().slice(0, 160)) })
  await openStep2(page)
  await page.getByLabel(/Địa chỉ đầy đủ/).first().fill('120 Bạch Đằng')
  const locationSelect = page.locator('select').filter({ hasText: 'Hải Châu' }).first()
  await locationSelect.selectOption({ label: 'Hải Châu' })
  await page.waitForTimeout(400)
  const search = page.getByRole('button', { name: 'Tìm vị trí tự động' })
  const consent = page.locator('.search-consent input[type=checkbox]')
  pass(await search.isDisabled(), 'LIVE search is disabled before address consent')
  pass(!(await consent.isChecked()), 'LIVE address consent defaults to false')
  await consent.check()
  pass(!(await search.isDisabled()), 'LIVE search enables after explicit consent')
  await search.click()
  await page.waitForTimeout(6000)
  const results = page.locator('.search-results .search-result')
  pass((await results.count()) > 0, 'LIVE geocoding returns candidates', `n=${await results.count()}`)
  if (await results.count()) {
    await results.first().click()
    await page.waitForTimeout(1000)
    const map = page.locator('.manual-map').first()
    if (await map.count()) {
      await map.scrollIntoViewIfNeeded()
      const box = await map.boundingBox()
      if (box) await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2)
      await page.waitForTimeout(800)
    }
    const checks = page.locator('.location-consent input[type=checkbox]')
    for (let i = 0; i < await checks.count(); i++) {
      if (!(await checks.nth(i).isChecked())) await checks.nth(i).check().catch(() => {})
    }
    const confirm = page.getByRole('button', { name: /Xác nhận vị trí/ }).first()
    pass(!(await confirm.isDisabled()), 'LIVE confirm is enabled after pin and consent')
    if (!(await confirm.isDisabled())) await confirm.click()
    await page.waitForTimeout(500)
    pass((await page.locator('body').innerText()).includes('Đã xác nhận vị trí'), 'LIVE confirmed location is displayed')
  }
  pass(errors.filter((e) => e.startsWith('pageerror:')).length === 0, 'LIVE quick-address has no page errors', errors.slice(0, 2).join(' | '))
  await page.close()

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } })
  const mobileErrors = []
  mobile.on('pageerror', (e) => mobileErrors.push(e.message))
  await openStep2(mobile)
  pass((await mobile.locator('.automatic-location').count()) > 0, 'LIVE mobile quick-address is available')
  const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  pass(overflow <= 2, 'LIVE mobile posting form has no horizontal overflow', `overflow=${overflow}px`)
  pass(mobileErrors.length === 0, 'LIVE mobile quick-address has no page errors')
  await mobile.close()

  const editId = process.env.SMARTPROP_POST_E2E_EDIT_ID || ''
  if (editId) {
    const editPage = await browser.newPage({ viewport: { width: 1366, height: 900 } })
    await openStep2(editPage, editId)
    const address = await editPage.getByLabel(/Địa chỉ đầy đủ/).first().inputValue()
    pass(address.trim().length > 0, 'LIVE edit hydrates address', address)
    pass((await editPage.locator('[data-location-pin]').count()) > 0, 'LIVE edit hydrates map pin/coordinates')
    pass((await editPage.locator('.automatic-location').count()) > 0, 'LIVE edit keeps quick-address search available')
    await editPage.close()
  } else {
    console.log('SKIP  edit hydration  set SMARTPROP_POST_E2E_EDIT_ID')
  }
}

const browser = await launch()
try { await main(browser) } finally { await browser.close() }
console.log('POST_LOCATION_E2E_RESULT=' + (failures === 0 ? 'ALL_PASS' : 'FAILURES=' + failures))
process.exit(failures === 0 ? 0 : 1)
