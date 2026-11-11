import test from 'node:test'
import assert from 'node:assert/strict'
import { parseQuickAddress, normalizeQuickAddress } from '../src/features/prediction/quickAddress.js'

test('parses district and legacy ward with diacritics', () => {
  const parsed = parseQuickAddress('120 Bạch Đằng, Phường Hải Châu 1, Quận Hải Châu')
  assert.equal(parsed.district, 'Hải Châu')
  assert.equal(parsed.ward, 'Hải Châu 1')
})

test('parses unaccented address and infers district from ward', () => {
  const parsed = parseQuickAddress('120 Bach Dang, Phuong Hoa Cuong Nam')
  assert.equal(parsed.district, 'Hải Châu')
  assert.equal(parsed.ward, 'Hoa Cuong Nam')
})

test('parses district-only address and returns no ward', () => {
  const parsed = parseQuickAddress('Đường Bạch Đằng, Hải Châu, Đà Nẵng')
  assert.equal(parsed.district, 'Hải Châu')
  assert.equal(parsed.ward, '')
})

test('normalizes for matching but does not invent a district', () => {
  assert.equal(normalizeQuickAddress('  HẢI CHÂU  '), 'hai chau')
  assert.equal(parseQuickAddress('Địa chỉ không có quận').district, '')
})
