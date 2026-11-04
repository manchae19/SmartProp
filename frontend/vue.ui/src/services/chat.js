import { advisorListingUrl } from './advisor.js'

export const CHAT_TIMEOUT_MS = 90000
const blocked = /TINIX_AI|tinix:|INTERNAL_RESEARCH|INTERNAL_DEMO|\bUNVERIFIED\b|HYBRID_ELIGIBLE_RESEARCH|sampleListingCount|raw_payload/i
const secretKeys = /"(?:password|dbPassword|db_password|authorization|demoKey|apiKey|accessToken|refreshToken|jwtSecret|jwt_secret|rawSql)"\s*:/i
const text = v => typeof v === 'string' && v.trim().length > 0
const strings = v => Array.isArray(v) && v.every(s => typeof s === 'string')
const invalid = () => Object.assign(Error('Kết quả không đạt điều kiện công khai. Nội dung đã được chặn.'), { code: 'UNSAFE_CHAT_RESPONSE' })
function decimal(value) {
  const raw = String(value)
  if (!/^\d{1,18}(?:\.\d{1,8})?$/.test(raw)) throw invalid()
  const [whole, fraction = ''] = raw.split('.')
  return BigInt(whole) * 100000000n + BigInt(fraction.padEnd(8, '0'))
}
export function formatChatNumber(value) {
  decimal(value)
  const [whole, fraction = ''] = String(value).split('.')
  const tail = fraction.replace(/0+$/, '')
  return whole.replace(/^0+(?=\d)/, '').replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (tail ? ',' + tail : '')
}
export function displayEvidenceText(value) {
  const labels = { PUBLIC_TRANSPORT: 'giao thông công cộng', HOSPITAL: 'cơ sở y tế', SCHOOL: 'cơ sở giáo dục',
    MARKET: 'chợ', SUPERMARKET: 'siêu thị', PARK: 'công viên', BEACH: 'bãi biển', SHARED: 'tiện ích dùng chung',
    CORRIDOR_DIRECT: 'gắn trực tiếp với tuyến đường', DIRECT_WARD_EVIDENCE: 'bằng chứng trực tiếp cấp phường/xã',
    DISTRICT_FACILITY: 'cơ sở phục vụ cấp quận/huyện', AREA_GENERAL: 'bằng chứng chung của khu vực',
    CORRIDOR: 'tuyến đường', DISTRICT: 'quận/huyện', WARD: 'phường/xã', POI: 'địa điểm tiện ích' }
  return value.replace(/\b(?:PUBLIC_TRANSPORT|HOSPITAL|SCHOOL|MARKET|SUPERMARKET|PARK|BEACH|SHARED|CORRIDOR_DIRECT|DIRECT_WARD_EVIDENCE|DISTRICT_FACILITY|AREA_GENERAL|CORRIDOR|DISTRICT|WARD|POI)\b/g, code => labels[code])
}
export function chatRequest(question, sessionId = null) {
  const value = String(question ?? '').trim()
  if (!value || value.length > 2000) throw Object.assign(Error('Nhập câu hỏi từ 1 đến 2.000 ký tự.'), { code: 'INVALID_CHAT_QUESTION' })
  // Only the opaque server-issued id travels. No transcript, criteria, mode or research flags:
  // context lives server-side and can never be escalated by the browser.
  const body = { question: value, requireGeneration: false }
  if (sessionId != null) {
    if (!/^[a-f0-9]{32}$/.test(String(sessionId))) throw Object.assign(Error('Phiên hội thoại chưa hợp lệ.'), { code: 'INVALID_CHAT_SESSION' })
    body.sessionId = String(sessionId)
  }
  return body
}

export function citationHref(citation, properties) {
  try {
    if (typeof citation.url !== 'string' || citation.url.startsWith('//')) return null
    const url = new URL(citation.url, 'https://source.invalid')
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) return null
    if (citation.kind === 'RECOMMENDATION' && url.pathname === '/api/v1/recommendations') {
      const property = properties.find(p => citation.sourceId === 'recommendation:' + p.id)
      if (!property) return null
      return advisorListingUrl(property)
    }
    if (['AREA_AMENITY', 'POI_EVIDENCE'].includes(citation.kind) && /^\/api\/v1\/amenities\/[A-Za-z0-9_-]{1,160}$/.test(url.pathname)) {
      // Canonical SAME-ORIGIN public API path: never send the browser to an internal origin.
      return url.pathname
    }
  } catch { /* Reject malformed/unexpected sources instead of rendering a raw href. */ }
  return null
}

