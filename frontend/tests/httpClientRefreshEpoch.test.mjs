/**
 * PR #37 P2 — authentication epoch vs legitimate token refresh.
 *
 * A refreshed access token is a credential renewal inside the same session. It must not be
 * mistaken for a replaced session (which invalidates the request), and it must not make a
 * confirmed successful mutation look failed. Every case below is deterministic: responses are
 * released explicitly instead of relying on timing.
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { createStateStore } from '../src/shared/state/createStateStore.js'
import { createHttpClient } from '../src/shared/lib/httpClient.js'

const actor = { id: 'fixture-user', role: 'ADMIN', status: 'ACTIVE' }
const active = { token: 'fixture-a', user: actor, status: 'AUTHENTICATED' }
const json = (body, status = 200) => Response.json(body, { status })

const deferred = () => {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}

function setup(fetcher, options = {}) {
  const session = createStateStore({ ...active, user: { ...actor } })
  const effects = { expired: 0, cleared: 0 }
  const client = createHttpClient({
    baseUrl: 'http://fixture.invalid',
    session,
    fetcher,
    refreshEnabled: true,
    expired: () => { effects.expired += 1 },
    clear: () => { effects.cleared += 1 },
    ...options,
  })
  return { session, client, effects }
}

/** Routes auth traffic and records business-path calls. */
function makeFetcher(handle) {
  const calls = { refresh: 0, csrf: 0, business: [] }
  const fetcher = async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') {
      calls.csrf += 1
      return json({ headerName: 'X-CSRF-Token', token: 'csrf-fixture' })
    }
    if (path === '/auth/refresh') {
      calls.refresh += 1
      return json({ accessToken: 'fixture-b', user: { ...actor } })
    }
    calls.business.push({ path, method: options.method, authorization: options.headers.Authorization })
    return handle(path, options, calls)
  }
  return { fetcher, calls }
}

// ---------------------------------------------------------------- A
test('A: two concurrent GETs with a shared refresh both recover, with one refresh', async () => {
  const delayed = deferred()
  let firstOne = true

  const { fetcher, calls } = makeFetcher(async (path, options) => {
    if (options.headers.Authorization === 'Bearer fixture-b') return json({ path, ok: true })
    if (path === '/one') {
      firstOne = false
      return json({ message: 'expired' }, 401)
    }
    // the second 401 is released only after the first request finished refreshing
    await delayed.promise
    return json({ message: 'expired' }, 401)
  })

  const { client, session, effects } = setup(fetcher)
  const one = client.request('/one', { method: 'GET' })
  const two = client.request('/two', { method: 'GET' })

  await one
  delayed.resolve()
  const second = await two

  assert.equal(second.ok, true)
  assert.equal(calls.refresh, 1, 'exactly one refresh')
  assert.equal(session.getSnapshot().token, 'fixture-b')
  assert.equal(session.getSnapshot().status, 'AUTHENTICATED')
  assert.deepEqual(effects, { expired: 0, cleared: 0 }, 'no logout')
  assert.equal(firstOne, false)
})

// ---------------------------------------------------------------- B
test('B: a successful GET that completes after a legitimate refresh is not a session failure', async () => {
  const release = deferred()
  const { fetcher, calls } = makeFetcher(async (path, options) => {
    if (path === '/slow') {
      await release.promise
      return json({ path, ok: true, auth: options.headers.Authorization })
    }
    if (path === '/trigger') {
      return options.headers.Authorization === 'Bearer fixture-b'
        ? json({ ok: true })
        : json({ message: 'expired' }, 401)
    }
    return json({ message: 'expired' }, 401)
  })

  const { client, session, effects } = setup(fetcher)
  const slow = client.request('/slow', { method: 'GET' })
  await client.request('/trigger', { method: 'GET' })   // performs the refresh

  assert.equal(session.getSnapshot().token, 'fixture-b')
  release.resolve()

  const result = await slow
  assert.equal(result.ok, true)
  assert.equal(calls.refresh, 1)
  assert.deepEqual(effects, { expired: 0, cleared: 0 })
})

