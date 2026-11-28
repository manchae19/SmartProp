import assert from 'node:assert/strict'
import { mkdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { marketResponse } from './pr37-market-fixture.mjs'

const id = '10000000-0000-4000-8000-000000000037'
const photo = '/media/projects/sun-ponte.jpg'
const secondPhoto = '/media/projects/the-filmore.jpg'
const district = 'Hải Châu'
const coordinate = {
  coordinateSource: 'MANUAL_PIN', accuracyLevel: 'STREET', verificationStatus: 'UNVERIFIED',
  geographicValidationStatus: 'VERIFIED_EXACT', referenceMapEligible: true,
  parcelAnalysisEligible: false, distanceAnalysisEligible: false, accuracyMeters: 40,
}
const house = {
  id, title: 'Nhà fixture Hải Châu', description: 'Mô tả nhà tổng hợp trong kiểm thử.',
  propertyType: 'HOUSE', transactionType: 'SALE', priceUnit: 'TOTAL', currency: 'VND',
  status: 'PUBLISHED', contentVersion: 1, city: 'Đà Nẵng', district, ward: 'Hòa Cường Bắc',
  address: 'Địa chỉ fixture, Hải Châu', price: 5_200_000_000, areaSqm: 80, bedrooms: 3,
  bathrooms: 2, images: [{ url: '/api/v1/fixture-images/one.jpg', cover: true }, { url: '/api/v1/fixture-images/two.jpg' }],
  latitude: null, longitude: null, coordinate, amenities: [],
}
const project = { id, name: 'Dự án fixture Hải Châu', developer: 'Chủ đầu tư fixture', district, status: 'PUBLISHED', images: [] }
const person = role => ({ id: 1, displayName: 'Tài khoản fixture', role, status: 'ACTIVE' })
const pageResult = items => ({ items, page: 0, size: 20, totalPages: items.length ? 1 : 0, totalElements: items.length })
const comparable = {
  candidateId: 'property:fixture', sourceKind: 'SMARTPROP', sourceLabel: 'SmartProp',
  liveListing: true, researchReference: false, propertyType: 'HOUSE', district,
  areaSqm: 82, askingPriceVnd: 4_100_000_000, similarityScore: 0.92, featureCoverage: 0.74,
  scoreBreakdown: { location: '1.0' }, listingUrl: '/listing/' + id,
}
const cohort = purpose => ({
  purpose, status: 'AVAILABLE', retrievedCandidateCount: 8, uniqueEligibleCandidateCount: 6,
  returnedSampleCount: 1, scanComplete: true, scannedCohortAskingPrice: {
    observations: 6, medianPriceVnd: 4_150_000_000, medianPricePerSqmVnd: 50_345_000,
  }, provenance: { SMARTPROP: { uniqueEligible: 6, returned: 1 } }, limitations: [],
})
const evidence = purpose => ({
  status: 'AVAILABLE', candidateCount: 1, searchStage: 'DISTRICT',
  comparables: [comparable], cohort: cohort(purpose), warnings: [],
})
const valuationEvidence = {
  available: true, modelVersion: 'v1.3', predictedAskingPriceVnd: '5280000000',
  featuresUsed: { areaSqm: 80 }, missingFeatures: [], warnings: [],
}
const categories = [{ category: 'Nhà ở', locations: [district] }]
const newsItem = {
  id: 'synthetic-news-37', title: 'Bài fixture thị trường Đà Nẵng', summary: 'Dữ liệu tổng hợp cho kiểm thử UI.',
  sourceName: 'Nguồn fixture', sourceUrl: 'https://example.invalid', articleUrl: 'https://example.invalid/news/1',
  category: 'Thị trường BĐS', publishedAt: '2026-11-20T00:00:00Z',
}
const coordItem = {
  ...coordinate, propertyId: id, listingCode: 'SP-FIXTURE', title: house.title, address: house.address,
  revision: 1, district, ward: house.ward, verificationStatus: 'PENDING_REVIEW',
  latitude: 16.06, longitude: 108.22,
}

const screenshots = resolve(process.env.PR37_SCREENSHOTS || '../.smartprop/pr37-screenshots')
mkdirSync(screenshots, { recursive: true })

export async function withFixture(browser, base, run) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, serviceWorkers: 'block' })
  const requests = []
  const errors = []
  const config = { role: 'BROKER', newsStatus: 200, researchStatus: 200, pendingResearch: null, researchIntercepted: null }
  await context.route('**/*', async route => {
    const request = route.request()
    const url = new URL(request.url())
    if (url.origin !== base) return route.abort()
    if (!url.pathname.startsWith('/api/')) return route.continue()
    const path = url.pathname
    const body = request.method() === 'POST' ? request.postDataJSON() : null
    requests.push({ path, query: url.searchParams, body, method: request.method(), authenticated: Boolean(request.headers().authorization) })
    const result = (json, status = 200) => route.fulfill({ json, status })
    if (path.startsWith('/api/v1/fixture-images/')) {
      const image = path.endsWith('/one.jpg') ? photo : secondPhoto
      return route.fulfill({ path: resolve('public' + image), contentType: 'image/jpeg' })
    }
    if (path.endsWith('/market-analytics')) {
      const selected = url.searchParams.get('district')
      const research = url.searchParams.get('includeResearch') === 'true'
      if (research && config.pendingResearch) {
        config.researchIntercepted?.()
        await config.pendingResearch
      }
      if (research && config.researchStatus !== 200) {
        return result({ code: config.researchStatus === 401 ? 'UNAUTHENTICATED' : 'FORBIDDEN', message: 'Fixture access denied' }, config.researchStatus)
      }
      // Canceling a real browser transport may close the intercepted request.
      return result(marketResponse({ district: selected, research, sufficient: research || selected !== 'Hòa Vang' })).catch(() => {})
    }
    if (/\/news(?:\/|$)/.test(path)) {
      return config.newsStatus === 200
        ? result({ ...pageResult([newsItem]), sources: [], lastUpdatedAt: '2026-11-28T00:00:00Z', refreshing: false })
        : result({ code: 'FEATURE_UNAVAILABLE' }, config.newsStatus)
    }
    if (path.endsWith('/auth/login')) return result({ accessToken: 'fixture-login', user: person(config.role) })
    if (path.endsWith('/users/me')) return result(person(config.role))
    if (path.endsWith('/notification-preferences')) return result({})
    if (path.endsWith('/projects')) return result(pageResult([project]))
    if (path.endsWith('/projects/' + id)) return result(project)
    if (path.endsWith('/properties')) return result(pageResult([house]))
    if (path.endsWith('/properties/' + id)) return result(house)
    if (path.endsWith('/points-of-interest') || path.endsWith('/coordinate/history')) return result([])
    if (path.endsWith('/coordinates/pending')) return result({ items: [coordItem], page: 0, size: 50, total: 1 })
    if (path.endsWith('/coordinates/stats')) return result({ total: 1, pendingReview: 1, unverified: 0, verified: 0, rejected: 0, stale: 0, districtMismatch: 0 })
    if (path.endsWith('/coordinates/' + id)) return result(coordItem)
    if (path.endsWith('/comparables')) return result({
      reference: {}, candidateCount: 1, searchStage: 'DISTRICT', comparables: [comparable],
      warnings: [], eligibleCountsBySource: { SMARTPROP: 6 }, evidence: cohort(body.purpose),
    })
    if (path.endsWith('/valuation-options')) return result({ categories })
    if (path.endsWith('/valuation-preview')) return result(valuationEvidence)
    if (path.endsWith('/model/options')) return result({ model_version: 'v1.3', categories, location_labels: { [district]: district } })
    if (path.endsWith('/predict')) return result({
      model_version: 'v1.3', predicted_asking_price_vnd: 5_310_000_000,
      features_used: { area_sqm: 80 }, missing_features: [], warnings: [],
    })
    if (path.endsWith('/geocoding/config')) return result({ available: true, provider: 'GEOAPIFY', mapProvider: 'OSM', storageAllowed: true })
    if (path.endsWith('/geocoding/search')) return result({
      status: 'OK', scope: 'DISTRICT', provider: 'GEOAPIFY', candidates: [{
        id: 'fixture-location', formattedAddress: 'Địa chỉ fixture Hải Châu', latitude: 16.06, longitude: 108.22,
        accuracy: 'EXACT', provider: 'GEOAPIFY', mapProvider: 'OSM', storageAllowed: true,
        addressMatched: true, locationLevel: 'BUILDING_ONLY', attribution: 'Geoapify fixture',
        context: { localityMatched: true, precision: 'EXACT' },
      }],
    })
    if (path.endsWith('/advisor/consult')) return result({
      advisorVersion: 'ADVISOR_ORCHESTRATOR_V1', mode: 'SAFE', serviceStatus: {},
      criteria: { includeResearch: false }, warnings: [], topAreas: [], recommendedProperties: [{
        ...house, priceVnd: house.price, recommendationScore: 85, liveListing: true,
        researchReference: false, source: { kind: 'PROPERTY', recordKey: id },
        comparableEvidence: evidence('SIMILAR_LISTING'),
        valuationComparableEvidence: evidence('VALUATION_SUPPORT'), valuationEvidence,
      }],
    })
    if (path === '/api/chat') return result({
      mode: 'SAFE', answer: 'Bạn muốn giới hạn ngân sách ở mức nào?',
      generationMode: 'EVIDENCE_ONLY', retrievalMode: 'TOOL_EVIDENCE_ONLY',
      recommendedProperties: [], citations: [], dataLimitations: [],
      evidence: {
        responseKind: 'CLARIFICATION_REQUIRED', quickReplies: ['Tìm nhà ở Hải Châu'],
        session: { id: '12345678901234567890123456789037' },
      },
    })
    if (path.endsWith('/research-config')) return result({ enabled: false })
    return result({ code: 'FEATURE_UNAVAILABLE', message: 'Fixture endpoint unavailable' }, 503)
  })
  const page = await context.newPage()
  page.setDefaultTimeout(7000)
  page.on('pageerror', error => errors.push(error.message))
  try {
    await run({ page, requests, config, base })
    assert.deepEqual(errors, [], 'Uncaught page errors')
  } catch (error) {
    const headings = await page.getByRole('heading').allTextContents()
    const alerts = await page.getByRole('alert').allTextContents()
    const paths = [...new Set(requests.map(request => request.path))]
    throw Error(error.message + '\nHeadings: ' + headings.slice(0, 5).join(' | ')
      + '\nAlerts: ' + alerts.slice(0, 3).join(' | ') + '\nFixture paths: ' + paths.join(', '))
  } finally {
    await context.close()
  }
}

