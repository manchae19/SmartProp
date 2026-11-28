// Real-data market analytics client (Step 21.5B).
// The backend aggregates real MySQL rows; this module only shapes the request,
// validates the contract and formats numbers. No value here is mock data.
import { api } from '../auth/api.js'

export const PUBLIC_ANALYSIS_SOURCES = Object.freeze({
  ALL: 'Tất cả nguồn công khai',
  SMARTPROP: 'SmartProp (đã duyệt)',
  EXTERNAL_LISTING: 'Tin ngoài (VALID)',
})

export const ANALYSIS_SOURCES = Object.freeze({
  ALL: 'Tất cả nguồn',
  SMARTPROP: 'SmartProp (đã duyệt)',
  EXTERNAL_LISTING: 'Tin ngoài (VALID)',
  TINIX_RESEARCH: 'TiniX — nghiên cứu',
})

export function marketResearchActorKey(snap) {
  if (!snap || snap.status !== 'AUTHENTICATED' || !snap.token) return ''
  if (snap.user?.role !== 'ADMIN') return ''
  if (snap.user?.status && snap.user.status !== 'ACTIVE') return ''
  const identity = snap.user.id ?? snap.user.userId ?? snap.user.sub ?? snap.user.email ?? snap.token ?? ''
  const normalized = String(identity).trim()
  return normalized ? `ADMIN:${normalized}` : ''
}

export const PROPERTY_TYPES = {
  '': 'Tất cả loại hình',
  HOUSE: 'Nhà ở / Nhà phố',
  APARTMENT: 'Căn hộ chung cư',
  LAND: 'Đất nền',
  VILLA: 'Biệt thự',
}

export function requestsMarketResearch(filters = {}) {
  return filters?.includeResearch === true
    || String(filters?.source ?? '').trim().toUpperCase() === 'TINIX_RESEARCH'
}

/** Builds the query string for GET /properties/market-analytics. */
export function buildAnalyticsQuery(filters = {}, options = {}) {
  const allowResearch = options.allowResearch !== false
  const params = new URLSearchParams()
  if (filters.district) params.set('district', String(filters.district).trim())
  if (filters.ward) params.set('ward', String(filters.ward).trim())
  if (filters.propertyType) params.set('propertyType', String(filters.propertyType))
  const source = filters.source ? String(filters.source).trim() : ''
  if (source && source !== 'ALL' && (allowResearch || source.toUpperCase() !== 'TINIX_RESEARCH')) {
    params.set('source', source)
  }
  params.set('includeResearch', allowResearch && filters.includeResearch === true ? 'true' : 'false')
  return params.toString()
}

const FORBIDDEN_KEYS = ['contactPhone', 'contactEmail', 'address_raw', 'ownerId', 'sampleListingCount']
const FORBIDDEN_TERMS = ['"forecast"', '"growthRate"', '"cagr"']

