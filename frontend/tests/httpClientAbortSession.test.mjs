import test from 'node:test'
import assert from 'node:assert/strict'
import { getEventListeners } from 'node:events'
import { createStateStore } from '../src/shared/state/createStateStore.js'
import { createHttpClient } from '../src/shared/lib/httpClient.js'
import { sessionJwt } from './fixtures/sessionJwt.mjs'

const actor = { id: 'fixture-user', role: 'ADMIN', status: 'ACTIVE' }
const tokenA = sessionJwt(actor.id, 'main-fixture-session', 1)
const tokenB = sessionJwt(actor.id, 'main-fixture-session', 2)
const active = { token: tokenA, user: actor, status: 'AUTHENTICATED' }
const json = (body, status = 200) => Response.json(body, { status })
const wait = ms => new Promise(resolve => setTimeout(resolve, ms))
const deferred = () => {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}
const onAbort = signal => new Promise((_, reject) => {
  if (signal.aborted) reject(signal.reason)
  else signal.addEventListener('abort', () => reject(signal.reason), { once: true })
})

function setup(fetcher, options = {}) {
  const session = createStateStore(active)
  const effects = { expired: 0, cleared: 0 }
  const client = createHttpClient({
    baseUrl: 'http://fixture.invalid', session, fetcher,
    expired: () => { effects.expired += 1 },
    clear: () => { effects.cleared += 1 },
    ...options,
  })
  return { session, client, effects }
}

test('already-aborted external signal never calls transport or touches session', async () => {
  const signal = AbortSignal.abort()
  const { client, session } = setup(() => assert.fail('transport must not be called'))
  await assert.rejects(client.request('/path', { signal }), { code: 'REQUEST_ABORTED', name: 'AbortError' })
  assert.equal(session.getSnapshot().status, 'AUTHENTICATED')
  assert.equal(getEventListeners(signal, 'abort').length, 0)
})

test('timeout with an external signal uses the timeout classification and removes the listener', async () => {
  const controller = new AbortController()
  const { client, effects } = setup((_, options) => onAbort(options.signal), { timeoutForPath: () => 12 })
  await assert.rejects(client.request('/path', { signal: controller.signal }), { code: 'REQUEST_TIMEOUT' })
  assert.equal(controller.signal.aborted, false)
  assert.equal(getEventListeners(controller.signal, 'abort').length, 0)
  assert.deepEqual(effects, { expired: 0, cleared: 0 })
})

test('external cancellation interrupts transport, clears the listener, and never logs out', async () => {
  const controller = new AbortController()
  const { client, effects } = setup((_, options) => onAbort(options.signal), { refreshEnabled: true })
  const pending = client.request('/path', { signal: controller.signal })
  assert.equal(getEventListeners(controller.signal, 'abort').length, 1)
  controller.abort()
  await assert.rejects(pending, { code: 'REQUEST_ABORTED', name: 'AbortError' })
  assert.equal(getEventListeners(controller.signal, 'abort').length, 0)
  assert.deepEqual(effects, { expired: 0, cleared: 0 })
})

for (const status of [200, 401]) {
  test('aborted request drops a late HTTP ' + status + ' including when transport ignores cancellation', async () => {
    const response = deferred()
    const controller = new AbortController()
    const { client, effects } = setup(() => response.promise)
    const pending = client.request('/path', { signal: controller.signal })
    controller.abort()
    response.resolve(json({}, status))
    await assert.rejects(pending, { code: 'REQUEST_ABORTED' })
    assert.deepEqual(effects, { expired: 0, cleared: 0 })
  })
}

test('abort during body parsing wins over a masked JSON parse failure', async () => {
  const parsing = deferred()
  const controller = new AbortController()
  const { client } = setup(async () => ({
    status: 200, ok: true,
    json() {
      parsing.resolve()
      return wait(15).then(() => { throw new SyntaxError('fixture parse error') })
    },
  }))
  const pending = client.request('/path', { signal: controller.signal })
  await parsing.promise
  controller.abort()
  await assert.rejects(pending, { code: 'REQUEST_ABORTED' })
  assert.equal(getEventListeners(controller.signal, 'abort').length, 0)
})

test('HTTP 403 authorization denial is returned and ordinary successes clear the listener', async () => {
  const controller = new AbortController()
  const { client, effects } = setup(async url => url.endsWith('denied')
    ? json({ code: 'FORBIDDEN' }, 403) : json({ ok: true }), { refreshEnabled: true })
  await assert.rejects(client.request('/denied', { signal: controller.signal }), { status: 403, code: 'FORBIDDEN' })
  assert.equal(getEventListeners(controller.signal, 'abort').length, 0)
  assert.deepEqual(await client.request('/ok', { signal: controller.signal }), { ok: true })
  assert.equal(getEventListeners(controller.signal, 'abort').length, 0)
  assert.deepEqual(effects, { expired: 0, cleared: 0 })
})

