import test from 'node:test'
import assert from 'node:assert/strict'
import {
  missingFeatureLabels,
  normalizeShapFactors,
  shapFactorLabel,
  v13AssumptionNotes,
} from '../src/features/prediction/valuationPresentation.js'

test('maps raw V6 subtype labels to Vietnamese', () => {
  assert.equal(shapFactorLabel({ feature_name: 'subtype_villa', label: 'subtype_villa' }, { access_type: 'frontage' }), 'Loại nhà: Biệt thự')
  assert.equal(shapFactorLabel({ feature_name: 'subtype_house_c4', label: 'subtype_house_c4' }), 'Loại nhà: Nhà cấp 4')
})

test('marks absent access/ward/street rather than presenting them as user facts', () => {
  assert.match(shapFactorLabel({ feature_name: 'access_alley' }, { access_type: 'frontage' }), /không áp dụng/)
  assert.match(shapFactorLabel({ feature_name: 'ward' }, { ward: null }), /đang thiếu/)
  assert.match(shapFactorLabel({ feature_name: 'raw_street_name' }, {}), /không có trong input/)
})

test('normalizes SHAP factors and formats impact', () => {
  const factors = normalizeShapFactors({
    top_factors: [
      { feature_name: 'area', label: 'Diện tích (100 m²)', shap_value: -0.2, impact_pct: -18.1, direction: 'decrease' },
      { feature_name: 'bad', shap_value: Number.NaN, impact_pct: 1 },
    ],
  }, { area: 100 })
  assert.equal(factors.length, 1)
  assert.equal(factors[0].displayLabel, 'Diện tích đất/sàn')
  assert.equal(factors[0].displayImpact, '-18.10%')
  assert.equal(factors[0].direction, 'decrease')
})

test('reports V1.3 adapter assumptions without inventing measurements', () => {
  const notes = v13AssumptionNotes({ road_width: 10, frontage_width: 5, ward: null, road_width_source: 'assumed', frontage_width_source: 'assumed' })
  assert.equal(notes.length, 3)
  assert.match(notes[0], /suy ra từ lối vào/)
  assert.match(notes[2], /chưa được cung cấp/)
})

test('does not label user/verified measurements as adapter assumptions', () => {
  const notes = v13AssumptionNotes({
    road_width: 7.5, frontage_width: 4.5, ward: 'Hải Châu 1',
    road_width_source: 'user', frontage_width_source: 'verified',
  })
  assert.deepEqual(notes, [])
})

test('maps/dedupes missing features', () => {
  assert.deepEqual(missingFeatureLabels(['street_name', 'project_name', 'street_name']), ['Tên tuyến đường', 'Dự án bất động sản'])
})
