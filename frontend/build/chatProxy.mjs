/** Same-origin chat and internal demo land boundary. Credentials go only to authorized loopback routes. */
import { relayChatResponse } from '../server/publicChat.mjs'
const validAuth = value => typeof value === 'string' && value.length <= 8192 && /^Bearer [A-Za-z0-9._-]+$/.test(value)
const cleanDemoKey = value => (typeof value === 'string' && value.trim().length >= 16 ? value.trim() : '')

export function publicChatProxy(target, { demoKey = '' } = {}) {
  if (!/^http:\/\/127[.]0[.]0[.]1:[0-9]{4,5}$/.test(target)) throw Error('Dev chat proxy must target a loopback HTTP port')
  const key = cleanDemoKey(demoKey)
  return { target, changeOrigin: true, proxyTimeout: 90000, selfHandleResponse: true,
    bypass: request => { if ((request.url || '').split('?')[0] !== '/api/chat/health') request.url = validAuth(request.headers.authorization) ? '/api/chat/personalized' : '/api/chat' },
    rewrite: path => path.replace(/^\/api\/chat/, '/chat'),
    configure: proxy => { proxy.on('proxyReq', request => {
      for (const name of ['Cookie', 'X-SmartProp-Demo-Key', 'X-Session-Activity', 'Forwarded', 'X-Forwarded-For']) request.removeHeader(name)
      if (key) request.setHeader('X-SmartProp-Demo-Key', key)
      request.setHeader('Accept-Encoding', 'identity')
    }); proxy.on('proxyRes', (upstream, request, response) => { if ((request.url || '').split('?')[0].endsWith('/health')) { response.statusCode = upstream.statusCode; response.setHeader('Content-Type', 'application/json'); response.setHeader('Cache-Control', 'no-store'); upstream.pipe(response) } else relayChatResponse(upstream, response, { allowDemo: Boolean(key) }) }) },
  }
}

export function publicChatBoundary({ demoKey = '' } = {}) {
  const allowDemo = Boolean(cleanDemoKey(demoKey))
  const install = server => { server.middlewares.use((request, response, next) => {
    const path = (request.url || '').split('?')[0]
    if (path === '/api/land' || path.startsWith('/api/land/')) {
      if (allowDemo && request.method === 'GET') return next()
      response.statusCode = 403
      response.setHeader('Content-Type', 'application/json; charset=utf-8')
      response.setHeader('Cache-Control', 'no-store')
      response.end(JSON.stringify({ code: 'FORBIDDEN', message: 'Hồ sơ đất demo chỉ dành cho môi trường trình diễn nội bộ được cấp phép.' }))
      return
    }
    if (!path.startsWith('/api/chat')) return next()
    const badAuth = request.headers.authorization != null && !validAuth(request.headers.authorization)
    if (path === '/api/chat/health' && request.method === 'GET' && !badAuth) return next()
    if (path === '/api/chat' && request.method === 'POST' && !badAuth) return next()
    response.statusCode = badAuth ? 401 : 404
    response.setHeader('Content-Type', 'application/json')
    response.setHeader('Cache-Control', 'no-store')
    response.end(JSON.stringify({ message: 'Chat route unavailable' }))
  }) }
  return { name: 'smartprop-public-chat-boundary', configureServer: install, configurePreviewServer: install }
}
