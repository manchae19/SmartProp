import { publicMapPoint, locationLabel } from '../map/locationDisplay.js'
import { nearbyPlaces, poiHasPoint } from '../map/nearbyPlaces.js'

const PURPOSES = new Set(['LIVING', 'INVESTMENT', 'RENTAL'])
const TYPES = new Set(['ALL', 'HOUSE', 'APARTMENT', 'LAND', 'VILLA', 'ROOM', 'COMMERCIAL'])
const EVIDENCE_BASES = new Set(['DIRECT_WARD_EVIDENCE', 'DISTRICT_SHARED_AMENITY', 'NO_AREA_MATCH'])
const AMENITY_LEVELS = new Set(['WARD', 'DISTRICT', 'UNKNOWN'])
const COMPARABLE_KINDS = new Set(['SMARTPROP', 'EXTERNAL_LISTING', 'TINIX_RESEARCH'])
const LOCATION_PRECISIONS = new Set(['VERIFIED_PROPERTY_PIN', 'WARD_FALLBACK', 'DISTRICT_FALLBACK', 'CITY_FALLBACK'])

export function parseAdvisorBudget(value) {
  const raw = String(value ?? '').trim()
  if (!/^(?:\d+|[1-9]\d{0,2}(?:\.\d{3})+)$/.test(raw)) {
    throw Error('Nhập ngân sách bằng số nguyên VNĐ, ví dụ 2.500.000.000; không dùng số âm hoặc số thập phân.')
  }
  if (raw.length > 40) throw Error('Ngân sách không được vượt quá 999.999.999.999.999 VNĐ.')
  const amount = BigInt(raw.replaceAll('.', ''))
  if (amount < 1n || amount > 999999999999999n) {
    throw Error('Ngân sách phải từ 1 đến 999.999.999.999.999 VNĐ.')
  }
  return Number(amount)
}

export const formatAdvisorBudget = value => new Intl.NumberFormat('vi-VN').format(parseAdvisorBudget(value))

export function effectiveBudgetPreview(budgetInput, flexibilityPct = 0) {
  const base = parseAdvisorBudget(budgetInput)
  const flex = Number(flexibilityPct ?? 0)
  if (!Number.isInteger(flex) || flex < 0 || flex > 30) {
    throw Error('Biên ngân sách linh hoạt phải từ 0% đến 30%.')
  }
  const ceiling = Math.min(999999999999999, Math.round(base * (100 + flex) / 100))
  return { statedBudgetVnd: base, budgetFlexibilityPct: flex, effectiveCeilingVnd: ceiling }
}

export function advisorConsultRequest(form) {
  let budgetVnd
  if (form.budgetVnd != null && String(form.budgetVnd).trim() !== '') {
    budgetVnd = parseAdvisorBudget(form.budgetVnd)
  } else {
    const raw = String(form.budgetBillions ?? '').trim()
    if (raw.length > 40 || !/^\d+(?:[.,]\d{1,9})?$/.test(raw)) {
      throw Error('Nhập ngân sách bằng số, đơn vị VNĐ hoặc tỷ đồng (ví dụ: 2.500.000.000).')
    }
    const [whole, fraction = ''] = raw.split(/[.,]/)
    budgetVnd = parseAdvisorBudget(String(BigInt(whole) * 1000000000n + BigInt(fraction.padEnd(9, '0'))))
  }

  const flex = Number(form.budgetFlexibilityPct ?? 0)
  if (!Number.isInteger(flex) || flex < 0 || flex > 30) {
    throw Error('Biên ngân sách linh hoạt phải là số nguyên từ 0% đến 30%.')
  }

  if (!PURPOSES.has(form.purpose) || !TYPES.has(form.propertyType)) {
    throw Error('Chọn mục đích mua và loại bất động sản hợp lệ.')
  }

  const limit = Number(form.limit ?? 5)
  if (!Number.isInteger(limit) || limit < 1 || limit > 10) {
    throw Error('Số lượng đề xuất phải từ 1 đến 10.')
  }

  const body = {
    budgetVnd,
    budgetFlexibilityPct: flex,
    purpose: form.purpose,
    propertyType: form.propertyType,
    limit,
    includeComparables: form.includeComparables !== false,
    includeValuation: form.includeValuation !== false,
    includeResearch: form.includeResearch === true,
  }

  if (form.minAreaSqm !== '' && form.minAreaSqm != null) {
    const area = Number(form.minAreaSqm)
    if (!Number.isFinite(area) || area <= 0 || area > 1e6) {
      throw Error('Diện tích tối thiểu phải lớn hơn 0 và không quá 1.000.000 m².')
    }
    body.minAreaSqm = area
  }

  const district = String(form.district ?? '').trim()
  if (district.length > 100) throw Error('Địa bàn không được vượt quá 100 ký tự.')
  if (district && district.toUpperCase() !== 'ALL' && district !== 'Tất cả') {
    body.district = district
  }

  const ward = String(form.ward ?? '').trim()
  if (ward.length > 100) throw Error('Phường/xã không được vượt quá 100 ký tự.')
  if (ward && ward.toUpperCase() !== 'ALL' && ward !== 'Tất cả') {
    body.ward = ward
  }

  return body
}

