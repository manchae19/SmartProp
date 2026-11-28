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
import { sessionJwt } from './fixtures/sessionJwt.mjs'

const actor = { id: 'fixture-user', role: 'ADMIN', status: 'ACTIVE' }
const tokenA = sessionJwt(actor.id, 'main-fixture-session', 1)
const tokenB = sessionJwt(actor.id, 'main-fixture-session', 2)
const tokenC = sessionJwt(actor.id, 'main-fixture-session', 3)
const newStart = sessionJwt('new-user', 'new-fixture-session', 1)
const newResultToken = sessionJwt('new-user', 'new-fixture-session', 2)
const active = { token: tokenA, user: actor, status: 'AUTHENTICATED' }
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
      return json({ accessToken: tokenB, user: { ...actor } })
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
    if (options.headers.Authorization === `Bearer ${tokenB}`) return json({ path, ok: true })
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
  assert.equal(session.getSnapshot().token, tokenB)
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
      return options.headers.Authorization === `Bearer ${tokenB}`
        ? json({ ok: true })
        : json({ message: 'expired' }, 401)
    }
    return json({ message: 'expired' }, 401)
  })

  const { client, session, effects } = setup(fetcher)
  const slow = client.request('/slow', { method: 'GET' })
  await client.request('/trigger', { method: 'GET' })   // performs the refresh

  assert.equal(session.getSnapshot().token, tokenB)
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
      return options.headers.Authorization === `Bearer ${tokenB}`
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
  assert.equal(session.getSnapshot().token, tokenB)
  const posts = calls.business.filter(call => call.method === 'POST')
  assert.equal(posts.length, 1, 'a mutation is never replayed automatically')
  assert.equal(posts[0].authorization, `Bearer ${tokenA}`, 'sent with the original credentials')
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
  assert.equal(session.getSnapshot().token, tokenB, 'session was recovered')
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
    if (options.headers['X-CSRF-Token']) { await gate.promise; return json({ accessToken: tokenB, user: { ...actor } }) }
    return json({})
  })

  const controller = new AbortController()
  const { client, effects } = setup(async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') return json({ headerName: 'X-CSRF-Token', token: 'csrf-fixture' })
    if (path === '/auth/refresh') { await gate.promise; return json({ accessToken: tokenB, user: { ...actor } }) }
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
test('J: pending requests started at generation B survive a B->C refresh', async () => {
  // Login installs A, A->B is a verified refresh, then requests are started with B and must keep
  // working across B->C. This is the case the old verifiedTokens Set broke.
  const releaseGet = deferred()
  const releasePost = deferred()
  const issued = [tokenB, tokenC]
  const business = []

  const { client, session, effects } = setup(async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') return json({ headerName: 'X-CSRF-Token', token: 'csrf' })
    if (path === '/auth/refresh') return json({ accessToken: issued.shift(), user: { ...actor } })
    const auth = options.headers.Authorization
    if (path === '/slow-get') {
      business.push({ path, method: 'GET', auth })
      await releaseGet.promise
      return json({ ok: true, auth })
    }
    if (path === '/slow-post') {
      business.push({ path, method: 'POST', auth })
      await releasePost.promise
      return json({ created: true, auth })
    }
    if (path === '/trigger-one') {
      return auth === `Bearer ${tokenB}` ? json({ ok: true }) : json({ message: 'expired' }, 401)
    }
    if (path === '/trigger-two') {
      return auth === `Bearer ${tokenC}` ? json({ ok: true }) : json({ message: 'expired' }, 401)
    }
    return json({ message: 'expired' }, 401)
  })

  await client.request('/trigger-one', { method: 'GET' })     // A -> B
  assert.equal(session.getSnapshot().token, tokenB)

  const pendingGet = client.request('/slow-get', { method: 'GET' })
  const pendingPost = client.request('/slow-post', { method: 'POST', body: {} })

  await client.request('/trigger-two', { method: 'GET' })     // B -> C
  assert.equal(session.getSnapshot().token, tokenC)

  releaseGet.resolve()
  releasePost.resolve()

  const getResult = await pendingGet
  const postResult = await pendingPost
  assert.equal(getResult.auth, `Bearer ${tokenB}`, 'GET kept its original credentials')
  assert.equal(postResult.created, true)
  assert.equal(postResult.auth, `Bearer ${tokenB}`, 'POST kept its original credentials')
  assert.equal(business.filter(call => call.method === 'POST').length, 1, 'no POST replay')
  assert.deepEqual(effects, { expired: 0, cleared: 0 }, 'no logout')
  assert.equal(session.getSnapshot().status, 'AUTHENTICATED')
})

