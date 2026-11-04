import test from 'node:test'
import assert from 'node:assert/strict'
import { searchLocations, candidateCanBeConfirmed, accuracyLabel, geocodingSignature, geocodingConfiguration, normalizeAddressQuery, administrativeHints, effectiveGeocodingInput, geocodingErrorMessage } from '../src/features/map/geocoding.js'
import { publicMapPoint, locationLabel } from '../src/features/map/locationDisplay.js'
import { buildPostPayload, locationSignature, locationConfirmed } from '../src/features/property/postForm.js'
import { mapUrl } from '../src/features/property/property.js'

const point = { id: 'geoapify-0', latitude: 1.25, longitude: 100.75, provider: 'GEOAPIFY', mapProvider: 'OSM', storageAllowed: true, addressMatched: true, locationLevel: 'BUILDING_ONLY', accuracy: 'UNKNOWN', context: {localityMatched:true,precision:'UNKNOWN'} }
test('address request uses authenticated API, original fields and explicit sharing consent', async () => {
  const original = { address: ' 10 Mock street ', city: 'Mock city', district: 'District', ward: 'Ward', shareAddress: true }
  let sent
  const result = await searchLocations(original, async (path, options) => { sent = { path, options }; return { status: 'OK', candidates: [point] } })
  assert.equal(sent.path, '/geocoding/search'); assert.equal(sent.options.method, 'POST'); assert.equal(sent.options.body.shareAddress, true)
  assert.equal(sent.options.body.address, original.address); assert.equal(sent.options.authenticated, undefined); assert.equal(result.candidates.length, 1)
})
test('missing address or city never reaches provider', async () => {
  for (const input of [{ address: '', city: 'City' }, { address: 'Street', city: '' }]) await assert.rejects(searchLocations(input, () => { throw Error('must not be called') }), /Nhập địa chỉ/)
})
test('invalid coordinates are excluded, not replaced with city center', async () => {
  const result = await searchLocations({ address: 'Mock', city: 'City', shareAddress:true }, async () => ({ candidates: [{ ...point, latitude: null }, { ...point, longitude: 200 }] }))
  assert.deepEqual(result.candidates, [])
})
test('multiple matching localities remain available for explicit selection', async () => {
  const result = await searchLocations({ address: 'Mock', city: 'City', shareAddress:true }, async () => ({ candidates: [{ ...point, id: 'a' }, { ...point, id: 'b', latitude: 2 }] }))
  assert.equal(result.candidates.length, 2)
})
test('empty results are not interpreted as a default coordinate', async () => {
  assert.deepEqual((await searchLocations({ address: 'Mock', city: 'City', shareAddress:true }, async () => ({ status: 'ZERO_RESULTS', candidates: [] }))).candidates, [])
})
test('Google rooftop content still cannot be persisted or sent to OSM', () => {
  assert.equal(candidateCanBeConfirmed({ ...point, provider: 'GOOGLE', mapProvider: 'GOOGLE', accuracy: 'EXACT', storageAllowed: false }), false)
})
test('street, city and partial house match require manual repositioning', () => {
  assert.equal(candidateCanBeConfirmed({ ...point, locationLevel: 'APPROXIMATE' }), false)
  assert.equal(candidateCanBeConfirmed({ ...point, addressMatched: false }), false)
  assert.equal(candidateCanBeConfirmed(point), true)
})
test('interpolated, approximate and unknown geometry get distinct labels', () => {
  assert.match(accuracyLabel({ ...point, accuracy: 'INTERPOLATED' }), /nội suy/)
  assert.match(accuracyLabel({ ...point, accuracy: 'APPROXIMATE' }), /khu vực/)
  assert.match(accuracyLabel(point), /chưa xác minh/)
})
function draft() { return { address: 'Mock street', city: 'City', district: 'District', ward: 'Ward', latitude: 1.25, longitude: 100.75, confirmedLocation: '' } }
test('selecting a marker does not itself confirm it', () => { assert.equal(locationConfirmed(draft()), false) })
test('manual marker can be confirmed using the existing signature', () => { const value=draft();value.confirmedLocation=locationSignature(value);assert.equal(locationConfirmed(value),true) })
test('changing any address component invalidates confirmation', () => {
  for(const field of ['address','city','district','ward']){const value=draft();value.confirmedLocation=locationSignature(value);value[field]+=' changed';assert.equal(locationConfirmed(value),false)}
})
test('moving either coordinate invalidates the old confirmation', () => {
  for(const field of ['latitude','longitude']){const value=draft();value.confirmedLocation=locationSignature(value);value[field]+=0.01;assert.equal(locationConfirmed(value),false)}
})
test('query identity changes for city, district and ward', () => {
  const value=draft();for(const field of ['address','city','district','ward'])assert.notEqual(geocodingSignature(value),geocodingSignature({...value,[field]:'changed'}))
})
test('save payload round-trip retains coordinates without provider content or key', () => {
  const value={...draft(),title:'Mock listing',propertyType:'Nhà phố',transactionType:'Bán',price:'2 tỷ',area:'50',selectedAmenities:[]}
  value.confirmedLocation=locationSignature(value);value.formattedAddress='provider content';value.providerKey='fixture-not-a-real-key'
  const saved=JSON.parse(JSON.stringify(buildPostPayload(value)))
  const reopened={...value,...saved};reopened.confirmedLocation=locationSignature(reopened)
  assert.equal(reopened.latitude,1.25);assert.equal(reopened.longitude,100.75);assert.equal(locationConfirmed(reopened),true)
  assert.equal('formattedAddress' in saved,false);assert.equal('providerKey' in saved,false)
})
test('public maps never use fallback coordinates for missing points', () => { assert.equal(publicMapPoint({latitude:null,longitude:null}),false);assert.equal(mapUrl({latitude:'',longitude:''}),'');assert.equal(mapUrl(null),'') })
test('map URLs use exact supplied axis order', () => { assert.match(mapUrl({latitude:1.25,longitude:100.75}), /marker=1\.25,100\.75/) })
test('future private and unapproved building-only points are not rendered', () => { assert.equal(mapUrl({...point,locationVisibility:'HIDDEN'}),'');assert.equal(mapUrl({...point,locationAccuracy:'BUILDING_ONLY',locationApproved:false}),'') })
test('legacy coordinates are labeled unknown; approximation is never presented as exact', () => { assert.match(locationLabel({}),/chưa xác minh/);assert.match(locationLabel({locationAccuracy:'APPROXIMATE'}),/tương đối/);assert.match(locationLabel({locationAccuracy:'BUILDING_ONLY'}),/tòa nhà/) })