// Legacy alias kept for compatibility
export const advisorRequest = advisorConsultRequest

function validScore100(v) {
  return v == null || (Number.isFinite(v) && v >= 0 && v <= 100)
}

function validStringList(v) {
  return Array.isArray(v) && v.every(s => typeof s === 'string')
}

export function validateAmenityEvidence(value) {
  if (value == null) return null
  if (typeof value !== 'object' || !EVIDENCE_BASES.has(value.evidenceBasis) || !AMENITY_LEVELS.has(value.areaLevel)) {
    throw Error('Bằng chứng tiện ích không hợp lệ.')
  }
  if (!validScore100(value.areaAmenityScore) || !validScore100(value.amenityFit)) {
    throw Error('Điểm tiện ích nằm ngoài khoảng [0, 100].')
  }
  if (!Number.isFinite(value.confidence) || value.confidence < 0 || value.confidence > 1) {
    throw Error('Độ tin cậy tiện ích không hợp lệ.')
  }
  const serialized = JSON.stringify(value)
  if (serialized.includes('sampleListingCount')) {
    throw Error('Bằng chứng tiện ích chứa dữ liệu nghiên cứu nội bộ bị hạn chế.')
  }
  return value
}

export function validateLocationIntelligence(loc, prop) {
  if (loc == null) return null
  if (typeof loc !== 'object' || !LOCATION_PRECISIONS.has(loc.locationPrecision) || typeof loc.mapEligible !== 'boolean') {
    throw Error('Thông tin trí tuệ không gian (locationIntelligence) không đúng định dạng.')
  }
  const isResearchOrNonPlatform = Boolean(prop?.researchReference) || prop?.source?.kind !== 'PROPERTY'
  if (isResearchOrNonPlatform && (loc.mapEligible || loc.latitude != null || loc.longitude != null || (Array.isArray(loc.nearbyPois) && loc.nearbyPois.length > 0))) {
    throw Error('Bản ghi nghiên cứu TiniX hoặc nguồn ngoài không được phép chứa tọa độ ghim hay khoảng cách tiện ích cấp căn.')
  }
  if (loc.mapEligible) {
    if (!Number.isFinite(loc.latitude) || !Number.isFinite(loc.longitude)
        || (loc.latitude === 0 && loc.longitude === 0)
        || loc.latitude < 15.8 || loc.latitude > 16.3
        || loc.longitude < 107.7 || loc.longitude > 108.5) {
      throw Error('Tọa độ ghim bản đồ nằm ngoài khung địa lý Đà Nẵng hợp lệ.')
    }
    if (!Array.isArray(loc.nearbyPois)) {
      throw Error('Danh sách tiện ích lân cận (nearbyPois) phải là mảng.')
    }
    for (const poi of loc.nearbyPois) {
      if (!poiHasPoint(poi) || !Number.isFinite(poi.distanceMeters) || poi.distanceMeters < 0 || poi.distanceMeters > 5000) {
        throw Error('Tiện ích lân cận chứa tọa độ hoặc khoảng cách mét không hợp lệ.')
      }
    }
  } else {
    if (loc.latitude != null || loc.longitude != null || (Array.isArray(loc.nearbyPois) && loc.nearbyPois.length > 0)) {
      throw Error('Bất động sản không đủ điều kiện bản đồ (mapEligible=false) không được đính kèm tọa độ hoặc POI cấp căn.')
    }
  }
  return loc
}

function hasResearchLeakText(list) {
  return Array.isArray(list) && list.some(s =>
    typeof s === 'string' && (
      s.startsWith('RESEARCH_COMPARABLES_LABEL:')
      || s.includes('TINIX_RESEARCH')
      || s.includes('CC BY-NC')
      || s.startsWith('INTERNAL_DEMO:')
    )
  )
}