test('J2: a delayed 401 from generation B after C is installed still recovers', async () => {
  const delayed = deferred()
  const issued = [tokenB, tokenC]
  let refreshes = 0

  const { client, session, effects } = setup(async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') return json({ headerName: 'X-CSRF-Token', token: 'csrf' })
    if (path === '/auth/refresh') {
      refreshes += 1
      return json({ accessToken: issued.shift(), user: { ...actor } })
    }
    const auth = options.headers.Authorization
    if (path === '/late') {
      if (auth === `Bearer ${tokenC}`) return json({ ok: true, auth })
      await delayed.promise
      return json({ message: 'expired' }, 401)
    }
    if (path === '/trigger-one') {
      return auth === `Bearer ${tokenB}` ? json({ ok: true }) : json({ message: 'expired' }, 401)
    }
    if (path === '/trigger-two') {
      return auth === `Bearer ${tokenC}` ? json({ ok: true }) : json({ message: 'expired' }, 401)
    }
    if (path === '/late-retry') return json({ ok: true, auth })
    return json({ message: 'expired' }, 401)
  })

  await client.request('/trigger-one', { method: 'GET' })       // A -> B
  const lateRequest = client.request('/late', { method: 'GET' }) // started at B
  await client.request('/trigger-two', { method: 'GET' })        // B -> C
  delayed.resolve()

  const result = await lateRequest
  assert.equal(result.ok, true)
  assert.equal(refreshes, 2, 'the delayed 401 must not start a third refresh')
  assert.deepEqual(effects, { expired: 0, cleared: 0 })
  assert.equal(session.getSnapshot().token, tokenC)
})

test('K: an externally replaced token invalidates an in-flight request', async () => {
  const release = deferred()
  const { fetcher } = makeFetcher(async (path, options) => {
    if (path === '/slow') {
      await release.promise
      return json({ ok: true, auth: options.headers.Authorization })
    }
    if (path === '/trigger') {
      return options.headers.Authorization === `Bearer ${tokenB}`
        ? json({ ok: true })
        : json({ message: 'expired' }, 401)
    }
    return json({ message: 'expired' }, 401)
  })

  const { client, session } = setup(fetcher)
  const slow = client.request('/slow', { method: 'GET' })
  await client.request('/trigger', { method: 'GET' })       // verified A -> B
  assert.equal(session.getSnapshot().token, tokenB)

  // nobody in this client produced C: it is an arbitrary replacement
  session.edit(draft => { draft.token = tokenC })
  release.resolve()

  await assert.rejects(slow, { code: 'SESSION_CHANGED' })
})

test('L: a delayed 401 never retries with an unrelated replacement token', async () => {
  const delayed = deferred()
  let refreshes = 0

  const { client, session } = setup(async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') return json({ headerName: 'X-CSRF-Token', token: 'csrf' })
    if (path === '/auth/refresh') {
      refreshes += 1
      return json({ accessToken: tokenB, user: { ...actor } })
    }
    const auth = options.headers.Authorization
    if (path === '/late') {
      if (auth === `Bearer ${tokenB}`) return json({ ok: true, auth })
      await delayed.promise
      return json({ message: 'expired' }, 401)
    }
    if (path === '/trigger') {
      return auth === `Bearer ${tokenB}` ? json({ ok: true }) : json({ message: 'expired' }, 401)
    }
    return json({ message: 'expired' }, 401)
  })

  const late = client.request('/late', { method: 'GET' })
  await client.request('/trigger', { method: 'GET' })        // verified A -> B
  session.edit(draft => { draft.token = tokenC })       // arbitrary replacement
  delayed.resolve()

  await assert.rejects(late, { code: 'SESSION_CHANGED' })
  assert.equal(refreshes, 1, 'the delayed 401 must not start another refresh')
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
      return json({ accessToken: tokenB, user: { ...actor } })
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
  assert.equal(session.getSnapshot().token, tokenA, 'token was not rotated')
})

