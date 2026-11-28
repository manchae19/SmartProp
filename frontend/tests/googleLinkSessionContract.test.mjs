/**
 * PR #37 <-> PR #48 shared session contract.
 *
 * PR #48 owns Google account linking and stores a server-issued JWT session identity
 * (`sub`, `jti`, `ver`) plus an `authGeneration` counter on the same session store. PR #37 owns the
 * HTTP client. This suite proves the client satisfies the shared contract using synthetic tokens
 * only - the JWT is decoded for UI continuity, never for authorization.
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { createStateStore } from '../src/shared/state/createStateStore.js'
import { createHttpClient } from '../src/shared/lib/httpClient.js'

const json = (body, status = 200) => Response.json(body, { status })
const deferred = () => {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}

/** Synthetic, unsigned JWT with the payload shape PR #48 stores. */
function fixtureToken(sub, jti, iat, ver = 0) {
  const payload = Buffer.from(JSON.stringify({
    iss: 'smartprop', sub: String(sub), jti, ver, iat,
  })).toString('base64url')
  return `eyJhbGciOiJub25lIn0.${payload}.fixture`
}

const user = (id, role = 'BUYER', status = 'ACTIVE') => ({ id, role, status })

function setup(fetcher, initial) {
  const session = createStateStore(initial)
  const client = createHttpClient({
    baseUrl: 'http://fixture.invalid',
    session,
    fetcher,
    refreshEnabled: true,
  })
  return { session, client }
}

function routes(handle) {
  return async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') return json({ headerName: 'X-CSRF-Token', token: 'csrf' })
    if (path === '/auth/refresh') return handle.refresh()
    return handle.business(path, options)
  }
}

test('contract: authGeneration participates in session identity', async () => {
  const release = deferred()
  const tokenA = fixtureToken(42, 'session-one', 1)
  const { session, client } = setup(routes({
    refresh: () => json({ accessToken: tokenA, user: user(42) }),
    business: async path => {
      if (path === '/slow') {
        await release.promise
        return json({ ok: true })
      }
      return json({ ok: true })
    },
  }), {
    token: tokenA, user: user(42), status: 'AUTHENTICATED', authGeneration: 1,
  })

  const pending = client.request('/slow', { method: 'GET' })
  // same account, new session: PR #48 bumps authGeneration and installs a new jti
  session.edit(draft => {
    draft.token = fixtureToken(42, 'session-two', 2)
    draft.authGeneration = 2
  })
  release.resolve()

  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
})

test('contract: a new jti inside the same generation is still an external replacement', async () => {
  const release = deferred()
  const tokenA = fixtureToken(7, 'session-one', 1)
  const { session, client } = setup(routes({
    refresh: () => json({ accessToken: tokenA, user: user(7) }),
    business: async path => {
      if (path === '/slow') {
        await release.promise
        return json({ ok: true })
      }
      return json({ ok: true })
    },
  }), { token: tokenA, user: user(7), status: 'AUTHENTICATED', authGeneration: 1 })

  const pending = client.request('/slow', { method: 'GET' })
  session.edit(draft => { draft.token = fixtureToken(7, 'session-two', 2) })
  release.resolve()

  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
})

test('contract: ver bump (server-authoritative role change) invalidates restricted responses', async () => {
  const release = deferred()
  const tokenA = fixtureToken(9, 'session-one', 1, 0)
  const { session, client } = setup(routes({
    refresh: () => json({ accessToken: tokenA, user: user(9) }),
    business: async path => {
      if (path === '/restricted') {
        await release.promise
        return json({ secret: true })
      }
      return json({ ok: true })
    },
  }), { token: tokenA, user: user(9, 'ADMIN'), status: 'AUTHENTICATED', authGeneration: 1 })

  const pending = client.request('/restricted', { method: 'GET' })
  // the same session, but the server demoted the account and rotated the credential with ver=1
  session.edit(draft => {
    draft.token = fixtureToken(9, 'session-one', 2, 1)
    draft.user = user(9, 'BUYER')
  })
  release.resolve()

  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
})

test('contract: a verified refresh keeps the same jti and continuity', async () => {
  const tokenA = fixtureToken(11, 'session-one', 1, 0)
  const tokenB = fixtureToken(11, 'session-one', 2, 0)
  let refreshed = 0
  const { session, client } = setup(routes({
    refresh: () => {
      refreshed += 1
      return json({ accessToken: tokenB, user: user(11) })
    },
    business: (path, options) => (options.headers.Authorization === `Bearer ${tokenB}`
      ? json({ ok: true })
      : json({ message: 'expired' }, 401)),
  }), { token: tokenA, user: user(11), status: 'AUTHENTICATED', authGeneration: 1 })

  const result = await client.request('/data', { method: 'GET' })
  assert.equal(result.ok, true)
  assert.equal(refreshed, 1)
  assert.equal(session.getSnapshot().token, tokenB)
  assert.equal(session.getSnapshot().authGeneration, 1, 'a renewal is not a new session')
})

test('contract: sessionScope exposes one bounded scope, no token history', () => {
  const tokenA = fixtureToken(5, 'session-one', 1)
  const { client } = setup(routes({
    refresh: () => json({ accessToken: tokenA, user: user(5) }),
    business: () => json({ ok: true }),
  }), { token: tokenA, user: user(5), status: 'AUTHENTICATED', authGeneration: 3 })

  const scope = client.sessionScope()
  assert.deepEqual(Object.keys(scope).sort(),
    ['authGeneration', 'authenticated', 'credentialGen', 'epoch', 'identityEpoch',
      'scopeGen'].sort())
  assert.equal(scope.authGeneration, 3)
  assert.equal(scope.authenticated, true)
  assert.equal('token' in scope, false, 'the credential must never be exposed')
  assert.equal(JSON.stringify(scope).includes('fixtureToken'), false)
})

test('contract: logout invalidates the scope and clears the credential', async () => {
  const tokenA = fixtureToken(13, 'session-one', 1)
  const release = deferred()
  const { session, client } = setup(routes({
    refresh: () => json({ accessToken: tokenA, user: user(13) }),
    business: async path => {
      if (path === '/slow') {
        await release.promise
        return json({ ok: true })
      }
      return json({ ok: true })
    },
  }), { token: tokenA, user: user(13), status: 'AUTHENTICATED', authGeneration: 1 })

  const pending = client.request('/slow', { method: 'GET' })
  session.edit(draft => {
    draft.token = null
    draft.user = null
    draft.status = 'UNAUTHENTICATED'
    draft.authGeneration = 0
  })
  release.resolve()

  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
  assert.equal(client.sessionScope().authenticated, false)
})