export function isResearchComparableItem(item) {
  return Boolean(
    item && (
      item.sourceKind === 'TINIX_RESEARCH'
      || item.researchReference === true
      || item.datasetLicense === 'CC BY-NC 4.0'
      || String(item.candidateId ?? '').startsWith('tnx-')
    )
  )
}

export function visibleAdvisorComparables(comparable, mode = 'SAFE', allowResearch = false) {
  const list = Array.isArray(comparable?.comparables) ? comparable.comparables : []
  const permitResearch = mode === 'INTERNAL_RESEARCH' && allowResearch === true
  return permitResearch ? list : list.filter(item => !isResearchComparableItem(item))
}

export function validateAdvisorResponse(data, options = {}) {
  if (!data || typeof data !== 'object'
      || data.advisorVersion !== 'ADVISOR_ORCHESTRATOR_V1'
      || !['SAFE', 'INTERNAL_RESEARCH'].includes(data.mode)
      || !Array.isArray(data.topAreas)
      || !Array.isArray(data.recommendedProperties)
      || !validStringList(data.warnings)
      || !data.serviceStatus) {
    throw Error('Phản hồi từ AI Advisor không đúng định dạng hợp đồng.')
  }

  const allowResearch = options.allowResearch !== undefined ? options.allowResearch === true : data.mode === 'INTERNAL_RESEARCH'
  if (!allowResearch && data.mode !== 'SAFE') {
    throw Error('Chế độ dữ liệu nghiên cứu không được phép khi truy vấn ở chế độ công khai SAFE.')
  }
  if (data.mode === 'SAFE' && (data.criteria?.includeResearch === true || hasResearchLeakText(data.warnings))) {
    throw Error('Phản hồi SAFE chứa cờ hoặc cảnh báo dữ liệu nghiên cứu nội bộ.')
  }

  const rawJson = JSON.stringify(data)
  if (rawJson.includes('contactPhone') || rawJson.includes('contactEmail') || rawJson.includes('sampleListingCount')) {
    throw Error('Phản hồi chứa trường dữ liệu hạn chế hoặc thông tin liên hệ cá nhân.')
  }

  if (data.recommendedProperties.length > 10 || data.topAreas.length > 5) {
    throw Error('Số lượng kết quả vượt quá giới hạn hợp đồng.')
  }

  const seenIds = new Set()
  for (const prop of data.recommendedProperties) {
    if (!prop || typeof prop.id !== 'string' || !prop.id.trim() || seenIds.has(prop.id)) {
      throw Error('Danh sách bất động sản đề xuất có ID thiếu hoặc trùng lặp.')
    }
    seenIds.add(prop.id)

    if (prop.isProtectedHoldout || prop.protectedHoldout || prop.is_protected_holdout) {
      throw Error('Phát hiện bản ghi holdout được bảo vệ trong kết quả.')
    }
    if (data.mode === 'SAFE' && (!prop.liveListing || prop.researchReference || prop.source?.kind === 'TINIX_AI' || hasResearchLeakText(prop.warnings) || hasResearchLeakText(prop.fitReasons))) {
      throw Error('Chế độ công khai SAFE không được phép trả bản ghi nghiên cứu TiniX.')
    }
    if (prop.researchReference && prop.source?.detailUrl != null) {
      throw Error('Bản ghi nghiên cứu không được phép có URL tin gốc.')
    }
    if (!Number.isFinite(Number(prop.priceVnd)) || Number(prop.priceVnd) <= 0
        || !Number.isFinite(Number(prop.areaSqm)) || Number(prop.areaSqm) <= 0
        || !validScore100(prop.recommendationScore)) {
      throw Error('Thông số giá, diện tích hoặc điểm phù hợp không hợp lệ.')
    }

    validateAmenityEvidence(prop.amenityEvidence)
    validateLocationIntelligence(prop.locationIntelligence, prop)

    // Validate Comparable Evidence
    if (prop.comparableEvidence) {
      const comp = prop.comparableEvidence
      if (!Array.isArray(comp.comparables) || comp.comparables.length > 5) {
        throw Error('Bằng chứng bất động sản tương đồng không hợp lệ.')
      }
      if (data.mode === 'SAFE' && hasResearchLeakText(comp.warnings)) {
        throw Error('Bằng chứng tương đồng ở chế độ SAFE chứa metadata nghiên cứu không hợp lệ.')
      }
      for (const item of comp.comparables) {
        if (!COMPARABLE_KINDS.has(item.sourceKind)) {
          throw Error('Nguồn bất động sản tương đồng không xác định.')
        }
        if (data.mode === 'SAFE' && isResearchComparableItem(item)) {
          throw Error('Chế độ công khai SAFE không được phép chứa bằng chứng tương đồng từ nguồn nghiên cứu TiniX.')
        }
        if (item.sourceKind === 'TINIX_RESEARCH') {
          if (!item.researchReference || item.liveListing || item.listingUrl != null || item.datasetLicense !== 'CC BY-NC 4.0') {
            throw Error('Dòng so sánh TiniX thiếu nhãn nghiên cứu hoặc chứa liên kết không hợp lệ.')
          }
        }
      }
    }

    // Validate Valuation & TreeSHAP Evidence
    if (prop.valuationEvidence) {
      const val = prop.valuationEvidence
      if (val.available) {
        if (val.modelVersion !== 'v1.3' || !Number.isFinite(Number(val.predictedAskingPriceVnd)) || Number(val.predictedAskingPriceVnd) <= 0) {
          throw Error('Bằng chứng định giá V1.3 thiếu giá hợp lệ hoặc sai phiên bản mô hình.')
        }
      } else if (val.predictedAskingPriceVnd != null) {
        throw Error('Không được hiển thị giá dự đoán khi định giá AI không khả dụng.')
      }
    }
  }

  return data
}

