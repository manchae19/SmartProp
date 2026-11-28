import test from 'node:test';
import assert from 'node:assert/strict';
import { createHttpClient } from '../src/shared/lib/httpClient.js';
import { createStateStore } from '../src/shared/state/createStateStore.js';
import { getGoogleLinkScope } from '../src/features/auth/api.js';
import { sessionJwt } from './fixtures/sessionJwt.mjs';

const user = { id: 42, role: 'ADMIN', status: 'ACTIVE' };
const a = sessionJwt(42, 'session', 1);
const b = sessionJwt(42, 'session', 2);
const c = sessionJwt(42, 'session', 3);
const json = (body = {}, status = 200) => Response.json(body, { status });
const unauthorized = () => json({ code: 'UNAUTHENTICATED' }, 401);
const csrf = () => json({ token: 'fixture', headerName: 'X-CSRF-TOKEN' });
const deferred = () => {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
};
const setup = (fetcher, token = a, lock = null) => {
  let expired = 0;
  const session = createStateStore({ token, user, status: 'AUTHENTICATED', authGeneration: 4 });
  const client = createHttpClient({
    baseUrl: '', session, fetcher, lock, refreshEnabled: true, expired: () => expired++
  });
  return { session, client, expired: () => expired };
};

test('opaque or malformed renewal retires the old scope; initialization may adopt a new cookie session', { timeout: 3000 }, async () => {
  const badHeader = 'bm90LWpzb24.' + a.split('.').slice(1).join('.');
  for (const original of ['opaque', a + '.extra', badHeader, a]) {
    const firstPending = deferred();
    const next = sessionJwt(42, 'cookie-session', 5);
    let refresh = 0;
    let oldCalls = 0;
    const { client, session } = setup(async path => {
      if (path === '/auth/google/link/status') {
        oldCalls++;
        return firstPending.promise;
      }
      if (path === '/auth/csrf') return csrf();
      if (path === '/auth/refresh') return json({ user, accessToken: ++refresh === 1 ? 'opaque-result' : next });
      return unauthorized();
    }, original);
    const old = assert.rejects(client.request('/auth/google/link/status'), { code: 'SESSION_CHANGED' });
    await assert.rejects(client.request('/trigger'), { code: 'SESSION_CHANGED' });
    assert.equal(getGoogleLinkScope(session.getSnapshot()), null);
    assert.equal(session.getSnapshot().token, null);
    assert.equal(refresh, 1);
    firstPending.resolve(json({ linked: true }));
    await old;
    assert.equal(oldCalls, 1);
    assert.equal(await client.initialize(), 'AUTHENTICATED');
    assert.equal(session.getSnapshot().token, next);
    assert.notEqual(getGoogleLinkScope(session.getSnapshot()), 4);
    assert.equal(refresh, 2);
  }
});

test('server ver and role reissues invalidate pending restricted results and publish current authority', { timeout: 3000 }, async () => {
  for (const nextUser of [user, { ...user, role: 'USER' }]) {
    const pending = deferred();
    const reissued = sessionJwt(42, 'session', 2, 1);
    const { client, session } = setup(async path => {
      if (path === '/restricted') return pending.promise;
      if (path === '/auth/csrf') return csrf();
      if (path === '/auth/refresh') return json({ user: nextUser, accessToken: reissued });
      return unauthorized();
    });
    const stale = assert.rejects(client.request('/restricted'), { code: 'SESSION_CHANGED' });
    await assert.rejects(client.request('/trigger'), { code: 'SESSION_CHANGED' });
    assert.equal(session.getSnapshot().token, reissued);
    assert.equal(session.getSnapshot().user.role, nextUser.role);
    assert.notEqual(getGoogleLinkScope(session.getSnapshot()), 4);
    pending.resolve(json({ restricted: true }));
    await stale;
  }
});

test('external credential ABA and same-token authority changes retire captured linking generations', async () => {
  const { session } = setup(async () => json());
  session.edit(draft => { draft.token = b; });
  session.edit(draft => { draft.token = a; });
  const restored = getGoogleLinkScope(session.getSnapshot());
  assert.notEqual(restored, 4);
  session.edit(draft => { draft.user.role = 'USER'; });
  session.edit(draft => { draft.user.role = 'ADMIN'; });
  assert.notEqual(getGoogleLinkScope(session.getSnapshot()), restored);
});

