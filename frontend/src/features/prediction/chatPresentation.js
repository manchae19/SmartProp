// Presentation-only projection. API packets, ranking and provenance stay untouched.
import { publicChatResponse, formatChatNumber, displayEvidenceText, citationHref } from './chat.js';
import { advisorListingUrl, advisorWarning } from './advisor.js';
export function compactChatPrice(value) {
  const exact = formatChatNumber(value);
  const [whole, fraction = ''] = String(value).split('.');
  const scaled = BigInt(whole) * 100000000n + BigInt(fraction.padEnd(8, '0'));
  const divisor = scaled >= 100000000000000000n ? 1000000000n : scaled >= 100000000000000n ? 1000000n : 1n;
  const unit = divisor === 1000000000n ? 'tỷ đồng' : divisor === 1000000n ? 'triệu đồng' : 'đồng';
  const base = divisor * 100000000n;
  const remainder = (scaled % base).toString().padStart(base.toString().length - 1, '0').replace(/0+$/, '');
  // Never round money to make it fit: unusual precision uses the exact VND value.
  if (remainder.length > 6 || divisor === 1n) return {
    text: exact + ' đồng',
    exact: exact + ' đồng'
  };
  return {
    text: formatChatNumber(String(scaled / base)) + (remainder ? ',' + remainder : '') + ' ' + unit,
    exact: exact + ' đồng'
  };
}
export function chatPresentation(packet) {
  const data = publicChatResponse(packet);
  const count = data.recommendedProperties.length;
  const noMatches = data.evidence.responseKind === 'NO_MATCHES';
  // A clarification is a normal answer, not a model outage: the question itself must be
  // visible, never hidden behind the collapsed raw-answer panel.
  const clarification = data.evidence.responseKind === 'CLARIFICATION_REQUIRED' ? data.answer : null;
  const cards = data.recommendedProperties.map(p => {
    const budgetFit = p.scoreBreakdown?.budgetFit;
    const validBudgetFit = budgetFit != null && Number.isFinite(Number(budgetFit)) && Number(budgetFit) >= 0 && Number(budgetFit) <= 100;
    const preferenceReason = p.explanations.find(note => note.includes('Ưu tiên do người dùng'));
    const reason = preferenceReason || (validBudgetFit ? 'Mức phù hợp ngân sách: ' + formatChatNumber(budgetFit) + '/100.' : p.explanations[0] || '');
    return {
      id: p.id,
      title: p.title,
      location: [p.ward, p.district].filter(Boolean).join(', ') || 'Nguồn chưa có địa bàn',
      price: compactChatPrice(p.priceVnd),
      area: formatChatNumber(p.areaSqm),
      score: formatChatNumber(p.score),
      reason: displayEvidenceText(reason),
      href: advisorListingUrl(p),
      platform: p.source.kind === 'PROPERTY',
      warnings: p.warnings.map(advisorWarning),
      sourceName: p.source.name
    };
  });
  const areaSources = data.citations.filter(c => ['AREA_AMENITY', 'POI_EVIDENCE'].includes(c.kind));
  let summary;
  if (clarification) summary = 'Mình cần thêm một chi tiết để trả lời chính xác.';else if (count) summary = `Mình tìm thấy ${count} bất động sản công khai phù hợp với nhu cầu đã gửi.` + (count > 3 ? ' Dưới đây là 3 lựa chọn đứng đầu danh sách.' : ' Bạn có thể xem thông tin bên dưới.');else if (noMatches) summary = 'Không có tin công khai phù hợp tại ' + (data.evidence.criteria?.district || 'Đà Nẵng') + ' trong ngân sách tối đa ' + compactChatPrice(data.evidence.criteria.budgetVnd).text + '. Bộ lọc khu vực đang được giữ từ hồ sơ hoặc cuộc chat; hệ thống không tự mở rộng.';else if (areaSources.length) summary = data.answer;else summary = 'Chưa có bằng chứng công khai phù hợp để trả lời. Bạn có thể nêu rõ ngân sách và khu vực muốn tìm.';
  if (data.evidence.responseKind === 'PROPERTY_NEARBY_EVIDENCE') summary = data.answer;
  return {
    summary,
    clarification,
    cards,
    noMatches,
    generated: data.generationMode === 'QWEN_GROUNDED_ANSWER',
    fallback: data.generationMode === 'EVIDENCE_ONLY' && !noMatches && !clarification,
    citations: data.citations.map((c, index) => {
      const property = data.recommendedProperties.find(p => c.sourceId === 'recommendation:' + p.id);
      return {
        ...c,
        number: index + 1,
        href: citationHref(c, data.recommendedProperties),
        label: property ? property.title : c.kind === 'AREA_AMENITY' ? 'Hồ sơ tiện ích khu vực' : 'Bằng chứng địa điểm tiện ích',
        basis: property ? 'Thông tin bất động sản' : c.kind === 'PROPERTY_NEARBY' ? 'Tiện ích theo tọa độ tin; khoảng cách đường chim bay và bán kính nằm trong phản hồi Backend' : 'Bằng chứng cấp khu vực; không xác định khoảng cách tới căn nhà'
      };
    }),
    originalAnswer: data.answer,
    limitations: data.dataLimitations
  };
}
export const isNearChatBottom = (element, threshold = 88) => !element || element.scrollHeight - element.clientHeight - element.scrollTop <= threshold;
