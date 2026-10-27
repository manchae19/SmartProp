import { test, expect } from '@playwright/test'

const options = {
  model_version: 'v6',
  categories: [
    { category: 'Nhà ở', locations: ['Cẩm Lệ'] },
    { category: 'Đất nền', locations: ['Cẩm Lệ'] },
    { category: 'Căn hộ chung cư', locations: ['Hải Châu'] },
  ],
  access_types: { alley: 'Trong kiệt/hẻm', frontage: 'Mặt tiền' },
  house_subtypes: { villa: 'Biệt thự', house_c4: 'Nhà cấp 4' },
}
const prediction = (payload, price = 3_829_364_014) => ({
  model_version: 'v6', model_run: 'b4b1339d3f35857e', configuration: 'all',
  category: payload.category, currency: 'VND', predicted_asking_price_vnd: price,
  predicted_asking_price_million: price / 1e6, price_basis: 'Giá rao ước tính từ dữ liệu tin đăng.',
  features_used: { area_sqm: payload.area_sqm, location_feature: payload.location_feature, ward_source: null,
    rooms: payload.rooms ?? null, floors: payload.floors ?? null, access_type: payload.access_type ?? null, house_subtype: null },
  missing_features: ['ward_source', 'house_subtype'], warnings: [],
})
const fulfill = (route, body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })

async function loginForHistory(page) {
  await page.route('**/api/v1/auth/login', (route) => fulfill(route, {
    accessToken: 'synthetic-browser-fixture', tokenType: 'Bearer', expiresIn: 1800,
    user: { id: 42, fullName: 'Tài khoản kiểm thử', role: 'BUYER' },
  }))
  await page.goto('/login?next=/valuation')
  await page.getByLabel('Email / tên quản trị').fill('fixture@example.test')
  await page.getByLabel('Mật khẩu', { exact: true }).fill('SyntheticFixture123!')
  await page.locator('form').getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  await expect(page).toHaveURL(/\/valuation$/)
}

