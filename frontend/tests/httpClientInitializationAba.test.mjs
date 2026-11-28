/**
 * PR #37 — initialization recovery and external-credential ABA discontinuity.
 *
 * Deterministic: every barrier is an explicit deferred, so ordering is proven rather than assumed.
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { createStateStore } from '../src/shared/state/createStateStore.js'
import { createHttpClient } from '../src/shared/lib/httpClient.js'
import { sessionJwt } from './fixtures/sessionJwt.mjs'

const json = (body, status = 200) => Response.json(body, { status })
const deferred = () => {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}
const actor = { id: 'fixture-user', role: 'ADMIN', status: 'ACTIVE' }
const tokenA = sessionJwt(actor.id, 'main-fixture-session', 1)
const tokenB = sessionJwt(actor.id, 'main-fixture-session', 2)
const tokenY = sessionJwt(actor.id, 'main-fixture-session', 3)
const tokenX = sessionJwt(actor.id, 'main-fixture-session', 4)

function setup(fetcher, initial = { token: null, user: null, status: 'INITIALIZING' }) {
  const session = createStateStore(initial)
  const client = createHttpClient({
    baseUrl: 'http://fixture.invalid', session, fetcher, refreshEnabled: true,
  })
  return { session, client }
}

const authRoutes = (handle) => async (url, options) => {
  const path = new URL(url).pathname
  if (path === '/auth/csrf') return json({ headerName: 'X-CSRF-Token', token: 'csrf' })
  if (path === '/auth/refresh') return handle.refresh()
  return handle.business(path, options)
}

// ---------------------------------------------------------------- initialization
test('init: a valid access token becomes an authenticated session', async () => {
  const { client, session } = setup(authRoutes({
    refresh: () => json({ accessToken: tokenB, user: actor }),
    business: () => json(actor),
  }), { token: tokenA, user: actor, status: 'INITIALIZING' })

  await client.initialize()
  assert.equal(session.getSnapshot().status, 'AUTHENTICATED')
  assert.equal(session.getSnapshot().token, tokenA, 'no unnecessary rotation')
})

test('init: an expired token recovers through one refresh', async () => {
  let refreshes = 0
  const { client, session } = setup(authRoutes({
    refresh: () => {
      refreshes += 1
      return json({ accessToken: tokenB, user: actor })
    },
    business: () => json({ message: 'expired' }, 401),
  }), { token: tokenA, user: actor, status: 'INITIALIZING' })

  await client.initialize()
  assert.equal(refreshes, 1)
  assert.equal(session.getSnapshot().token, tokenB)
  assert.equal(session.getSnapshot().status, 'AUTHENTICATED')
})

test('init: cookie-based restoration establishes the session without a token', async () => {
  const { client, session } = setup(authRoutes({
    refresh: () => json({ accessToken: 'fixture-cookie', user: actor }),
    business: () => json({ ok: true }),
  }))

  await client.initialize()
  assert.equal(session.getSnapshot().token, 'fixture-cookie')
  assert.equal(session.getSnapshot().user.id, actor.id)
  assert.equal(session.getSnapshot().status, 'AUTHENTICATED')
})

test('init: no cookie and no token stays unauthenticated', async () => {
  const { client, session } = setup(authRoutes({
    refresh: () => json({ message: 'no session' }, 401),
    business: () => json({ ok: true }),
  }))

  await client.initialize()
  assert.equal(session.getSnapshot().status, 'UNAUTHENTICATED')
  assert.equal(session.getSnapshot().token, null)
})

test('init: an account switch during initialization is not overwritten', async () => {
  const gate = deferred()
  const { client, session } = setup(authRoutes({
    refresh: async () => {
      await gate.promise
      return json({ accessToken: 'fixture-old-result', user: actor })
    },
    business: () => json({ message: 'expired' }, 401),
  }), { token: tokenA, user: actor, status: 'INITIALIZING' })

  const initialized = client.initialize()
  await new Promise(resolve => setTimeout(resolve, 5))
  session.edit(draft => {
    draft.token = 'fixture-new'
    draft.user = { ...actor, id: 'new-user' }
    draft.authGeneration = 2
  })
  gate.resolve()
  await initialized

  assert.equal(session.getSnapshot().token, 'fixture-new', 'old refresh did not overwrite')
  assert.equal(session.getSnapshot().user.id, 'new-user')
})

// ---------------------------------------------------------------- ABA discontinuity
function abaClient() {
  const release = deferred()
  const { client, session } = setup(authRoutes({
    refresh: () => json({ accessToken: tokenY, user: actor }),
    business: async (path, options) => {
      const auth = options.headers.Authorization
      if (path === '/slow') {
        await release.promise
        return json({ ok: true, auth })
      }
      if (path === '/data') {
        return auth === `Bearer ${tokenY}` ? json({ ok: true }) : json({ message: 'expired' }, 401)
      }
      return json({ message: 'expired' }, 401)
    },
  }), { token: tokenA, user: actor, status: 'AUTHENTICATED' })
  return { client, session, release }
}

test('ABA: A -> X -> A still invalidates the pending request', async () => {
  const { client, session, release } = abaClient()
  const pending = client.request('/slow', { method: 'GET' })

  session.edit(draft => { draft.token = 'fixture-x' })   // external replacement
  session.edit(draft => { draft.token = tokenA })   // external restoration

  release.resolve()
  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
})

test('ABA: a later valid refresh cannot revalidate an obsolete scope', async () => {
  const { client, session, release } = abaClient()
  const pending = client.request('/slow', { method: 'GET' })

  session.edit(draft => { draft.token = tokenX })   // external
  await client.request('/data', { method: 'GET' })       // verified X -> Y
  assert.equal(session.getSnapshot().token, tokenY)

  release.resolve()
  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
})

test('ABA: replacement and restoration during the CSRF request rejects the refresh', async () => {
  const csrfGate = deferred()
  const { client, session } = setup(async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') {
      await csrfGate.promise
      return json({ headerName: 'X-CSRF-Token', token: 'csrf' })
    }
    if (path === '/auth/refresh') return json({ accessToken: tokenY, user: actor })
    return json({ message: 'expired' }, 401)
  }, { token: tokenA, user: actor, status: 'AUTHENTICATED' })

  const pending = client.request('/data', { method: 'GET' })
  await new Promise(resolve => setTimeout(resolve, 5))
  session.edit(draft => { draft.token = 'fixture-x' })
  session.edit(draft => { draft.token = tokenA })
  csrfGate.resolve()

  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
  assert.equal(session.getSnapshot().token, tokenA, 'no refresh result was installed')
})

test('ABA: replacement and restoration during the refresh response rejects it', async () => {
  const gate = deferred()
  const { client, session } = setup(authRoutes({
    refresh: async () => {
      await gate.promise
      return json({ accessToken: tokenY, user: actor })
    },
    business: () => json({ message: 'expired' }, 401),
  }), { token: tokenA, user: actor, status: 'AUTHENTICATED' })

  const pending = client.request('/data', { method: 'GET' })
  await new Promise(resolve => setTimeout(resolve, 5))
  session.edit(draft => { draft.token = 'fixture-x' })
  session.edit(draft => { draft.token = tokenA })
  gate.resolve()

  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
  assert.equal(session.getSnapshot().token, tokenA)
})

test('ABA: replacement and restoration before the GET retry rejects the retry', async () => {
  const delayed = deferred()
  const { client, session } = setup(authRoutes({
    refresh: () => json({ accessToken: tokenB, user: actor }),
    business: async (path, options) => {
      const auth = options.headers.Authorization
      if (path === '/late') {
        if (auth === `Bearer ${tokenB}`) return json({ ok: true })
        await delayed.promise
        return json({ message: 'expired' }, 401)
      }
      return json({ message: 'expired' }, 401)
    },
  }), { token: tokenA, user: actor, status: 'AUTHENTICATED' })

  const pending = client.request('/late', { method: 'GET' })
  await new Promise(resolve => setTimeout(resolve, 5))
  session.edit(draft => { draft.token = 'fixture-x' })   // external
  session.edit(draft => { draft.token = tokenB })   // external restore of the refreshed token
  delayed.resolve()

  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
})
