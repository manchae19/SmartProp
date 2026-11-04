import { reactive } from 'vue'
import { createHttpClient } from './httpClient.js'
import { CHAT_TIMEOUT_MS, createChatClient, createChatSession } from './chat.js'

const baseUrl = (import.meta.env?.VITE_CHAT_API_BASE_URL || '/api').replace(/\/$/, '')
if (!/^\/[A-Za-z0-9/_-]*$/.test(baseUrl) || baseUrl.startsWith('//')) throw Error('Chat requires a same-origin API base path')
// Independent public transport uses the EXISTING HTTP client; auth state/refresh stay untouched.
const client = createHttpClient({ baseUrl, session: { token: null }, refreshEnabled: false,
  timeoutForPath: () => CHAT_TIMEOUT_MS,
  fetcher: (url, options) => fetch(url, { ...options, credentials: 'omit', cache: 'no-store' }),
})
const postChat = createChatClient(client.request)
// `send` receives a validated {question, sessionId} object from the session layer.
export const chatSession = createChatSession(request => postChat(request.question, request.sessionId ?? null), { reactive })
