import test from 'node:test'
import assert from 'node:assert/strict'
import { nearbyPlaces, poiHasPoint, poiLabel, poiSymbol } from '../src/features/map/nearbyPlaces.js'
const poi = Object.freeze({ id: 'school-1', name: 'Tên từ hồ sơ địa điểm', category: 'SCHOOL', latitude: 16.06, longitude: 108.21, distanceMeters: 250 })

test('uses real response coordinates and distance without mutating the record', () => {
  const result = nearbyPlaces(Object.freeze([poi]), 1000)
  assert.deepEqual(result, [poi]); assert.notEqual(result[0], poi)
  assert.equal(result[0].latitude, 16.06); assert.equal(result[0].distanceMeters, 250)
})
test('invalid coordinates never become a default marker; list entry remains honest', () => {
  for (const latitude of [null, undefined, '', false, NaN, Infinity, 91, '16.06']) {
    const entry = { ...poi, latitude }
    assert.equal(poiHasPoint(entry), false)
    assert.equal(nearbyPlaces([entry], 1000).length, 1)
  }
  for (const longitude of [null, undefined, '', true, Infinity, 181, '108.21']) assert.equal(poiHasPoint({ ...poi, longitude }), false)
  assert.equal(poiHasPoint(poi), true)
})
test('filters malformed distances, distances outside current radius, missing IDs and names', () => {
  const values = [-1, NaN, Infinity, null, '250', 1001].map((distanceMeters, i) => ({ ...poi, id: String(i), distanceMeters }))
  assert.equal(nearbyPlaces([...values, { ...poi, id: '' }, { ...poi, name: ' ' }, null], 1000).length, 0)
  assert.equal(nearbyPlaces([{ ...poi, distanceMeters: 0 }], 1000).length, 1)
})
test('deduplicates by source ID and sorts by supplied straight-line distance', () => {
  assert.deepEqual(nearbyPlaces([poi, { ...poi, name: 'Duplicate' }, { ...poi, id: 'hospital', distanceMeters: 10 }], 1000).map(p => p.id), ['hospital', 'school-1'])
})
test('invalid provider response or radius is treated as unavailable, not fabricated places', () => {
  assert.deepEqual(nearbyPlaces({ items: [poi] }, 1000), [])
  for (const radius of [0, -1, Infinity, NaN, 50001]) assert.deepEqual(nearbyPlaces([poi], radius), [])
})
test('category presentation keeps unknown provider categories without inventing a verified type', () => {
  assert.equal(poiLabel('school'), 'Trường học')
  assert.equal(poiLabel('HOSPITAL'), 'Bệnh viện')
  assert.equal(poiLabel('Community Center'), 'Community Center')
  assert.equal(poiSymbol('Community Center'), '●')
})