test('interpolated geometry cannot be directly confirmed even with a full house match', () => { assert.equal(candidateCanBeConfirmed({ ...point, accuracy: 'INTERPOLATED' }), false) })

test('configuration lookup never sends an address or provider key',async()=>{
 let sent;await geocodingConfiguration(async(path,options)=>{sent={path,options};return {available:false,reason:'MISSING_PROVIDER_KEY'}});assert.deepEqual(sent,{path:'/geocoding/config',options:undefined})
})
test('sharing consent is required before the client can submit an address',async()=>{
 let calls=0;for(const shareAddress of [undefined,false])await assert.rejects(searchLocations({address:'Mock',city:'City',shareAddress},async()=>{calls++}),/đồng ý/);assert.equal(calls,0)
})
test('sample query deduplicates administrative prefixes and accented city aliases without editing original input',()=>{
 const input=Object.freeze({address:'Lô số 03, Khu A2-1, Phường Thọ Quang, Quận Sơn Trà, Đà Nẵng',ward:'Thọ Quang',district:'Sơn Trà',city:'Da Nang'})
 assert.equal(normalizeAddressQuery(input),input.address+', Việt Nam');assert.ok(input.address.startsWith('Lô số 03'))
})
test('a full ward address never gains a former district from optional fields',()=>{
 assert.equal(normalizeAddressQuery({address:'Phường Sơn Trà, Đà Nẵng',district:'Sơn Trà',ward:'Sơn Trà',city:'Da Nang'}),'Phường Sơn Trà, Đà Nẵng, Việt Nam')
})
test('administrative suggestions only use explicit unambiguous input and do not overwrite selections',()=>{
 const value={address:'Lô 03, Phường Thọ Quang, Quận Sơn Trà, Đà Nẵng'};assert.deepEqual(administrativeHints(value,['Sơn Trà','Cẩm Lệ']),{district:'Sơn Trà',ward:'Thọ Quang'})
 assert.deepEqual(administrativeHints({...value,district:'Cẩm Lệ',ward:'Đã chọn'},['Sơn Trà','Cẩm Lệ']),{district:'',ward:''})
 assert.equal(administrativeHints({address:'Phường Sơn Trà, Đà Nẵng'},['Sơn Trà']).district,'')
 assert.equal(administrativeHints({address:'Quận Sơn Trà, Quận Cẩm Lệ'},['Sơn Trà','Cẩm Lệ']).district,'')
})
test('unknown or conflicting provider geography cannot be confirmed directly',()=>{
 assert.equal(candidateCanBeConfirmed({...point,context:undefined}),false);assert.equal(candidateCanBeConfirmed({...point,context:{localityMatched:false,warning:'Khác địa bàn'}}),false)
 assert.match(accuracyLabel({...point,context:{precision:'APPROXIMATE_STREET'}}),/chưa xác định số nhà/);assert.match(accuracyLabel({...point,locationLevel:'UNKNOWN'}),/Chưa xác định/)
})