export async function closeWelcome(page) {
  const dialog = page.locator('dialog.welcome-notice[open]')
  if (await dialog.isVisible()) await dialog.getByRole('button', { name: 'Đóng thông báo' }).click()
}

async function open(fixture, path, heading, role) {
  const { page, base, config } = fixture
  if (role) {
    config.role = role
    await page.goto(base + '/market-analytics')
    await page.locator('[data-ma-sample]').waitFor()
    await setSession(page, { role })
    await page.evaluate(next => window.pr37Fixture.navigate(next), path)
  } else {
    await page.goto(base + path)
  }
  const title = page.getByRole('heading', { name: heading, level: 1 })
  await title.waitFor()
  await closeWelcome(page)
  return title
}

async function setSession(page, value) {
  await page.evaluate(next => window.pr37Fixture.set(next), value)
}

function expectRequest(requests, predicate) {
  const request = requests.find(predicate)
  assert.ok(request, 'Expected fixture endpoint request was not made')
  return request
}

export async function assertBounds(locator, name) {
  await locator.waitFor()
  await locator.scrollIntoViewIfNeeded()
  const result = await locator.evaluate(element => {
    const box = element.getBoundingClientRect()
    const outside = []
    const tolerance = 2
    if (box.width <= 0 || box.height <= 0 || box.left < -tolerance || box.right > document.documentElement.clientWidth + tolerance) {
      outside.push('viewport x')
    }
    if (document.documentElement.scrollWidth > document.documentElement.clientWidth + tolerance) outside.push('document x')
    for (let node = element.parentElement; node && node !== document.body; node = node.parentElement) {
      const css = getComputedStyle(node)
      if (css.display === 'contents') continue
      const bounds = node.getBoundingClientRect()
      const left = bounds.left + node.clientLeft
      const top = bounds.top + node.clientTop
      if (/^(hidden|clip)$/.test(css.overflowX) && (box.left < left - tolerance || box.right > left + node.clientWidth + tolerance)) {
        outside.push(node.tagName + ' overflow-x')
      }
      if (/^(hidden|clip)$/.test(css.overflowY) && (box.top < top - tolerance || box.bottom > top + node.clientHeight + tolerance)) {
        outside.push(node.tagName + ' overflow-y')
      }
    }
    return outside
  })
  assert.deepEqual(result, [], name)
}

