import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createStateStore } from '../src/shared/state/createStateStore.js'
import { createHttpClient } from '../src/shared/lib/httpClient.js'
import { coordinateHeadline, coordinateSourceLabel, coordinateTone } from '../src/features/property/coordinateStatus.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const FRONTEND_DIR = path.resolve(__dirname, '..')

test('httpClient expires authenticated session on 401/ACCOUNT_LOCKED but preserves session on public 401/403 (e.g. News unavailable)', async () => {
  const session = createStateStore({
    token: 'tok-active',
    user: { id: 5, role: 'BROKER', status: 'ACTIVE' },
    status: 'AUTHENTICATED',
    error: null,
  })
  let expiredCount = 0
  let clearedCount = 0

  const client = createHttpClient({
    baseUrl: 'http://127.0.0.1:18080/api/v1',
    session,
    refreshEnabled: false,
    expired: () => { expiredCount += 1 },
    clear: () => { clearedCount += 1 },
    fetcher: async (url) => {
      if (url.includes('/news')) {
        return new Response(JSON.stringify({ code: 'FORBIDDEN', message: 'Denied' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      return new Response(JSON.stringify({ code: 'UNAUTHENTICATED', message: 'Token revoked' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      })
    },
  })

  await assert.rejects(() => client.request('/news?page=0', { authenticated: false }))
  assert.equal(session.getSnapshot().status, 'AUTHENTICATED')
  assert.equal(session.getSnapshot().token, 'tok-active')
  assert.equal(expiredCount, 0)

  await assert.rejects(() => client.request('/users/me', { authenticated: true }))
  assert.equal(session.getSnapshot().status, 'UNAUTHENTICATED')
  assert.equal(session.getSnapshot().token, null)
  assert.equal(expiredCount, 1)
  assert.equal(clearedCount, 1)
})

test('httpClient honors external AbortSignal cancellation immediately with AbortError', async () => {
  const session = createStateStore({ token: null, user: null, status: 'UNAUTHENTICATED', error: null })
  const controller = new AbortController()
  const client = createHttpClient({
    baseUrl: 'http://127.0.0.1:18080/api/v1',
    session,
    fetcher: (_url, init) =>
      new Promise((_resolve, reject) => {
        init.signal.addEventListener('abort', () => {
          const err = new Error('Aborted')
          err.name = 'AbortError'
          reject(err)
        })
      }),
  })

  const pending = client.request('/properties/market-analytics?includeResearch=false', {
    authenticated: false,
    signal: controller.signal,
  })
  controller.abort()
  await assert.rejects(pending, (err) => err.name === 'AbortError' && err.code === 'REQUEST_ABORTED')
})

test('ListingDetailView and router preserve CoordinateStatusPanel, admin coordinate-review, News route, and zero null bytes', () => {
  const routerSrc = fs.readFileSync(path.join(FRONTEND_DIR, 'src/app/router.js'), 'utf8')
  assert.match(routerSrc, /path:\s*['"]\/news['"]/)
  assert.match(routerSrc, /['"]coordinate-review['"]:\s*['"]CoordinateReviewView['"]/)
  assert.match(routerSrc, /AdminCoordinateReviewView\.jsx/)

  const detailBuf = fs.readFileSync(path.join(FRONTEND_DIR, 'src/features/property/ListingDetailView.jsx'))
  assert.equal(detailBuf.includes(0), false, 'ListingDetailView.jsx must not contain null bytes')
  const detailSrc = detailBuf.toString('utf8')
  assert.match(detailSrc, /import CoordinateStatusPanel from ["']\.\/CoordinateStatusPanel\.jsx["']/)
  assert.match(detailSrc, /<CoordinateStatusPanel\s+coordinate=\{view\.property\?\.coordinate\}\s*\/>/)
  assert.match(detailSrc, /role="dialog"\s+aria-modal="true"/)

  assert.equal(coordinateTone({ geographicValidationStatus: 'INVALID_DISTRICT_MISMATCH' }), 'warning')
  assert.match(coordinateHeadline({ parcelAnalysisEligible: true, verificationStatus: 'VERIFIED' }), /cấp thửa/i)
  assert.equal(coordinateSourceLabel('USER_PINNED'), 'Người đăng chọn trên bản đồ')
})
