/** Development-only exact public route. No Research/health/docs pass-through. */
import { relayChatResponse } from '../server/publicChat.mjs'
export function publicChatProxy(target) {
  if (!/^http:\/\/127[.]0[.]0[.]1:[0-9]{4,5}$/.test(target)) throw Error('Dev chat proxy must target a loopback HTTP port')
  return { target, changeOrigin: true, proxyTimeout: 90000, selfHandleResponse: true,
    rewrite: path => path.replace(/^\/api\/chat(?=\?|$)/, '/chat'),
    configure: proxy => { proxy.on('proxyReq', request => {
      for (const name of ['Authorization', 'Cookie', 'X-SmartProp-Demo-Key', 'X-Session-Activity']) request.removeHeader(name)
      request.setHeader('Accept-Encoding', 'identity')
    }); proxy.on('proxyRes', (upstream, request, response) => relayChatResponse(upstream, response)) },
  }
}
export function publicChatBoundary() {
  const install = server => { server.middlewares.use((request, response, next) => {
    const path = (request.url || '').split('?')[0]
    if (!path.startsWith('/api/chat')) return next()
    if (path === '/api/chat' && request.method === 'POST') return next()
    response.statusCode = 404
    response.setHeader('Content-Type', 'application/json')
    response.setHeader('Cache-Control', 'no-store')
    response.end(JSON.stringify({ message: 'Public chat route unavailable' }))
  }) }
  return { name: 'smartprop-public-chat-boundary', configureServer: install, configurePreviewServer: install }
}
