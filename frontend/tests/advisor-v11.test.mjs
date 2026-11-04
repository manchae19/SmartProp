import test from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { publicAdvisorResponse, v11AdvisorResponse, amenityEvidence, advisorWarning } from '../src/features/prediction/advisor.js'

const evidence = overrides => ({
  areaId: 'ward-my-an-ngu-hanh-son', areaLevel: 'WARD', areaName: 'Mỹ An, Ngũ Hành Sơn', parentDistrict: 'Ngũ Hành Sơn',
  areaAmenityScore: 66.7, amenityFit: 66.7, confidence: 0.79, evidenceBasis: 'DIRECT_WARD_EVIDENCE',
  categoryScores: { essentials: 78, education: 68, healthcare: 52, transit: 60, recreation: 88 },
  poiEvidence: [{ name: 'Chợ Bắc Mỹ An', category: 'MARKET' }, { name: 'Bãi tắm Mỹ An', category: 'BEACH' }],
  dataLimitations: ['Không có tọa độ GPS cấp căn nên SmartProp không tính khoảng cách mét tới tiện ích.'],
  coverage: 'MEDIUM', note: 'Tiện ích được xác định theo phường/xã của bất động sản; đây là đặc điểm khu vực, không phải khoảng cách từ căn nhà.',
  ...overrides,
})
const property = overrides => ({
  id: 'external:one', title: 'Unit test V1.1', propertyType: 'HOUSE', priceVnd: 2e9, areaSqm: 80, district: 'Ngũ Hành Sơn', ward: 'Mỹ An',
  score: 78.5, scoreBreakdown: { budgetFit: 100, areaFit: 80, propertyTypeFit: 100, amenityFit: 66.7 },
  source: { kind: 'EXTERNAL', name: 'Source', recordKey: 'one' }, qualityStatus: 'VALID', verificationStatus: 'VERIFIED',
  explanations: ['Giá rao 2.000.000.000 VND nằm trong ngân sách'], warnings: [], amenityEvidence: evidence(), ...overrides,
})
const area = overrides => ({
  district: 'Ngũ Hành Sơn', ward: 'Mỹ An', candidateCount: 3, score: 74, averageAskingPriceVnd: 2e9,
  sources: ['Source'], unverifiedCount: 0, needsReviewCount: 0, explanations: ['Điểm trung bình ứng viên'],
  warnings: [], amenityScore: 66.7, amenityConfidence: 0.79, amenityAreaId: 'ward-my-an-ngu-hanh-son',
  amenityEvidenceBasis: 'DIRECT_WARD_EVIDENCE', amenityCoverage: 'MEDIUM',
  poiEvidence: [{ name: 'Chợ Bắc Mỹ An', category: 'MARKET' }], ...overrides,
})
const response = overrides => ({
  method: 'HEURISTIC_V1_1', mode: 'SAFE', priceBasis: 'ASKING_SALE_VND_TOTAL', criteria: { budgetVnd: 2e9 },
  eligibleCandidateCount: 3, topAreas: [area()], topProperties: [property()], warnings: ['HEURISTIC_V1_1: quy tắc có trọng số'],
  scoringWeights: { budgetFit: 0.38, areaFit: 0.17, propertyTypeFit: 0.2, amenityFit: 0.25 }, ...overrides,
})

test('V1.1 payload passes the strict public contract', () => {
  const data = response()
  assert.equal(publicAdvisorResponse(data), data)
  assert.equal(v11AdvisorResponse(data), data)
})

