/**
 * SmartProp Chatbot E2E — live integration (real React + RAG + Spring Boot + MySQL/staging).
 *
 * Prerequisites:
 *   - React on http://127.0.0.1:5173
 *   - Backend 8080 (staging or real, V1.1 enabled) + RAG 8001
 *   - Playwright installed (or set PLAYWRIGHT_PATH to the package directory)
 *   - For private-mode test: SMARTPROP_CHAT_E2E_EMAIL / SMARTPROP_CHAT_E2E_PASSWORD
 *     (staging account only; never put credentials in this file)
 *
 * Run (from frontend/):
 *   $env:PLAYWRIGHT_PATH="F:\SmartProp\frontend\vue.ui\node_modules\playwright"
 *   node e2e/chatbot.e2e.mjs
 *
 * Tests marked LIVE use real services/data. Tests marked STUBBED explicitly
 * simulate a transport failure only to verify the UI error state; they are not
 * evidence of a live integration PASS.
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

const BASE = process.env.SMARTPROP_CHAT_E2E_BASE || 'http://127.0.0.1:5173'
const EMAIL = process.env.SMARTPROP_CHAT_E2E_EMAIL || ''
const PASSWORD = process.env.SMARTPROP_CHAT_E2E_PASSWORD || ''
let failures = 0
let browser

function pass(condition, label, detail = '') {
  console.log(`${condition ? 'PASS' : 'FAIL'}  ${label}${detail ? '  ' + detail : ''}`)
  if (!condition) failures++
}
function skip(label, reason) { console.log(`SKIP  ${label}  ${reason}`) }

async function launch() {
  try { return await chromium.launch() } catch { return chromium.launch({ channel: 'msedge' }) }
}

async function newPage(viewport = { width: 1366, height: 900 }) {
  const page = await browser.newPage({ viewport })
  const errors = []
  page.on('pageerror', (e) => errors.push('pageerror:' + e.message))
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console:' + m.text().slice(0, 120)) })
  return { page, errors }
}

async function openChat(page) {
  await page.goto(BASE + '/advisor/chat', { waitUntil: 'networkidle' })
  await page.waitForTimeout(1000)
  for (const name of ['Đã hiểu', 'Đóng']) {
    const dialog = page.getByRole('button', { name })
    if (await dialog.count()) await dialog.first().click().catch(() => {})
  }
}

async function clickQuick(page, text) {
  const button = page.locator('.chat-quick-replies button', { hasText: text }).first()
  await button.waitFor({ state: 'visible', timeout: 30000 })
  await button.click()
  await page.waitForTimeout(1000)
}

async function sendQuestion(page, text) {
  await page.fill('#chat-question', text)
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
}

async function waitForListings(page, timeoutCycles = 60) {
  for (let i = 0; i < timeoutCycles; i++) {
    await page.waitForTimeout(2000)
    if (await page.locator('a[href^="/listing/"]').count()) return true
  }
  return false
}

async function loginAndOpenChat(page) {
  await page.goto(BASE + '/login', { waitUntil: 'networkidle' })
  await page.fill('#email-input', EMAIL)
  await page.fill('#password-input', PASSWORD)
  await page.press('#password-input', 'Enter')
  await page.waitForTimeout(2200)
  await page.evaluate(() => document.querySelector('a[href="/advisor"]')?.click())
  await page.waitForTimeout(1800)
  await page.evaluate(() => document.querySelector('[data-chat-entry]')?.click())
  await page.waitForTimeout(2200)
}

async function testGuidedLive() {
  const { page, errors } = await newPage()
  await openChat(page)
  await page.getByRole('button', { name: 'Tư vấn từng bước' }).click()
  await page.waitForTimeout(1200)
  for (const answer of ['Mua để ở', '3 tỷ', 'Hải Châu', 'Nhà phố', '50 m²', 'Trường học']) {
    await clickQuick(page, answer)
  }
  const hasListings = await waitForListings(page)
  const images = await page.locator('[data-chat-image]').count()
  let loaded = 0
  for (let i = 0; i < images; i++) {
    if (await page.locator('[data-chat-image]').nth(i).evaluate((el) => el.complete && el.naturalWidth > 0).catch(() => false)) loaded++
  }
  const reasons = await page.locator('[data-chat-reasons]').count()
  const pois = await page.locator('[data-chat-pois]').count()
  const text = await page.locator('body').innerText()
  pass(hasListings, 'LIVE guided intake reaches real listings')
  pass(images > 0 && loaded > 0, 'LIVE card images load from real content', `images=${images} loaded=${loaded}`)
  pass(reasons > 0, 'LIVE cards explain fit criteria', `blocks=${reasons}`)
  pass(pois > 0, 'LIVE cards show real POI evidence', `blocks=${pois}`)
  pass(text.includes('đường chim bay'), 'LIVE distance is labelled straight-line')
  pass(errors.length === 0, 'LIVE guided flow has no console/page errors', errors.slice(0, 2).join(' | '))
  // Multi-turn on the same session.
  await sendQuestion(page, 'Căn thứ hai có tiện ích gì?')
  await page.waitForTimeout(12000)
  pass((await page.locator('[data-chat-property]').count()) > 0, 'LIVE multi-turn returns a referenced card')
  pass((await page.locator('[data-chat-pois]').count()) > 0, 'LIVE multi-turn keeps POI evidence')
  // Wait until the follow-up response releases the edit-needs action.
  await page.waitForFunction(() => {
    const button = document.querySelector('[data-chat-edit-needs]')
    return Boolean(button && !button.disabled)
  }, null, { timeout: 30000 }).catch(() => {})
  await page.evaluate(() => document.querySelector('[data-chat-edit-needs]')?.click())
  await page.waitForSelector('.chat-quick-replies button', { timeout: 15000 }).catch(() => {})
  await page.waitForTimeout(2500)
  const quick = await page.locator('.chat-quick-replies button').allInnerTexts()
  pass(quick.some((value) => value.includes('Mua để ở')), 'LIVE edit-needs resets to guided purpose')
  await page.close()
}

async function testNoMatchLive() {
  const { page, errors } = await newPage()
  await openChat(page)
  await sendQuestion(page, 'Tìm nhà phố dưới 1 tỷ ở Hải Châu')
  await page.waitForTimeout(7000)
  const text = await page.locator('body').innerText()
  pass((await page.locator('[data-chat-property]').count()) === 0, 'LIVE no-match shows no fabricated cards')
  pass(text.includes('Chưa tìm thấy') || text.includes('nới ngân sách'), 'LIVE no-match explains relaxation criteria')
  pass(errors.length === 0, 'LIVE no-match has no console/page errors', errors.slice(0, 2).join(' | '))
  await page.close()
}

async function testPrivateModeLive() {
  if (!EMAIL || !PASSWORD) { skip('LIVE private mode', 'set SMARTPROP_CHAT_E2E_EMAIL/PASSWORD (staging only)'); return }
  const { page, errors } = await newPage()
  const requests = []
  page.on('request', (request) => {
    if (request.url().includes('/api/chat')) requests.push({ url: request.url(), auth: !!request.headers()['authorization'] })
  })
  await openChat(page)
  await loginAndOpenChat(page)
  const label = await page.locator('[data-chat-profile-label]').innerText()
  pass(label.includes('Đang dùng hồ sơ'), 'LIVE profile chip shows saved consent', label)
  await page.evaluate(() => document.querySelector('[data-chat-profile-toggle]')?.click())
  await page.waitForTimeout(800)
  pass((await page.locator('[data-chat-profile-label]').innerText()).includes('Không dùng'), 'LIVE private mode toggles off')
  await page.evaluate(() => Array.from(document.querySelectorAll('button')).find((b) => b.textContent.trim() === 'Tư vấn từng bước')?.click())
  await page.waitForTimeout(2500)
  const off = requests.at(-1)
  pass(off && off.auth === false, 'LIVE private request carries no Authorization', JSON.stringify(off))
  await page.evaluate(() => document.querySelector('[data-chat-profile-toggle]')?.click())
  await page.waitForTimeout(800)
  await page.evaluate(() => Array.from(document.querySelectorAll('button')).find((b) => b.textContent.trim() === 'Tư vấn từng bước')?.click())
  await page.waitForTimeout(2500)
  const on = requests.at(-1)
  pass(on && on.auth === true, 'LIVE personalized request carries Bearer token', JSON.stringify(on))
  pass(errors.filter((e) => e.startsWith('pageerror:')).length === 0, 'LIVE private/personalized has no page errors', errors.slice(0, 2).join(' | '))
  await page.close()
}

async function testResponsiveLive() {
  for (const viewport of [{ width: 1024, height: 768 }, { width: 390, height: 844 }]) {
    const { page, errors } = await newPage(viewport)
    await openChat(page)
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    pass(overflow <= 2, `LIVE responsive /advisor/chat @${viewport.width}`, `overflow=${overflow}px`)
    pass(errors.filter((e) => e.startsWith('pageerror:')).length === 0, `LIVE responsive no page errors @${viewport.width}`)
    await page.close()
  }
}

async function testStubbedRagDown() {
  const { page, errors } = await newPage()
  await page.route('**/api/chat', (route) => route.abort())
  await openChat(page)
  await sendQuestion(page, 'Tìm nhà phố 3 tỷ ở Hải Châu')
  await page.waitForTimeout(2500)
  const text = await page.locator('body').innerText()
  pass(/không kết nối|tạm gián đoạn|thử lại|sự cố/i.test(text), 'STUBBED RAG-down shows an explicit error state (not live evidence)')
  pass(errors.filter((e) => e.startsWith('pageerror:')).length === 0, 'STUBBED RAG-down has no page errors')
  await page.close()
}

browser = await launch()
try {
  await testGuidedLive()
  await testNoMatchLive()
  await testPrivateModeLive()
  await testResponsiveLive()
  await testStubbedRagDown()
} finally {
  await browser.close()
}
console.log('CHATBOT_E2E_RESULT=' + (failures === 0 ? 'ALL_PASS' : 'FAILURES=' + failures))
process.exit(failures === 0 ? 0 : 1)
