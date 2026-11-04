import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildValuationPayload, createValuationClient, locationLabel } from '../src/features/prediction/valuation.js'

const badLocation = 'new_unit:ban nha rieng duong nguyen duy hieu - phuong cam chau'
const options = {
  model_version: 'v6',
  categories: [{ category: 'Nhà ở', locations: ['Hải Châu', 'new_unit:hoa xuan', badLocation] }],
  location_labels: { 'Hải Châu': 'Hải Châu', 'new_unit:hoa xuan': 'Hòa Xuân (địa bàn mở rộng)' },
  access_types: { alley: 'Trong kiệt/hẻm' },
  house_subtypes: { house_c4: 'Nhà cấp 4' },
}

test('normalized model locations display Vietnamese accents without changing their code', () => {
  assert.equal(locationLabel('new_unit:hoa xuan', options.location_labels), 'Hòa Xuân (địa bàn mở rộng)')
  assert.equal(locationLabel('Hải Châu'), 'Hải Châu')
})

test('the public dropdown never offers a listing title as a location', async () => {
  const client = createValuationClient({ fetchImpl: async () => new Response(JSON.stringify(options)) })
  const data = await client.getOptions()
  assert.ok(data.categories[0].locations.includes('new_unit:hoa xuan'))
  assert.ok(!data.categories[0].locations.includes(badLocation), 'Listing-title token is still offered to users')
})

test('an older API without reviewed labels cannot leak unknown codes into the dropdown or payload', async () => {
  const old = { ...options }
  delete old.location_labels
  const client = createValuationClient({ fetchImpl: async () => new Response(JSON.stringify(old)) })
  const data = await client.getOptions()
  assert.deepEqual(data.categories[0].locations, ['Hải Châu'])
  assert.throws(() => buildValuationPayload({ category: 'Nhà ở', area_sqm: 80, location_feature: badLocation }, old))
  assert.equal(locationLabel(badLocation), 'Địa bàn chưa được xác nhận')
})