test('overlapping login, logout, Google completion and refresh preserve only the latest owner', { timeout: 3000 }, async () => {
  const refreshSent = deferred();
  const refreshResponse = deferred();
  const loginResponse = deferred();
  const logoutSent = deferred();
  const logoutResponse = deferred();
  const googleSent = deferred();
  const googleResponse = deferred();
  const googleToken = sessionJwt(42, 'google', 4);
  const { client, session } = setup(async path => {
    if (path === '/auth/csrf') return csrf();
    if (path === '/auth/refresh') {
      refreshSent.resolve();
      return refreshResponse.promise;
    }
    if (path === '/auth/login') return loginResponse.promise;
    if (path === '/auth/logout') {
      logoutSent.resolve();
      return logoutResponse.promise;
    }
    if (path === '/auth/oauth2/complete') {
      googleSent.resolve();
      return googleResponse.promise;
    }
    return unauthorized();
  });
  const refresh = assert.rejects(client.request('/trigger'), { code: 'SESSION_CHANGED' });
  await refreshSent.promise;
  const login = assert.rejects(client.login({}), { code: 'SESSION_CHANGED' });
  assert.equal(session.getSnapshot().authTransition, true);
  const logout = assert.rejects(client.logout(), { code: 'SESSION_CHANGED' });
  await logoutSent.promise;
  const google = client.google();
  await googleSent.promise;
  const owner = session.getSnapshot().authGeneration;
  await assert.rejects(client.request('/restricted'), { code: 'SESSION_CHANGED' });

  refreshResponse.resolve(json({ user, accessToken: b }));
  loginResponse.resolve(json({ user, accessToken: c }));
  logoutResponse.resolve(new Response(null, { status: 204 }));
  await Promise.all([refresh, login, logout]);
  assert.equal(getGoogleLinkScope(session.getSnapshot()), null);
  assert.equal(session.getSnapshot().authTransition, true);
  assert.equal(session.getSnapshot().authGeneration, owner);
  googleResponse.resolve(json({ user, accessToken: googleToken }));
  await google;
  assert.equal(session.getSnapshot().token, googleToken);
  assert.equal(session.getSnapshot().authTransition, false);
  assert.equal(getGoogleLinkScope(session.getSnapshot()), owner);
});

test('failed login keeps old transport responses retired even after the transition ends', { timeout: 3000 }, async () => {
  const loginResponse = deferred();
  const oldStatus = deferred();
  const { client, session } = setup(path => path === '/auth/login' ? loginResponse.promise : oldStatus.promise);
  const pending = assert.rejects(client.request('/auth/google/link/status'), { code: 'SESSION_CHANGED' });
  const failed = assert.rejects(client.login({}), { code: 'INVALID_CREDENTIALS' });
  assert.equal(getGoogleLinkScope(session.getSnapshot()), null);
  loginResponse.resolve(json({ code: 'INVALID_CREDENTIALS' }, 401));
  await failed;
  assert.equal(session.getSnapshot().token, a);
  assert.notEqual(getGoogleLinkScope(session.getSnapshot()), 4);
  oldStatus.resolve(json({ linked: true }));
  await pending;
});

test('late linking write is never replayed and a second late GET 401 leaves newer credentials intact', { timeout: 3000 }, async () => {
  const sentByA = deferred();
  const sentByB = deferred();
  const write = deferred();
  let refreshes = 0;
  let writes = 0;
  const { client, session, expired } = setup(async (path, options) => {
    const bearer = options.headers.Authorization;
    if (path === '/auth/google/link/status') return bearer === 'Bearer ' + a ? sentByA.promise : sentByB.promise;
    if (path === '/auth/google/link/complete') {
      writes++;
      return write.promise;
    }
    if (path === '/auth/csrf') return csrf();
    if (path === '/auth/refresh') return json({ user, accessToken: ++refreshes === 1 ? b : c });
    const expected = path === '/first' ? b : c;
    return bearer === 'Bearer ' + expected ? json() : unauthorized();
  });
  const get = assert.rejects(client.request('/auth/google/link/status'), { code: 'UNAUTHENTICATED' });
  const post = assert.rejects(client.request('/auth/google/link/complete', { method: 'POST' }), { code: 'AUTH_RETRY_REQUIRED' });
  await client.request('/first');
  sentByA.resolve(unauthorized());
  write.resolve(unauthorized());
  await post;
  await client.request('/second');
  sentByB.resolve(unauthorized());
  await get;
  assert.equal(session.getSnapshot().token, c);
  assert.equal(expired(), 0);
  assert.equal(writes, 1);
  assert.equal(refreshes, 2);
});