test('V1.1 rejects malformed amenity evidence and restricted research fields', () => {
  const bad = [
    evidence({ evidenceBasis: 'GUESSED' }),
    evidence({ areaLevel: 'STREET' }),
    evidence({ confidence: 1.4 }),
    evidence({ areaAmenityScore: 140 }),
    evidence({ amenityFit: -3 }),
    evidence({ categoryScores: { education: 'high' } }),
    evidence({ dataLimitations: 'not-an-array' }),
    evidence({ poiEvidence: [{ name: 1, category: 'PARK' }] }),
  ]
  for (const b of bad) assert.throws(() => amenityEvidence(b), undefined, JSON.stringify(b))
  const leak = { ...property(), amenityEvidence: evidence({ sampleListingCount: 6056 }) }
  assert.throws(() => publicAdvisorResponse(response({ topProperties: [leak] })))
  // Unknown area is allowed but must not carry a score.
  assert.doesNotThrow(() => amenityEvidence(evidence({ areaLevel: 'UNKNOWN', areaAmenityScore: null, amenityFit: null, confidence: 0, evidenceBasis: 'NO_AREA_MATCH', categoryScores: {}, poiEvidence: [] })))
})

test('V1.1 rejects missing or impossible weights and out-of-range area amenity', () => {
  assert.throws(() => v11AdvisorResponse(response({ scoringWeights: undefined })))
  assert.throws(() => v11AdvisorResponse(response({ scoringWeights: { budgetFit: 1.2, areaFit: 0, propertyTypeFit: 0, amenityFit: 0 } })))
  assert.throws(() => publicAdvisorResponse(response({ topAreas: [area({ amenityScore: 120 })] })))
  assert.throws(() => publicAdvisorResponse(response({ topAreas: [area({ amenityConfidence: 2 })] })))
})

test('V1 client still accepts V1 responses while V1.1 requires its own contract', () => {
  const v1 = { method: 'HEURISTIC_V1', mode: 'SAFE', eligibleCandidateCount: 1, topAreas: [], topProperties: [property({ amenityEvidence: undefined, scoreBreakdown: { budgetFit: 90, areaFit: 80 } })], warnings: [] }
  assert.equal(publicAdvisorResponse(v1), v1)
  assert.throws(() => v11AdvisorResponse({ ...response(), scoringWeights: undefined }))
  assert.throws(() => v11AdvisorResponse({ ...v1 }))
})

test('compiled Vue renders V1.1 breakdown, ward basis and POI evidence without fake distances', async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  try {
    const component = (await vite.ssrLoadModule('/src/components/AdvisorResults.vue')).default
    const html = await renderToString(createSSRApp(component, { result: response(), points: [], selectedId: '' }))
    assert.match(html, /data-score-breakdown/)
    assert.match(html, /Loại BĐS/)
    assert.match(html, /data-amenity-evidence/)
    assert.match(html, /Chợ Bắc Mỹ An/)
    assert.match(html, /Tin cậy 79%/)
    assert.match(html, /Theo đúng phường\/xã/)
    assert.match(html, /data-area-amenity/)
    assert.doesNotMatch(html, /cách\s+\d+\s*m/i)
    assert.doesNotMatch(html, /sampleListingCount/)

    const noProfile = await renderToString(createSSRApp(component, {
      result: response({ topAreas: [area({ amenityScore: null, amenityConfidence: null, amenityEvidenceBasis: 'NO_AREA_MATCH', poiEvidence: [] })],
        topProperties: [property({ amenityEvidence: evidence({ areaLevel: 'UNKNOWN', areaAmenityScore: null, amenityFit: null, confidence: 0, evidenceBasis: 'NO_AREA_MATCH', categoryScores: {}, poiEvidence: [], coverage: 'UNKNOWN' }) })] }),
      points: [], selectedId: '',
    }))
    assert.match(noProfile, /data-area-amenity-missing/)
    assert.match(noProfile, /Chưa có điểm tiện ích/)
  } finally { await vite.close() }
})

test('V1.1 warnings are translated and never leak raw codes', () => {
  for (const code of ['HEURISTIC_V1_1: x', 'PURPOSE_WEIGHTS: x', 'NO_AMENITY_EVIDENCE: x', 'AMENITY_IS_DISTRICT_SHARED: x', 'AMENITY_COVERAGE_GAPS: x'])
    assert.doesNotMatch(advisorWarning(code), /^[A-Z_0-9]+:/)
})