test('query deduplication preserves address but the request always retains the selected geographic constraints',async()=>{
 const address='46 Điện Biên Phủ, phường Thanh Khê, Đà Nẵng, Việt Nam',input=Object.freeze({address,city:'Da Nang',ward:'Thạc Gián',district:'Thanh Khê',shareAddress:true})
 assert.equal(normalizeAddressQuery(input),address)
 let sent;await searchLocations(input,async(p,o)=>{sent=o.body;return {candidates:[]}})
 assert.equal(sent.address,address);assert.equal(sent.ward,'Thạc Gián');assert.equal(sent.district,'Thanh Khê');assert.equal(input.ward,'Thạc Gián')
})
test('explicit historical address keeps its own ward and district, ignoring conflicting optional values',()=>{
 const address='46 Điện Biên Phủ, Phường Thạc Gián, Quận Thanh Khê, Đà Nẵng'
 assert.equal(normalizeAddressQuery({address,city:'Da Nang',ward:'Hòa Quý',district:'Ngũ Hành Sơn'}),address+', Việt Nam')
})
test('a changed explicit district cannot inherit the previous ward',()=>{
 const value={address:'10 Đường kiểm thử, Quận Sơn Trà, Đà Nẵng',city:'Da Nang',ward:'Thạc Gián',district:'Thanh Khê'}
 assert.equal(effectiveGeocodingInput(value).ward,'');assert.equal(effectiveGeocodingInput(value).district,'Sơn Trà');assert.equal(normalizeAddressQuery(value),value.address+', Việt Nam')
})
test('multiple explicit wards stay ambiguous, without an invented replacement',()=>{
 const input={address:'Địa chỉ, Phường Thanh Khê, Phường Hải Châu, Đà Nẵng',city:'Da Nang',ward:'Thạc Gián',district:'Thanh Khê'}
 assert.equal(effectiveGeocodingInput(input).ward,'');assert.equal(effectiveGeocodingInput(input).district,'');assert.equal(normalizeAddressQuery(input),input.address+', Việt Nam')
})
test('provider timeout, quota, rate limit, auth and errors have distinct messages',()=>{
 const messages=['GEOCODING_TIMEOUT','GEOCODING_QUOTA','RATE_LIMITED','GEOCODING_AUTH_FAILED','GEOCODING_PROVIDER_ERROR'].map(code=>geocodingErrorMessage({code}))
 assert.equal(new Set(messages).size,5);assert.match(messages[0],/thời gian/);assert.match(messages[1],/hạn mức/);assert.match(messages[3],/Key/)
})

test('district and historical ward selections are sent unchanged for street-only search',async()=>{
 const input=Object.freeze({address:'Võ Nguyên Giáp',city:'Da Nang',district:'Ngũ Hành Sơn',ward:'Hòa Hải',shareAddress:true});let sent;await searchLocations(input,async(p,o)=>{sent=o.body;return {status:'SCOPE_UNAVAILABLE',candidates:[]}});assert.equal(sent.district,input.district);assert.equal(sent.ward,input.ward);assert.equal(sent.address,input.address)
})
