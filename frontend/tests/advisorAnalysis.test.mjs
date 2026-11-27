import test from 'node:test'
import assert from 'node:assert/strict'
import {
  advisorConsultRequest,
  advisorError,
  createAdvisorConsultClient,
  effectiveBudgetPreview,
  parseAdvisorBudget,
  validateAdvisorResponse,
  visibleAdvisorComparables,
} from '../src/features/prediction/advisorAnalysis.js'

test('parseAdvisorBudget accepts VN dot-grouped integers', () => {
  assert.equal(parseAdvisorBudget('3.500.000.000'), 3500000000)
  assert.equal(parseAdvisorBudget('1000000'), 1000000)
})

test('parseAdvisorBudget rejects invalid input', () => {
  assert.throws(() => parseAdvisorBudget('abc'))
  assert.throws(() => parseAdvisorBudget('-5'))
  assert.throws(() => parseAdvisorBudget('1,5'))
})

test('effectiveBudgetPreview computes a bounded ceiling', () => {
  const preview = effectiveBudgetPreview('3.500.000.000', 10)
  assert.equal(preview.statedBudgetVnd, 3500000000)
  assert.equal(preview.effectiveCeilingVnd, 3850000000)
})

test('effectiveBudgetPreview rejects an out-of-range flexibility', () => {
  assert.throws(() => effectiveBudgetPreview('3.500.000.000', 40))
})

test('advisorConsultRequest builds a public (SAFE) request', () => {
  const body = advisorConsultRequest({ budgetVnd: '3.500.000.000', budgetFlexibilityPct: 10, purpose: 'LIVING', propertyType: 'ALL', limit: 5 })
  assert.equal(body.purpose, 'LIVING')
  assert.equal(body.includeResearch, false)
  assert.equal(body.propertyType, 'ALL')
})

test('advisorConsultRequest rejects an invalid purpose', () => {
  assert.throws(() => advisorConsultRequest({ budgetVnd: '1.000.000.000', purpose: 'NOPE', propertyType: 'ALL', limit: 5 }))
})

test('advisorError maps HTTP statuses to user messages', () => {
  assert.match(advisorError({ status: 401 }), /Phiên đăng nhập/)
  assert.match(advisorError({ status: 403 }), /quyền/)
  assert.match(advisorError({ status: 429 }), /nhiều yêu cầu/)
  assert.match(advisorError({ status: 503 }), /tạm gián đoạn/)
})

function sampleSafePayload(overrides = {}) {
  return {
    advisorVersion: 'ADVISOR_ORCHESTRATOR_V1',
    mode: 'SAFE',
    criteria: { includeResearch: false },
    serviceStatus: { recommendationService: 'AVAILABLE', areaService: 'AVAILABLE', comparableService: 'AVAILABLE', valuationService: 'AVAILABLE', partialResult: false },
    topAreas: [],
    recommendedProperties: [
      {
        id: 'prop:hc-01',
        title: 'Nhà phố Hải Châu',
        priceVnd: 4400000000,
        areaSqm: 85,
        recommendationScore: 84,
        liveListing: true,
        researchReference: false,
        source: { kind: 'PROPERTY', name: 'SmartProp', recordKey: 'hc-01', detailUrl: '/listing/hc-01' },
        fitReasons: ['Phù hợp ngân sách'],
        warnings: [],
        comparableEvidence: {
          status: 'AVAILABLE',
          candidateCount: 1,
          searchStage: 'WARD',
          comparables: [
            {
              candidateId: 'property:hc-02',
              sourceKind: 'SMARTPROP',
              liveListing: true,
              researchReference: false,
              listingUrl: '/listing/hc-02',
            },
          ],
          warnings: [],
        },
        valuationEvidence: {
          available: true,
          modelVersion: 'v1.3',
          predictedAskingPriceVnd: 4600000000,
        },
      },
    ],
    warnings: [],
    ...overrides,
  }
}

test('validateAdvisorResponse rejects TINIX_RESEARCH comparable and research warnings in SAFE mode', () => {
  const valid = sampleSafePayload()
  assert.equal(validateAdvisorResponse(valid, { allowResearch: false }).mode, 'SAFE')

  const leakedComp = sampleSafePayload()
  leakedComp.recommendedProperties[0].comparableEvidence.comparables.push({
    candidateId: 'tnx-99',
    sourceKind: 'TINIX_RESEARCH',
    liveListing: false,
    researchReference: true,
    listingUrl: null,
    datasetLicense: 'CC BY-NC 4.0',
  })
  assert.throws(() => validateAdvisorResponse(leakedComp, { allowResearch: false }), /SAFE/)

  const leakedWarning = sampleSafePayload({ warnings: ['RESEARCH_COMPARABLES_LABEL: TiniX CC BY-NC 4.0'] })
  assert.throws(() => validateAdvisorResponse(leakedWarning, { allowResearch: false }), /SAFE/)

  const unexpectedMode = sampleSafePayload({ mode: 'INTERNAL_RESEARCH' })
  assert.throws(() => validateAdvisorResponse(unexpectedMode, { allowResearch: false }), /SAFE/)
})

test('visibleAdvisorComparables strips research items unless both mode and allowResearch are enabled', () => {
  const comparable = {
    comparables: [
      { candidateId: 'property:hc-02', sourceKind: 'SMARTPROP', researchReference: false },
      { candidateId: 'tnx-99', sourceKind: 'TINIX_RESEARCH', researchReference: true, datasetLicense: 'CC BY-NC 4.0' },
    ],
  }
  assert.equal(visibleAdvisorComparables(comparable, 'SAFE', false).length, 1)
  assert.equal(visibleAdvisorComparables(comparable, 'SAFE', true).length, 1)
  assert.equal(visibleAdvisorComparables(comparable, 'INTERNAL_RESEARCH', false).length, 1)
  assert.equal(visibleAdvisorComparables(comparable, 'INTERNAL_RESEARCH', true).length, 2)
})

test('createAdvisorConsultClient blocks non-admin includeResearch before calling API', async () => {
  let called = false
  const client = createAdvisorConsultClient(
    async () => { called = true; return sampleSafePayload() },
    () => ({ status: 'AUTHENTICATED', user: { role: 'BROKER' } })
  )
  await assert.rejects(
    () => client({ budgetVnd: '3.500.000.000', purpose: 'LIVING', propertyType: 'HOUSE', includeResearch: true }),
    (err) => err.status === 403
  )
  assert.equal(called, false)
})
