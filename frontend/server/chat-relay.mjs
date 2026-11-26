/** Optional production public relay behind your web server. No secrets required. */
import http from 'node:http'
import https from 'node:https'
import { relayChatResponse } from './publicChat.mjs'
const target = new URL(process.env.CHAT_UPSTREAM_URL || '')
if (!['http:', 'https:'].includes(target.protocol) || target.pathname !== '/chat' || target.username || target.password || target.search || target.hash) throw Error('Set CHAT_UPSTREAM_URL to the trusted server-side /chat endpoint')
const port = Number(process.env.CHAT_RELAY_PORT || 8082)
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw Error('Invalid relay port')
const server = http.createServer((request, response) => {
  const error = status => { if (!response.writableEnded) { response.writeHead(status, {'Content-Type':'application/json','Cache-Control':'no-store'}); response.end(JSON.stringify({message:'Public chat unavailable'})) } }
  if (request.url !== '/api/chat' || request.method !== 'POST') return error(404)
  const chunks = []; let size = 0
  request.on('data', chunk => { size += chunk.length; if (size > 16384) error(413); else chunks.push(chunk) })
  request.on('end', () => {
    if (response.writableEnded) return
    try {
      const body = JSON.parse(Buffer.concat(chunks).toString('utf8'))
      if (!body || Object.keys(body).some(k => !['question','requireGeneration','sessionId','propertyId','landId'].includes(k)) || typeof body.question !== 'string' || !body.question.trim() || body.question.length > 2000 || body.requireGeneration !== false) return error(422)
      if (body.sessionId != null && !/^[a-f0-9]{32}$/.test(body.sessionId)) return error(422)
      for (const key of ['propertyId','landId']) if (body[key] != null && !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(body[key])) return error(422)
      const auth = request.headers.authorization
      if (auth && !/^Bearer [A-Za-z0-9._-]+$/.test(auth)) return error(401)
      const endpoint = new URL(target)
      if (auth) endpoint.pathname = '/chat/personalized'
      const headers = {Accept:'application/json','Content-Type':'application/json','Accept-Encoding':'identity'}
      if (auth) headers.Authorization = auth
      const wire = Buffer.from(JSON.stringify(body))
      headers['Content-Length'] = wire.length
      const upstream = (target.protocol === 'https:' ? https : http).request(endpoint, {method:'POST',headers}, incoming => relayChatResponse(incoming, response))
      upstream.setTimeout(90000, () => { upstream.destroy(); error(504) })
      upstream.on('error', () => error(502)); upstream.end(wire)
    } catch { error(422) }
  })
  request.on('error', () => error(400))
})
server.requestTimeout = 95000
server.listen(port, process.env.CHAT_RELAY_HOST || '127.0.0.1', () => console.log('Public Chat relay ready; private routes disabled'))
