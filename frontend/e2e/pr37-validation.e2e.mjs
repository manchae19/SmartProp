/**
 * PR #37 browser groups. All browser API responses come from synthetic fixtures.
 * Run against the isolated production-mode preview from pr37-preview.mjs.
 */
import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve } from 'node:path'
import { assertBounds, assertImages, surfaceGroups, withFixture } from './pr37-surfaces.mjs'

const base = process.env.PR37_BASE
assert.match(base || '', /^http:\/\/127\.0\.0\.1:\d+$/, 'Set PR37_BASE to the isolated preview')
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright')
const screenshots = resolve(process.env.PR37_SCREENSHOTS || '../.smartprop/pr37-screenshots')
const results = []
const group = run => browser => withFixture(browser, base, run)
const heading = (page, district) => page.getByRole('heading', {
  level: 1, name: new RegExp('^Hồ sơ thị trường (Quận |Huyện )?' + district + '\\.$'),
})
const marketCalls = requests => requests.filter(request => request.path.endsWith('/market-analytics'))
async function openMarket(page, slug, district) {
  await page.goto(base + '/market/' + slug)
  const title = heading(page, district)
  await title.waitFor()
  await page.locator('[data-market-hero-sample]').filter({ hasText: /\d+ tin/ }).waitFor()
  return title
}
const groups = {
  g1_market_hoa_vang: group(async ({ page, requests }) => {
    await openMarket(page, 'hoa-vang', 'Hòa Vang')
    await page.locator('[data-market-hero-median]').filter({ hasText: /Chưa đủ mẫu/ }).waitFor()
    const pinned = marketCalls(requests).filter(request => request.query.has('district'))
    assert.ok(pinned.length > 0, 'District-specific endpoint called')
    assert.ok(pinned.every(request => request.query.get('district') === 'Hòa Vang'))
    assert.doesNotMatch(await page.locator('[data-market-hero-median]').innerText(), /145 triệu/)
    assert.doesNotMatch(await page.locator('main').innerText(), /AI Valuation V1\.3/)
    await page.getByText('7 quận/huyện Đà Nẵng · Trung vị giá rao công khai (không phải giá giao dịch)', { exact: true }).waitFor()
  }),
  g2_unknown_slug: group(async ({ page, requests }) => {
    await page.goto(base + '/market/khong-ton-tai')
    const alert = page.locator('[data-market-not-found]')
    await alert.getByRole('heading', { name: /Khu vực.*khong-ton-tai.*không thuộc 7 quận\/huyện/ }).waitFor()
    assert.equal(await heading(page, 'Sơn Trà').count(), 0)
    await alert.getByRole('link', { name: /Hòa Vang/ }).click()
    await heading(page, 'Hòa Vang').waitFor()
    await page.locator('[data-market-hero-sample]').filter({ hasText: /2 tin/ }).waitFor()
    assert.ok(marketCalls(requests).some(r => r.query.get('district') === 'Hòa Vang'))
  }),
  g3_market_safe_calls: group(async ({ page, requests }) => {
    await openMarket(page, 'hoa-vang', 'Hòa Vang')
    assert.equal(await page.locator('[data-ma-research-toggle]').count(), 0)
    const calls = marketCalls(requests)
    assert.ok(calls.length > 0 && calls.every(r => r.query.get('includeResearch') === 'false' && !r.authenticated))
  }),
  g4_market_responsive: group(async ({ page }) => {
    const title = await openMarket(page, 'hoa-vang', 'Hòa Vang')
    for (const width of [390, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 })
      await assertBounds(title, 'Market heading ' + width)
      await assertBounds(page.locator('[data-market-hero-median]'), 'Market median ' + width)
      await assertBounds(page.locator('[data-market-hero-sample]'), 'Market sample ' + width)
      await page.evaluate(() => scrollTo(0, 0))
      await page.screenshot({ path: resolve(screenshots, 'market-hoa-vang-' + width + '.png') })
    }
  }),
  g5_news_degradation: group(async ({ page, config, requests }) => {
    config.newsStatus = 503
    await page.goto(base + '/news')
    await page.getByRole('heading', { level: 1, name: 'Tin tức bất động sản & góc nhìn thị trường.' }).waitFor()
    const unavailable = page.getByRole('alert').filter({ hasText: 'Nguồn tin tức tạm thời không khả dụng.' }).first()
    await unavailable.getByRole('button', { name: 'Thử lại' }).waitFor()
    assert.equal(await page.locator('.news-card').count(), 0)
    const newsCalls = requests.filter(r => /\/news(?:\/|$)/.test(r.path))
    assert.ok(newsCalls.length > 0 && newsCalls.every(r => !r.authenticated))
  }),
  g6_asset_integrity: group(async ({ page }) => {
    await page.goto(base + '/home')
    const initialNotice = page.getByRole('button', { name: 'Đóng thông báo' })
    await initialNotice.click()
    await assertImages(page, '.project-directory img', { atLeast: 3 })
    await assertImages(page, '.lifestyle-image img', { atLeast: 3, decorative: '.lifestyle-image img' })
    await assertImages(page, '.news-card img')
  }),
  g7_data_honesty: group(async ({ page }) => {
    await openMarket(page, 'hai-chau', 'Hải Châu')
    const median = page.locator('[data-market-hero-median]')
    await median.filter({ hasText: '145 triệu/m²' }).waitFor()
    const body = await page.locator('[data-ui-view=MarketInsightsView]').innerText()
    assert.doesNotMatch(body, /TINIX_RESEARCH|AI Valuation V1\.3|priceGrowthYoY|\+\s?\d+([.,]\d+)?\s?%|tăng trưởng\s*:\s*\+?\d/i)
    assert.match(body, /Không dự báo|không phải dự báo/i)
  }),
  ...surfaceGroups(base),
}

const arg = process.argv.find(value => value.startsWith('--groups='))
const wanted = arg ? arg.split('=')[1].split(',') : Object.keys(groups)
const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM || process.env.CHROME })
try {
  for (const name of wanted) {
    const key = Object.keys(groups).find(item => item === name || item.startsWith(name + '_'))
    try {
      assert.ok(key, 'Unknown group ' + name)
      await groups[key](browser)
      results.push({ group: key, status: 'PASS' })
      console.log('PASS', key)
    } catch (error) {
      results.push({ group: key ?? name, status: 'FAIL', detail: error.message.slice(0, 1200) })
      console.log('FAIL', key ?? name, error.message.slice(0, 1200))
    }
  }
} finally {
  await browser.close()
}
const out = resolve(process.env.PR37_REPORT || '../.smartprop/pr37-browser.json')
mkdirSync(resolve(out, '..'), { recursive: true })
writeFileSync(out, JSON.stringify(results, null, 2) + '\n')
console.log(results.filter(item => item.status === 'PASS').length + '/' + results.length + ' groups passed')
process.exitCode = results.some(item => item.status === 'FAIL') ? 1 : 0