test('authenticated user saves a server snapshot and deletes it from personal history', async ({ page }) => {
  await page.route('**/api/ai/model/options', (route) => fulfill(route, options))
  await page.route('**/api/ai/predict', (route) => fulfill(route, prediction(route.request().postDataJSON())))
  let items = [], saveCalls = 0
  await page.route('**/api/v1/users/me/valuation-history**', (route) => {
    const request = route.request()
    expect(request.headers().authorization).toBe('Bearer synthetic-browser-fixture')
    if (request.method() === 'POST') {
      saveCalls++
      const input = request.postDataJSON()
      expect(input).toEqual({ category: 'Nhà ở', area_sqm: 80, location_feature: 'Cẩm Lệ' })
      expect(request.headers()['idempotency-key']).toMatch(/^[0-9a-f-]{36}$/)
      items = [{ id: '10000000-0000-4000-8000-000000000001', createdAt: '2026-10-26T12:00:00Z', input, prediction: prediction(input) }]
      return fulfill(route, items[0], 201)
    }
    if (request.method() === 'DELETE') { items = []; return route.fulfill({ status: 204 }) }
    return fulfill(route, { items, page: 0, size: 10, totalElements: items.length, totalPages: items.length ? 1 : 0 })
  })
  await loginForHistory(page)
  await expect(page.getByText('Chưa có kết quả đã lưu.')).toBeVisible()
  await fillMinimum(page)
  await page.getByRole('button', { name: 'Ước tính giá rao', exact: true }).click()
  await page.getByRole('button', { name: 'Lưu kết quả', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Đã lưu kết quả' })).toBeDisabled()
  await expect(page.getByTestId('history-item')).toContainText('Nhà ở · 80 m² · Cẩm Lệ')
  expect(saveCalls).toBe(1)
  await page.getByRole('button', { name: 'Xóa kết quả 3,83 tỷ đồng' }).click()
  await expect(page.getByText('Chưa có kết quả đã lưu.')).toBeVisible()
  await expect(page.getByTestId('estimated-price')).toHaveText('3,83 tỷ đồng')
})

test('history outage preserves the prediction and a failed save can be retried', async ({ page }) => {
  await page.route('**/api/ai/model/options', (route) => fulfill(route, options))
  await page.route('**/api/ai/predict', (route) => fulfill(route, prediction(route.request().postDataJSON())))
  const keys = []
  await page.route('**/api/v1/users/me/valuation-history**', (route) => {
    if (route.request().method() === 'POST') {
      keys.push(route.request().headers()['idempotency-key'])
      return fulfill(route, { message: 'Lịch sử chưa sẵn sàng.' }, 503)
    }
    return fulfill(route, { items: [], totalPages: 0, totalElements: 0 })
  })
  await loginForHistory(page)
  await fillMinimum(page)
  await page.getByRole('button', { name: 'Ước tính giá rao', exact: true }).click()
  await page.getByRole('button', { name: 'Lưu kết quả', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Lịch sử chưa sẵn sàng.')
  await expect(page.getByTestId('estimated-price')).toHaveText('3,83 tỷ đồng')
  await page.getByRole('button', { name: 'Lưu kết quả', exact: true }).click()
  await expect.poll(() => keys.length).toBe(2)
  expect(keys[0]).toBe(keys[1])
})

async function fillMinimum(page) {
  await page.getByLabel('Địa bàn').selectOption('Cẩm Lệ')
  await page.getByLabel('Diện tích (m²)').fill('80')
}

test('form uses supported locations, sends only model inputs and clears stale results on edits', async ({ page }) => {
  await page.route('**/api/ai/model/options', (route) => fulfill(route, options))
  let sent
  await page.route('**/api/ai/predict', (route) => {
    sent = route.request().postDataJSON()
    return fulfill(route, prediction(sent))
  })
  await page.goto('/valuation')
  await fillMinimum(page)
  await page.getByLabel('Phòng ngủ').fill('3')
  await page.getByLabel('Số tầng nhà').fill('2')
  await page.getByLabel('Lối vào').selectOption('alley')
  await page.getByRole('button', { name: 'Ước tính giá rao', exact: true }).click()
  await expect(page.getByTestId('estimated-price')).toHaveText('3,83 tỷ đồng')
  expect(sent).toEqual({ category: 'Nhà ở', area_sqm: 80, location_feature: 'Cẩm Lệ', rooms: 3, floors: 2, access_type: 'alley' })
  await expect(page.getByText('Thông tin còn thiếu: Phường/xã theo tin, Loại nhà chi tiết.')).toBeVisible()
  await page.getByLabel('Diện tích (m²)').fill('90')
  await expect(page.getByTestId('valuation-result')).toHaveCount(0)
  await page.getByLabel('Loại bất động sản').selectOption('Đất nền')
  await expect(page.getByLabel('Phòng ngủ')).toHaveCount(0)
  await expect(page.getByLabel('Số tầng nhà')).toHaveCount(0)
  await page.getByLabel('Loại bất động sản').selectOption('Căn hộ chung cư')
  await expect(page.getByLabel('Lối vào')).toHaveCount(0)
  await expect(page.getByLabel('Địa bàn')).toHaveValue('')
})

test('invalid form blocks prediction and API errors can be retried without a fake fallback price', async ({ page }) => {
  await page.route('**/api/ai/model/options', (route) => fulfill(route, options))
  let calls = 0
  await page.route('**/api/ai/predict', (route) => {
    calls++
    return calls === 1 ? fulfill(route, {}, 503) : fulfill(route, prediction(route.request().postDataJSON()))
  })
  await page.goto('/valuation')
  await fillMinimum(page)
  await page.getByLabel('Diện tích (m²)').fill('10')
  await page.getByRole('button', { name: 'Ước tính giá rao', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Diện tích (m²) phải từ 20 đến 1000.')
  expect(calls).toBe(0)
  await page.getByLabel('Diện tích (m²)').fill('80')
  await page.getByRole('button', { name: 'Ước tính giá rao', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('chưa sẵn sàng')
  await expect(page.getByTestId('estimated-price')).toHaveCount(0)
  await page.getByRole('button', { name: 'Ước tính giá rao', exact: true }).click()
  await expect(page.getByTestId('estimated-price')).toBeVisible()
})

test('options outage offers a connection retry', async ({ page }) => {
  let calls = 0
  await page.route('**/api/ai/model/options', (route) => fulfill(route, ++calls === 1 ? {} : options, calls === 1 ? 503 : 200))
  await page.goto('/valuation')
  await expect(page.getByRole('alert')).toContainText('chưa sẵn sàng')
  await page.getByRole('button', { name: 'Thử kết nối lại' }).click()
  await expect(page.getByLabel('Địa bàn')).toBeVisible()
})

test('an old slow response cannot appear after editing inputs', async ({ page }) => {
  await page.route('**/api/ai/model/options', (route) => fulfill(route, options))
  let finish
  await page.route('**/api/ai/predict', (route) => new Promise((resolve) => {
    finish = async () => {
      try { await fulfill(route, prediction(route.request().postDataJSON())) } catch { /* request was canceled */ }
      resolve()
    }
  }))
  await page.goto('/valuation')
  await fillMinimum(page)
  await page.getByRole('button', { name: 'Ước tính giá rao', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Đang ước tính…' })).toBeDisabled()
  await expect.poll(() => typeof finish).toBe('function')
  await page.getByLabel('Diện tích (m²)').fill('90')
  await finish()
  await expect(page.getByTestId('valuation-result')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Ước tính giá rao', exact: true })).toBeEnabled()
})

test('switching listing in the same SPA clears the old price and pre-fills the new category', async ({ page }) => {
  const broadOptions = { ...options, categories: options.categories.map((item) => ({ ...item, locations: ['Hải Châu', 'Cẩm Lệ'] })) }
  await page.route('**/api/ai/model/options', (route) => fulfill(route, broadOptions))
  await page.route('**/api/ai/predict', (route) => fulfill(route, prediction(route.request().postDataJSON())))
  await page.goto('/listing/1')
  await page.getByRole('button', { name: 'Ước tính giá rao', exact: true }).click()
  await expect(page.getByTestId('estimated-price')).toBeVisible()
  await page.evaluate(() => { history.pushState({}, '', '/listing/2'); dispatchEvent(new PopStateEvent('popstate')) })
  await expect(page.getByLabel('Loại bất động sản')).toHaveValue('Căn hộ chung cư')
  await expect(page.getByTestId('estimated-price')).toHaveCount(0)
  await expect(page.getByLabel('Diện tích (m²)')).toHaveValue('68')
})

for (const [id, category] of [[1, 'Nhà ở'], [2, 'Căn hộ chung cư'], [3, 'Đất nền']]) {
  test(`live v6 through Vite proxy: ${category}`, async ({ page, request }, testInfo) => {
    const browserErrors = []
    page.on('pageerror', (error) => browserErrors.push(error.message))
    await page.goto(`/listing/${id}`)
    await expect(page.getByLabel('Loại bất động sản')).toHaveValue(category)
    const pending = page.waitForResponse((response) => response.url().endsWith('/api/ai/predict'))
    await page.getByRole('button', { name: 'Ước tính giá rao', exact: true }).click()
    const response = await pending
    expect(response.status()).toBe(200)
    const payload = response.request().postDataJSON()
    expect(payload.category).toBe(category)
    expect(payload).not.toHaveProperty('price_million')
    const direct = await request.post('http://127.0.0.1:18080/predict', { data: payload })
    expect(direct.ok()).toBeTruthy()
    expect((await response.json()).predicted_asking_price_vnd).toBe((await direct.json()).predicted_asking_price_vnd)
    await expect(page.getByTestId('estimated-price')).toBeVisible()
    expect(browserErrors).toEqual([])
    if (id === 1) await page.locator('.valuation-panel').screenshot({ path: testInfo.outputPath('valuation-desktop.png') })
  })
}

test('mobile real prediction works with missing optional data and fits the viewport', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/valuation')
  await fillMinimum(page)
  await page.getByRole('button', { name: 'Ước tính giá rao', exact: true }).click()
  await expect(page.getByTestId('estimated-price')).toBeVisible()
  await expect(page.getByText(/Thông tin còn thiếu:/)).toContainText('Phòng ngủ')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.screenshot({ path: testInfo.outputPath('valuation-mobile.png'), fullPage: true })
})

test('home valuation section uses v6 instead of the former unit-price calculator', async ({ page }) => {
  await page.goto('/home#valuation')
  await expect(page.locator('#valuation').getByLabel('Loại bất động sản')).toBeVisible()
  await expect(page.getByLabel('Đơn giá tham khảo (triệu/m²)')).toHaveCount(0)
  await page.locator('#valuation').getByRole('link', { name: 'Mở trang ước tính giá' }).click()
  await expect(page).toHaveURL(/\/valuation$/)
})

test('reviewed location labels have accents while the real model receives the original code', async ({ page }, testInfo) => {
  await page.goto('/valuation')
  const select = page.getByLabel('Địa bàn')
  await expect(select.getByRole('option', { name: 'Hòa Xuân (địa bàn mở rộng)', exact: true })).toHaveCount(1)
  await expect(select.getByRole('option', { name: /ban nha rieng|nguyen duy hieu|cam chau/ })).toHaveCount(0)
  await select.selectOption('new_unit:hoa xuan')
  await page.getByLabel('Diện tích (m²)').fill('200')
  await page.getByLabel('Phòng ngủ').fill('3')
  await page.getByLabel('Số tầng nhà').fill('2')
  await page.getByLabel('Lối vào').selectOption('alley')
  await page.getByLabel('Loại nhà chi tiết').selectOption('house_c4')
  const pending = page.waitForResponse((response) => response.url().endsWith('/api/ai/predict'))
  await page.getByRole('button', { name: 'Ước tính giá rao', exact: true }).click()
  const response = await pending
  expect(response.status()).toBe(200)
  expect(response.request().postDataJSON().location_feature).toBe('new_unit:hoa xuan')
  expect((await response.json()).predicted_asking_price_vnd).toBe(4283741699)
  await expect(page.getByTestId('estimated-price')).toHaveText('4,28 tỷ đồng')
  await expect(page.getByTestId('valuation-result')).toContainText('Hòa Xuân (địa bàn mở rộng)')
  await expect(page.getByTestId('valuation-result')).not.toContainText('hoa xuan')
  await page.screenshot({ path: testInfo.outputPath('accented-location-result.png'), fullPage: true })
})

test('a normalized ward from the model preserves the accented name typed by the user', async ({ page }) => {
  await page.goto('/valuation')
  await fillMinimum(page)
  await page.getByLabel('Phường/xã theo tin').fill('Phường Hòa Xuân')
  const pending = page.waitForResponse((response) => response.url().endsWith('/api/ai/predict'))
  await page.getByRole('button', { name: 'Ước tính giá rao', exact: true }).click()
  const response = await pending
  expect((await response.json()).features_used.ward_source).toBe('hoa xuan')
  await expect(page.getByTestId('valuation-result')).toContainText('Phường Hòa Xuân')
})
