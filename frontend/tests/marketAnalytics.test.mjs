import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildAnalyticsQuery,
  bandWidth,
  formatBillion,
  formatPerSqm,
  isInsufficient,
  validateMarketAnalytics,
} from '../src/features/market/marketAnalytics.js'

const VALID = {
  meta: {
    priceBasis: 'ASKING_SALE_VND_TOTAL',
    minSample: 30,
    disclaimer: 'Giá rao bán, không phải giá giao dịch.',
    dataQualityWarnings: [],
    researchIncluded: false,
    temporalStatus: 'NOT_REQUESTED',
  },
  overall: { count: 1304, dataStatus: 'OK', medianAskingPriceVnd: 5e9, medianPricePerSqm: 75e6, p25AskingPriceVnd: 3e9, p75AskingPriceVnd: 10e9 },
  byDistrict: [], byPropertyType: [], bySource: [], priceBands: [], areaBands: [], monthly: [], warnings: [],
}

test('query builder defaults includeResearch=false', () => {
  assert.match(buildAnalyticsQuery({}), /includeResearch=false/)
})

test('query builder carries filters', () => {
  const q = buildAnalyticsQuery({ district: 'Hải Châu', propertyType: 'HOUSE', source: 'SMARTPROP' })
  assert.match(q, /district=/)
  assert.match(q, /propertyType=HOUSE/)
  assert.match(q, /source=SMARTPROP/)
})

test('validate accepts the real contract payload', () => {
  assert.equal(validateMarketAnalytics(VALID).overall.count, 1304)
})

test('validate rejects a missing disclaimer', () => {
  const bad = { ...VALID, meta: { ...VALID.meta, disclaimer: '' } }
  assert.throws(() => validateMarketAnalytics(bad))
})

test('validate rejects a wrong price basis', () => {
  const bad = { ...VALID, meta: { ...VALID.meta, priceBasis: 'MEAN' } }
  assert.throws(() => validateMarketAnalytics(bad))
})

test('validate rejects forecast fields (no forecasting allowed)', () => {
  assert.throws(() => validateMarketAnalytics({ ...VALID, growthRate: 1.2 }))
})

test('formatters', () => {
  assert.equal(formatBillion(5e9), '5 tỷ')
  assert.equal(formatPerSqm(75e6), '75 triệu/m²')
})

test('bandWidth is relative to the tallest bar', () => {
  assert.equal(bandWidth(5, [{ count: 10 }, { count: 5 }]), 50)
})

test('isInsufficient reflects the suppression flag', () => {
  assert.equal(isInsufficient({ count: 0, dataStatus: 'INSUFFICIENT_DATA' }), true)
  assert.equal(isInsufficient({ count: 5, dataStatus: 'OK' }), false)
})
