// Presentation-only projection. API packets, ranking and provenance stay untouched.
import { publicChatResponse, formatChatNumber, displayEvidenceText, citationHref } from './chat.js'
import { advisorListingUrl, advisorWarning } from './advisor.js'

export function compactChatPrice(value) {
  const exact = formatChatNumber(value)
  const [whole, fraction = ''] = String(value).split('.')
  const scaled = BigInt(whole) * 100000000n + BigInt(fraction.padEnd(8, '0'))
  const divisor = scaled >= 100000000000000000n ? 1000000000n : scaled >= 100000000000000n ? 1000000n : 1n
  const unit = divisor === 1000000000n ? 'tỷ đồng' : divisor === 1000000n ? 'triệu đồng' : 'đồng'
  const base = divisor * 100000000n
  const remainder = (scaled % base).toString().padStart(base.toString().length - 1, '0').replace(/0+$/, '')
  // Never round money to make it fit: unusual precision uses the exact VND value.
  if (remainder.length > 6 || divisor === 1n) return { text: exact + ' đồng', exact: exact + ' đồng' }
  return { text: formatChatNumber(String(scaled / base)) + (remainder ? ',' + remainder : '') + ' ' + unit, exact: exact + ' đồng' }
}

export function chatPresentation(packet) {
  const data = publicChatResponse(packet)
  const count = data.recommendedProperties.length
  const noMatches = data.evidence.responseKind === 'NO_MATCHES'
  // A clarification is a normal answer, not a model outage: the question itself must be
  // visible, never hidden behind the collapsed raw-answer panel.
  const clarification = data.evidence.responseKind === 'CLARIFICATION_REQUIRED' ? data.answer : null
  const cards = data.recommendedProperties.map(p => {
    const budgetFit = p.scoreBreakdown?.budgetFit
    const validBudgetFit = budgetFit != null && Number.isFinite(Number(budgetFit)) && Number(budgetFit) >= 0 && Number(budgetFit) <= 100
    const preferenceReason = p.explanations.find(note => note.includes('Ưu tiên do người dùng'))
    const reason = preferenceReason || (validBudgetFit ? 'Mức phù hợp ngân sách: ' + formatChatNumber(budgetFit) + '/100.' : p.explanations[0] || '')
    const fitLabels = {budgetFit: 'Ngân sách', areaFit: 'Diện tích', propertyTypeFit: 'Loại BĐS', amenityFit: 'Tiện ích'}
    const reasons = []
    for (const [key, label] of Object.entries(fitLabels)) {
      const value = p.scoreBreakdown?.[key]
      if (value != null && Number.isFinite(Number(value)) && Number(value) >= 0 && Number(value) <= 100) {
        reasons.push(`${label}: ${formatChatNumber(value)}/100`)
      }
    }
    for (const explanation of p.explanations || []) {
      const text = displayEvidenceText(explanation)
      if (text && !reasons.includes(text)) reasons.push(text)
    }
    if (!reasons.length && reason) reasons.push(displayEvidenceText(reason))
    const nearbyPois = Array.isArray(p.nearbyPois) ? p.nearbyPois.filter(x => x && typeof x.name === 'string' && Number.isFinite(Number(x.distanceMeters))).slice(0, 6).map(x => ({
      name: x.name, category: x.category,
      label: {SCHOOL:'Trường học',HOSPITAL:'Y tế',PHARMACY:'Nhà thuốc',MARKET:'Chợ',SUPERMARKET:'Siêu thị',PARK:'Công viên',BEACH:'Bãi biển',PUBLIC_TRANSPORT:'Giao thông công cộng',TRANSPORT:'Giao thông',EDUCATION:'Giáo dục',HEALTH:'Y tế',HEALTHCARE:'Y tế',SHOPPING:'Mua sắm',LEISURE:'Không gian xanh'}[x.category] || displayEvidenceText(x.category || '') || 'Tiện ích',
      distance: Number(x.distanceMeters) < 1000 ? Math.round(Number(x.distanceMeters)) + ' m' : (Number(x.distanceMeters) / 1000).toFixed(1) + ' km'
    })) : []
    const nearbyPoisStatus = p.nearbyPoisStatus || (nearbyPois.length ? 'AVAILABLE' : 'UNAVAILABLE')
    const nearbyPoisNote = nearbyPoisStatus === 'NO_POIS_IN_RADIUS'
      ? 'Không có POI trong bán kính 1 km theo dữ liệu hiện có.'
      : nearbyPoisStatus === 'PROPERTY_NOT_PUBLIC'
        ? 'Tin không còn công khai nên không thể đối chiếu POI.'
        : nearbyPoisStatus === 'UNAVAILABLE'
          ? 'Chưa tải được dữ liệu POI cho tin này.'
          : 'Khoảng cách là đường chim bay; chưa tính thời gian di chuyển thực tế.'
    return { id: p.id, title: p.title, location: [p.ward, p.district].filter(Boolean).join(', ') || 'Nguồn chưa có địa bàn',
      price: compactChatPrice(p.priceVnd), area: formatChatNumber(p.areaSqm), score: formatChatNumber(p.score),
      reason: displayEvidenceText(reason), reasons: reasons.slice(0, 5), href: advisorListingUrl(p), platform: p.source.kind === 'PROPERTY',
      imageUrl: typeof p.imageUrl === 'string' && p.imageUrl.startsWith('/api/v1/properties/') && !p.imageUrl.includes('..') && !p.imageUrl.includes('//') ? p.imageUrl : null,
      nearbyPois, nearbyPoisStatus, nearbyPoisNote,
      warnings: p.warnings.map(advisorWarning), sourceName: p.source.name }
  })
  const areaSources = data.citations.filter(c => ['AREA_AMENITY', 'POI_EVIDENCE'].includes(c.kind))
  let summary
  if (clarification) summary = 'Mình cần thêm một chi tiết để trả lời chính xác.'
  else if (count) summary = `Mình tìm thấy ${count} bất động sản công khai phù hợp với nhu cầu đã gửi.` +
    (count > 3 ? ' Dưới đây là 3 lựa chọn đứng đầu danh sách.' : ' Bạn có thể xem thông tin bên dưới.') +
    (count < 3 ? ' Hiện có ít kết quả; có thể nới ngân sách, mở rộng khu vực hoặc giảm diện tích tối thiểu.' : '')
  else if (noMatches || data.evidence.criteria?.budgetVnd) summary = 'Hiện chưa tìm thấy bất động sản công khai phù hợp trong dữ liệu hiện có. Bạn có thể nới ngân sách, mở rộng khu vực, giảm diện tích tối thiểu hoặc đổi loại bất động sản; hệ thống không tự bỏ qua ngân sách.'
  else if (areaSources.length) summary = `Mình tìm được ${areaSources.length} nguồn dẫn chứng tiện ích trong hồ sơ khu vực. Bạn có thể mở nguồn bên dưới để đối chiếu; đây không phải khoảng cách từ một căn nhà.`
  else summary = 'Chưa có bằng chứng công khai phù hợp để trả lời. Bạn có thể nêu rõ ngân sách và khu vực muốn tìm.'
  return { summary, clarification, cards, noMatches, generated: data.generationMode === 'QWEN_GROUNDED_ANSWER',
    fallback: data.generationMode === 'EVIDENCE_ONLY' && !noMatches && !clarification,
    citations: data.citations.map((c, index) => {
      const property = data.recommendedProperties.find(p => c.sourceId === 'recommendation:' + p.id)
      return { ...c, number: index + 1, href: citationHref(c, data.recommendedProperties),
        label: property ? property.title : c.kind === 'AREA_AMENITY' ? 'Hồ sơ tiện ích khu vực' : 'Bằng chứng địa điểm tiện ích',
        basis: property ? 'Thông tin bất động sản' : 'Bằng chứng cấp khu vực; không xác định khoảng cách tới căn nhà' }
    }),
    originalAnswer: data.answer, limitations: data.dataLimitations }
}

export const isNearChatBottom = (element, threshold = 88) => !element || element.scrollHeight - element.clientHeight - element.scrollTop <= threshold
