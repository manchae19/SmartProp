import assert from 'node:assert/strict'
import test from 'node:test'
import { advisorEvidenceMetadata } from '../src/features/prediction/advisorEvidenceModel.js'

const valuation = {
  kind: 'VALUATION',
  reference: 'valuationEvidence',
  source: 'XGBOOST_V1_3',
  status: 'AVAILABLE',
  freshness: 'UNKNOWN',
  limitations: ['ESTIMATED_ASKING_PRICE'],
}

test('legacy consult, missing provenance and missing observation stay distinct', () => {
  assert.equal(advisorEvidenceMetadata(undefined), null)
  const generatedAt = '2026-11-29T00:00:00Z'
  const value = advisorEvidenceMetadata([{ ...valuation, source: null, generatedAt, freshness: 'STALE' }]).get('VALUATION')
  assert.equal(value.source, null)
  assert.equal(value.freshness, 'UNKNOWN')
  assert.equal(value.generatedAt, generatedAt)
  assert.equal(value.observedAt, null)
})

test('only trusted observations strictly older than 90 days are stale', () => {
  const now = Date.parse('2026-11-29T00:00:00Z')
  const age = observedAt => advisorEvidenceMetadata([{ ...valuation, observedAt }], false, now).get('VALUATION').freshness
  assert.equal(age('2026-08-31T00:00:00Z'), 'RECENT')
  assert.equal(age('2026-08-30T23:59:59Z'), 'STALE')
  assert.equal(age('2026-11-30T00:00:00Z'), 'UNKNOWN')
  assert.equal(age('2026-02-30T00:00:00Z'), 'UNKNOWN')
})

test('malformed optional metadata is isolated and cannot inject research, URLs or prices', () => {
  const research = {
    ...valuation,
    kind: 'RECOMMENDATION',
    reference: 'source',
    source: 'TINIX_RESEARCH',
  }
  assert.equal(advisorEvidenceMetadata([research]).size, 0)
  assert.equal(advisorEvidenceMetadata([research], true).get('RECOMMENDATION').source, 'TINIX_RESEARCH')
  assert.equal(advisorEvidenceMetadata([{ ...valuation, reference: 'https://example.invalid' }]).size, 0)
  assert.equal(advisorEvidenceMetadata([valuation, valuation]).size, 0)
  assert.equal(advisorEvidenceMetadata({}).size, 0)
  const cleaned = advisorEvidenceMetadata([{
    ...valuation, price: 123, token: 'fixture', limitations: ['PRIVATE', 'ESTIMATED_ASKING_PRICE'],
  }]).get('VALUATION')
  assert.equal(cleaned.price, undefined)
  assert.equal(cleaned.token, undefined)
  assert.deepEqual(cleaned.limitations, ['ESTIMATED_ASKING_PRICE'])
})
