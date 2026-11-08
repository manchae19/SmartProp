// Real-data market analytics client (Step 21.5B).
// The backend aggregates real MySQL rows; this module only shapes the request,
// validates the contract and formats numbers. No value here is mock data.
import { api } from '../auth/api.js'

export const ANALYSIS_SOURCES = {
  ALL: 'Tất cả nguồn',
  SMARTPROP: 'SmartProp (đã duyệt)',
  EXTERNAL_LISTING: 'Tin ngoài (VALID)',
  TINIX_RESEARCH: 'TiniX — nghiên cứu',
}

export const PROPERTY_TYPES = {
  '': 'Tất cả loại hình',
  HOUSE: 'Nhà ở / Nhà phố',
  APARTMENT: 'Căn hộ chung cư',
  LAND: 'Đất nền',
  VILLA: 'Biệt thự',
}

/** Builds the query string for GET /properties/market-analytics. */
export function buildAnalyticsQuery(filters = {}) {
  const params = new URLSearchParams()
  if (filters.district) params.set('district', String(filters.district).trim())
  if (filters.ward) params.set('ward', String(filters.ward).trim())
  if (filters.propertyType) params.set('propertyType', String(filters.propertyType))
  if (filters.source && filters.source !== 'ALL') params.set('source', String(filters.source))
  params.set('includeResearch', filters.includeResearch === true ? 'true' : 'false')
  return params.toString()
}

const FORBIDDEN_KEYS = ['contactPhone', 'contactEmail', 'address_raw', 'ownerId', 'sampleListingCount']
const FORBIDDEN_TERMS = ['"forecast"', '"growthRate"', '"cagr"']

/** Rejects malformed / unsafe payloads instead of rendering half a report. */
export function validateMarketAnalytics(data) {
  if (!data || typeof data !== 'object' || !data.meta || !data.overall) {
    throw new Error('Dữ liệu thị trường không đúng định dạng hợp đồng.')
  }
  for (const key of ['byDistrict', 'byPropertyType', 'bySource', 'priceBands', 'areaBands', 'monthly', 'warnings']) {
    if (key !== 'warnings' && !Array.isArray(data[key])) throw new Error('Dữ liệu thị trường thiếu mảng ' + key + '.')
  }
  if (!Array.isArray(data.meta.dataQualityWarnings)) throw new Error('Thiếu cảnh báo chất lượng dữ liệu.')
  if (typeof data.meta.disclaimer !== 'string' || !data.meta.disclaimer) throw new Error('Thiếu tuyên bố miễn trừ (disclaimer).')
  if (data.meta.priceBasis !== 'ASKING_SALE_VND_TOTAL') throw new Error('Cơ sở giá không phải giá rao bán tổng.')

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

export async function loadMarketAnalytics(filters = {}) {
  const query = buildAnalyticsQuery(filters)
  const data = await api('/properties/market-analytics?' + query, { authenticated: false })
  return validateMarketAnalytics(data)
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