// ---------------------------------------------------------------- C
test('C: a confirmed successful mutation is returned even if credentials rotated', async () => {
  const release = deferred()
  const { fetcher, calls } = makeFetcher(async (path, options) => {
    if (path === '/mutation') {
      await release.promise
      return json({ path, created: true, auth: options.headers.Authorization })
    }
    if (path === '/trigger') {
      return options.headers.Authorization === 'Bearer fixture-b'
        ? json({ ok: true })
        : json({ message: 'expired' }, 401)
    }
    return json({ message: 'expired' }, 401)
  })

  const { client, session, effects } = setup(fetcher)
  const mutation = client.request('/mutation', { method: 'POST', body: { value: 1 } })
  await client.request('/trigger', { method: 'GET' })
  release.resolve()

  const result = await mutation
  assert.equal(result.created, true)
  assert.equal(session.getSnapshot().token, 'fixture-b')
  const posts = calls.business.filter(call => call.method === 'POST')
  assert.equal(posts.length, 1, 'a mutation is never replayed automatically')
  assert.equal(posts[0].authorization, 'Bearer fixture-a', 'sent with the original credentials')
  assert.deepEqual(effects, { expired: 0, cleared: 0 })
})

// ---------------------------------------------------------------- D
test('D: a POST that receives 401 still requires an explicit resubmission', async () => {
  const { fetcher, calls } = makeFetcher(async path => {
    if (path === '/mutation') return json({ message: 'expired' }, 401)
    return json({ message: 'expired' }, 401)
  })

  const { client, session, effects } = setup(fetcher)
  await assert.rejects(
    client.request('/mutation', { method: 'POST', body: {} }),
    { code: 'AUTH_RETRY_REQUIRED', sessionRecovered: true },
  )
  assert.equal(calls.refresh, 1)
  assert.equal(session.getSnapshot().token, 'fixture-b', 'session was recovered')
  assert.equal(effects.expired, 0, 'recovery is not a logout')
  assert.equal(calls.business.filter(call => call.method === 'POST').length, 1, 'no replay')
})

// ---------------------------------------------------------------- E
test('E: results from a replaced session are rejected', async () => {
  const release = deferred()
  const { fetcher } = makeFetcher(async path => {
    if (path === '/slow') {
      await release.promise
      return json({ stale: true })
    }
    return json({})
  })

  const { client, session } = setup(fetcher)
  const pending = client.request('/slow', { method: 'GET' })

  // a different account takes over the session while the request is in flight
  session.edit(draft => { draft.token = 'fixture-other'; draft.user = { ...actor, id: 'other-user' } })
  release.resolve()

  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
})

// ---------------------------------------------------------------- F
test('F: a revoked-then-restored role cannot validate a restricted response', async () => {
  const release = deferred()
  const { fetcher } = makeFetcher(async path => {
    if (path === '/restricted') {
      await release.promise
      return json({ secret: true })
    }
    return json({})
  })

  const { client, session } = setup(fetcher)
  const pending = client.request('/restricted', { method: 'GET' })

  // snapshot ends up looking exactly like the original one, but the identity did change
  session.edit(draft => { draft.user = { ...actor, role: 'USER' } })
  session.edit(draft => { draft.user = { ...actor, role: 'ADMIN' } })
  release.resolve()

  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
})

// ---------------------------------------------------------------- G
test('G: external cancellation during a shared refresh keeps abort semantics', async () => {
  const gate = deferred()
  const { fetcher } = makeFetcher(async (path, options) => {
    if (path === '/one') return json({ message: 'expired' }, 401)
    if (path === '/two') return json({ message: 'expired' }, 401)
    return json({})
  })
  const hanging = makeFetcher(async (path, options) => {
    if (options.headers['X-CSRF-Token']) { await gate.promise; return json({ accessToken: 'fixture-b', user: { ...actor } }) }
    return json({})
  })

  const controller = new AbortController()
  const { client, effects } = setup(async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') return json({ headerName: 'X-CSRF-Token', token: 'csrf-fixture' })
    if (path === '/auth/refresh') { await gate.promise; return json({ accessToken: 'fixture-b', user: { ...actor } }) }
    return json({ message: 'expired' }, 401)
  })

  const pending = client.request('/one', { method: 'GET', signal: controller.signal })
  await new Promise(resolve => setTimeout(resolve, 10))
  controller.abort()

  await assert.rejects(pending, { code: 'REQUEST_ABORTED' })
  assert.deepEqual(effects, { expired: 0, cleared: 0 })
  gate.resolve()
  void fetcher
  void hanging
})