export function publicChatResponse(data) {
  if (!data || data.mode !== 'SAFE' || blocked.test(JSON.stringify(data)) || secretKeys.test(JSON.stringify(data)) || !text(data.answer) || data.answer.length > 40000
      || !['EVIDENCE_ONLY', 'QWEN_GROUNDED_ANSWER', 'QWEN_GROUNDED_PLAN'].includes(data.generationMode)
      || !['E5_FAISS', 'TOOL_EVIDENCE_ONLY'].includes(data.retrievalMode)
      || !Array.isArray(data.recommendedProperties) || data.recommendedProperties.length > 10
      || !Array.isArray(data.citations) || data.citations.length > 100
      || !strings(data.dataLimitations) || !data.evidence || typeof data.evidence !== 'object') throw invalid()
  const ids = new Set(), groups = new Set(), sourceIds = new Set()
  if (data.evidence.topAreas && (!Array.isArray(data.evidence.topAreas) || data.evidence.topAreas.some(a => a.unverifiedCount !== 0 || a.needsReviewCount !== 0))) throw invalid()
  for (const p of data.recommendedProperties) {
    const platform = p?.source?.kind === 'PROPERTY' && p.qualityStatus === 'PLATFORM_PUBLISHED' && p.verificationStatus === 'PLATFORM_PUBLISHED'
    const external = p?.source?.kind === 'EXTERNAL' && p.qualityStatus === 'VALID' && p.verificationStatus === 'VERIFIED'
    if ((!platform && !external) || !text(p.id) || ids.has(p.id) || !text(p.title) || !text(p.source.name) || !text(p.source.recordKey)
        || !strings(p.explanations) || !strings(p.warnings) || decimal(p.score) > 10000000000n
        || p.isProtectedHoldout || p.protectedHoldout || p.is_protected_holdout || p.holdout || p.groupHasHoldout
        || decimal(p.priceVnd) <= 0n || decimal(p.areaSqm) <= 0n) throw invalid()
    if (data.evidence.criteria?.budgetVnd != null && decimal(p.priceVnd) > decimal(data.evidence.criteria.budgetVnd)) throw invalid()
    if (p.duplicateGroup) { if (groups.has(p.duplicateGroup)) throw invalid(); groups.add(p.duplicateGroup) }
    ids.add(p.id)
  }
  for (const c of data.citations) {
    if (!c || c.scope !== 'PUBLIC' || !text(c.sourceId) || sourceIds.has(c.sourceId) || !text(c.version)
        || !/^[a-f0-9]{64}$/.test(c.contentHash) || !citationHref(c, data.recommendedProperties)) throw invalid()
    sourceIds.add(c.sourceId)
  }
  if (data.recommendedProperties.some(p => !sourceIds.has('recommendation:' + p.id))) throw invalid()
  const generation = data.evidence.generation
  if (data.evidence.responseKind === 'NO_MATCHES' && (data.generationMode !== 'EVIDENCE_ONLY' || data.retrievalMode !== 'TOOL_EVIDENCE_ONLY'
      || data.recommendedProperties.length || data.citations.length || !data.evidence.criteria?.budgetVnd
      || data.evidence.recommendationSearch?.performed !== true || data.evidence.recommendationSearch.resultCount !== 0
      || data.evidence.recommendationSearch.sourcePath !== '/api/v1/recommendations'
      || !/^[a-f0-9]{64}$/.test(data.evidence.recommendationSearch.criteriaHash) || generation?.accepted !== false
      || generation.reason !== 'NOT_NEEDED_FOR_EMPTY_SEARCH')) throw invalid()
  if (!data.citations.length && (data.recommendedProperties.length || data.generationMode !== 'EVIDENCE_ONLY')) throw invalid()
  if (data.generationMode === 'QWEN_GROUNDED_ANSWER' && (!generation?.accepted || !(generation.eval_count > 0)
      || !Array.isArray(generation.sentences) || !generation.sentences.length
      || generation.sentences.some(s => !text(s.text) || !sourceIds.has(s.sourceId) || !data.answer.includes(s.text)))) throw invalid()
  // Explicit POI category questions may only be answered from POI evidence of that category.
  // The server enforces this; the client refuses a packet that still cites area/other evidence.
  const intent = data.evidence.amenityIntent
  if (intent !== undefined) {
    const categories = intent?.categories
    if (!Array.isArray(categories) || categories.length > 8 || !categories.every(c => typeof c === 'string' && /^[A-Z_]{3,24}$/.test(c))
        || (intent.district !== null && (typeof intent.district !== 'string' || !intent.district.trim()))) throw invalid()
    if (categories.length) {
      // Only POI evidence (or a recommended property) may back an explicit category answer.
      if (data.citations.some(c => !['POI_EVIDENCE', 'RECOMMENDATION'].includes(c.kind))) throw invalid()
      const kindById = new Map(data.citations.map(c => [c.sourceId, c.kind]))
      if (generation?.sentences?.some(s => kindById.get(s.sourceId) !== 'POI_EVIDENCE')) throw invalid()
    }
  }
  return data
}

