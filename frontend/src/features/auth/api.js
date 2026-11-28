import { createStateStore } from "../../shared/state/createStateStore.js";
import { createHttpClient } from '../../shared/lib/httpClient.js';
export const session = createStateStore({
  token: null,
  user: null,
  status: 'INITIALIZING',
  error: null
});
export const refreshEnabled = import.meta.env?.VITE_ENABLE_REFRESH === 'true';
const baseUrl = (import.meta.env?.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');
let client;
export function clearSession() {
  client?.invalidate();
  session.edit(draftValue => draftValue["token"] = null);
  session.edit(draftValue => draftValue["user"] = null);
  session.edit(draftValue => draftValue["status"] = 'UNAUTHENTICATED');
  session.edit(draftValue => draftValue["error"] = null);
  globalThis.localStorage?.removeItem('token');
  globalThis.localStorage?.removeItem('role');
}
globalThis.localStorage?.removeItem('token');
globalThis.localStorage?.removeItem('role');
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
client = createHttpClient({
  baseUrl,
  session,
  refreshEnabled,
  clear: clearSession,
  expired: () => window.dispatchEvent(new Event('smartprop:session-expired')),
  activity,
  lock: globalThis.navigator?.locks ? run => navigator.locks.request('smartprop-refresh', run) : null
});
// Cross-tab logout sends no credentials, token or profile. Web Locks serializes cookie rotation.
const channel = typeof window !== 'undefined' && window.location && typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('smartprop-session') : null;
if (channel) channel.onmessage = e => {
  if (e.data === 'logout') {
    clearSession();
    window.dispatchEvent(new Event('smartprop:session-expired'));
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
  session.edit((resolvedValue => draftValue => draftValue["user"] = resolvedValue)(await api('/users/me')));
  return session.getSnapshot().user;
}
export async function logout() {
  await client.logout();
  channel?.postMessage('logout');
}
export async function completeGoogleLogin() {
  const result = await client.google();
  return result.user;
}
function requireLinkSession() {
  const snapshot = session.getSnapshot();
  if (snapshot.status !== 'AUTHENTICATED' || !snapshot.token) {
    throw Object.assign(Error('Bạn cần đăng nhập SmartProp để liên kết Google.'), { code: 'UNAUTHENTICATED' });
  }
  return snapshot.token;
}

async function postGoogleLink(path, body) {
  const token = requireLinkSession();
  const csrf = await api('/auth/csrf', { authenticated: false });
  if (requireLinkSession() !== token) {
    throw Object.assign(Error('Phiên đăng nhập đã thay đổi. Vui lòng thực hiện lại.'), { code: 'SESSION_CHANGED' });
  }
  return api(path, { method: 'POST', body, headers: { [csrf.headerName]: csrf.token } });
}

export const googleLinkStatus = () => api('/auth/google/link/status');
export async function startGoogleLink(currentPassword) {
  if (!refreshEnabled) throw Object.assign(Error('Phiên làm mới đăng nhập chưa được bật ở frontend. Vui lòng cấu hình VITE_ENABLE_REFRESH=true rồi tải lại trang.'), { code: 'FEATURE_DISABLED' });
  return postGoogleLink('/auth/google/link/start', { currentPassword });
}
export async function completeGoogleLink() {
  if (session.getSnapshot().status === 'INITIALIZING') await initializeAuth();
  return postGoogleLink('/auth/google/link/complete');
}