export const createAdvisorConsultClient = (request, getSession = null) => async form => {
  const body = advisorConsultRequest(form)
  if (body.includeResearch === true && typeof getSession === 'function') {
    const snap = getSession()
    if (snap?.status !== 'AUTHENTICATED' || snap?.user?.role !== 'ADMIN') {
      const err = new Error('Chế độ dữ liệu nghiên cứu yêu cầu phiên ADMIN hợp lệ.')
      err.status = 403
      throw err
    }
  }
  const data = await request('/advisor/consult', {
    method: 'POST',
    authenticated: body.includeResearch === true,
    body,
  })
  return validateAdvisorResponse(data, { allowResearch: body.includeResearch === true })
}

export function safeAdvisorPropertyUrl(property) {
  if (!property || property.researchReference || property.source?.kind === 'TINIX_AI') return null
  if (property.source?.kind === 'PROPERTY') {
    const key = String(property.source.recordKey ?? '').trim()
    return /^[\w-]{1,64}$/.test(key) ? '/listing/' + encodeURIComponent(key) : null
  }
  try {
    const url = new URL(property.source?.detailUrl)
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null
  } catch {
    return null
  }
}

export function safeComparableItemUrl(item) {
  if (!item || item.researchReference || item.sourceKind === 'TINIX_RESEARCH') return null
  const raw = typeof item.listingUrl === 'string' ? item.listingUrl.trim() : ''
  if (!raw) return null
  if (item.sourceKind === 'SMARTPROP') {
    return /^\/listing\/[\w-]{1,64}$/.test(raw) ? raw : null
  }
  try {
    const url = new URL(raw)
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null
  } catch {
    return null
  }
}

export function advisorSelectedPois(property) {
  const loc = property?.locationIntelligence
  if (!property || property.researchReference || property.source?.kind !== 'PROPERTY' || !loc?.mapEligible) {
    return []
  }
  const radius = Number.isFinite(loc.nearbyPoiRadiusMeters) ? loc.nearbyPoiRadiusMeters : 1500
  return nearbyPlaces(loc.nearbyPois || [], radius).filter(poiHasPoint)
}

