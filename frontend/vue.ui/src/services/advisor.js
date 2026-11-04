import { publicMapPoint, locationLabel } from './locationDisplay.js'

const purposes = new Set(['LIVING', 'INVESTMENT', 'RENTAL'])
const types = new Set(['ALL', 'HOUSE', 'APARTMENT', 'LAND', 'VILLA', 'ROOM', 'COMMERCIAL'])

export function parseAdvisorBudget(value) {
  const raw = String(value ?? '').trim()
  if (!/^(?:\d+|[1-9]\d{0,2}(?:\.\d{3})+)$/.test(raw)) throw Error('Nhập ngân sách bằng số nguyên VNĐ, ví dụ 2.350.000.000; không dùng số âm hoặc số thập phân.')
  if (raw.length > 40) throw Error('Ngân sách không được vượt quá 999.999.999.999.999 VNĐ.')
  const amount = BigInt(raw.replaceAll('.', ''))
  if (amount < 1n || amount > 999999999999999n) throw Error('Ngân sách phải từ 1 đến 999.999.999.999.999 VNĐ.')
  return Number(amount) // The contract maximum is below Number.MAX_SAFE_INTEGER.
}

export const formatAdvisorBudget = value => new Intl.NumberFormat('vi-VN').format(parseAdvisorBudget(value))

export function advisorRequest(form) {
  let budgetVnd
  if (form.budgetVnd != null) budgetVnd = parseAdvisorBudget(form.budgetVnd)
  else {
    // Compatibility for existing callers that still send billion-unit form values.
    const raw = String(form.budgetBillions ?? '').trim()
    if (raw.length > 40 || !/^\d+(?:[.,]\d{1,9})?$/.test(raw)) throw Error('Nhập ngân sách bằng số, đơn vị tỷ đồng (ví dụ: 2,5).')
    const [whole, fraction = ''] = raw.split(/[.,]/)
    budgetVnd = parseAdvisorBudget(String(BigInt(whole) * 1000000000n + BigInt(fraction.padEnd(9, '0'))))
  }
  if (!purposes.has(form.purpose) || !types.has(form.propertyType)) throw Error('Chọn mục đích và loại bất động sản hợp lệ.')
  const limit = Number(form.limit ?? 10)
  if (!Number.isInteger(limit) || limit < 1 || limit > 10) throw Error('Số kết quả phải từ 1 đến 10.')
  const body = { budgetVnd, purpose: form.purpose, propertyType: form.propertyType, limit }
  if (form.minAreaSqm !== '' && form.minAreaSqm != null) {
    const area = Number(form.minAreaSqm)
    if (!Number.isFinite(area) || area <= 0 || area > 1e6) throw Error('Diện tích tối thiểu phải lớn hơn 0 và không quá 1.000.000 m².')
    body.minAreaSqm = area
  }
  for (const key of ['district', 'ward']) {
    const value = String(form[key] ?? '').trim()
    if (value.length > 100) throw Error('Địa bàn không được vượt quá 100 ký tự.')
    if (value) body[key] = value
  }
  return body
}

const evidenceBases = new Set(['DIRECT_WARD_EVIDENCE', 'DISTRICT_SHARED_AMENITY', 'NO_AREA_MATCH'])
const amenityLevels = new Set(['WARD', 'DISTRICT', 'UNKNOWN'])

function validEvidenceScores(value) {
  return value == null || (Number.isFinite(value) && value >= 0 && value <= 100)
}
function validStringList(value) {
  return Array.isArray(value) && value.every(v => typeof v === 'string')
}

/** Validates one amenity evidence block. Rejects unknown provenance and research-only leaks. */
export function amenityEvidence(value) {
  if (value == null) return null
  if (typeof value !== 'object' || !evidenceBases.has(value.evidenceBasis) || !amenityLevels.has(value.areaLevel)) throw Error('Bằng chứng tiện ích không hợp lệ.')
  if (!validEvidenceScores(value.areaAmenityScore) || !validEvidenceScores(value.amenityFit)) throw Error('Điểm tiện ích nằm ngoài khoảng cho phép.')
  if (!Number.isFinite(value.confidence) || value.confidence < 0 || value.confidence > 1) throw Error('Độ tin cậy tiện ích không hợp lệ.')
  if (!validStringList(value.dataLimitations) || !Array.isArray(value.poiEvidence) || !value.categoryScores || typeof value.categoryScores !== 'object') throw Error('Bằng chứng tiện ích thiếu dữ liệu bắt buộc.')
  // Defence in depth: restricted research metadata must never reach the browser.
  const json = JSON.stringify(value)
  if (json.includes('sampleListingCount') || json.includes('listingCount')) throw Error('Bằng chứng tiện ích chứa dữ liệu nghiên cứu bị hạn chế.')
  if (value.poiEvidence.some(p => !p || typeof p.name !== 'string' || typeof p.category !== 'string')) throw Error('Danh sách tiện ích không hợp lệ.')
  if (Object.values(value.categoryScores).some(v => !Number.isFinite(v))) throw Error('Điểm danh mục tiện ích không hợp lệ.')
  return value
}

