import { createStateStore } from "../../shared/state/createStateStore.js";
import { createHttpClient } from '../../shared/lib/httpClient.js';
export const session = createStateStore({
  token: null,
  user: null,
  status: 'INITIALIZING',
  error: null,
  authGeneration: 0,
  authTransition: false
});
export const refreshEnabled = import.meta.env?.VITE_ENABLE_REFRESH === 'true';
const baseUrl = (import.meta.env?.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');
function clearLegacyCredentials() {
  globalThis.localStorage?.removeItem('token');
  globalThis.localStorage?.removeItem('role');
}
clearLegacyCredentials();
let activityPending = true;
if (typeof window !== 'undefined') {
  for (const event of ['pointerdown', 'keydown']) window.addEventListener(event, e => {
    if (e.isTrusted) activityPending = true;
  }, {
    passive: true
  });
}
const activity = () => {
  const pending = activityPending;
  activityPending = false;
  return pending;
};
const client = createHttpClient({
  baseUrl,
  session,
  refreshEnabled,
  clear: clearLegacyCredentials,
  expired: () => window.dispatchEvent(new Event('smartprop:session-expired')),
  activity,
  lock: globalThis.navigator?.locks ? run => navigator.locks.request('smartprop-refresh', run) : null
});
export const clearSession = () => client.clearSession();
// Cross-tab messages carry only the action. Tabs restore credentials through the server cookie.
const channel = typeof window !== 'undefined' && window.location && typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('smartprop-session') : null;
if (channel) channel.onmessage = e => {
  if (e.data === 'logout') {
    clearSession();
    window.dispatchEvent(new Event('smartprop:session-expired'));
  } else if (e.data === 'login' && refreshEnabled) {
    clearSession();
    void client.initialize({ force: true });
  }
};
export const api = (path, options) => client.request(path, options);
export const restoreSession = () => client.restore();
export const initializeAuth = options => client.initialize(options);
export const authUnavailable = error => client.unavailable(error);
export function errorText(error) {
  if (error.status === 503 && ['FEATURE_DISABLED', 'FEATURE_UNAVAILABLE'].includes(error.code)) return 'Tính năng chưa được bật trên máy chủ. Vui lòng liên hệ quản trị viên.';
  return [error.message, ...Object.entries(error.fields || {}).map(([key, value]) => key + ': ' + value)].join(' — ');
}
export async function login(email, password, rememberMe = false) {
  const value = email.trim(),
    result = await client.login({
      email: value.toLowerCase() === 'admin' ? 'admin@smartprop.local' : value,
      password,
      rememberMe
    });
  channel?.postMessage("login");
  return result.user;
}
export const register = body => api('/auth/register', {
  method: 'POST',
  body: {
    ...body,
    email: body.email.trim()
  },
  authenticated: false
});
export async function loadProfile() {
  const generation = session.getSnapshot().authGeneration;
  const user = await api('/users/me');
  if (generation !== session.getSnapshot().authGeneration) throw sessionChanged();
  session.edit(draft => { draft.user = user; });
  return user;
}
export async function logout() {
  await client.logout();
  channel?.postMessage('logout');
}
export async function completeGoogleLogin() {
  const result = await client.google();
  channel?.postMessage("login");
  return result.user;
}
export function getGoogleLinkScope(snapshot = session.getSnapshot()) {
  return snapshot.status === 'AUTHENTICATED' && !snapshot.authTransition
    && snapshot.token && snapshot.user?.id != null
    && (!snapshot.user.status || snapshot.user.status === 'ACTIVE')
    ? snapshot.authGeneration : null;
}

function sessionChanged() {
  return Object.assign(Error('Phiên đăng nhập đã thay đổi. Vui lòng thực hiện lại.'), { code: 'SESSION_CHANGED' });
}

export function assertGoogleLinkScope(scope) {
  if (scope == null || scope !== getGoogleLinkScope()) throw sessionChanged();
}

async function requestGoogleLink(path, scope, method, body) {
  assertGoogleLinkScope(scope);
  try {
    let options;
    if (method === 'POST') {
      const csrf = await api('/auth/csrf', { authenticated: false });
      assertGoogleLinkScope(scope);
      options = { method, body, headers: { [csrf.headerName]: csrf.token } };
    }
    const result = await api(path, options);
    assertGoogleLinkScope(scope);
    return result;
  } catch (error) {
    assertGoogleLinkScope(scope);
    throw error;
  }
}

export const googleLinkStatus = scope => requestGoogleLink('/auth/google/link/status', scope);
export function startGoogleLink(currentPassword, scope) {
  if (!refreshEnabled) throw Object.assign(Error('Phiên làm mới đăng nhập chưa được bật ở frontend. Vui lòng cấu hình VITE_ENABLE_REFRESH=true rồi tải lại trang.'), { code: 'FEATURE_DISABLED' });
  return requestGoogleLink('/auth/google/link/start', scope, 'POST', { currentPassword });
}
export const completeGoogleLink = scope => requestGoogleLink('/auth/google/link/complete', scope, 'POST');
