import { createStateStore, combineStateStores } from "../../shared/state/createStateStore.js";
import { advisorListingUrl } from './advisor.js';
export const CHAT_TIMEOUT_MS = 90000;
const blocked = /TINIX_AI|tinix:|INTERNAL_RESEARCH|INTERNAL_DEMO|\bUNVERIFIED\b|HYBRID_ELIGIBLE_RESEARCH|sampleListingCount|raw_payload/i;
const secretKeys = /"(?:password|dbPassword|db_password|authorization|demoKey|apiKey|accessToken|refreshToken|jwtSecret|jwt_secret|rawSql)"\s*:/i;
const text = v => typeof v === 'string' && v.trim().length > 0;
const strings = v => Array.isArray(v) && v.every(s => typeof s === 'string');
const invalid = () => Object.assign(Error('Kết quả không đạt điều kiện công khai. Nội dung đã được chặn.'), {
  code: 'UNSAFE_CHAT_RESPONSE'
});
function decimal(value) {
  const raw = String(value);
  if (!/^\d{1,18}(?:\.\d{1,8})?$/.test(raw)) throw invalid();
  const [whole, fraction = ''] = raw.split('.');
  return BigInt(whole) * 100000000n + BigInt(fraction.padEnd(8, '0'));
}
export function formatChatNumber(value) {
  decimal(value);
  const [whole, fraction = ''] = String(value).split('.');
  const tail = fraction.replace(/0+$/, '');
  return whole.replace(/^0+(?=\d)/, '').replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (tail ? ',' + tail : '');
}
export function displayEvidenceText(value) {
  const labels = {
    PUBLIC_TRANSPORT: 'giao thông công cộng',
    HOSPITAL: 'cơ sở y tế',
    SCHOOL: 'cơ sở giáo dục',
    MARKET: 'chợ',
    SUPERMARKET: 'siêu thị',
    PARK: 'công viên',
    BEACH: 'bãi biển',
    SHARED: 'tiện ích dùng chung',
    CORRIDOR_DIRECT: 'gắn trực tiếp với tuyến đường',
    DIRECT_WARD_EVIDENCE: 'bằng chứng trực tiếp cấp phường/xã',
    DISTRICT_FACILITY: 'cơ sở phục vụ cấp quận/huyện',
    AREA_GENERAL: 'bằng chứng chung của khu vực',
    CORRIDOR: 'tuyến đường',
    DISTRICT: 'quận/huyện',
    WARD: 'phường/xã',
    POI: 'địa điểm tiện ích'
  };
  return value.replace(/\b(?:PUBLIC_TRANSPORT|HOSPITAL|SCHOOL|MARKET|SUPERMARKET|PARK|BEACH|SHARED|CORRIDOR_DIRECT|DIRECT_WARD_EVIDENCE|DISTRICT_FACILITY|AREA_GENERAL|CORRIDOR|DISTRICT|WARD|POI)\b/g, code => labels[code]);
}
export function chatRequest(question, sessionId = null, propertyId = null) {
  const value = String(question ?? '').trim();
  if (!value || value.length > 2000) throw Object.assign(Error('Nhập câu hỏi từ 1 đến 2.000 ký tự.'), {
    code: 'INVALID_CHAT_QUESTION'
  });
  // Only the opaque server-issued id travels. No transcript, criteria, mode or research flags:
  // context lives server-side and can never be escalated by the browser.
  const body = {
    question: value,
    requireGeneration: false
  };
  if (sessionId != null) {
    if (!/^[a-f0-9]{32}$/.test(String(sessionId))) throw Object.assign(Error('Phiên hội thoại chưa hợp lệ.'), {
      code: 'INVALID_CHAT_SESSION'
    });
    body.sessionId = String(sessionId);
  }
  if (propertyId != null) {
    if (!/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/.test(propertyId)) throw Error('Invalid property reference');
    body.propertyId = propertyId;
  }
  return body;
}
export function citationHref(citation, properties) {
  try {
    if (typeof citation.url !== 'string' || citation.url.startsWith('//')) return null;
    const url = new URL(citation.url, 'https://source.invalid');
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.hash) return null;
    if (citation.kind === 'SOURCE_DOCUMENT') {
      if (!citation.url.startsWith('https://') || url.hostname === 'source.invalid' || url.protocol !== 'https:' || url.search || url.port || !url.hostname.includes('.') || /^[0-9.]+$/.test(url.hostname) || url.hostname.includes(':') || /(?:^|\.)(?:localhost|local|internal)$/.test(url.hostname)) return null;
      return url.href;
    }
    if (citation.kind === 'MARKET_SUMMARY' && url.pathname === '/api/v1/properties/market-summary') {
      const seen = new Set();
      for (const [key, value] of url.searchParams) {
        if (seen.has(key) || !['district', 'propertyType', 'transactionType', 'priceUnit'].includes(key)) return null;
        seen.add(key);
        if (key === 'district' && (!value.trim() || value.length > 100)) return null;
        if (key === 'propertyType' && !['HOUSE','APARTMENT','LAND','VILLA','ROOM','COMMERCIAL'].includes(value)) return null;
      }
      if (!['SALE','RENT'].includes(url.searchParams.get('transactionType')) || !['TOTAL','PER_MONTH','PER_YEAR','PER_DAY'].includes(url.searchParams.get('priceUnit'))) return null;
      if (url.searchParams.get('transactionType') === 'SALE' && url.searchParams.get('priceUnit') !== 'TOTAL') return null;
      return url.pathname + url.search;
    }
    if (url.search) return null;
    if (citation.kind === 'PROPERTY_DETAIL' && /^property:[a-f0-9-]{36}$/.test(citation.sourceId) && url.pathname === '/api/v1/properties/' + citation.sourceId.slice(9)) return '/listing/' + citation.sourceId.slice(9);
    if (citation.kind === 'RECOMMENDATION' && url.pathname === '/api/v1/recommendations') {
      const property = properties.find(p => citation.sourceId === 'recommendation:' + p.id);
      if (!property) return null;
      return advisorListingUrl(property);
    }
    if (citation.kind === 'PROPERTY_NEARBY' && properties.some(p => p.source.kind === 'PROPERTY' && url.pathname === '/api/v1/properties/' + p.source.recordKey + '/nearby')) return url.pathname;
    if (['AREA_AMENITY', 'POI_EVIDENCE'].includes(citation.kind) && /^\/api\/v1\/amenities\/[A-Za-z0-9_-]{1,160}$/.test(url.pathname)) {
      // Canonical SAME-ORIGIN public API path: never send the browser to an internal origin.
      return url.pathname;
    }
  } catch {/* Reject malformed/unexpected sources instead of rendering a raw href. */}
  return null;
}
export function publicChatResponse(data, { historical = false } = {}) {
  if (!data || data.mode !== 'SAFE' || blocked.test(JSON.stringify(data)) || secretKeys.test(JSON.stringify(data)) || !text(data.answer) || data.answer.length > 40000 || !['EVIDENCE_ONLY', 'QWEN_GROUNDED_ANSWER', 'QWEN_GROUNDED_PLAN'].includes(data.generationMode) || !['E5_FAISS', 'TOOL_EVIDENCE_ONLY'].includes(data.retrievalMode) || !Array.isArray(data.recommendedProperties) || data.recommendedProperties.length > 10 || !Array.isArray(data.citations) || data.citations.length > 100 || !strings(data.dataLimitations) || !data.evidence || typeof data.evidence !== 'object') throw invalid();
  const needs = data.evidence.needs;
  if (needs !== undefined && (!needs || !strings(needs.summary) || needs.summary.length > 12 || !strings(needs.priorities) || needs.priorities.length > 4 || !strings(needs.limitations) || needs.summary.some(v => v.length > 300))) throw invalid();
  if (data.evidence.quickReplies !== undefined && (!strings(data.evidence.quickReplies) || data.evidence.quickReplies.length > 8 || data.evidence.quickReplies.some(v => v.length > 100))) throw invalid();
  const ids = new Set(),
    groups = new Set(),
    sourceIds = new Set();
  if (data.evidence.topAreas && (!Array.isArray(data.evidence.topAreas) || data.evidence.topAreas.some(a => a.unverifiedCount !== 0 || a.needsReviewCount !== 0))) throw invalid();
  for (const p of data.recommendedProperties) {
    const platform = p?.source?.kind === 'PROPERTY' && p.qualityStatus === 'PLATFORM_PUBLISHED' && p.verificationStatus === 'PLATFORM_PUBLISHED';
    const external = p?.source?.kind === 'EXTERNAL' && p.qualityStatus === 'VALID' && p.verificationStatus === 'VERIFIED';
    if (!platform && !external || !text(p.id) || ids.has(p.id) || !text(p.title) || !text(p.source.name) || !text(p.source.recordKey) || !strings(p.explanations) || !strings(p.warnings) || decimal(p.score) > 10000000000n || p.isProtectedHoldout || p.protectedHoldout || p.is_protected_holdout || p.holdout || p.groupHasHoldout || decimal(p.priceVnd) <= 0n || decimal(p.areaSqm) <= 0n) throw invalid();
    if (data.evidence.criteria?.budgetVnd != null && decimal(p.priceVnd) > decimal(data.evidence.criteria.budgetVnd)) throw invalid();
    if (data.evidence.criteria?.minPriceVnd != null && decimal(p.priceVnd) < decimal(data.evidence.criteria.minPriceVnd)) throw invalid();
    if (p.duplicateGroup) {
      if (groups.has(p.duplicateGroup)) throw invalid();
      groups.add(p.duplicateGroup);
    }
    ids.add(p.id);
  }
  for (const c of data.citations) {
    if (!c || c.scope !== 'PUBLIC' || !text(c.sourceId) || sourceIds.has(c.sourceId) || !text(c.version) || !/^[a-f0-9]{64}$/.test(c.contentHash) || !citationHref(c, data.recommendedProperties)) throw invalid();
    sourceIds.add(c.sourceId);
  }
  if (data.recommendedProperties.some(p => !sourceIds.has('recommendation:' + p.id))) throw invalid();
  const market = data.evidence.marketSummary;
  const marketCitations = data.citations.filter(c => c.kind === 'MARKET_SUMMARY');
  if (market !== undefined || marketCitations.length) {
    const citation = marketCitations[0];
    if (!market || marketCitations.length !== 1 || data.recommendedProperties.length || market.sourceId !== citation.sourceId || market.asOf !== citation.version || !Number.isFinite(Date.parse(market.asOf)) || market.source !== 'CURRENT_PUBLISHED_ASKING_PRICES' || market.historyAvailable !== false || !market.query || typeof market.query !== 'object' || Array.isArray(market.query)) throw invalid();
    const params = new URL(citationHref(citation, []), 'https://source.invalid').searchParams;
    if (Object.keys(market.query).length !== [...params].length || Object.entries(market.query).some(([k,v]) => params.get(k) !== v)) throw invalid();
    const a = market.amounts;
    if (!a || !Number.isSafeInteger(a.count) || a.count < 0) throw invalid();
    for (const key of ['totalAskingPrice','averageAskingPrice','minimumAskingPrice','maximumAskingPrice','weightedAskingPricePerSqm']) if (a[key] != null) decimal(a[key]);
    if (a.count && (a.minimumAskingPrice == null || a.averageAskingPrice == null || a.maximumAskingPrice == null || decimal(a.minimumAskingPrice) > decimal(a.averageAskingPrice) || decimal(a.averageAskingPrice) > decimal(a.maximumAskingPrice))) throw invalid();
    if (!a.count && ['averageAskingPrice','minimumAskingPrice','maximumAskingPrice'].some(k => a[k] != null)) throw invalid();
  }
  const documentCitations = data.citations.filter(c => c.kind === 'SOURCE_DOCUMENT');
  const documents = data.evidence.documents;
  if (documentCitations.length || documents !== undefined) {
    if (!Array.isArray(documents) || documents.length > 4 || documents.length !== documentCitations.length) throw invalid();
    const seenDocuments = new Set();
    for (const doc of documents) {
      const source = documentCitations.find(c => c.sourceId === doc.sourceId);
      if (!source || seenDocuments.has(doc.sourceId) || source.url !== doc.url || source.version !== doc.version || source.title !== doc.title || !text(doc.publisher) || !text(doc.jurisdiction)) throw invalid();
      const dates = ['publishedAt','retrievedAt','validUntil'].map(k => Date.parse(doc[k]));
      if (dates.some(v => !Number.isFinite(v)) || dates[0] > dates[1] || dates[1] > Date.now()+5000 || (!historical && dates[2] <= Date.now())) throw invalid();
      seenDocuments.add(doc.sourceId);
    }
  }
  const generation = data.evidence.generation;
  if (data.evidence.responseKind === 'NO_MATCHES' && (data.generationMode !== 'EVIDENCE_ONLY' || data.retrievalMode !== 'TOOL_EVIDENCE_ONLY' || data.recommendedProperties.length || data.citations.length || !data.evidence.criteria?.budgetVnd || data.evidence.recommendationSearch?.performed !== true || data.evidence.recommendationSearch.resultCount !== 0 || data.evidence.recommendationSearch.sourcePath !== '/api/v1/recommendations' || !/^[a-f0-9]{64}$/.test(data.evidence.recommendationSearch.criteriaHash) || generation?.accepted !== false || generation.reason !== 'NOT_NEEDED_FOR_EMPTY_SEARCH')) throw invalid();
  if (!data.citations.length && (data.recommendedProperties.length || data.generationMode !== 'EVIDENCE_ONLY')) throw invalid();
  if (data.generationMode === 'QWEN_GROUNDED_ANSWER' && (!generation?.accepted || !(generation.eval_count > 0) || !Array.isArray(generation.sentences) || !generation.sentences.length || generation.sentences.some(s => !text(s.text) || !sourceIds.has(s.sourceId) || !data.answer.includes(s.text)))) throw invalid();
  // Explicit POI category questions may only be answered from POI evidence of that category.
  // The server enforces this; the client refuses a packet that still cites area/other evidence.
  const intent = data.evidence.amenityIntent;
  if (intent !== undefined) {
    const categories = intent?.categories;
    if (!Array.isArray(categories) || categories.length > 9 || !categories.every(c => typeof c === 'string' && /^[A-Z_]{3,24}$/.test(c)) || intent.district !== null && (typeof intent.district !== 'string' || !intent.district.trim())) throw invalid();
    if (categories.length) {
      // Only POI evidence (or a recommended property) may back an explicit category answer.
      if (data.citations.some(c => !['POI_EVIDENCE', 'RECOMMENDATION'].includes(c.kind))) throw invalid();
      const kindById = new Map(data.citations.map(c => [c.sourceId, c.kind]));
      if (generation?.sentences?.some(s => kindById.get(s.sourceId) !== 'POI_EVIDENCE')) throw invalid();
    }
  }
  return data;
}
export const createChatClient = request => async (question, sessionId = null) => publicChatResponse(await request('/chat', {
  method: 'POST',
  authenticated: false,
  body: chatRequest(question, sessionId)
}));
export function chatError(error) {
  if (error?.code === 'UNSAFE_CHAT_RESPONSE') return {
    text: 'Kết quả không đạt điều kiện công khai nên đã được chặn. Không hiển thị dữ liệu này.',
    retry: false,
    delayMs: 0
  };
  if (error?.code === 'REQUEST_TIMEOUT') return {
    text: 'Đã hết thời gian chờ 90 giây. Máy chủ có thể vẫn đang xử lý; hãy chờ rồi thử lại thủ công.',
    retry: true,
    delayMs: 20000
  };
  if (error?.code === 'NETWORK_ERROR') return {
    text: 'Không kết nối được dịch vụ chat. Kiểm tra kết nối rồi thử lại.',
    retry: true,
    delayMs: 5000
  };
  if ([401, 403].includes(error?.status)) return {
    text: 'Phiên đăng nhập đã hết hạn hoặc bạn không có quyền truy cập hội thoại. Hãy đăng nhập lại hoặc tạo hội thoại mới.',
    retry: false,
    delayMs: 0
  };
  if (error?.status === 409) return { text: "Hội thoại đã được cập nhật ở nơi khác. Chọn lại hội thoại trong lịch sử trước khi gửi tiếp.", retry: false, delayMs: 0 };
  if (error?.status === 404) return { text: "Không tìm thấy hội thoại hoặc bạn không có quyền truy cập. Hãy chọn lại hoặc tạo hội thoại mới.", retry: false, delayMs: 0 };
  if (error?.status === 422 || error?.code === 'INVALID_CHAT_QUESTION') return {
    text: 'Câu hỏi chưa hợp lệ. Nhập từ 1 đến 2.000 ký tự rồi gửi lại.',
    retry: false,
    delayMs: 0
  };
  if (error?.status === 429) return {
    text: 'Hệ thống đang bận. Vui lòng chờ trước khi gửi lại.',
    retry: true,
    delayMs: Math.min(120000, Math.max(10000, (error.retryAfter || 10) * 1000))
  };
  return {
    text: 'Dịch vụ chat tạm gián đoạn. Không có câu trả lời thay thế; bạn có thể thử lại sau.',
    retry: true,
    delayMs: 5000
  };
}
export function createChatSession(send, {
  now = Date.now
} = {}) {
  const state = createStateStore({
    messages: [],
    busy: false,
    startedAt: 0,
    retryAt: 0,
    failedQuestion: '',
    error: null,
    trimmed: false,
    propertyContext: null,
    sessionId: null
  });
  let id = 0;
  let generation = 0;
  async function submit(question, retry = false) {
    if (state.getSnapshot().busy || now() < state.getSnapshot().retryAt) return false;
    const run = generation;
    let request;
    try {
      request = chatRequest(question, state.getSnapshot().sessionId, state.getSnapshot().propertyContext?.id);
    } catch (error) {
      state.edit(draftValue => draftValue["error"] = chatError(error));
      return false;
    }
    state.edit(draftValue => draftValue["busy"] = true);
    state.edit(draftValue => draftValue["startedAt"] = now());
    state.edit(draftValue => draftValue["error"] = null);
    state.edit(draftValue => draftValue["failedQuestion"] = '');
    if (!retry) state.edit(draftValue => draftValue["messages"].push({
      id: ++id,
      role: 'user',
      text: request.question,
      sessionTurn: request.sessionId ? 'followup' : 'start'
    }));
    try {
      const response = await send(request);
      if (run !== generation) return false;
      // The server owns the identifier; a fresh conversation never inherits an old one.
      // It may also retire a capped/expired thread and issue a replacement id.
      if (response?.evidence?.clearPropertyContext || (state.getSnapshot().propertyContext && response?.evidence?.intentFamily === 'PROPERTY_SEARCH')) state.edit(d => d.propertyContext = null);
      const issued = response?.evidence?.session?.id;
      if (typeof issued === 'string' && /^[a-f0-9]{32}$/.test(issued)) state.edit(draftValue => draftValue["sessionId"] = issued);
      state.edit(draftValue => draftValue["messages"].push({
        id: ++id,
        role: 'assistant',
        response
      }));
      if (state.getSnapshot().messages.length > 24) {
        state.edit(draftValue => draftValue["messages"].splice(0, state.getSnapshot().messages.length - 24));
        state.edit(draftValue => draftValue["trimmed"] = true);
      }
      state.edit(draftValue => draftValue["retryAt"] = 0);
      return true;
    } catch (error) {
      if (run !== generation) return false;
      state.edit(draftValue => draftValue["error"] = chatError(error));
      state.edit(draftValue => draftValue["failedQuestion"] = request.question);
      state.edit(draftValue => draftValue["retryAt"] = now() + state.getSnapshot().error.delayMs);
      return false;
    } finally {
      if (run === generation) state.edit(draftValue => draftValue["busy"] = false);
    }
  }
  return combineStateStores([state], () => ({
    state: state.getSnapshot(),
    restore: saved => {
      if (!/^[a-f0-9]{32}$/.test(saved.id) || !Array.isArray(saved.turns) || saved.turns.length > 12) throw invalid();
      const messages = saved.turns.flatMap(turn => {
        if (!text(turn.question) || turn.question.length > 2000) throw invalid();
        return [{id: ++id, role: "user", text: turn.question}, {id: ++id, role: "assistant", response: publicChatResponse(turn.response, {historical:true}), historical:true}];
      });
      generation++;
      state.edit(d => Object.assign(d, {messages, sessionId:saved.id, busy:false, error:null, retryAt:0, failedQuestion:"", propertyContext:null, trimmed:!!saved.trimmed}));
    },
    focusProperty: (id, label) => {
      chatRequest('context', null, id);
      generation++;
      state.edit(d => Object.assign(d, {messages: [], busy:false, error:null, retryAt:0, sessionId:null, propertyContext:{id,label}}));
    },
    submit: question => submit(question),
    retry: () => state.getSnapshot().error?.retry && submit(state.getSnapshot().failedQuestion, true),
    clear: () => {
      if (state.getSnapshot().busy || now() < state.getSnapshot().retryAt) return;
      state.edit(draftValue => draftValue["messages"].splice(0));
      state.edit(draftValue => draftValue["error"] = null);
      state.edit(draftValue => draftValue["failedQuestion"] = '');
      state.edit(draftValue => draftValue["trimmed"] = false);
      state.edit(draftValue => draftValue["sessionId"] = null);
      state.edit(d => d.propertyContext = null);
    },
    reset: () => {
      generation++;
      state.edit(draftValue => Object.assign(draftValue, {messages: [], busy: false, startedAt: 0, retryAt: 0, failedQuestion: '', error: null, trimmed: false, sessionId: null, propertyContext:null}));
    },
    updateState: state.edit,
    updateStateValue: state.set
  }));
}