async function responsive(page, name, locators) {
  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    for (const [label, locator] of locators) await assertBounds(locator, `${name} ${width}px ${label}`)
    await page.evaluate(() => scrollTo(0, 0))
    await page.screenshot({ path: resolve(screenshots, `${name}-${width}.png`) })
  }
}

export async function assertImages(page, selector, { atLeast = 1, decorative = '' } = {}) {
  const images = page.locator(selector)
  await images.first().waitFor()
  const count = await images.count()
  assert.ok(count >= atLeast, `${selector}: expected at least ${atLeast} images, got ${count}`)
  for (const item of await images.all()) {
    await item.scrollIntoViewIfNeeded()
    await item.evaluate(img => img.decode())
    const value = await item.evaluate((img, allowed) => ({
      path: new URL(img.currentSrc || img.src, location.origin).pathname,
      width: img.naturalWidth,
      hasAlt: !!img.getAttribute('alt')?.trim() || img.getAttribute('aria-hidden') === 'true'
        || (allowed && img.matches(allowed) && img.getAttribute('alt') === ''),
    }), decorative)
    assert.ok(value.width > 0 && value.hasAlt, `Image missing pixels or alt: ${value.path}`)
    assert.ok(!value.path.startsWith('/media/areas/'), 'Unapproved district image rendered')
  }
}