/** Shared V1.1 gates, applied by the public validator too so restricted data cannot slip through. */
function validateV11Payload(data) {
  if (data.method !== 'HEURISTIC_V1_1') return
  if (!data.scoringWeights || typeof data.scoringWeights !== 'object') throw Error('Kết quả tư vấn V1.1 thiếu trọng số.')
  const weights = Object.values(data.scoringWeights)
  if (weights.length !== 4 || weights.some(v => !Number.isFinite(v) || v < 0 || v > 1)) throw Error('Trọng số tư vấn V1.1 không hợp lệ.')
  for (const a of data.topAreas || []) {
    if (a == null || a.amenityScore == null) continue
    if (!Number.isFinite(a.amenityScore) || a.amenityScore < 0 || a.amenityScore > 100) throw Error('Điểm tiện ích khu vực không hợp lệ.')
    if (a.amenityConfidence != null && (!Number.isFinite(a.amenityConfidence) || a.amenityConfidence < 0 || a.amenityConfidence > 1)) throw Error('Độ tin cậy khu vực không hợp lệ.')
  }
}

export function v11AdvisorResponse(data) {
  if (data?.method !== 'HEURISTIC_V1_1' || !Array.isArray(data.topProperties) || !Array.isArray(data.topAreas)) throw Error('Kết quả tư vấn V1.1 không hợp lệ.')
  validateV11Payload(data)
  for (const p of data.topProperties) {
    amenityEvidence(p.amenityEvidence)
    if (p.scoreBreakdown && 'amenityFit' in p.scoreBreakdown && p.amenityEvidence?.areaAmenityScore == null) throw Error('Điểm tiện ích không khớp bằng chứng.')
  }
  return data
}

export function publicAdvisorResponse(data) {
  if (data?.mode !== 'SAFE' || !['HEURISTIC_V1', 'HEURISTIC_V1_1'].includes(data.method)
      || !Array.isArray(data.topProperties) || !Array.isArray(data.topAreas)) throw Error('Dịch vụ chưa cung cấp kết quả phù hợp cho truy cập công khai.')
  const strings = value => Array.isArray(value) && value.every(s => typeof s === 'string')
  const score = value => Number.isFinite(value) && value >= 0 && value <= 100
  const positive = value => Number.isFinite(value) && value > 0
  const text = value => typeof value === 'string' && value.trim().length > 0
  const ids = new Set(), groups = new Set()
  if (data.topProperties.length > 10 || data.topAreas.length > 5
      || !Number.isInteger(data.eligibleCandidateCount) || data.eligibleCandidateCount < data.topProperties.length || !strings(data.warnings)) throw Error('Dịch vụ trả về dữ liệu chưa đầy đủ. Vui lòng thử lại.')
  for (const p of data.topProperties) {
    const platform = p?.source?.kind === 'PROPERTY' && p.qualityStatus === 'PLATFORM_PUBLISHED' && p.verificationStatus === 'PLATFORM_PUBLISHED'
    const verified = p?.source?.kind === 'EXTERNAL' && p.qualityStatus === 'VALID' && p.verificationStatus === 'VERIFIED'
    if ((!platform && !verified) || p.isProtectedHoldout || p.protectedHoldout || p.is_protected_holdout) throw Error('Kết quả chưa đủ điều kiện hiển thị công khai.')
    if (!text(p.id) || ids.has(p.id) || !text(p.title) || !types.has(p.propertyType) || p.propertyType === 'ALL'
        || !positive(p.priceVnd) || !positive(p.areaSqm) || !score(p.score) || !text(p.source.name) || !text(p.source.recordKey)
        || !strings(p.explanations) || !strings(p.warnings)) throw Error('Dịch vụ trả về dữ liệu chưa đầy đủ. Vui lòng thử lại.')
    if (amenityEvidence(p.amenityEvidence) && p.scoreBreakdown && 'amenityFit' in p.scoreBreakdown && p.amenityEvidence.areaAmenityScore == null) throw Error('Điểm tiện ích không khớp bằng chứng.')
    ids.add(p.id)
    if (p.source.kind === 'EXTERNAL' && p.duplicateGroup) {
      if (groups.has(p.duplicateGroup)) throw Error('Kết quả có tin trùng. Vui lòng thử lại.')
      groups.add(p.duplicateGroup)
    }
  }
  if (data.topAreas.some(a => !a || a.unverifiedCount !== 0 || a.needsReviewCount !== 0
      || !text(a.district) || !score(a.score) || !Number.isInteger(a.candidateCount) || a.candidateCount < 1
      || !positive(a.averageAskingPriceVnd) || !strings(a.explanations) || !strings(a.sources) || !strings(a.warnings))) throw Error('Kết quả khu vực chưa đủ điều kiện hiển thị công khai.')
  if (JSON.stringify(data.topAreas).includes('sampleListingCount') || JSON.stringify(data.topProperties).includes('sampleListingCount')) throw Error('Kết quả chứa dữ liệu nghiên cứu bị hạn chế.')
  validateV11Payload(data)
  return data
}

