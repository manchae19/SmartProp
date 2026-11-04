import { randomUUID } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { test, expect } from '@playwright/test'

const historyPath = '/api/v1/users/me/valuation-history'
const password = 'SyntheticBrowserFixture123!'
const account = () => ({ email: `browser-${randomUUID()}@example.test`, name: 'Tài khoản kiểm thử trình duyệt' })
const responseFor = (page, path, method) => page.waitForResponse((r) => r.url().includes(path) && r.request().method() === method)

test.beforeAll(() => {
  const python = resolve('../ai-services/.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
  const result = execFileSync(python, ['-X', 'utf8', resolve('../backend/scripts/check-local.py'),
    '--frontend-port', '15174', '--ai-port', '18081', '--backend-port', '18082'], { encoding: 'utf8', timeout: 15000 })
  console.log(result.trim())
})

async function register(page, user) {
  await page.goto('/login?next=/valuation')
  await page.locator('.toggle').getByRole('button', { name: 'Đăng ký', exact: true }).click()
  await page.getByLabel('Họ và tên').fill(user.name)
  await page.getByLabel('Email', { exact: true }).fill(user.email)
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password)
  await page.getByLabel('Xác nhận mật khẩu').fill(password)
  const pending = responseFor(page, '/api/v1/auth/register', 'POST')
  await page.locator('form').getByRole('button', { name: 'Đăng ký', exact: true }).click()
  expect((await pending).status()).toBe(201)
  await expect(page.getByRole('status')).toHaveText('Đăng ký thành công. Vui lòng đăng nhập.')
}

async function login(page, user) {
  await page.getByLabel('Email / tên quản trị').fill(user.email)
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password)
  const pending = responseFor(page, '/api/v1/auth/login', 'POST')
  await page.locator('form').getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  const response = await pending
  expect(response.status()).toBe(200)
  const data = await response.json()
  await expect(page).toHaveURL(/\/valuation$/)
  await expect(page.getByRole('button', { name: 'Đăng xuất', exact: true })).toBeVisible()
  return data.accessToken
}

async function savePrediction(page, category = 'Nhà ở', location = 'Cẩm Lệ') {
  await page.getByLabel('Loại bất động sản').selectOption(category)
  await page.getByLabel('Địa bàn').selectOption(location)
  await page.getByLabel('Diện tích (m²)').fill('80')
  const predictionResponse = responseFor(page, '/api/ai/predict', 'POST')
  await page.getByRole('button', { name: 'Ước tính giá rao', exact: true }).click()
  const predicted = await predictionResponse
  expect(predicted.status()).toBe(200)
  const prediction = await predicted.json()
  expect(prediction.model_run).toBe('b4b1339d3f35857e')
  expect(prediction.predicted_asking_price_vnd).toBeGreaterThan(0)
  const savedResponse = responseFor(page, historyPath, 'POST')
  await page.getByRole('button', { name: 'Lưu kết quả', exact: true }).click()
  const saved = await savedResponse
  expect(saved.status()).toBe(201)
  const snapshot = await saved.json()
  expect(snapshot.prediction.predicted_asking_price_vnd).toBe(prediction.predicted_asking_price_vnd)
  expect(snapshot.prediction.model_run).toBe(prediction.model_run)
  expect(snapshot.input.category).toBe(category)
  await expect(page.getByRole('button', { name: 'Đã lưu kết quả', exact: true })).toBeDisabled()
  await expect(page.getByTestId('history-item').filter({ hasText: `${category} · 80 m²` })).toHaveCount(1)
  return snapshot
}

