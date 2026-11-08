// Comparable listings for a valuation: same ward, then district, then neighbours.
// The backend does the filtering, ranking and eligibility; this module only
// shapes the request and normalises the response for the card.
import { api } from '../auth/api.js'

const CATEGORY_TYPES = { 'Nhà ở': 'HOUSE', 'Đất nền': 'LAND', 'Căn hộ chung cư': 'APARTMENT' }
export const COMPARABLE_DISTRICTS = ['Hải Châu', 'Thanh Khê', 'Sơn Trà', 'Ngũ Hành Sơn', 'Cẩm Lệ', 'Liên Chiểu', 'Hòa Vang']
const DISTRICT_SET = new Set(COMPARABLE_DISTRICTS)

const SOURCE_LABELS = {
  SMARTPROP: 'SmartProp',
  EXTERNAL_LISTING: 'Tin đăng bên ngoài',
  TINIX_RESEARCH: 'TiniX — nghiên cứu',
}

export function sourceKindLabel(kind) {
  return SOURCE_LABELS[kind] ?? 'Không rõ nguồn'
}

/**
 * Builds the POST body for /properties/comparables from a plain form.
 * Throws a user-facing message when the input cannot produce a comparison.
 */
export function buildComparableBody(form = {}) {
  const type = CATEGORY_TYPES[form.propertyType] ?? (['HOUSE', 'LAND', 'APARTMENT', 'VILLA'].includes(form.propertyType) ? form.propertyType : null)
  if (!type) throw new Error('Loại bất động sản này chưa có dữ liệu so sánh.')
  const district = String(form.district ?? '').trim()
  if (!DISTRICT_SET.has(district)) throw new Error('Chỉ địa bàn cấp quận/huyện mới có dữ liệu tin tương đồng.')
  const area = Number(form.areaSqm)
  if (!Number.isFinite(area) || area < 5 || area > 50000) throw new Error('Diện tích không hợp lệ để tìm tin tương đồng.')
  const body = { propertyType: type, district, areaSqm: area }
  const ward = String(form.ward ?? '').trim()
  if (ward) body.ward = ward
  const price = Number(form.priceVnd)
  if (Number.isFinite(price) && price > 0) body.priceVnd = price
  const bedrooms = Number(form.bedrooms)
  if (Number.isInteger(bedrooms) && bedrooms > 0) body.bedrooms = bedrooms
  const floors = Number(form.floors)
  if (Number.isFinite(floors) && floors > 0) body.floors = floors
  body.limit = 5
  return body
}

/** Links only survive if the server already sanitised them to http(s). */
export function safeListingLink(candidate) {
  const url = typeof candidate?.listingUrl === 'string' ? candidate.listingUrl.trim() : ''
  if (candidate?.sourceKind === 'TINIX_RESEARCH') return ''
  if (candidate?.sourceKind === 'SMARTPROP') return /^\/properties\/[\w-]{1,64}$/.test(url) ? url : ''
  return /^https?:\/\//i.test(url) ? url : ''
}

export function similarityPercent(score) {
  return Number.isFinite(score) ? Math.round(Math.max(0, Math.min(1, score)) * 100) : 0
}

export function priceDelta(candidate) {
  const raw = candidate?.priceDifferencePct
  if (typeof raw !== 'number' && typeof raw !== 'string') return ''
  const value = Number(raw)
  if (raw === '' || !Number.isFinite(value)) return ''
  const rounded = Math.abs(value) < 0.05 ? 0 : value
  return `${rounded > 0 ? '+' : ''}${rounded.toFixed(1).replace('.', ',')}% so với giá tham chiếu`
}

export function comparableWarnings(response) {
  return Array.isArray(response?.warnings) ? response.warnings.filter((w) => typeof w === 'string') : []
}

export function validateComparableResponse(data) {
  if (!data || typeof data !== 'object' || !Array.isArray(data.comparables) || !data.reference) {
    throw new Error('Dữ liệu tin tương đồng không hợp lệ.')
  }
  for (const candidate of data.comparables) {
    if (typeof candidate.candidateId !== 'string' || !SOURCE_LABELS[candidate.sourceKind]) {
      throw new Error('Dữ liệu tin tương đồng không hợp lệ.')
    }
  }
  if (data.comparables.length > 5) throw new Error('Dữ liệu tin tương đồng vượt quá giới hạn 5 kết quả.')
  return data
}

/**
 * True when the API refused the caller because comparable search needs
 * BROKER/ADMIN. The UI must not widen access; it explains the requirement.
 */
export function isForbidden(error) {
  return error?.status === 403
}

export async function loadComparables(body) {
  const data = await api('/properties/comparables', { method: 'POST', body })
  return validateComparableResponse(data)
}