export function surfaceGroups(base) {
  const group = run => browser => withFixture(browser, base, run)
  return {
    g8_home_navigation: group(async fx => {
      const { page } = fx
      const title = await open(fx, '/home', /Hiểu vị trí.*Chọn không gian/s)
      const footer = page.getByRole('navigation', { name: 'Khám phá cuối trang' })
      await footer.getByRole('link', { name: /Tin đăng|Bất động sản/ }).waitFor()
      await responsive(page, 'home', [['heading', title], ['footer links', footer]])
      const nav = page.getByRole('navigation', { name: 'Điều hướng chính' })
      const desktop = nav.getByRole('link', { name: /Tin đăng|Bất động sản/ })
      await desktop.waitFor()
      for (const width of [390, 768]) {
        await page.setViewportSize({ width, height: 900 })
        await page.getByRole('button', { name: 'Mở menu điều hướng' }).click()
        const drawer = page.getByRole('dialog').filter({ hasText: /Điều hướng|Trang chủ/ })
        const link = drawer.getByRole('link', { name: /Tin đăng|Bất động sản/ })
        await assertBounds(link, 'mobile navigation link')
        await page.keyboard.press('Escape')
        await drawer.waitFor({ state: 'hidden' })
      }
      await page.setViewportSize({ width: 1440, height: 900 })
      await desktop.click()
      await page.getByRole('heading', { level: 1, name: /Không gian sống dành riêng/ }).waitFor()
    }),
    g9_listings: group(async fx => {
      const { page, requests } = fx
      const title = await open(fx, '/listings', /Không gian sống dành riêng/)
      const card = page.getByRole('link', { name: house.title })
      await card.waitFor()
      const districtFilter = page.locator('select[name=district]')
      await districtFilter.selectOption({ label: district })
      await Promise.all([
        page.waitForResponse(r => {
          const url = new URL(r.url())
          return url.pathname.endsWith('/properties') && url.searchParams.get('district') === district
        }),
        page.getByRole('button', { name: /^Tìm kiếm$/ }).click(),
      ])
      await card.waitFor()
      expectRequest(requests, r => r.path.endsWith('/properties') && r.query.get('district') === district)
      await responsive(page, 'listings', [['heading', title], ['filter', districtFilter], ['property card link', card]])
      await assertImages(page, '.collection-grid img')
    }),
    g10_listing_detail: group(async fx => {
      const { page, requests } = fx
      const title = await open(fx, '/listing/' + id, house.title, 'BROKER')
      const coordinatePanel = page.getByRole('region', { name: 'Trạng thái vị trí' })
      await coordinatePanel.getByText(/không xác nhận ranh giới/).waitFor()
      await page.locator('.cmp-lookup').click()
      const card = page.locator('[data-comparable-card]')
      await card.getByText(/Độ phủ thuộc tính 74%/).waitFor()
      assert.equal(expectRequest(requests, r => r.path.endsWith('/comparables')).body.purpose, 'SIMILAR_LISTING')
      await responsive(page, 'listing-detail', [['heading', title], ['coordinate provenance', coordinatePanel], ['comparable', card]])
      for (const width of [390, 768, 1440]) {
        await page.setViewportSize({ width, height: 900 })
        await page.getByRole('button', { name: 'Mở thư viện ảnh: ' + house.title }).click()
        const gallery = page.getByRole('dialog', { name: /Thư viện ảnh/ })
        const next = gallery.getByRole('button', { name: 'Ảnh tiếp theo' })
        await assertBounds(next, 'gallery next control')
        await next.click()
        await gallery.getByAltText('Ảnh 2 của ' + house.title).waitFor()
        await assertImages(page, '.signature-gallery img')
        await page.screenshot({ path: resolve(screenshots, `gallery-${width}.png`) })
        await page.keyboard.press('Escape')
        await gallery.waitFor({ state: 'hidden' })
      }
      await assertImages(page, '.listing-gallery img:visible')
    }),
    g11_projects: group(async fx => {
      const { page, requests } = fx
      const title = await open(fx, '/projects', 'Dự án bất động sản')
      const directory = page.getByRole('region', { name: 'Danh mục giới thiệu' })
      const official = directory.getByRole('link', { name: /Sun Ponte Residence/ })
      assert.match(await official.getAttribute('href'), /^https:\/\/sunpropertygroup\.vn\//)
      const internal = page.getByRole('link', { name: new RegExp(project.name) })
      await internal.waitFor()
      expectRequest(requests, r => r.path.endsWith('/projects'))
      await responsive(page, 'projects', [['heading', title], ['official project', official], ['internal project', internal]])
      await assertImages(page, '.project-directory img', { atLeast: 6 })
      await internal.click()
      await page.getByRole('heading', { name: project.name, level: 1 }).waitFor()
    }),
    g12_account_login: group(async fx => {
      const { page, requests } = fx
      await page.goto(fx.base + '/login')
      const heading = page.locator('#auth-heading')
      await heading.waitFor()
      assert.match(await heading.innerText(), /Đăng nhập|Chào mừng/)
      const email = page.locator('#email-input')
      const password = page.locator('#password-input')
      await responsive(page, 'login', [['heading', heading], ['email', email], ['password', password]])
      await email.fill('fixture@example.invalid')
      await password.fill('fixture-only-value')
      await Promise.all([
        page.waitForResponse(r => r.url().endsWith('/auth/login')),
        page.getByRole('button', { name: 'Đăng nhập', exact: true }).click(),
      ])
      expectRequest(requests, r => r.path.endsWith('/auth/login') && r.method === 'POST')
      await page.evaluate(() => window.pr37Fixture.navigate('/account'))
      const account = page.getByRole('heading', { name: /Hồ sơ cá nhân|Tài khoản của bạn/, level: 1 })
      await account.waitFor()
      await closeWelcome(page)
      await responsive(page, 'account', [['heading', account]])
      expectRequest(requests, r => r.path.endsWith('/users/me') && r.authenticated)
    }),
    g13_market_authorization: group(async fx => {
      const { page, requests, config } = fx
      const title = await open(fx, '/market-analytics', 'Thống kê giá rao theo dữ liệu thực')
      const toggle = page.getByRole('checkbox', { name: 'Yêu cầu dữ liệu nghiên cứu' })
      const research = page.locator('[data-ma-sample]').filter({ hasText: /^224$/ })
      const safe = page.locator('[data-ma-sample]').filter({ hasText: /^128$/ })
      await safe.waitFor()
      const market = () => requests.filter(r => r.path.endsWith('/market-analytics'))
      const restricted = () => market().filter(r => r.query.get('includeResearch') === 'true')
      async function submitResearch(status) {
        // A fast denial can reset the controlled checkbox before Playwright checks it.
        await Promise.all([
          page.waitForResponse(response => {
            const url = new URL(response.url())
            return url.pathname.endsWith('/market-analytics')
              && url.searchParams.get('includeResearch') === 'true'
              && response.status() === status
          }),
          toggle.click(),
        ])
      }
      assert.equal(market().length, 1)
      for (const role of ['BUYER', 'BROKER', 'ADMIN']) {
        await setSession(page, { role })
        if (role === 'ADMIN') await toggle.waitFor()
        else await toggle.waitFor({ state: 'hidden' })
        await closeWelcome(page)
        assert.equal(restricted().length, 0)
      }
      config.researchStatus = 403
      await submitResearch(403)
      await page.locator('[data-ma-research-error]').waitFor()
      await safe.waitFor()
      assert.equal(await toggle.isChecked(), false)
      assert.equal(restricted().length, 1)
      assert.ok(restricted()[0].authenticated)
      config.researchStatus = 200
      await submitResearch(200)
      await research.waitFor()
      assert.equal(await toggle.isChecked(), true)
      await page.locator('option[value=TINIX_RESEARCH]').waitFor({ state: 'attached' })
      await responsive(page, 'market-analytics', [['heading', title], ['research toggle', toggle], ['statistic', research]])
      const beforeTransition = restricted().length
      await page.evaluate(() => window.pr37Fixture.authorization({ transition: true }))
      await toggle.waitFor({ state: 'hidden' })
      await research.waitFor({ state: 'hidden' })
      await safe.waitFor()
      await page.evaluate(() => window.pr37Fixture.authorization({ transition: false }))
      await toggle.waitFor()
      assert.equal(await toggle.isChecked(), false)
      assert.equal(restricted().length, beforeTransition)
      await submitResearch(200)
      await research.waitFor()
      await page.evaluate(() => window.pr37Fixture.authorization({ transition: false, replaceScope: true }))
      await research.waitFor({ state: 'hidden' })
      await safe.waitFor()
      assert.equal(await toggle.isChecked(), false)
      await submitResearch(200)
      await research.waitFor()
      for (const next of [
        { role: 'BUYER' }, { role: 'ADMIN', revision: 2 }, { role: 'ADMIN', actor: 2 },
        { role: 'ADMIN', accountStatus: 'LOCKED' }, {},
      ]) {
        const count = restricted().length
        await setSession(page, next)
        await safe.waitFor()
        await research.waitFor({ state: 'hidden' })
        assert.equal(await page.locator('option[value=TINIX_RESEARCH]').count(), 0)
        await setSession(page, { role: 'ADMIN' })
        await toggle.waitFor()
        await closeWelcome(page)
        assert.equal(await toggle.isChecked(), false)
        assert.equal(restricted().length, count)
        await submitResearch(200)
        await research.waitFor()
      }
      let release
      config.pendingResearch = new Promise(done => { release = done })
      const intercepted = new Promise(done => { config.researchIntercepted = done })
      const start = restricted().length
      await page.getByLabel('Quận/Huyện').selectOption({ label: district })
      const timeout = setTimeout(release, 7000)
      try {
        await page.waitForFunction(() => document.querySelector('[data-market-analytics]')?.getAttribute('aria-busy') === 'true')
        await Promise.race([intercepted, config.pendingResearch.then(() => {
          if (restricted().length === start) assert.fail('Research request was not intercepted')
        })])
      } finally {
        clearTimeout(timeout)
      }
      assert.equal(restricted().length, start + 1)
      await page.evaluate(() => {
        window.pr37Fixture.set({ role: 'BUYER' })
        window.pr37Fixture.set({ role: 'ADMIN' })
      })
      release()
      config.pendingResearch = null
      config.researchIntercepted = null
      await safe.waitFor()
      assert.equal(await toggle.isChecked(), false)
      assert.equal(await page.locator('option[value=TINIX_RESEARCH]').count(), 0)
      await setSession(page, { role: 'ADMIN', status: 'UNAVAILABLE' })
      await toggle.waitFor({ state: 'hidden' })
      await research.waitFor({ state: 'hidden' })
      await setSession(page, { role: 'ADMIN' })
      await toggle.waitFor()
      assert.equal(await toggle.isChecked(), false)
      config.researchStatus = 401
      await submitResearch(401)
      await toggle.waitFor({ state: 'hidden' })
      await safe.waitFor()
      assert.match(page.url(), /\/market-analytics$/)
      const publicCalls = market().filter(r => r.query.get('includeResearch') === 'false')
      assert.ok(publicCalls.length >= 2 && publicCalls.every(r => !r.authenticated && r.query.get('source') !== 'TINIX_RESEARCH'))
    }),
    g14_news_retry: group(async fx => {
      const { page, requests, config } = fx
      config.newsStatus = 503
      const title = await open(fx, '/news', 'Tin tức bất động sản & góc nhìn thị trường.')
      const alert = page.getByRole('alert').filter({ hasText: 'Nguồn tin tức tạm thời không khả dụng' }).first()
      await alert.waitFor()
      assert.equal(await page.locator('.news-card').count(), 0)
      const retry = alert.getByRole('button', { name: 'Thử lại' })
      await responsive(page, 'news-unavailable', [['heading', title], ['retry', retry]])
      const before = requests.filter(r => r.path.includes('/news')).length
      assert.ok(before > 0)
      config.newsStatus = 200
      await retry.click()
      await page.getByRole('link', { name: newsItem.title, exact: true }).waitFor()
      assert.ok(requests.filter(r => r.path.includes('/news')).length > before)
      await assertImages(page, '.news-card img')
      await page.locator('.news-illustration-label').filter({ hasText: /Ảnh minh họa.*AI/i }).first().waitFor()
      await page.locator('.news-image-credit summary').first().click()
      const credit = page.locator('.news-image-credit[open] a')
      assert.ok(await credit.count() >= 2, 'Illustration attribution and licence links')
    }),
    g15_post_location_valuation: group(async fx => {
      const { page, requests } = fx
      const title = await open(fx, '/post', 'Tạo tin đăng mới', 'BROKER')
      const type = page.locator('#post-propertyType')
      await page.getByRole('button', { name: 'Đăng bán', exact: true }).click()
      await type.selectOption({ label: 'Nhà phố' })
      await page.locator('#post-title').fill('Nhà tổng hợp dùng để kiểm thử biểu mẫu')
      await page.locator('#post-area').fill('80')
      await page.locator('#post-price').fill('5000000000')
      await page.locator('.valuation-optional summary').click()
      const valuation = page.getByTestId('valuation-preview')
      await valuation.waitFor()
      const loc = page.locator('.valuation-optional select').filter({ has: page.getByRole('option', { name: district, exact: true }) })
      if (await loc.count()) await loc.selectOption({ label: district })
      await valuation.click()
      await page.getByText(/5\.280\.000\.000/).first().waitFor()
      expectRequest(requests, r => r.path.endsWith('/valuation-preview') && r.method === 'POST')
      await responsive(page, 'post', [['heading', title], ['property type', type], ['valuation preview', valuation]])
      await page.evaluate(() => window.pr37Fixture.navigate('/post/step-2'))
      const address = page.locator('#post-address')
      await address.fill('120 Bạch Đằng')
      await page.locator('#post-city').selectOption({ label: 'Đà Nẵng' })
      await page.locator('#post-district').selectOption({ label: district })
      const search = page.getByRole('button', { name: 'Tìm vị trí tự động' })
      const consent = page.locator('.search-consent input[type=checkbox]')
      await consent.waitFor()
      assert.equal(await consent.isChecked(), false)
      assert.equal(await search.isDisabled(), true)
      assert.equal(requests.some(r => r.path.endsWith('/geocoding/search')), false)
      await consent.check()
      await search.click()
      const candidate = page.getByRole('radio', { name: /Địa chỉ fixture Hải Châu/ })
      await candidate.waitFor()
      const request = expectRequest(requests, r => r.path.endsWith('/geocoding/search'))
      assert.equal(request.body.shareAddress, true)
      assert.equal(request.body.district, district)
      await responsive(page, 'post-location', [['address', address], ['consent', consent], ['candidate', candidate]])
      await candidate.check()
      const checks = page.locator('.location-consent input[type=checkbox]')
      assert.equal(await checks.count(), 2)
      for (const check of await checks.all()) await check.check()
      await page.getByRole('button', { name: 'Xác nhận vị trí', exact: true }).click()
      await page.getByText('Đã xác nhận vị trí', { exact: true }).waitFor()
      assert.ok(!requests.some(r => r.method === 'POST' && r.path.endsWith('/properties')))
    }),
    g16_admin_coordinate_review: group(async fx => {
      const { page, requests } = fx
      const title = await open(fx, '/admin/coordinate-review', 'Xác minh tọa độ', 'ADMIN')
      const item = page.getByRole('button', { name: /SP-FIXTURE/ })
      await item.click()
      const detail = page.getByRole('region', { name: 'Chi tiết tin đang chọn' })
      await detail.getByText(house.title, { exact: true }).waitFor()
      for (const endpoint of ['/coordinates/stats', '/coordinates/pending', '/coordinates/' + id, '/coordinate/history']) {
        expectRequest(requests, r => r.path.endsWith(endpoint) && r.authenticated)
      }
      await responsive(page, 'admin-coordinate', [['heading', title], ['queue item', item], ['detail panel', detail]])
    }),
    g17_valuation_comparable: group(async fx => {
      const { page, requests } = fx
      const title = await open(fx, '/valuation', 'Tham khảo giá trước khi quyết định')
      const form = page.locator('form').filter({ has: page.getByRole('button', { name: 'Ước tính giá rao' }) })
      const submit = form.getByRole('button', { name: 'Ước tính giá rao' })
      const areaInput = form.getByPlaceholder('Ví dụ: 80')
      await areaInput.fill('80')
      const location = form.locator('select').filter({ has: page.getByRole('option', { name: district, exact: true }) })
      await location.selectOption({ label: district })
      await submit.click()
      const price = page.getByTestId('estimated-price')
      await price.filter({ hasText: /5,31/ }).waitFor()
      const prediction = expectRequest(requests, r => r.path.endsWith('/predict') && r.method === 'POST')
      assert.equal(prediction.body.area_sqm, 80)
      await responsive(page, 'valuation', [['heading', title], ['submit', submit], ['result', price]])
      expectRequest(requests, r => r.path.endsWith('/model/options'))
      await setSession(page, { role: 'BROKER' })
      await page.evaluate(() => window.pr37Fixture.navigate('/comparables'))
      const comparableTitle = page.getByRole('heading', { name: 'Tìm bất động sản tương đồng', level: 1 })
      await comparableTitle.waitFor()
      await closeWelcome(page)
      const area = page.locator('[data-comparables-view] input[type=number]').first()
      await area.fill('80')
      await page.getByRole('button', { name: 'Tìm tin tương đồng' }).click()
      const card = page.locator('[data-comparable-card]')
      await card.getByText('Độ phủ thuộc tính 74%').waitFor()
      assert.equal(expectRequest(requests, r => r.path.endsWith('/comparables')).body.purpose, 'SIMILAR_LISTING')
      await responsive(page, 'comparables', [['heading', comparableTitle], ['area input', area], ['card', card]])
    }),
    g18_chat_advisor: group(async fx => {
      const { page, requests } = fx
      const chat = await open(fx, '/advisor/chat', 'SmartProp AI Advisor')
      const composer = page.locator('textarea')
      await composer.fill('Tư vấn tìm nhà Hải Châu')
      await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
      await page.locator('[data-chat-clarification]').filter({ hasText: 'Bạn muốn giới hạn ngân sách ở mức nào?' }).waitFor()
      assert.equal(expectRequest(requests, r => r.path === '/api/chat').authenticated, false)
      const next = await Promise.all([
        page.waitForRequest(r => new URL(r.url()).pathname === '/api/chat'),
        page.getByRole('button', { name: 'Tìm nhà ở Hải Châu' }).click(),
      ])
      assert.match(next[0].postDataJSON().sessionId, /^[a-f0-9]{32}$/)
      await responsive(page, 'chat', [['heading', chat], ['composer', composer]])
      await page.evaluate(() => window.pr37Fixture.navigate('/advisor/analysis'))
      const advisor = page.getByRole('heading', { name: 'Tư vấn bất động sản đa bằng chứng', level: 1 })
      await advisor.waitFor()
      const budget = page.getByLabel(/Ngân sách mục tiêu/)
      await budget.fill('4500000000')
      await page.locator('.advisor-page button[type=submit]').click()
      await page.getByRole('heading', { name: 'Báo cáo tư vấn theo nhu cầu' }).waitFor()
      const call = expectRequest(requests, r => r.path.endsWith('/advisor/consult'))
      assert.equal(call.body.includeResearch, false)
      const cards = page.locator('[data-comparable-card]')
      await cards.nth(1).getByText('Độ phủ thuộc tính 74%').waitFor()
      assert.equal(await cards.count(), 2)
      await responsive(page, 'advisor', [['heading', advisor], ['criteria', budget], ['valuation comparison', cards.nth(1)]])
    }),
  }
}