for (const [name, response, change] of [
  ['epoch invalidation drops data', json({ private: true }), fx => fx.client.invalidate()],
  ['same-actor token replacement drops data', json({ private: true }), fx => fx.session.set({ ...active, token: tokenB })],
  ['role change drops data', json({ private: true }), fx => fx.session.set({ ...active, user: { ...actor, role: 'BUYER' } })],
  ['old-account 401 cannot expire the new account', json({}, 401), fx => fx.session.set({ ...active, user: { ...actor, id: 'fixture-other' } })],
]) {
  test(name, async () => {
    const transport = deferred()
    const fixture = setup(() => transport.promise)
    const pending = fixture.client.request('/private')
    change(fixture)
    transport.resolve(response)
    await assert.rejects(pending, { code: 'SESSION_CHANGED' })
    assert.deepEqual(fixture.effects, { expired: 0, cleared: 0 })
  })
}

function refreshFixture({ delayRefresh = false, delayRetry = false } = {}) {
  const refreshStarted = deferred()
  const refreshResponse = deferred()
  const retryStarted = deferred()
  const retryResponse = deferred()
  const paths = []
  const fixture = setup(async (url, options) => {
    const path = new URL(url).pathname
    paths.push(path)
    if (path === '/auth/csrf') return json({ headerName: 'X-CSRF', token: 'fixture-csrf' })
    if (path === '/auth/refresh') {
      refreshStarted.resolve()
      if (delayRefresh) await refreshResponse.promise
      return json({ accessToken: tokenB, user: actor })
    }
    if (options.headers.Authorization !== `Bearer ${tokenB}`) return json({}, 401)
    retryStarted.resolve()
    if (delayRetry) await retryResponse.promise
    return json({ refreshed: true })
  }, { refreshEnabled: true })
  return { ...fixture, paths, refreshStarted, refreshResponse, retryStarted, retryResponse }
}

test('refresh renews and retries a GET for the same actor', async () => {
  const { client, paths, session } = refreshFixture()
  const controller = new AbortController()
  assert.deepEqual(await client.request('/private', { signal: controller.signal }), { refreshed: true })
  assert.deepEqual(paths, ['/private', '/auth/csrf', '/auth/refresh', '/private'])
  assert.equal(session.getSnapshot().status, 'AUTHENTICATED')
  assert.equal(getEventListeners(controller.signal, 'abort').length, 0)
})

test('aborting one wait does not cancel shared refresh or replay that caller', async () => {
  const fx = refreshFixture({ delayRefresh: true })
  const controller = new AbortController()
  const canceled = fx.client.request('/first', { signal: controller.signal })
  await fx.refreshStarted.promise
  const surviving = fx.client.request('/second')
  await wait(0)
  controller.abort()
  await assert.rejects(canceled, { code: 'REQUEST_ABORTED' })
  assert.equal(getEventListeners(controller.signal, 'abort').length, 0)
  fx.refreshResponse.resolve()
  assert.deepEqual(await surviving, { refreshed: true })
  assert.equal(fx.paths.filter(path => path === '/first').length, 1)
  assert.equal(fx.paths.filter(path => path === '/auth/refresh').length, 1)
  assert.deepEqual(fx.effects, { expired: 0, cleared: 0 })
})

test('epoch change during the post-refresh retry rejects the response', async () => {
  const fx = refreshFixture({ delayRetry: true })
  const pending = fx.client.request('/private')
  await fx.retryStarted.promise
  fx.client.invalidate()
  fx.retryResponse.resolve()
  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
  assert.deepEqual(fx.effects, { expired: 0, cleared: 0 })
})

test('refresh finishing after same-user token replacement cannot overwrite the session', async () => {
  const fx = refreshFixture({ delayRefresh: true })
  const pending = fx.client.request('/private')
  await fx.refreshStarted.promise
  const replacement = { ...active, token: 'fixture-replacement' }
  fx.session.set(replacement)
  const replacementScope = fx.session.getSnapshot()
  fx.refreshResponse.resolve()
  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
  assert.equal(fx.session.getSnapshot(), replacementScope)
  assert.equal(replacementScope.token, replacement.token)
  assert.equal(fx.paths.filter(path => path === '/private').length, 1)
  assert.deepEqual(fx.effects, { expired: 0, cleared: 0 })
})

test('ordinary authenticated 401 expires the session and public 401 does not', async () => {
  const fixture = setup(async () => json({ code: 'UNAUTHENTICATED' }, 401))
  await assert.rejects(fixture.client.request('/public', { authenticated: false }), { status: 401 })
  assert.equal(fixture.session.getSnapshot().status, 'AUTHENTICATED')
  await assert.rejects(fixture.client.request('/private'), { status: 401 })
  assert.equal(fixture.session.getSnapshot().status, 'UNAUTHENTICATED')
  assert.deepEqual(fixture.effects, { expired: 1, cleared: 1 })
})

test('optional authenticated content clears the expired session without redirecting the public page', async () => {
  const fixture = setup(async () => json({ code: 'UNAUTHENTICATED' }, 401))
  await assert.rejects(fixture.client.request('/optional', { redirectOnSessionExpiry: false }), { status: 401 })
  assert.equal(fixture.session.getSnapshot().status, 'UNAUTHENTICATED')
  assert.deepEqual(fixture.effects, { expired: 0, cleared: 1 })
})
