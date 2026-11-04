import { advisorRequest, publicAdvisorResponse } from './advisor.js'

export function researchAdvisorResponse(data) {
  if (data?.mode !== 'INTERNAL_DEMO' || !['HEURISTIC_V1', 'HEURISTIC_V1_1'].includes(data.method) || !Array.isArray(data.topProperties) || !Array.isArray(data.topAreas)
      || data.topProperties.length > 10 || data.topAreas.length > 5 || !Array.isArray(data.warnings)) throw Error('Kết quả nghiên cứu không hợp lệ.')
  const seen = new Set(), groups = new Set()
  for (const p of data.topProperties) {
    if (p?.source?.kind !== 'TINIX_AI') {
      publicAdvisorResponse({ ...data, mode: 'SAFE', topProperties: [p], topAreas: [] })
    } else if (p.verificationStatus !== 'UNVERIFIED' || p.qualityStatus !== 'HYBRID_ELIGIBLE_RESEARCH'
        || !/^tinix:[a-f0-9]{64}$/.test(p.id) || p.source.recordKey !== p.id.slice(6) || p.source.detailUrl != null
        || !p.duplicateGroup || p.isProtectedHoldout || p.protectedHoldout || p.is_protected_holdout
        || !Number.isFinite(p.priceVnd) || p.priceVnd <= 0 || !Number.isFinite(p.areaSqm) || p.areaSqm <= 0
        || !Number.isFinite(p.score) || p.score < 0 || p.score > 100 || !p.title || !Array.isArray(p.explanations)
        || (data.method === 'HEURISTIC_V1_1' && !data.scoringWeights)
        || !Array.isArray(p.warnings) || !p.warnings.some(v => v.includes('TiniX AI') && v.includes('chưa xác minh'))) throw Error('Bản ghi TiniX không đủ điều kiện nghiên cứu.')
    if (seen.has(p.id) || p.duplicateGroup && groups.has(p.duplicateGroup)) throw Error('Kết quả có nhóm nghi trùng.')
    seen.add(p.id); if (p.duplicateGroup) groups.add(p.duplicateGroup)
    if (p.priceVnd > data.criteria.budgetVnd) throw Error('Kết quả vượt ngân sách đã nhập.')
  }
  if (data.topAreas.some(a => !a.district || !Number.isFinite(a.score) || !Array.isArray(a.sources) || !Array.isArray(a.explanations) || !Array.isArray(a.warnings))) throw Error('Thống kê khu vực không hợp lệ.')
  return data
}
export const createResearchAdvisorClient = request => async form => researchAdvisorResponse(await request('/recommendations/research', {
  method: 'POST', authenticated: true, body: advisorRequest(form),
}))
