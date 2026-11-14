/** Shared server boundary for dev proxy and a production same-origin relay. */
import { publicChatResponse } from '../src/features/prediction/chat.js'

export function publicChatBody(data) {
  publicChatResponse(data)
  const result = { ...data, citations: data.citations.map(c => ({ ...c, url: new URL(c.url, 'https://source.invalid').pathname })) }
  if (/https?:\/\/(?:127[.]|localhost|\[::1\])/i.test(JSON.stringify(result))) throw Error('Internal source origin blocked')
  return result
}

export function relayChatResponse(upstream, response) {
  const chunks = []; let size = 0, ended = false
  function finish(status, body) {
    if (ended || response.writableEnded) return
    ended = true; response.statusCode = status
    response.setHeader('Content-Type', 'application/json; charset=utf-8'); response.setHeader('Cache-Control', 'no-store')
    if (status === 429 && /^\d+$/.test(String(upstream.headers['retry-after'] || ''))) response.setHeader('Retry-After', String(Math.min(120, Number(upstream.headers['retry-after']))))
    response.end(JSON.stringify(body))
  }
  upstream.on('data', chunk => { size += chunk.length; if (size > 2 * 1024 * 1024) { finish(502, {message:'Chat response unavailable'}); upstream.destroy() } else chunks.push(chunk) })
  upstream.on('error', () => finish(502, {message:'Chat upstream unavailable'}))
  upstream.on('aborted', () => finish(502, {message:'Chat upstream unavailable'}))
  upstream.on('end', () => {
    if (ended) return
    if (upstream.statusCode !== 200) return finish(upstream.statusCode >= 400 && upstream.statusCode <= 599 ? upstream.statusCode : 502, {message:'Chat service unavailable'})
    try { finish(200, publicChatBody(JSON.parse(Buffer.concat(chunks).toString('utf8')))) }
    catch { finish(502, {message:'Chat response blocked by public safety checks'}) }
  })
}
