import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildValuationPayload, createValuationClient, formatPrice } from '../src/features/prediction/valuation.js'

const options = {
  model_version: 'v6',
  categories: ['Nhà ở', 'Đất nền', 'Căn hộ chung cư'].map((category) => ({ category, locations: ['Cẩm Lệ'] })),
  access_types: { alley: 'Trong kiệt/hẻm', frontage: 'Mặt tiền' },
  house_subtypes: { villa: 'Biệt thự', house_c4: 'Nhà cấp 4' },
}
const base = { category: 'Nhà ở', area_sqm: '80', location_feature: 'Cẩm Lệ' }
const prediction = {
  model_version: 'v6', category: 'Nhà ở', currency: 'VND', predicted_asking_price_vnd: 3_829_364_014,
  features_used: {}, missing_features: [], warnings: [],
}
const json = (body, status = 200) => new Response(JSON.stringify(body), { status })

test('payload contains numeric inputs and excludes price, ID and listing text', () => {
  const result = buildValuationPayload({ ...base, rooms: '3', floors: '2', access_type: 'alley', ward: '  Hoà Xuân ',
    id: 42, price_million: 5000, price: 5e9, title: 'Nhà 8 phòng ngủ' }, options)
  assert.deepEqual(result, { category: 'Nhà ở', area_sqm: 80, location_feature: 'Cẩm Lệ',
    ward: 'Hoà Xuân', rooms: 3, floors: 2, access_type: 'alley' })
})

test('unknown optional values stay absent, and fields of other property types do not leak', () => {
  assert.deepEqual(buildValuationPayload(base, options), { category: 'Nhà ở', area_sqm: 80, location_feature: 'Cẩm Lệ' })
  const dirty = { ...base, rooms: 3, floors: 2, house_subtype: 'villa', access_type: 'alley' }
  assert.deepEqual(buildValuationPayload({ ...dirty, category: 'Đất nền' }, options),
    { category: 'Đất nền', area_sqm: 80, location_feature: 'Cẩm Lệ', access_type: 'alley' })
  assert.deepEqual(buildValuationPayload({ ...dirty, category: 'Căn hộ chung cư' }, options),
    { category: 'Căn hộ chung cư', area_sqm: 80, location_feature: 'Cẩm Lệ', rooms: 3 })
})

test('out of scope inputs are rejected before requesting prediction', () => {
  for (const area_sqm of ['', null, false, Infinity, NaN, 19, 1001]) {
    assert.throws(() => buildValuationPayload({ ...base, area_sqm }, options))
  }
  for (const rooms of [0, 31, 2.5, true]) assert.throws(() => buildValuationPayload({ ...base, rooms }, options))
  assert.throws(() => buildValuationPayload({ ...base, location_feature: 'Unknown' }, options))
})

test('options and predictions use only the local AI proxy with the correct method', async () => {
  const calls = []
  const client = createValuationClient({ fetchImpl: async (url, init) => {
    calls.push({ url, init })
    return json(url.endsWith('/options') ? options : prediction)
  } })
  assert.deepEqual(await client.getOptions(), options)
  const payload = buildValuationPayload(base, options)
  assert.deepEqual(await client.predict(payload), prediction)
  assert.equal(calls[0].url, '/api/ai/model/options')
  assert.equal(calls[0].init.method, 'GET')
  assert.equal(calls[1].url, '/api/ai/predict')
  assert.equal(calls[1].init.method, 'POST')
  assert.deepEqual(JSON.parse(calls[1].init.body), payload)
})

test('backend validation, offline, proxy failure and malformed responses stay readable', async () => {
  await assert.rejects(createValuationClient({ fetchImpl: async () => json({ detail: 'Địa bàn chưa có trong model.' }, 422) }).predict(base), /Địa bàn/)
  await assert.rejects(createValuationClient({ fetchImpl: async () => json({}, 503) }).getOptions(), /chưa sẵn sàng/)
  await assert.rejects(createValuationClient({ fetchImpl: async () => { throw new TypeError('Network failure') } }).getOptions(), /Chưa kết nối/)
  await assert.rejects(createValuationClient({ fetchImpl: async () => json({}) }).getOptions(), /chưa hợp lệ/)
  await assert.rejects(createValuationClient({ fetchImpl: async () => json({ ...prediction, predicted_asking_price_vnd: null }) }).predict(base), /chưa hợp lệ/)
})

test('slow response has a bounded wait and changing input can cancel a request', async () => {
  const fetchImpl = async (_, { signal }) => new Promise((resolve, reject) => {
    signal.addEventListener('abort', () => reject(new DOMException('Canceled', 'AbortError')), { once: true })
  })
  await assert.rejects(createValuationClient({ fetchImpl, timeoutMs: 10 }).getOptions(), /phản hồi chậm/)
  const controller = new AbortController()
  const request = createValuationClient({ fetchImpl }).predict(base, { signal: controller.signal })
  controller.abort()
  await assert.rejects(request, { name: 'AbortError' })
})

test('price formatting distinguishes VND, million and billion without an invented interval', () => {
  assert.equal(formatPrice(3_829_364_014), '3,83 tỷ đồng')
  assert.equal(formatPrice(800_000_000), '800 triệu đồng')
})
