import test from 'node:test'
import assert from 'node:assert/strict'
import { advancedFieldsFor, advancedValuationPayload } from '../src/features/prediction/advancedValuation.js'

test('land listings allow dimensions but not floors or directions', () => {
  const allowed = advancedFieldsFor('Đất nền')
  assert.equal(allowed.road, true)
  assert.equal(allowed.frontage, true)
  assert.equal(allowed.floors, false)
  assert.equal(allowed.directions, false)
  assert.equal(allowed.subtype, false)
})

test('apartments allow project and directions but never road or frontage', () => {
  const allowed = advancedFieldsFor('Căn hộ chung cư')
  assert.equal(allowed.project, true)
  assert.equal(allowed.road, false)
  assert.equal(allowed.frontage, false)
  assert.equal(allowed.floors, false)
  assert.equal(allowed.directions, true)
})

test('houses allow the full set including floors and subtype', () => {
  const allowed = advancedFieldsFor('Nhà phố')
  assert.equal(allowed.road, true)
  assert.equal(allowed.frontage, true)
  assert.equal(allowed.floors, true)
  assert.equal(allowed.subtype, true)
  assert.equal(allowed.directions, true)
})

test('villas do not offer a subtype because the type already implies it', () => {
  assert.equal(advancedFieldsFor('Biệt thự').subtype, false)
})

test('blank draft produces an empty payload', () => {
  assert.deepEqual(advancedValuationPayload({}, 'Nhà phố'), {})
})

test('only explicitly entered values are forwarded', () => {
  const payload = advancedValuationPayload({
    streetName: '  Nguyễn Văn Linh  ',
    projectName: '',
    roadWidthM: '7.5',
    frontageWidthM: '4.2',
    floors: '3',
    houseSubtype: 'house_c4',
    balconyDirection: 'Đông Nam',
  }, 'Nhà phố')
  assert.equal(payload.streetName, 'Nguyễn Văn Linh')
  assert.equal('projectName' in payload, false)
  assert.equal(payload.roadWidthM, 7.5)
  assert.equal(payload.frontageWidthM, 4.2)
  assert.equal(payload.floors, 3)
  assert.equal(payload.houseSubtype, 'house_c4')
  assert.equal(payload.balconyDirection, 'Đông Nam')
})

test('out-of-range dimensions are dropped, not clamped', () => {
  const payload = advancedValuationPayload({
    roadWidthM: '0', frontageWidthM: '9999', floors: '0',
  }, 'Nhà phố')
  assert.equal('roadWidthM' in payload, false)
  assert.equal('frontageWidthM' in payload, false)
  assert.equal('floors' in payload, false)
})

test('non-numeric input is dropped', () => {
  const payload = advancedValuationPayload({ roadWidthM: 'abc', floors: '2.5' }, 'Nhà phố')
  assert.equal('roadWidthM' in payload, false)
  assert.equal('floors' in payload, false)
})

test('apartment payload never carries road or frontage even if the draft has them', () => {
  const payload = advancedValuationPayload({
    roadWidthM: '7.5', frontageWidthM: '4.2', projectName: 'FPT Plaza 2',
  }, 'Căn hộ chung cư')
  assert.equal('roadWidthM' in payload, false)
  assert.equal('frontageWidthM' in payload, false)
  assert.equal(payload.projectName, 'FPT Plaza 2')
})

test('unknown subtype is dropped', () => {
  const payload = advancedValuationPayload({ houseSubtype: 'penthouse' }, 'Nhà phố')
  assert.equal('houseSubtype' in payload, false)
})

test('text is truncated to the API limits', () => {
  const payload = advancedValuationPayload({
    streetName: 'a'.repeat(300), balconyDirection: 'b'.repeat(80),
  }, 'Nhà phố')
  assert.equal(payload.streetName.length, 200)
  assert.equal(payload.balconyDirection.length, 50)
})