test('N: multiple waiters all reject when identity changes mid-refresh', async () => {
  const gate = deferred()
  const { fetcher } = makeFetcher(async (path, options) => {
    if (path === '/one' || path === '/two') return json({ message: 'expired' }, 401)
    if (path === '/trigger') {
      return options.headers.Authorization === `Bearer ${tokenB}`
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
      return json({ accessToken: tokenB, user: { ...actor } })
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

test('O: an obsolete refresh cannot overwrite a new session, and the new one recovers', async () => {
  const oldGate = deferred()
  const newGate = deferred()
  const oldActor = { ...actor, id: 'old-user', role: 'ADMIN' }
  const newActor = { ...actor, id: 'new-user', role: 'BROKER' }
  let refreshes = 0

  const { client, session } = setup(async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') return json({ headerName: 'X-CSRF-Token', token: 'csrf' })
    if (path === '/auth/refresh') {
      refreshes += 1
      // the first refresh belongs to the old session and answers late with the old actor
      if (refreshes === 1) {
        await oldGate.promise
        return json({ accessToken: 'fixture-old-result', user: oldActor })
      }
      await newGate.promise
      return json({ accessToken: newResultToken, user: newActor })
    }
    const auth = options.headers.Authorization
    if (path === '/old') return json({ message: 'expired' }, 401)
    if (path === '/new') {
      return auth === `Bearer ${newResultToken}`
        ? json({ ok: true, auth })
        : json({ message: 'expired' }, 401)
    }
    return json({ message: 'expired' }, 401)
  })

  const oldRequest = client.request('/old', { method: 'GET' })   // starts the old flight
  await new Promise(resolve => setTimeout(resolve, 5))

  // a different account signs in while the old refresh is pending
  session.edit(draft => { draft.token = newStart; draft.user = newActor })
  const newRequest = client.request('/new', { method: 'GET' })   // starts its own flight

  oldGate.resolve()                                              // old flight finishes first
  await assert.rejects(oldRequest, { code: 'SESSION_CHANGED' })

  newGate.resolve()
  const recovered = await newRequest

  assert.equal(recovered.ok, true, 'the new session request recovers instead of being rejected')
  assert.equal(recovered.auth, `Bearer ${newResultToken}`)
  assert.equal(refreshes, 2)
  assert.equal(session.getSnapshot().user.id, 'new-user')
  assert.equal(session.getSnapshot().token, newResultToken)
})

test('P: only the owning refresh flight clears the shared reference', async () => {
  const oldGate = deferred()
  const newGate = deferred()
  const oldActor = { ...actor, id: 'old-user' }
  const newActor = { ...actor, id: 'new-user', role: 'BROKER' }
  let refreshes = 0

  const { client, session } = setup(async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') return json({ headerName: 'X-CSRF-Token', token: 'csrf' })
    if (path === '/auth/refresh') {
      refreshes += 1
      if (refreshes === 1) {
        await oldGate.promise
        return json({ accessToken: 'fixture-old-result', user: oldActor })
      }
      await newGate.promise
      return json({ accessToken: newResultToken, user: newActor })
    }
    const auth = options.headers.Authorization
    if (path === '/new-request' || path === '/join') {
      return auth === `Bearer ${newResultToken}`
        ? json({ ok: true, auth })
        : json({ message: 'expired' }, 401)
    }
    return json({ message: 'expired' }, 401)
  })

  const oldRequest = client.request('/old-request', { method: 'GET' })
  await new Promise(resolve => setTimeout(resolve, 5))

  session.edit(draft => { draft.token = newStart; draft.user = newActor })
  const newRequest = client.request('/new-request', { method: 'GET' })
  await new Promise(resolve => setTimeout(resolve, 5))
  const joined = client.request('/join', { method: 'GET' })   // must join the new flight

  oldGate.resolve()                                          // old flight finishes first
  await assert.rejects(oldRequest, { code: 'SESSION_CHANGED' })

  newGate.resolve()
  const newResult = await newRequest
  const joinedResult = await joined

  assert.equal(newResult.ok, true)
  assert.equal(joinedResult.ok, true, 'the third request joined the surviving flight')
  assert.equal(refreshes, 2, 'exactly one refresh for the new session')
  assert.equal(session.getSnapshot().token, newResultToken)
  assert.equal(session.getSnapshot().user.id, 'new-user')
})

test('Q: renewing an authenticated session cannot install another account', async () => {
  const { client, session } = setup(async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') return json({ headerName: 'X-CSRF-Token', token: 'csrf' })
    if (path === '/auth/refresh') {
      return json({ accessToken: tokenB, user: { ...actor, id: 'someone-else' } })
    }
    return json({ message: 'expired' }, 401)
  })

  await assert.rejects(client.request('/one', { method: 'GET' }), { code: 'SESSION_CHANGED' })
  assert.equal(session.getSnapshot().token, null, 'the old scope was retired without installing the foreign credential')
  assert.equal(session.getSnapshot().user, null)
})

test('R: continuity survives many rotations without retaining history', async () => {
  const release = deferred()
  let refreshes = 0
  let triggerCalls = 0
  const { client, session } = setup(async (url, options) => {
    const path = new URL(url).pathname
    if (path === '/auth/csrf') return json({ headerName: 'X-CSRF-Token', token: 'csrf' })
    if (path === '/auth/refresh') {
      refreshes += 1
      return json({ accessToken: sessionJwt(actor.id, 'main-fixture-session', 100 + refreshes), user: { ...actor } })
    }
    const auth = options.headers.Authorization
    if (path === '/slow') {
      await release.promise
      return json({ ok: true, auth })
    }
    if (path === '/trigger') {
      // first attempt of every call is rejected, the retry succeeds: exactly one rotation per call
      triggerCalls += 1
      if (triggerCalls % 2 === 1) return json({ message: 'expired' }, 401)
      return json({ ok: true, auth })
    }
    return json({ message: 'expired' }, 401)
  })

  const slow = client.request('/slow', { method: 'GET' })
  for (let step = 0; step < 5; step += 1) {
    await client.request('/trigger', { method: 'GET' })
  }
  assert.equal(refreshes, 5)
  assert.equal(session.getSnapshot().token, sessionJwt(actor.id, 'main-fixture-session', 105))

  release.resolve()
  const result = await slow
  assert.equal(result.auth, `Bearer ${tokenA}`, 'the original request kept its credentials')
})