/** Rejects malformed / unsafe payloads instead of rendering half a report. */
export function validateMarketAnalytics(data, options = {}) {
  if (!data || typeof data !== 'object' || !data.meta || !data.overall) {
    throw new Error('Dữ liệu thị trường không đúng định dạng hợp đồng.')
  }
  for (const key of ['byDistrict', 'byPropertyType', 'bySource', 'priceBands', 'areaBands', 'monthly', 'warnings']) {
    if (key !== 'warnings' && !Array.isArray(data[key])) throw new Error('Dữ liệu thị trường thiếu mảng ' + key + '.')
  }
  if (!Array.isArray(data.meta.dataQualityWarnings)) throw new Error('Thiếu cảnh báo chất lượng dữ liệu.')
  if (typeof data.meta.disclaimer !== 'string' || !data.meta.disclaimer) throw new Error('Thiếu tuyên bố miễn trừ (disclaimer).')
  if (data.meta.priceBasis !== 'ASKING_SALE_VND_TOTAL') throw new Error('Cơ sở giá không phải giá rao bán tổng.')

  const allowResearch = options.allowResearch !== undefined
    ? options.allowResearch === true
    : data.meta.researchIncluded === true

  if (!allowResearch && data.meta.researchIncluded === true) {
    throw new Error('Phản hồi chứa dữ liệu nghiên cứu không được phép ở chế độ công khai.')
  }
  if (!data.meta.researchIncluded) {
    if (data.meta.researchLicense != null
        || data.monthly.length > 0
        || data.bySource.some((s) => s?.source === 'TINIX_RESEARCH' || s?.researchReference === true)
        || data.meta.dataQualityWarnings.some((w) => typeof w === 'string' && (w.includes('TINIX') || w.includes('CC BY-NC')))) {
      throw new Error('Phản hồi chế độ công khai chứa siêu dữ liệu nghiên cứu TiniX không hợp lệ.')
    }
  }

  const raw = JSON.stringify(data)
  if (FORBIDDEN_KEYS.some((k) => raw.includes(k))) {
    throw new Error('Phản hồi chứa trường thông tin không được phép (PII/nội bộ).')
  }
  if (FORBIDDEN_TERMS.some((t) => raw.includes(t))) {
    throw new Error('Phản hồi chứa trường dự báo; hệ thống không hỗ trợ dự báo giá.')
  }
  for (const stat of [data.overall, ...data.byDistrict, ...data.byPropertyType]) {
    if (typeof stat.count !== 'number' || stat.count < 0) throw new Error('Sample count không hợp lệ.')
  }
  return data
}

export async function loadMarketAnalytics(filters = {}, client = api, options = {}) {
  const allowResearch = options.allowResearch !== undefined
    ? options.allowResearch === true
    : requestsMarketResearch(filters)
  const wantsResearch = allowResearch && requestsMarketResearch(filters)
  if (requestsMarketResearch(filters) && !wantsResearch) {
    const err = new Error('Chế độ dữ liệu nghiên cứu yêu cầu phiên ADMIN hợp lệ và cấu hình máy chủ được bật.')
    err.status = 403
    throw err
  }
  if (wantsResearch && typeof options.getSession === 'function') {
    const snap = options.getSession()
    if (!marketResearchActorKey(snap)) {
      const err = new Error('Chế độ dữ liệu nghiên cứu yêu cầu phiên ADMIN hợp lệ.')
      err.status = 403
      throw err
    }
  }
  const query = buildAnalyticsQuery(filters, { allowResearch: wantsResearch })
  const requestOptions = { authenticated: wantsResearch }
  if (options.signal) requestOptions.signal = options.signal
  const data = await client('/properties/market-analytics?' + query, requestOptions)
  return validateMarketAnalytics(data, { allowResearch: wantsResearch })
}

export function isInsufficient(stat) {
  return !stat || stat.dataStatus === 'INSUFFICIENT_DATA' || stat.count === 0
}

/** VND → compact "x,y tỷ"; '' when the value is suppressed. */
export function formatBillion(value) {
  if (value == null) return ''
  const n = Number(value)
  if (!Number.isFinite(n)) return ''
  return (n / 1e9).toLocaleString('vi-VN', { maximumFractionDigits: 2 }) + ' tỷ'
}

/** VND/m² → "x,y triệu/m²". */
export function formatPerSqm(value) {
  if (value == null) return ''
  const n = Number(value)
  if (!Number.isFinite(n)) return ''
  return (n / 1e6).toLocaleString('vi-VN', { maximumFractionDigits: 1 }) + ' triệu/m²'
}

export function formatArea(value) {
  if (value == null) return ''
  const n = Number(value)
  return Number.isFinite(n) ? n.toLocaleString('vi-VN', { maximumFractionDigits: 1 }) + ' m²' : ''
}

export function formatCount(value) {
  const n = Number(value)
  return Number.isFinite(n) ? n.toLocaleString('vi-VN') : '0'
}

/** Percent of a bar relative to the tallest bar. */
export function bandWidth(count, bands) {
  const max = Math.max(1, ...bands.map((b) => Number(b.count) || 0))
  return Math.round(((Number(count) || 0) / max) * 100)
}
