import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildComparableBody,
  isForbidden,
  loadComparables,
  safeListingLink,
  similarityPercent,
  validateComparableResponse,
  valuationComparableBody,
} from '../src/features/property/comparables.js'

test('buildComparableBody accepts a valid district lookup', () => {
  const body = buildComparableBody({ propertyType: 'Nhà ở', district: 'Hải Châu', areaSqm: '80', priceVnd: '5000000000', bedrooms: '3' })
  assert.equal(body.propertyType, 'HOUSE')
  assert.equal(body.purpose, 'SIMILAR_LISTING')
  assert.equal(body.district, 'Hải Châu')
  assert.equal(body.areaSqm, 80)
  assert.equal(body.limit, 5)
})

test('standalone and posting valuation adapters never forward target or drafted price', () => {
  assert.deepEqual(valuationComparableBody({ category: 'Nhà ở', house_subtype: 'villa', location_feature: 'Hải Châu',
    area_sqm: 90, rooms: 3, priceVnd: 9000000000, predicted_asking_price_vnd: 5000000000 }), {
    purpose: 'VALUATION_SUPPORT', propertyType: 'VILLA', district: 'Hải Châu', areaSqm: 90, bedrooms: 3, limit: 5,
  })
  assert.deepEqual(valuationComparableBody({ propertyType: 'LAND', locationFeature: 'Hải Châu', areaSqm: 80,
    askingPriceVnd: 4000000000 }), {
    purpose: 'VALUATION_SUPPORT', propertyType: 'LAND', district: 'Hải Châu', areaSqm: 80, limit: 5,
  })
})

test('buyer budget is forwarded as a hard cap and SAFE rejects aggregate research metadata', () => {
  const body = buildComparableBody({ purpose: 'BUYER_BUDGET_SEARCH', propertyType: 'HOUSE',
    district: 'Hải Châu', areaSqm: 80, priceVnd: 3000000000 })
  assert.equal(body.buyerBudgetVnd, 3000000000)
  assert.equal(Object.hasOwn(body, 'priceVnd'), false)
  assert.throws(() => validateComparableResponse({ reference: {}, comparables: [],
    evidence: { provenance: { TINIX_RESEARCH: { uniqueEligible: 2 } } } }, { allowResearch: false }), /nghiên cứu/)
})

test('buildComparableBody rejects an unsupported district', () => {
  assert.throws(() => buildComparableBody({ propertyType: 'Nhà ở', district: 'Hội An', areaSqm: 80 }))
})

test('buildComparableBody rejects an out-of-range area', () => {
  assert.throws(() => buildComparableBody({ propertyType: 'Nhà ở', district: 'Hải Châu', areaSqm: 1 }))
})

test('validateComparableResponse accepts a valid payload', () => {
  const data = { reference: { priceVnd: 1 }, comparables: [{ candidateId: 'a', sourceKind: 'SMARTPROP' }] }
  assert.equal(validateComparableResponse(data).comparables.length, 1)
})

test('validateComparableResponse rejects an unknown source', () => {
  assert.throws(() => validateComparableResponse({ reference: {}, comparables: [{ candidateId: 'a', sourceKind: 'X' }] }))
})

test('validateComparableResponse rejects more than five rows', () => {
  const comparables = Array.from({ length: 6 }, (_, i) => ({ candidateId: 'c' + i, sourceKind: 'SMARTPROP' }))
  assert.throws(() => validateComparableResponse({ reference: {}, comparables }))
})

test('safeListingLink only keeps sanitised links', () => {
  assert.equal(safeListingLink({ sourceKind: 'SMARTPROP', listingUrl: '/properties/abc' }), '/listing/abc')
  assert.equal(safeListingLink({ sourceKind: 'SMARTPROP', listingUrl: 'https://evil.example/x' }), '')
  assert.equal(safeListingLink({ sourceKind: 'EXTERNAL_LISTING', listingUrl: 'https://example.com/x' }), 'https://example.com/x')
  assert.equal(safeListingLink({ sourceKind: 'TINIX_RESEARCH', listingUrl: 'https://example.com/x' }), '')
})

test('isForbidden treats 401 and 403 as authorisation refusals', () => {
  assert.equal(isForbidden({ status: 401 }), true)
  assert.equal(isForbidden({ status: 403 }), true)
  assert.equal(isForbidden({ status: 400 }), false)
})

test('similarityPercent rounds a 0..1 score', () => {
  assert.equal(similarityPercent(0.916), 92)
  assert.equal(similarityPercent(undefined), 0)
})

test('validateComparableResponse and loadComparables reject TINIX_RESEARCH leaks in public mode', async () => {
  const tinixPayload = {
    reference: { priceVnd: 5e9 },
    comparables: [{ candidateId: 'tnx-1', sourceKind: 'TINIX_RESEARCH' }],
    eligibleCountsBySource: { SMARTPROP: 2, EXTERNAL_LISTING: 5, TINIX_RESEARCH: 55816 },
    warnings: ['TiniX — CC BY-NC 4.0'],
  }
  assert.throws(() => validateComparableResponse(tinixPayload, { allowResearch: false }), /công khai/)
  assert.throws(() => validateComparableResponse(
    { reference: {}, comparables: [], eligibleCountsBySource: { SMARTPROP: 2, TINIX_RESEARCH: 0 } },
    { allowResearch: false }
  ), /công khai/)

  await assert.rejects(
    () => loadComparables({ propertyType: 'HOUSE', district: 'Hải Châu', areaSqm: 80 }, async () => tinixPayload),
    /công khai/
  )

  const okResearch = await loadComparables(
    { propertyType: 'HOUSE', district: 'Hải Châu', areaSqm: 80, includeResearch: true },
    async () => tinixPayload
  )
  assert.equal(okResearch.comparables.length, 1)
})
