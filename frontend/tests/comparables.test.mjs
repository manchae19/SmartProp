import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildComparableBody,
  isForbidden,
  safeListingLink,
  similarityPercent,
  validateComparableResponse,
} from '../src/features/property/comparables.js'

test('buildComparableBody accepts a valid district lookup', () => {
  const body = buildComparableBody({ propertyType: 'Nhà ở', district: 'Hải Châu', areaSqm: '80', priceVnd: '5000000000', bedrooms: '3' })
  assert.equal(body.propertyType, 'HOUSE')
  assert.equal(body.district, 'Hải Châu')
  assert.equal(body.areaSqm, 80)
  assert.equal(body.limit, 5)
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