test('real registration and all three model categories persist through logout and login', async ({ page }) => {
  const user = account()
  await register(page, user)
  await login(page, user)
  await expect(page.getByText('Chưa có kết quả đã lưu.')).toBeVisible()
  const saved = []
  for (const [category, location] of [['Nhà ở', 'Cẩm Lệ'], ['Đất nền', 'Cẩm Lệ'], ['Căn hộ chung cư', 'Hải Châu']]) {
    saved.push(await savePrediction(page, category, location))
  }
  await expect(page.getByTestId('history-item')).toHaveCount(3)
  const outgoing = responseFor(page, '/api/v1/auth/logout', 'POST')
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
  expect((await outgoing).status()).toBe(204)
  await expect(page.getByTestId('history-item')).toHaveCount(0)
  await page.getByRole('link', { name: 'Đăng nhập', exact: true }).click()
  const token = await login(page, user)
  await expect(page.getByTestId('history-item')).toHaveCount(3)
  const response = await page.request.get(historyPath, { headers: { Authorization: `Bearer ${token}` } })
  expect(response.status()).toBe(200)
  const actual = (await response.json()).items
  expect(actual.map((item) => item.id).sort()).toEqual(saved.map((item) => item.id).sort())
  for (const snapshot of saved) {
    expect(actual.find((item) => item.id === snapshot.id).prediction).toEqual(snapshot.prediction)
  }
  for (let remaining = saved.length; remaining > 0; remaining--) {
    const removed = responseFor(page, historyPath, 'DELETE')
    const reloaded = responseFor(page, `${historyPath}?`, 'GET')
    await page.getByTestId('history-item').first().getByRole('button').click()
    expect((await removed).status()).toBe(204)
    expect((await reloaded).status()).toBe(200)
    await expect(page.getByTestId('history-item')).toHaveCount(remaining - 1)
    if (remaining > 1) await expect(page.getByTestId('history-item').first().getByRole('button')).toBeEnabled()
  }
  await expect(page.getByText('Chưa có kết quả đã lưu.')).toBeVisible()
})

test('another account cannot read or delete a real saved snapshot and logout revokes access', async ({ page, browser }) => {
  const owner = account(), other = account()
  await register(page, owner)
  const ownerToken = await login(page, owner)
  const saved = await savePrediction(page)
  const otherContext = await browser.newContext({ baseURL: new URL(page.url()).origin })
  try {
    const otherPage = await otherContext.newPage()
    await register(otherPage, other)
    const otherToken = await login(otherPage, other)
    await expect(otherPage.getByText('Chưa có kết quả đã lưu.')).toBeVisible()
    const foreign = { headers: { Authorization: `Bearer ${otherToken}` } }
    expect((await otherPage.request.get(`${historyPath}/${saved.id}`, foreign)).status()).toBe(404)
    expect((await otherPage.request.delete(`${historyPath}/${saved.id}`, foreign)).status()).toBe(404)
    expect((await otherPage.request.get(historyPath)).status()).toBe(401)
    await expect(page.getByTestId('history-item')).toHaveCount(1)
    const outgoing = responseFor(page, '/api/v1/auth/logout', 'POST')
    await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
    expect((await outgoing).status()).toBe(204)
    expect((await page.request.get(historyPath, { headers: { Authorization: `Bearer ${ownerToken}` } })).status()).toBe(401)
  } finally {
    await otherContext.close()
  }
})

test('invalid credentials recover on retry and a reload requires login without losing database history', async ({ page }) => {
  const user = account()
  await register(page, user)
  await page.getByLabel('Mật khẩu', { exact: true }).fill('WrongSyntheticPassword123!')
  const rejected = responseFor(page, '/api/v1/auth/login', 'POST')
  await page.locator('form').getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  expect((await rejected).status()).toBe(401)
  await expect(page.getByRole('status')).toHaveText('Email hoặc mật khẩu không đúng')
  await login(page, user)
  const saved = await savePrediction(page)
  await page.reload()
  await expect(page.getByTestId('history-item')).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'Đăng nhập', exact: true })).toBeVisible()
  expect(await page.evaluate(() => localStorage.getItem('token'))).toBeNull()
  await page.getByRole('link', { name: 'Đăng nhập', exact: true }).click()
  const token = await login(page, user)
  await expect(page.getByTestId('history-item')).toHaveCount(1)
  const response = await page.request.get(`${historyPath}/${saved.id}`, { headers: { Authorization: `Bearer ${token}` } })
  expect(response.status()).toBe(200)
  expect((await response.json()).prediction).toEqual(saved.prediction)
})