export const createChatClient = request => async (question, sessionId = null) => publicChatResponse(await request('/chat', {
  method: 'POST', authenticated: false, body: chatRequest(question, sessionId),
}))

export function chatError(error) {
  if (error?.code === 'UNSAFE_CHAT_RESPONSE') return { text: 'Kết quả không đạt điều kiện công khai nên đã được chặn. Không hiển thị dữ liệu này.', retry: false, delayMs: 0 }
  if (error?.code === 'REQUEST_TIMEOUT') return { text: 'Đã hết thời gian chờ 90 giây. Máy chủ có thể vẫn đang xử lý; hãy chờ rồi thử lại thủ công.', retry: true, delayMs: 20000 }
  if (error?.code === 'NETWORK_ERROR') return { text: 'Không kết nối được dịch vụ chat. Kiểm tra kết nối rồi thử lại.', retry: true, delayMs: 5000 }
  if ([401, 403].includes(error?.status)) return { text: 'Dịch vụ chat công khai chưa sẵn sàng. Bạn không cần đổi tài khoản hoặc bật chế độ nghiên cứu.', retry: false, delayMs: 0 }
  if (error?.status === 422 || error?.code === 'INVALID_CHAT_QUESTION') return { text: 'Câu hỏi chưa hợp lệ. Nhập từ 1 đến 2.000 ký tự rồi gửi lại.', retry: false, delayMs: 0 }
  if (error?.status === 429) return { text: 'Hệ thống đang bận. Vui lòng chờ trước khi gửi lại.', retry: true, delayMs: Math.min(120000, Math.max(10000, (error.retryAfter || 10) * 1000)) }
  return { text: 'Dịch vụ chat tạm gián đoạn. Không có câu trả lời thay thế; bạn có thể thử lại sau.', retry: true, delayMs: 5000 }
}

export function createChatSession(send, { reactive = value => value, now = Date.now } = {}) {
  const state = reactive({ messages: [], busy: false, startedAt: 0, retryAt: 0, failedQuestion: '', error: null, trimmed: false, sessionId: null })
  let id = 0
  async function submit(question, retry = false) {
    if (state.busy || now() < state.retryAt) return false
    let request
    try { request = chatRequest(question, state.sessionId) } catch (error) { state.error = chatError(error); return false }
    state.busy = true; state.startedAt = now(); state.error = null; state.failedQuestion = ''
    if (!retry) state.messages.push({ id: ++id, role: 'user', text: request.question, sessionTurn: request.sessionId ? 'followup' : 'start' })
    try {
      const response = await send(request)
      // The server owns the identifier; a fresh conversation never inherits an old one.
      // It may also retire a capped/expired thread and issue a replacement id.
      const issued = response?.evidence?.session?.id
      if (typeof issued === 'string' && /^[a-f0-9]{32}$/.test(issued)) state.sessionId = issued
      state.messages.push({ id: ++id, role: 'assistant', response })
      if (state.messages.length > 24) { state.messages.splice(0, state.messages.length - 24); state.trimmed = true }
      state.retryAt = 0
      return true
    } catch (error) {
      state.error = chatError(error); state.failedQuestion = request.question; state.retryAt = now() + state.error.delayMs
      return false
    } finally { state.busy = false }
  }
  return { state, submit: question => submit(question), retry: () => state.error?.retry && submit(state.failedQuestion, true),
    clear: () => { if (state.busy || now() < state.retryAt) return; state.messages.splice(0); state.error = null; state.failedQuestion = ''; state.trimmed = false; state.sessionId = null } }
}
