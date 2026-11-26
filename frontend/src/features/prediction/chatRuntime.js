import { createChatHistory } from './chatHistory.js';
import { session, restoreSession, api } from '../auth/api.js';
import { CHAT_TIMEOUT_MS, createChatSession, chatRequest, publicChatResponse } from './chat.js';
const baseUrl = (import.meta.env?.VITE_CHAT_API_BASE_URL || '/api').replace(/\/$/, '');
if (!/^\/[A-Za-z0-9/_-]*$/.test(baseUrl) || baseUrl.startsWith('//')) throw Error('Chat requires a same-origin API base path');

let selectedLand = null;
export function selectChatLand(landId, sessionId) {
  selectedLand = {landId, sessionId};
}
async function send(request) {
  // Refresh through the existing auth client; no profile or user id is accepted from the browser.
  if (session.getSnapshot().user && !session.getSnapshot().token) await restoreSession();
  const current = session.getSnapshot().user?.id == null ? 'guest' : String(session.getSnapshot().user.id);
  const body = chatRequest(request.question, request.sessionId, request.propertyId);
  if (selectedLand?.sessionId && selectedLand.sessionId === request.sessionId && /^[a-f0-9-]{36}$/.test(selectedLand.landId)) body.landId = selectedLand.landId;

  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json'
  };
  if (session.getSnapshot().token) headers.Authorization = 'Bearer ' + session.getSnapshot().token;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), CHAT_TIMEOUT_MS);
  try {
    let response = await fetch(baseUrl + '/chat', {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      credentials: 'omit',
      cache: 'no-store',
      signal: controller.signal
    });
    if (response.status === 401 && session.getSnapshot().token) {
      await restoreSession();
      if ((session.getSnapshot().user?.id == null ? 'guest' : String(session.getSnapshot().user.id)) !== current || !session.getSnapshot().token) throw Object.assign(Error('Phiên đã hết hạn.'), {
        status: 401
      });
      headers.Authorization = 'Bearer ' + session.getSnapshot().token;
      response = await fetch(baseUrl + '/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        credentials: 'omit',
        cache: 'no-store',
        signal: controller.signal
      });
    }
    const data = await response.json();
    if (!response.ok) throw Object.assign(Error(data.message || 'Chat unavailable'), {
      status: response.status
    });
    if ((session.getSnapshot().user?.id == null ? 'guest' : String(session.getSnapshot().user.id)) !== current) throw Object.assign(Error('Phiên đã thay đổi.'), {
      code: 'SESSION_CHANGED'
    });
    const result = publicChatResponse(data);
    if (current !== "guest") chatHistory.refresh(true);
    return result;
  } catch (error) {
    if (error.name === 'AbortError') throw Object.assign(Error('Chat timeout'), {
      code: 'REQUEST_TIMEOUT'
    });
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
export const chatSession = createChatSession(send, {});

export const chatHistory = createChatHistory(chatSession, api, () => session.getSnapshot().user?.id == null ? null : String(session.getSnapshot().user.id));
// Shared floating/full-page chat and history always belong to one identity.
let visibleOwner = session.getSnapshot().user?.id == null ? 'guest' : String(session.getSnapshot().user.id);
session.subscribe(() => {
  const nextOwner = session.getSnapshot().user?.id == null ? 'guest' : String(session.getSnapshot().user.id);
  if (nextOwner !== visibleOwner) {
    visibleOwner = nextOwner;
    selectedLand = null;
    chatHistory.reset();
    chatSession.getSnapshot().reset();
    if (nextOwner !== "guest") chatHistory.refresh();
  }
});
