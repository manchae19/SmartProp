import test from 'node:test';
import assert from 'node:assert/strict';
import { createHttpClient } from '../src/shared/lib/httpClient.js';
import { createStateStore } from '../src/shared/state/createStateStore.js';
import { errorText } from '../src/features/auth/api.js';

test('refresh restores SmartProp JWT after OAuth redirect before linking completion', async () => {
  const session = createStateStore({ token: null, user: null, status: 'INITIALIZING', error: null });
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith('/auth/csrf')) return json({ token: 'csrf-test', headerName: 'X-CSRF-TOKEN' });
    if (url.endsWith('/auth/refresh')) return json({ accessToken: 'fresh-access-token', tokenType: 'Bearer', expiresIn: 300, user: { id: 41 } });
    if (url.endsWith('/auth/google/link/complete')) return json({ linked: true });
    throw new Error('Unexpected endpoint');
  };
  const client = createHttpClient({ baseUrl: '/api/v1', session, refreshEnabled: true, fetcher, activity: () => true });

  await client.initialize({ force: true });
  const csrf = await client.request('/auth/csrf', { authenticated: false });
  const result = await client.request('/auth/google/link/complete', {
    method: 'POST',
    headers: { [csrf.headerName]: csrf.token }
  });

  assert.deepEqual(result, { linked: true });
  assert.equal(session.getSnapshot().token, 'fresh-access-token');
  const completion = calls.find(call => call.url.endsWith('/auth/google/link/complete'));
  assert.equal(completion.options.headers.Authorization, 'Bearer fresh-access-token');
  assert.equal(completion.options.headers['X-CSRF-TOKEN'], 'csrf-test');
  assert.equal(completion.options.credentials, 'include');
  assert.equal(calls.some(call => call.url.endsWith('/auth/oauth2/complete')), false);
});

test('wrong linking password keeps the current session and does not start OAuth', async () => {
  const session = createStateStore({ token: 'valid-access-token', user: { id: 42 }, status: 'AUTHENTICATED', error: null });
  const calls = [];
  let clearCount = 0;
  let expiredCount = 0;
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith('/auth/csrf')) return json({ token: 'csrf-test', headerName: 'X-CSRF-TOKEN' });
    if (url.endsWith('/auth/google/link/start')) {
      return failure(400, { code: 'WRONG_PASSWORD', message: 'Mật khẩu hiện tại không chính xác' });
    }
    throw new Error('Unexpected endpoint');
  };
  const client = createHttpClient({
    baseUrl: '/api/v1', session, refreshEnabled: true, fetcher,
    clear: () => clearCount++, expired: () => expiredCount++, activity: () => true
  });

  const csrf = await client.request('/auth/csrf', { authenticated: false });
  let receivedError;
  await assert.rejects(client.request('/auth/google/link/start', {
    method: 'POST', body: { currentPassword: 'wrong' },
    headers: { [csrf.headerName]: csrf.token }
  }), error => {
    receivedError = error;
    return error.status === 400 && error.code === 'WRONG_PASSWORD'
      && error.message === 'Mật khẩu hiện tại không chính xác';
  });
  assert.equal(errorText(receivedError), 'Mật khẩu hiện tại không chính xác');

  assert.equal(session.getSnapshot().token, 'valid-access-token');
  assert.deepEqual(session.getSnapshot().user, { id: 42 });
  assert.equal(session.getSnapshot().status, 'AUTHENTICATED');
  assert.equal(clearCount, 0);
  assert.equal(expiredCount, 0);
  assert.equal(calls.some(call => call.url.endsWith('/auth/refresh')), false);
  assert.equal(calls.some(call => call.url.endsWith('/auth/logout')), false);
  assert.equal(calls.some(call => call.url.includes('/auth/oauth2/link/authorize/google')), false);
  assert.equal(calls.find(call => call.url.endsWith('/auth/google/link/start')).options.credentials, 'include');
});

test('a real unauthenticated linking request still expires the invalid session', async () => {
  const session = createStateStore({ token: 'invalid-access-token', user: { id: 42 }, status: 'AUTHENTICATED', error: null });
  const calls = [];
  let clearCount = 0;
  let expiredCount = 0;
  const fetcher = async (url, options) => {
    calls.push({ url, options });
    return failure(401, { code: 'UNAUTHENTICATED', message: 'Phiên đã hết hạn hoặc bị thu hồi.' });
  };
  const client = createHttpClient({
    baseUrl: '/api/v1', session, refreshEnabled: true, fetcher,
    clear: () => clearCount++, expired: () => expiredCount++
  });

  await assert.rejects(client.request('/auth/google/link/start', { method: 'POST', body: { currentPassword: 'test' } }),
    error => error.status === 401 && error.code === 'UNAUTHENTICATED');

  assert.equal(session.getSnapshot().token, null);
  assert.equal(session.getSnapshot().user, null);
  assert.equal(session.getSnapshot().status, 'UNAUTHENTICATED');
  assert.equal(clearCount, 1);
  assert.equal(expiredCount, 1);
  assert.equal(calls.some(call => call.url.endsWith('/auth/refresh')), false);
});

function json(body) {
  return {
    ok: true,
    status: 200,
    headers: new Headers({ 'Content-Type': 'application/json' }),
    json: async () => body
  };
}

function failure(status, body) {
  return {
    ok: false,
    status,
    headers: new Headers({ 'Content-Type': 'application/json' }),
    json: async () => body
  };
}
