import test from 'node:test'
import assert from 'node:assert/strict'
import { locationPreviewRegion, projectPreviewRegion } from '../src/features/map/locationPreview.js'

const point = { latitude: 16.066, longitude: 108.199, provider: 'GEOAPIFY', mapProvider: 'OSM', accuracy: 'UNKNOWN', locationLevel: 'BUILDING_ONLY', confidence: .98, addressMatched: true, context: { resultType: 'building', precision: 'UNKNOWN', localityMatched: true } }

test('high confidence house match keeps the existing pin without a surrounding area', () => {
  assert.equal(locationPreviewRegion(point), null)
  assert.equal(locationPreviewRegion({ ...point, accuracy: 'EXACT' }), null)
})
test('missing house number, street and ward matches get explicitly illustrative circles', () => {
  const street = locationPreviewRegion({ ...point, locationLevel: 'APPROXIMATE', accuracy: 'APPROXIMATE', context: { resultType: 'street', precision: 'APPROXIMATE_STREET' } })
  const area = locationPreviewRegion({ ...point, locationLevel: 'APPROXIMATE', accuracy: 'APPROXIMATE', context: { resultType: 'suburb', precision: 'APPROXIMATE_AREA' } })
  assert.equal(street.kind, 'ILLUSTRATIVE_CIRCLE'); assert.equal(area.kind, 'ILLUSTRATIVE_CIRCLE')
  assert.match(street.label, /chỉ minh họa/); assert.match(area.label, /không phải ranh giới tài sản hoặc bán kính sai số đã xác minh/)
  assert.equal(street.latitude, point.latitude); assert.equal(street.longitude, point.longitude)
})
test('manual points, unknown precision and Google content do not get a fabricated region', () => {
  for (const value of [null, { latitude: 16, longitude: 108 }, point, { ...point, provider: 'GOOGLE', mapProvider: 'GOOGLE', accuracy: 'APPROXIMATE' }]) assert.equal(locationPreviewRegion(value), null)
})
test('an interpolated number is still a suggestion and does not change candidate accuracy', () => {
  const value = Object.freeze({ ...point, accuracy: 'INTERPOLATED' })
  assert(locationPreviewRegion(value)); assert.equal(value.accuracy, 'INTERPOLATED'); assert.equal(value.addressMatched, true)
})
test('invalid or missing coordinates never create an area at a default location', () => {
  for (const latitude of [null, '', NaN, 95]) assert.equal(locationPreviewRegion({ ...point, latitude, accuracy: 'APPROXIMATE' }), null)
  assert.equal(locationPreviewRegion({ ...point, longitude: 200, accuracy: 'APPROXIMATE' }), null)
})
test('overlay follows map projection on pan, zoom and resize, anchored to the original suggestion', () => {
  const region = locationPreviewRegion({ ...point, accuracy: 'APPROXIMATE' }), center = { latitude: point.latitude, longitude: point.longitude }
  const initial = projectPreviewRegion(region, center, 13, 600, 320)
  assert.equal(initial.cx, 300); assert.equal(initial.cy, 160)
  const zoomed = projectPreviewRegion(region, center, 14, 600, 320)
  assert(Math.abs(zoomed.radius / initial.radius - 2) < 1e-9)
  const panned = projectPreviewRegion(region, { ...center, longitude: center.longitude + .001 }, 13, 600, 320)
  assert(panned.cx < initial.cx); assert.equal(panned.radius, initial.radius)
  assert.equal(projectPreviewRegion(region, center, 13, 390, 320).cx, 195)
  assert.equal(region.latitude, point.latitude); assert.equal(region.longitude, point.longitude)
})
test('invalid viewport/region metadata cannot produce NaN SVG geometry', () => {
  const region = locationPreviewRegion({ ...point, accuracy: 'APPROXIMATE' })
  assert.equal(projectPreviewRegion(null, point, 13, 600, 320), null)
  assert.equal(projectPreviewRegion(region, { latitude: '', longitude: '' }, 13, 600, 320), null)
  assert.equal(projectPreviewRegion(region, point, 13, 0, 320), null)
  assert.equal(projectPreviewRegion(region, point, 40, 600, 320), null)
})
