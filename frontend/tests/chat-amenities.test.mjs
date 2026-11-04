import test from 'node:test'
import assert from 'node:assert/strict'
import { amenityIntent, validateAmenityMap, amenitySummary } from '../src/features/prediction/chatAmenities.js'
import { poiColor, poiSvgPath } from '../src/features/map/nearbyPlaces.js'
import { createServer } from 'vite'
import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'
const packet={mode:'SAFE',generationMode:'EVIDENCE_ONLY',retrievalMode:'TOOL_EVIDENCE_ONLY',answer:'Unit only',recommendedProperties:[],citations:[],dataLimitations:[],evidence:{}}
const intent=amenityIntent('Hải Châu có bệnh viện nào?',packet)
function data(){return {version:'POI_MAP_V1',visibility:'PUBLIC',district:'Hải Châu',category:'HOSPITAL',eligibleCount:1,truncated:false,dataLimitations:['Unit only'],items:[{id:'unit-only',name:'Unit fixture <img>',category:'HOSPITAL',district:'Hải Châu',latitude:16.05,longitude:108.22,coordinateBasis:'OSM_NODE',reviewStatus:'VALID',sourceName:'openstreetmap_overpass',sourceUrl:'https://www.openstreetmap.org/node/12',attribution:'OSM',sourceLicense:'ODbL'}]}}
test('question intent matches exact district/category, accents, multiple categories and no arbitrary area fallback',()=>{
  for(const [q,d,c] of [['Hải Châu có bệnh viện nào?','Hải Châu','HOSPITAL'],['Cẩm Lệ có trường học nào?','Cẩm Lệ','SCHOOL'],['Ngũ Hành Sơn có bãi biển nào?','Ngũ Hành Sơn','BEACH'],['Sơn Trà có những tiện ích gì?','Sơn Trà',undefined]]){
    const i=amenityIntent(q,packet);assert.equal(i.district,d);assert.equal(i.categories[0],c);assert.equal(i.enabled,true)
  }
  assert.equal(amenityIntent('Cho tôi nhà ở Cẩm Lệ',packet).categories.length,0)
  assert.deepEqual(amenityIntent('Chợ và siêu thị Sơn Trà',packet).categories,['SUPERMARKET','MARKET'])
  assert.equal(amenityIntent('Bệnh viện Hải Châu và Sơn Trà',packet).enabled,false)
  assert.equal(amenityIntent('Trường học ở phường Hòa Xuân Cẩm Lệ',packet).enabled,false)
  assert.equal(amenityIntent('Tiện ích ở Hà Nội',packet).enabled,false)
})
test('follow-up without a district uses the server-resolved amenity intent, user text still wins',()=>{
  const followup={...packet,evidence:{amenityIntent:{district:'Hải Châu',categories:['HOSPITAL']}}}
  const i=amenityIntent('Có bệnh viện nào trong khu vực đó?',followup)
  assert.equal(i.district,'Hải Châu');assert.deepEqual(i.categories,['HOSPITAL']);assert.equal(i.enabled,true);assert.equal(i.requested,true)
  // A rephrasing the local regex misses inherits the same server category the answer was validated against.
  const yTe=amenityIntent('Trong khu vực đó có tiện ích y tế nào?',followup)
  assert.equal(yTe.district,'Hải Châu');assert.deepEqual(yTe.categories,['HOSPITAL']);assert.equal(yTe.enabled,true)
  // An explicitly named district always overrides the inherited one.
  assert.equal(amenityIntent('Có bệnh viện nào ở Sơn Trà?',followup).district,'Sơn Trà')
  // Ward/street narrowing is still refused, and a packet without an intent is unchanged.
  assert.equal(amenityIntent('Bệnh viện ở phường Hòa Xuân?',followup).enabled,false)
  assert.equal(amenityIntent('Có bệnh viện nào trong khu vực đó?',packet).enabled,false)
  // The server intent is evidence, not authority: a category the map cannot render must
  // refuse rather than silently widen to every category in the district.
  const unmapped={...packet,evidence:{amenityIntent:{district:'Hải Châu',categories:['WATER_PARK']}}}
  const widened=amenityIntent('Trong khu vực đó có tiện ích y tế nào?',unmapped)
  assert.deepEqual(widened.categories,[]);assert.equal(widened.enabled,false);assert.equal(widened.requested,false)
})

test('public map guard rejects unverified, research, mismatched geography, fake coordinate basis, source and distances',()=>{
  assert.equal(validateAmenityMap(data(),intent).items.length,1)
  for(const change of [{reviewStatus:'LEGACY_UNVERIFIED'},{coordinateBasis:'AREA_CENTROID'},{sourceUrl:'https://evil.invalid/12'},{district:'Sơn Trà'},{latitude:NaN},{longitude:0},{distanceMeters:100},{sampleListingCount:5},{category:'TiniX'}]){
    const d=data();Object.assign(d.items[0],change);assert.throws(()=>validateAmenityMap(d,intent))
  }
  const d=data();d.visibility='INTERNAL_RESEARCH';assert.throws(()=>validateAmenityMap(d,intent))
  assert.throws(()=>amenityIntent('Hải Châu', {...packet,mode:'INTERNAL_RESEARCH'}))
})
test('real names drive short summary without mutating source payload; category colors/icons distinct',()=>{
  const d=data(),before=JSON.stringify(d);assert.match(amenitySummary(validateAmenityMap(d,intent)),/Unit fixture/);assert.equal(JSON.stringify(d),before)
  for(const [a,b] of [['BEACH','PARK'],['MARKET','SUPERMARKET'],['PHARMACY','HOSPITAL']]) {assert.notEqual(poiColor(a),poiColor(b));assert.notEqual(poiSvgPath(a),poiSvgPath(b))}
})
test('boundary requires verified source/version and closed coordinates; cannot substitute a centroid',()=>{
  const d=data();d.items=[];d.eligibleCount=0
  d.boundary={name:'Hải Châu',version:'OCHA-2020-geoBoundaries-9469f09',sourceUrl:'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/VNM/ADM2/geoBoundaries-VNM-ADM2.geojson',attribution:'Unit boundary',license:'CC',geometry:{type:'Polygon',coordinates:[[[108.2,16],[108.21,16],[108.21,16.1],[108.2,16]]]}}
  assert.equal(validateAmenityMap(d,intent).items.length,0)
  for(const type of ['Point','Circle']){const copy=structuredClone(d);copy.boundary.geometry.type=type;assert.throws(()=>validateAmenityMap(copy,intent))}
  d.boundary.version='guessed';assert.throws(()=>validateAmenityMap(d,intent))
})
test('compiled amenity component renders escaped real fields, OSM attribution, loading/error/empty without empty map',async()=>{
  const vite=await createServer({server:{middlewareMode:true,hmr:false},appType:'custom'})
  try {
    const component=(await vite.ssrLoadModule('/src/components/ChatAmenityMap.vue')).default
    const render=props=>renderToString(createSSRApp(component,props))
    const html=await render({data:data(),status:'ready'});assert.match(html,/data-chat-map/);assert.match(html,/&lt;img&gt;/);assert.match(html,/openstreetmap.org\/node\/12/);assert.doesNotMatch(html,/Cách BĐS/)
    for(const status of ['loading','error','ready']) {const h=await render({status});assert.doesNotMatch(h,/data-chat-map/);assert.match(h,status==='error'?/Thử lại bản đồ/:status==='loading'?/Đang tìm/:/không đặt ghim/)}
  } finally {await vite.close()}
})