export const createAdvisorClient = request => async form => {
  const data = await request('/recommendations', { method: 'POST', authenticated: false, body: advisorRequest(form) })
  publicAdvisorResponse(data)
  return data.method === 'HEURISTIC_V1_1' ? v11AdvisorResponse(data) : data
}

export function advisorListingUrl(property) {
  if (property.source?.kind === 'PROPERTY') return '/listing/' + encodeURIComponent(property.source.recordKey)
  try {
    const url = new URL(property.source?.detailUrl)
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null
  } catch { return null }
}

export async function advisorMapData(properties, request) {
  const results = await Promise.allSettled(properties.filter(p => p.source?.kind === 'PROPERTY').map(async p => {
    const detail = await request('/properties/' + encodeURIComponent(p.source.recordKey))
    if (detail.id !== p.source.recordKey || detail.status !== 'PUBLISHED' || !publicMapPoint(detail)
        || !Number.isFinite(detail.latitude) || !Number.isFinite(detail.longitude)
        || Math.abs(detail.latitude) > 85.05112878 || Math.abs(detail.longitude) > 180
        || detail.latitude === 0 && detail.longitude === 0) return null
    return { id: p.id, title: p.title, latitude: detail.latitude, longitude: detail.longitude,
      price: p.priceVnd, currency: 'VND', priceUnit: 'TOTAL', transactionType: 'SALE', locationLabel: locationLabel(detail) }
  }))
  const points = results.filter(r => r.status === 'fulfilled' && r.value).map(r => r.value)
  return { points, failedCount: results.filter(r => r.status === 'rejected').length, unlocatedCount: properties.length - points.length }
}

export const advisorMapPoints = async (properties, request) => (await advisorMapData(properties, request)).points

export function advisorError(error) {
  if (error?.status === 401) return 'Dịch vụ tư vấn công khai chưa sẵn sàng trên máy chủ đang kết nối. Vui lòng thử lại sau.'
  if (error?.status === 403) return 'Dịch vụ tư vấn hiện chưa mở cho truy cập công khai. Vui lòng thử lại sau.'
  if (error?.status === 429) return 'Bạn đã gửi nhiều yêu cầu. Vui lòng chờ một lát rồi thử lại.'
  if (error?.status >= 500) return 'Dịch vụ tư vấn đang tạm gián đoạn. Vui lòng thử lại sau.'
  return error?.message || 'Chưa thể tải gợi ý. Vui lòng kiểm tra kết nối và thử lại.'
}

export function advisorWarning(text) {
  if (text.startsWith('HEURISTIC_V1:')) return 'Điểm phù hợp được tính theo quy tắc tham khảo, không phải dự báo lợi nhuận hay AI cá nhân hóa đã huấn luyện.'
  if (text.startsWith('HEURISTIC_V1_1:')) return 'Điểm phù hợp V1.1 là quy tắc có trọng số (ngân sách, diện tích, loại bất động sản, tiện ích khu vực); không phải dự báo lợi nhuận.'
  if (text.startsWith('PURPOSE_WEIGHTS:')) return 'Với mục đích này, trọng số tiện ích được giảm để không lấn át tiêu chí tài chính.'
  if (text.startsWith('NO_AMENITY_EVIDENCE:')) return 'Khu vực chưa có hồ sơ tiện ích đã kiểm chứng; điểm không cộng thành phần tiện ích thay vì bị trừ điểm.'
  if (text.startsWith('AMENITY_IS_DISTRICT_SHARED:')) return 'Tiện ích được tính theo quận/huyện, không phải tiện ích nằm sát bất động sản.'
  if (text.startsWith('AMENITY_COVERAGE_GAPS:')) return 'Hồ sơ tiện ích còn thiếu trụ cột. Điểm thấp có thể do thiếu dữ liệu số hóa, không hẳn do khu vực kém tiện nghi.'
  if (text.startsWith('RENTAL là')) return 'Mua để cho thuê sử dụng tổng ngân sách mua bất động sản; chưa dự đoán giá thuê hoặc lợi suất.'
  if (text.startsWith('External chưa có ward')) return 'Một số nguồn chưa có phường/xã chuẩn hóa; không suy đoán từ địa chỉ thô.'
  if (text.startsWith('Một đại diện nhóm nghi trùng')) return 'Tin này đại diện một nhóm nghi trùng. Hãy đối chiếu nguồn và tình trạng giao dịch trước khi quyết định.'
  return text
}
