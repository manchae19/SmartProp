import test from 'node:test'
import assert from 'node:assert/strict'
import {
  ADVANCED_DRAFT_DEFAULTS,
  advancedFieldsFor,
  advancedValuationPayload,
} from '../src/features/prediction/advancedValuation.js'

// reset() and initialize() use Object.assign(draft, initialDraft()). That only overwrites
// keys that already exist, so an advanced valuation field missing from the defaults would
// survive a property switch and be sent for the next listing. These tests guard that.

const ADVANCED_KEYS = Object.keys(ADVANCED_DRAFT_DEFAULTS)

test('every advanced field has an empty default so reset can clear it', () => {
  assert.ok(ADVANCED_KEYS.length >= 7)
  for (const key of ADVANCED_KEYS) {
    assert.equal(ADVANCED_DRAFT_DEFAULTS[key], '', `${key} phải mặc định rỗng`)
  }
})

test('a populated draft resets every advanced field', () => {
  const draft = {
    ...ADVANCED_DRAFT_DEFAULTS,
    streetName: 'Nguyễn Văn Linh', projectName: 'Dự án A',
    roadWidthM: '7.5', frontageWidthM: '4.5', floors: '3',
    houseSubtype: 'house_c4', balconyDirection: 'Đông Nam',
  }
  Object.assign(draft, ADVANCED_DRAFT_DEFAULTS)
  for (const key of ADVANCED_KEYS) {
    assert.equal(draft[key], '', `${key} phải được xoá về rỗng`)
  }
})

test('a freshly reset draft produces no advanced payload', () => {
  const draft = { ...ADVANCED_DRAFT_DEFAULTS, propertyType: 'Nhà phố' }
  assert.deepEqual(advancedValuationPayload(draft, draft.propertyType), {})
})

test('switching to an apartment drops dimensions the old draft still holds', () => {
  const draft = {
    ...ADVANCED_DRAFT_DEFAULTS,
    roadWidthM: '7.5', frontageWidthM: '4.5', projectName: 'FPT Plaza 2',
  }
  const payload = advancedValuationPayload(draft, 'Căn hộ chung cư')
  assert.equal('roadWidthM' in payload, false)
  assert.equal('frontageWidthM' in payload, false)
  assert.equal(payload.projectName, 'FPT Plaza 2')
})

test('switching to land drops floors and directions', () => {
  const draft = {
    ...ADVANCED_DRAFT_DEFAULTS,
    floors: '3', balconyDirection: 'Đông', streetName: 'Trường Sa',
  }
  const payload = advancedValuationPayload(draft, 'Đất nền')
  assert.equal('floors' in payload, false)
  assert.equal('balconyDirection' in payload, false)
  assert.equal(payload.streetName, 'Trường Sa')
})

test('defaults cover every field any property type can allow', () => {
  const allowedKeys = new Set()
  const map = { street: 'streetName', project: 'projectName', road: 'roadWidthM', frontage: 'frontageWidthM', floors: 'floors', directions: 'balconyDirection', subtype: 'houseSubtype' }
  for (const type of ['Đất nền', 'Căn hộ chung cư', 'Nhà phố', 'Biệt thự']) {
    const allowed = advancedFieldsFor(type)
    for (const [flag, key] of Object.entries(map)) {
      if (allowed[flag]) allowedKeys.add(key)
    }
  }
  for (const key of allowedKeys) {
    assert.ok(key in ADVANCED_DRAFT_DEFAULTS, `${key} phải có trong ADVANCED_DRAFT_DEFAULTS`)
  }
})
