import test from 'node:test'
import assert from 'node:assert/strict'
import { buildValuationPayload, ValuationError } from '../src/features/prediction/valuation.js'

const options = {
  categories: [{ category: 'Nhà ở', locations: ['Hải Châu'] }],
  location_labels: { 'Hải Châu': 'Hải Châu' },
}

function form(extra = {}) {
  return { category: 'Nhà ở', area_sqm: '80', location_feature: 'Hải Châu', ...extra }
}

test('omits unknown real features instead of defaulting them', () => {
  const payload = buildValuationPayload(form(), options)
  assert.equal('road_width_m' in payload, false)
  assert.equal('frontage_width_m' in payload, false)
  assert.equal('street_name' in payload, false)
})

test('passes only explicitly entered measurements and text', () => {
  const payload = buildValuationPayload(form({
    road_width_m: '7.5', frontage_width_m: '4.5', street_name: 'Nguyễn Văn Linh',
    project_name: 'Dự án A', bathrooms: '2', house_direction: 'Đông Nam',
  }), options)
  assert.equal(payload.road_width_m, 7.5)
  assert.equal(payload.frontage_width_m, 4.5)
  assert.equal(payload.street_name, 'Nguyễn Văn Linh')
  assert.equal(payload.project_name, 'Dự án A')
  assert.equal(payload.bathrooms, 2)
  assert.equal(payload.house_direction, 'Đông Nam')
})

test('rejects zero/negative/out-of-range dimensions', () => {
  for (const extra of [{ road_width_m: '0' }, { road_width_m: '-1' }, { road_width_m: '101' },
                       { frontage_width_m: '0' }, { frontage_width_m: '501' }]) {
    assert.throws(() => buildValuationPayload(form(extra), options), ValuationError)
  }
})

test('alley selection alone does not create dimensions', () => {
  const payload = buildValuationPayload(form({ access_type: 'alley' }), options)
  assert.equal(payload.access_type, 'alley')
  assert.equal('road_width_m' in payload, false)
  assert.equal('frontage_width_m' in payload, false)
})