export async function advisorMapData(properties, request) {
  if (!Array.isArray(properties) || !properties.length) {
    return { points: [], failedCount: 0, unlocatedCount: 0 }
  }

  // Fast path (Step 21.4C): use server-verified locationIntelligence directly without N+1 HTTP calls
  if (properties.some(p => p.locationIntelligence != null)) {
    const points = []
    for (const p of properties) {
      const loc = p.locationIntelligence
      if (p.source?.kind === 'PROPERTY'
          && !p.researchReference
          && loc?.mapEligible === true
          && Number.isFinite(loc.latitude)
          && Number.isFinite(loc.longitude)
          && !(loc.latitude === 0 && loc.longitude === 0)) {
        points.push({
          id: p.id,
          title: p.title,
          latitude: loc.latitude,
          longitude: loc.longitude,
          price: p.priceVnd,
          currency: 'VND',
          priceUnit: 'TOTAL',
          transactionType: 'SALE',
          locationLabel: loc.displayLabel || locationLabel({ district: p.district, ward: p.ward, city: 'Đà Nẵng' }),
        })
      }
    }
    return {
      points,
      failedCount: 0,
      unlocatedCount: properties.length - points.length,
    }
  }

  // Legacy fallback when locationIntelligence is omitted in Step 21.3 mock fixtures
  const results = await Promise.allSettled(
    properties
      .filter(p => p.source?.kind === 'PROPERTY' && p.source.recordKey && !p.researchReference)
      .map(async p => {
        const detail = await request('/properties/' + encodeURIComponent(p.source.recordKey))
        if (detail.id !== p.source.recordKey
            || detail.status !== 'PUBLISHED'
            || !publicMapPoint(detail)
            || !Number.isFinite(detail.latitude)
            || !Number.isFinite(detail.longitude)
            || Math.abs(detail.latitude) > 85.05112878
            || Math.abs(detail.longitude) > 180
            || (detail.latitude === 0 && detail.longitude === 0)) {
          return null
        }
        return {
          id: p.id,
          title: p.title,
          latitude: detail.latitude,
          longitude: detail.longitude,
          price: p.priceVnd,
          currency: 'VND',
          priceUnit: 'TOTAL',
          transactionType: 'SALE',
          locationLabel: locationLabel(detail),
        }
      })
  )
  const points = results.filter(r => r.status === 'fulfilled' && r.value).map(r => r.value)
  return {
    points,
    failedCount: results.filter(r => r.status === 'rejected').length,
    unlocatedCount: properties.length - points.length,
  }
}

export function advisorError(error) {
  if (error?.status === 401) return 'Phiên đăng nhập không hợp lệ hoặc đã hết hạn.'
  if (error?.status === 403) return 'Chế độ dữ liệu nghiên cứu yêu cầu quyền quản trị/môi giới hợp lệ và được bật trên máy chủ.'
  if (error?.status === 429) return 'Bạn đã gửi nhiều yêu cầu liên tiếp. Vui lòng chờ ít giây rồi thử lại.'
  if (error?.status >= 500) return 'Dịch vụ AI Advisor đang tạm gián đoạn. Vui lòng thử lại sau.'
  return error?.message || 'Chưa thể tải kết quả tư vấn. Vui lòng kiểm tra kết nối và thử lại.'
}

export function advisorWarning(text) {
  if (!text) return ''
  if (text.startsWith('HEURISTIC_V1:')) return 'Điểm phù hợp được tính theo quy tắc tham khảo, không phải xác suất hay dự báo lợi nhuận.'
  if (text.startsWith('HEURISTIC_V1_1:')) return 'Điểm phù hợp V1.1 là quy tắc có trọng số (ngân sách, diện tích, loại BĐS, tiện ích khu vực); không phải xác suất đã hiệu chuẩn.'
  if (text.startsWith('PURPOSE_WEIGHTS:')) return 'Trọng số tiện ích được điều chỉnh theo mục đích mua để không lấn át tiêu chí tài chính.'
  if (text.startsWith('NO_AMENITY_EVIDENCE:')) return 'Khu vực chưa có hồ sơ tiện ích đã kiểm chứng; điểm không cộng thành phần tiện ích thay vì trừ điểm.'
  if (text.startsWith('AMENITY_IS_DISTRICT_SHARED:')) return 'Tiện ích được xác định ở cấp quận/huyện, không phải khoảng cách trực tiếp từ căn nhà.'
  if (text.startsWith('AMENITY_COVERAGE_GAPS:')) return 'Hồ sơ tiện ích còn thiếu dữ liệu số hóa ở một số nhóm tiện ích.'
  if (text.startsWith('FLEXIBLE_BUDGET:')) return text.replace('FLEXIBLE_BUDGET: ', '')
  if (text.startsWith('FLEXIBLE_BUDGET_ITEM:')) return 'Giá rao vượt ngân sách gốc nhưng nằm trong biên linh hoạt bạn đã cho phép.'
  if (text.startsWith('VALUATION_SERVICE_UNAVAILABLE:')) return text.replace('VALUATION_SERVICE_UNAVAILABLE: ', '')
  if (text.startsWith('RESEARCH_COMPARABLES_LABEL:')) return text.replace('RESEARCH_COMPARABLES_LABEL: ', '')
  if (text.startsWith('NO_ELIGIBLE_CANDIDATES:')) return text.replace('NO_ELIGIBLE_CANDIDATES: ', '')
  if (text.startsWith('LOCATION_NORMALIZATION:')) return text.replace('LOCATION_NORMALIZATION: ', '')
  if (text.startsWith('GIS_COORDINATE_MISMATCH:')) return text.replace('GIS_COORDINATE_MISMATCH: ', '')
  return text
}