// ---------------------------------------------------------------- role/actor boundaries
test('H: a different actor with the same token is still a different session', async () => {
  const release = deferred()
  const { fetcher } = makeFetcher(async path => {
    if (path === '/slow') {
      await release.promise
      return json({ ok: true })
    }
    return json({})
  })

  const { client, session } = setup(fetcher)
  const pending = client.request('/slow', { method: 'GET' })
  // same token, different actor: the credential is reused, the identity is not
  session.edit(draft => { draft.user = { ...actor, id: 'other-user' } })
  release.resolve()

  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
})

test('I: logout during an outstanding request rejects it and does not resurrect the token', async () => {
  const release = deferred()
  const { fetcher } = makeFetcher(async path => {
    if (path === '/slow') {
      await release.promise
      return json({ ok: true })
    }
    return json({})
  })

  const { client, session } = setup(fetcher)
  const pending = client.request('/slow', { method: 'GET' })
  session.edit(draft => { draft.token = null; draft.user = null; draft.status = 'UNAUTHENTICATED' })
  release.resolve()

  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
  assert.equal(session.getSnapshot().token, null)
})

// ---------------------------------------------------------------- verified refresh chain
test('J: a verified refresh keeps an in-flight request valid across multiple rotations', async () => {
  const release = deferred()
  let rotations = 0
  const { fetcher, calls } = makeFetcher(async (path, options) => {
    const auth = options.headers.Authorization
    if (path === '/slow') {
      await release.promise
      return json({ ok: true, auth })
    }
    if (path === '/first') {
      return auth === 'Bearer fixture-a' ? json({ message: 'expired' }, 401) : json({ ok: true, auth })
    }
    if (path === '/second') {
      return auth === 'Bearer fixture-b' ? json({ message: 'expired' }, 401) : json({ ok: true, auth })
    }
    return json({ message: 'expired' }, 401)
  })

  // refresh yields B then C, both verified by this client
  const chained = async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') return json({ headerName: 'X-CSRF-Token', token: 'csrf' })
    if (path === '/auth/refresh') {
      rotations += 1
      return json({ accessToken: rotations === 1 ? 'fixture-b' : 'fixture-c', user: { ...actor } })
    }
    return fetcher(url, options)
  }

  const { client, session, effects } = setup(chained)
  const slow = client.request('/slow', { method: 'GET' })
  await client.request('/first', { method: 'GET' })
  assert.equal(session.getSnapshot().token, 'fixture-b')
  await client.request('/second', { method: 'GET' })
  assert.equal(session.getSnapshot().token, 'fixture-c')

  release.resolve()
  const result = await slow
  assert.equal(result.auth, 'Bearer fixture-a', 'sent with the original credentials')
  void calls
  assert.equal(rotations, 2, 'two verified refreshes happened')
  assert.deepEqual(effects, { expired: 0, cleared: 0 })
})

test('K: an externally replaced token invalidates an in-flight request', async () => {
  const release = deferred()
  const { fetcher } = makeFetcher(async (path, options) => {
    if (path === '/slow') {
      await release.promise
      return json({ ok: true, auth: options.headers.Authorization })
    }
    if (path === '/trigger') {
      return options.headers.Authorization === 'Bearer fixture-b'
        ? json({ ok: true })
        : json({ message: 'expired' }, 401)
    }
    return json({ message: 'expired' }, 401)
  })

  const { client, session } = setup(fetcher)
  const slow = client.request('/slow', { method: 'GET' })
  await client.request('/trigger', { method: 'GET' })       // verified A -> B
  assert.equal(session.getSnapshot().token, 'fixture-b')

  // nobody in this client produced C: it is an arbitrary replacement
  session.edit(draft => { draft.token = 'fixture-c' })
  release.resolve()

  await assert.rejects(slow, { code: 'SESSION_CHANGED' })
})

test('L: a delayed 401 never retries with an unrelated replacement token', async () => {
  const delayed = deferred()
  const { fetcher, calls } = makeFetcher(async (path, options) => {
    if (path === '/late') {
      await delayed.promise
      return json({ message: 'expired' }, 401)
    }
    if (path === '/trigger') {
      return options.headers.Authorization === 'Bearer fixture-b'
        ? json({ ok: true })
        : json({ message: 'expired' }, 401)
    }
    return json({ message: 'expired' }, 401)
  })

  const { client, session } = setup(fetcher)
  const late = client.request('/late', { method: 'GET' })
  await client.request('/trigger', { method: 'GET' })
  session.edit(draft => { draft.token = 'fixture-c' })     // arbitrary replacement
  delayed.resolve()

  await assert.rejects(late, { code: 'SESSION_CHANGED' })
  // the delayed 401 must not have triggered another refresh
  assert.equal(calls.refresh, 1, `refresh calls: ${calls.refresh}`)
})

