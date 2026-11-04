import test from 'node:test'
import assert from 'node:assert/strict'
import { normalizeFilters, listingLink, filterError, lifestylePresets } from '../src/features/property/listingFilters.js'
import { createComparison } from '../src/features/property/comparison.js'

test('Home -> Listings -> GIS roundtrip preserves all supported filters and exact price text', () => {
  const input = { keyword: 'Căn hộ ven sông', district: 'Hải Châu', city: 'Đà Nẵng', ward: 'Hải Châu', propertyType: 'APARTMENT', transactionType: 'RENT', minPrice: '12000000.50', maxPrice: '15000000', minArea: '30.50', maxArea: '90', bedrooms: '2', sort: 'areaDesc' }
  for (const path of ['/home', '/listings', '/map']) assert.deepEqual(normalizeFilters(listingLink(path, input).query), input)
})
test('query arrays, whitespace, all-district and zero are handled without default prices', () => {
  assert.deepEqual(normalizeFilters({ district: [' Hải Châu ', 'Sơn Trà'], minPrice: '0', bedrooms: 0 }), { district: 'Hải Châu', minPrice: '0', bedrooms: '0', sort: 'newest' })
  assert.deepEqual(normalizeFilters({ district: 'Tất cả' }), { sort: 'newest' })
})
test('unsupported, nonfinite, negative and malformed API filters are excluded', () => {
  assert.deepEqual(normalizeFilters({ propertyType: 'other', transactionType: 'rent', sort: 'DROP TABLE', minPrice: '-3', maxPrice: 'Infinity', minArea: 'NaN', maxArea: '1e300', bedrooms: '2.5', role: 'ADMIN', status: 'DRAFT', bbox: 'demo' }), { sort: 'newest' })
})
test('filter normalization does not mutate user input or round high precision amounts', () => {
  const input = Object.freeze({ minPrice: '9999999999999999.99', keyword: '  nhà  ' })
  assert.equal(normalizeFilters(input).minPrice, input.minPrice)
  assert.equal(input.keyword, '  nhà  ')
})
test('prototype names cannot be used as property type or sort enum values', () => {
  assert.deepEqual(normalizeFilters({ propertyType: '__proto__', sort: 'constructor' }), { sort: 'newest' })
})
test('invalid numeric text is explained instead of silently dropping a submitted filter', () => {
  for (const value of ['-2', '1e9', 'NaN', 'Infinity', '1.234']) assert.ok(filterError({ minPrice: value }))
  assert.ok(filterError({ bedrooms: '2.5' }))
})
test('price range validation retains cents beyond Number safe integer', () => {
  assert.ok(filterError({ minPrice: '9999999999999999.99', maxPrice: '9999999999999999.98' }))
  assert.equal(filterError({ minPrice: '9999999999999999.98', maxPrice: '9999999999999999.99' }), '')
})
test('inverted price and area ranges fail before search; zero and equality work', () => {
  assert.ok(filterError({ minPrice: '5', maxPrice: '3' }))
  assert.ok(filterError({ minArea: '90', maxArea: '80' }))
  assert.equal(filterError({ minPrice: 0, maxPrice: 0, minArea: '', maxArea: '' }), '')
})
test('district chip can clear district without dropping transaction or room filters', () => {
  assert.deepEqual(listingLink('/map', { district: undefined, transactionType: 'SALE', bedrooms: '2' }, { propertyId: 'uuid' }), { path: '/map', query: { transactionType: 'SALE', bedrooms: '2', propertyId: 'uuid' } })
})
test('lifestyle presets are explainable API filters and never insert coordinates, ROI or fake proximity', () => {
  for (const preset of lifestylePresets) {
    assert.ok(preset.explanation.length > 40)
    assert.deepEqual(normalizeFilters(preset.filters), { ...preset.filters, sort: 'newest' })
    assert.ok(Object.keys(preset.filters).every(key => ['district', 'bedrooms', 'transactionType', 'propertyType'].includes(key)))
  }
})
test('comparison survives collection page changes, removes same UUID and limits to three', () => {
  const compare = createComparison()
  assert.ok(compare.toggle({ id: 'a', title: 'page 1' }))
  assert.ok(compare.toggle({ id: 'b', title: 'page 2' }))
  assert.ok(compare.toggle({ id: 'c', title: 'page 3' }))
  assert.equal(compare.toggle({ id: 'd' }), false)
  assert.deepEqual(compare.items.map(p => p.id), ['a', 'b', 'c'])
  compare.toggle({ id: 'a', title: 'updated title' })
  assert.deepEqual(compare.items.map(p => p.id), ['b', 'c'])
})
test('comparison revalidation replaces snapshots and removes unavailable entries without duplicates', () => {
  const compare = createComparison()
  compare.toggle({ id: 'a', price: 1 }); compare.toggle({ id: 'b' })
  compare.replace([{ id: 'a', price: 2 }, { id: 'a', price: 2 }])
  assert.deepEqual(compare.items, [{ id: 'a', price: 2 }])
  compare.clear(); assert.equal(compare.items.length, 0)
})
