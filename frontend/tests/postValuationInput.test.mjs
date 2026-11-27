import test from 'node:test'
import assert from 'node:assert/strict'
import { valuationInput } from '../src/features/prediction/valuation.js'

// Luồng B — Post Property valuation. Draft đến từ form đăng tin, không phải form
// định giá độc lập, nên chỉ những field form thực sự thu thập mới được gửi.

function draft(extra = {}) {
  return {
    propertyType: 'Căn hộ chung cư',
    transactionType: 'Bán',
    area: '80',
    bedrooms: '2',
    bathrooms: '2',
    title: 'Căn hộ thử',
    description: 'Mô tả',
    ...extra,
  }
}

test('omits optional fields the draft does not carry', () => {
  const input = valuationInput(draft(), 'Hải Châu')
  assert.equal(input.reason, undefined)
  assert.equal('ward' in input.body, false)
  assert.equal('houseDirection' in input.body, false)
  assert.equal('roadWidthM' in input.body, false)
  assert.equal('frontageWidthM' in input.body, false)
  assert.equal('streetName' in input.body, false)
  assert.equal('projectName' in input.body, false)
})

test('forwards ward and direction when the draft has them', () => {
  const input = valuationInput(draft({ ward: 'Thạch Thang', direction: 'Đông Nam' }), 'Hải Châu')
  assert.equal(input.body.ward, 'Thạch Thang')
  assert.equal(input.body.houseDirection, 'Đông Nam')
})

test('trims and truncates forwarded text to the API limits', () => {
  const input = valuationInput(
    draft({ ward: `  ${'a'.repeat(120)}  `, direction: `  ${'b'.repeat(60)}  ` }),
    'Hải Châu',
  )
  assert.equal(input.body.ward.length, 100)
  assert.equal(input.body.houseDirection.length, 50)
})

test('blank optional text is omitted, not sent as empty string', () => {
  const input = valuationInput(draft({ ward: '   ', direction: '' }), 'Hải Châu')
  assert.equal('ward' in input.body, false)
  assert.equal('houseDirection' in input.body, false)
})

test('land listings omit bedrooms and bathrooms', () => {
  const input = valuationInput(
    draft({ propertyType: 'Đất nền', bedrooms: '0', bathrooms: '0' }),
    'Hải Châu',
  )
  assert.equal(input.body.bedrooms, null)
  assert.equal('bathrooms' in input.body, false)
})

test('rejects a rent listing before building a payload', () => {
  const input = valuationInput(draft({ transactionType: 'Thuê' }), 'Hải Châu')
  assert.equal(input.body, undefined)
  assert.match(input.reason, /chỉ hỗ trợ tin bán/)
})

test('rejects an area outside the model range', () => {
  const input = valuationInput(draft({ area: '10' }), 'Hải Châu')
  assert.equal(input.body, undefined)
  assert.match(input.reason, /20 đến 1000/)
})

// Bedrooms là optional: chưa nhập là MISSING (gửi null), không phải 0 và không phải lỗi.
// 0 là giá trị người dùng chủ động khai báo ("chưa khai báo" theo contract của model).
for (const [label, value, expected] of [
  ['chuỗi rỗng (chưa nhập)', '', null],
  ['undefined (không có field)', undefined, null],
  ['null', null, null],
  ['khoảng trắng', '   ', null],
  ['0', '0', 0],
  ['1', '1', 1],
  ['30 (biên trên)', '30', 30],
]) {
  test(`bedrooms ${label} → missing/value đúng, không báo lỗi`, () => {
    const input = valuationInput(draft({ bedrooms: value }), 'Hải Châu')
    assert.equal(input.reason, undefined)
    assert.equal(input.body.bedrooms, expected)
  })
}

for (const [label, value] of [
  ['-1', '-1'],
  ['31 (vượt biên)', '31'],
  ['số thập phân', '2.5'],
  ['chuỗi không hợp lệ', 'abc'],
]) {
  test(`bedrooms ${label} → báo ngoài phạm vi`, () => {
    const input = valuationInput(draft({ bedrooms: value }), 'Hải Châu')
    assert.match(input.reason, /phòng ngủ/i)
  })
}

test('LAND không gửi bedrooms dù draft có giá trị', () => {
  const input = valuationInput(draft({ propertyType: 'Đất nền', bedrooms: '5' }), 'Hải Châu')
  assert.equal(input.reason, undefined)
  assert.equal(input.body.bedrooms, null)
})

test('LAND với bedrooms trống vẫn không báo lỗi', () => {
  const input = valuationInput(draft({ propertyType: 'Đất nền', bedrooms: '' }), 'Hải Châu')
  assert.equal(input.reason, undefined)
  assert.equal(input.body.bedrooms, null)
})