// ---------------------------------------------------------------- refresh operation scoping
test('M: a role revocation during a pending refresh cannot overwrite the session', async () => {
  const csrfGate = deferred()
  const refreshGate = deferred()
  const { fetcher } = makeFetcher(async (path) => {
    if (path === '/one') return json({ message: 'expired' }, 401)
    return json({ message: 'expired' }, 401)
  })

  const { client, session } = setup(async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') {
      await csrfGate.promise
      return json({ headerName: 'X-CSRF-Token', token: 'csrf' })
    }
    if (path === '/auth/refresh') {
      await refreshGate.promise
      return json({ accessToken: 'fixture-b', user: { ...actor } })
    }
    return fetcher(url, options)
  })

  const pending = client.request('/one', { method: 'GET' })
  await new Promise(resolve => setTimeout(resolve, 5))

  // revocation while the CSRF request is still pending
  session.edit(draft => { draft.user = { ...actor, role: 'USER' } })
  csrfGate.resolve()
  refreshGate.resolve()

  await assert.rejects(pending, { code: 'SESSION_CHANGED' })
  assert.equal(session.getSnapshot().user.role, 'USER', 'obsolete refresh must not restore ADMIN')
  assert.equal(session.getSnapshot().token, 'fixture-a', 'token was not rotated')
})

test('N: multiple waiters all reject when identity changes mid-refresh', async () => {
  const gate = deferred()
  const { fetcher } = makeFetcher(async (path, options) => {
    if (path === '/one' || path === '/two') return json({ message: 'expired' }, 401)
    if (path === '/trigger') {
      return options.headers.Authorization === 'Bearer fixture-b'
        ? json({ ok: true })
        : json({ message: 'expired' }, 401)
    }
    return json({ message: 'expired' }, 401)
  })

  const { client, session } = setup(async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') return json({ headerName: 'X-CSRF-Token', token: 'csrf' })
    if (path === '/auth/refresh') {
      await gate.promise
      return json({ accessToken: 'fixture-b', user: { ...actor } })
    }
    return fetcher(url, options)
  })

  const one = client.request('/one', { method: 'GET' })
  const two = client.request('/two', { method: 'GET' })
  await new Promise(resolve => setTimeout(resolve, 5))
  session.edit(draft => { draft.user = { ...actor, role: 'USER' } })
  gate.resolve()

  const outcomes = await Promise.allSettled([one, two])
  assert.equal(outcomes.every(item => item.status === 'rejected'), true)
  assert.equal(session.getSnapshot().user.role, 'USER')
})

test('O: a new session does not join an obsolete refresh flight', async () => {
  const gate = deferred()
  let refreshes = 0
  const { client, session } = setup(async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') return json({ headerName: 'X-CSRF-Token', token: 'csrf' })
    if (path === '/auth/refresh') {
      refreshes += 1
      await gate.promise
      return json({ accessToken: 'fixture-b', user: { ...actor } })
    }
    if (path === '/one') return json({ message: 'expired' }, 401)
    if (path === '/two') {
      // the new session starts fresh: its first call is unauthenticated for the new token
      return options.headers.Authorization === 'Bearer fixture-new'
        ? json({ message: 'expired' }, 401)
        : json({ message: 'expired' }, 401)
    }
    return json({ message: 'expired' }, 401)
  })

  const first = client.request('/one', { method: 'GET' })
  await new Promise(resolve => setTimeout(resolve, 5))

  // a different account signs in while the old refresh is still pending
  session.edit(draft => { draft.token = 'fixture-new'; draft.user = { ...actor, id: 'new-user' } })
  const second = client.request('/two', { method: 'GET' })

  gate.resolve()
  await assert.rejects(first, { code: 'SESSION_CHANGED' })
  await assert.rejects(second)
  assert.equal(refreshes, 2, 'the obsolete flight was not reused')
})
