/** Same-origin chat boundary. Credentials go only to the authenticated RAG route. */
import { relayChatResponse } from '../server/publicChat.mjs'
const validAuth = value => typeof value === 'string' && value.length <= 8192 && /^Bearer [A-Za-z0-9._-]+$/.test(value)
export function publicChatProxy(target) {
  if (!/^http:\/\/127[.]0[.]0[.]1:[0-9]{4,5}$/.test(target)) throw Error('Dev chat proxy must target a loopback HTTP port')
  return { target, changeOrigin: true, proxyTimeout: 90000, selfHandleResponse: true,
    bypass: request => { request.url = validAuth(request.headers.authorization) ? '/api/chat/personalized' : '/api/chat' },
    rewrite: path => path.replace(/^\/api\/chat/, '/chat'),
    configure: proxy => { proxy.on('proxyReq', request => {
      for (const name of ['Cookie', 'X-SmartProp-Demo-Key', 'X-Session-Activity']) request.removeHeader(name)
      request.setHeader('Accept-Encoding', 'identity')
    }); proxy.on('proxyRes', (upstream, request, response) => relayChatResponse(upstream, response)) },
  }
}
export function publicChatBoundary() {
  const install = server => { server.middlewares.use((request, response, next) => {
    const path = (request.url || '').split('?')[0]
    if (!path.startsWith('/api/chat')) return next()
    const badAuth = request.headers.authorization != null && !validAuth(request.headers.authorization)
    if (path === '/api/chat' && request.method === 'POST' && !badAuth) return next()
    response.statusCode = badAuth ? 401 : 404
    response.setHeader('Content-Type', 'application/json')
    response.setHeader('Cache-Control', 'no-store')
    response.end(JSON.stringify({ message: 'Chat route unavailable' }))
  }) }
  return { name: 'smartprop-public-chat-boundary', configureServer: install, configurePreviewServer: install }
}
