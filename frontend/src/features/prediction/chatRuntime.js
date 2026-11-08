import { reactive } from '../../shared/state/store.js'
import { session, restoreSession } from '../auth/api.js'
import { CHAT_TIMEOUT_MS, createChatSession, chatRequest, publicChatResponse } from './chat.js'

const baseUrl = (import.meta.env?.VITE_CHAT_API_BASE_URL || '/api').replace(/\/$/, '')
if (!/^\/[A-Za-z0-9/_-]*$/.test(baseUrl) || baseUrl.startsWith('//')) throw Error('Chat requires a same-origin API base path')
let owner = null
async function send(request) {
  // Refresh through the existing auth client; no profile or user id is accepted from the browser.
  if (session.user && !session.token) await restoreSession()
  const current = session.user?.id == null ? 'guest' : String(session.user.id)
  const body = chatRequest(request.question, current === owner ? request.sessionId : null)
  owner = current
  const headers = {'Content-Type':'application/json',Accept:'application/json'}
  if (session.token) headers.Authorization = 'Bearer ' + session.token
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), CHAT_TIMEOUT_MS)
  try {
    let response = await fetch(baseUrl+'/chat', {method:'POST',headers,body:JSON.stringify(body),credentials:'omit',cache:'no-store',signal:controller.signal})
    if (response.status === 401 && session.token) {
      await restoreSession()
      if ((session.user?.id == null ? 'guest' : String(session.user.id)) !== current || !session.token) throw Object.assign(Error('Phiên đã hết hạn.'),{status:401})
      headers.Authorization = 'Bearer ' + session.token
      response = await fetch(baseUrl+'/chat', {method:'POST',headers,body:JSON.stringify(body),credentials:'omit',cache:'no-store',signal:controller.signal})
    }
    const data = await response.json()
    if (!response.ok) throw Object.assign(Error(data.message || 'Chat unavailable'), {status:response.status})
    if ((session.user?.id == null ? 'guest' : String(session.user.id)) !== current) throw Object.assign(Error('Phiên đã thay đổi.'),{code:'SESSION_CHANGED'})
    return publicChatResponse(data)
  } catch (error) {
    if (error.name === 'AbortError') throw Object.assign(Error('Chat timeout'),{code:'REQUEST_TIMEOUT'})
    throw error
  } finally {clearTimeout(timer)}
}
export const chatSession = createChatSession(send, { reactive })
