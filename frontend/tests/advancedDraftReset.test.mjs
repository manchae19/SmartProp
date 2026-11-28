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

test('switching to land drops floors and balcony direction', () => {
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
  const map = { street: 'streetName', project: 'projectName', road: 'roadWidthM', frontage: 'frontageWidthM', floors: 'floors', balconyDirection: 'balconyDirection', subtype: 'houseSubtype' }
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

// ---------------------------------------------------------------
// Ghi chú: initialDraft() nằm trong usePostEditor.js, module này import file .jsx nên
// node test runner thuần không nạp được (ERR_UNKNOWN_FILE_EXTENSION). Vì vậy reset được
// kiểm qua production payload builder bên dưới - hàm mà editor thật sự gọi - thay vì
// mô phỏng lại bằng Object.assign.
// ---------------------------------------------------------------
// Chuyển loại BĐS: payload production tự lọc field không còn áp dụng,
// kể cả khi draft còn giữ giá trị cũ (stale hidden value).
test('chuyển loại BĐS: payload production lọc đúng field stale', async () => {
  const { advancedValuationPayload } = await import('../src/features/prediction/advancedValuation.js')
  const stale = {
    streetName: 'Trường Sa', projectName: 'Dự án A',
    roadWidthM: '12', frontageWidthM: '6',
    floors: '3', houseSubtype: 'villa', balconyDirection: 'Đông',
  }
  const land = advancedValuationPayload(stale, 'Đất nền')
  assert.equal('floors' in land, false)
  assert.equal('houseSubtype' in land, false)
  assert.equal('balconyDirection' in land, false)
  assert.equal(land.roadWidthM, 12)

  const house = advancedValuationPayload(stale, 'Nhà phố')
  assert.equal('balconyDirection' in house, false)
  assert.equal(house.floors, 3)

  const apartment = advancedValuationPayload(stale, 'Căn hộ chung cư')
  assert.equal('roadWidthM' in apartment, false)
  assert.equal('frontageWidthM' in apartment, false)
  assert.equal('floors' in apartment, false)
  assert.equal(apartment.balconyDirection, 'Đông')
})
