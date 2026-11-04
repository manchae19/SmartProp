import test from 'node:test'
import assert from 'node:assert/strict'
import { chatPresentation, compactChatPrice, isNearChatBottom } from '../src/features/prediction/chatPresentation.js'

function packet(count=8) {
  const ps=Array.from({length:count},(_,i)=>({id:'property:unit-'+i,title:'Fixture property '+i,priceVnd:String(7080000000+i),areaSqm:'90',score:String(83-i),source:{kind:'PROPERTY',name:'Unit only',recordKey:'unit-'+i},qualityStatus:'PLATFORM_PUBLISHED',verificationStatus:'PLATFORM_PUBLISHED',ward:'Unit ward',district:'Unit district',explanations:['Fixture reason '+i],warnings:[],scoreBreakdown:{budgetFit:88.5}}))
  return {mode:'SAFE',generationMode:'QWEN_GROUNDED_ANSWER',retrievalMode:'E5_FAISS',answer:'Original fixture text with property:unit-0 and 7080000000 — not live data.',recommendedProperties:ps,
    citations:ps.map(p=>({sourceId:'recommendation:'+p.id,url:'/api/v1/recommendations',kind:'RECOMMENDATION',scope:'PUBLIC',version:'UNIT',contentHash:'a'.repeat(64)})),
    evidence:{criteria:{budgetVnd:'10000000000'},generation:{accepted:true,eval_count:10,sentences:[{text:'Original fixture text',sourceId:'recommendation:property:unit-0'}]}},dataLimitations:['Isolated fixture only']}
}
test('summary derives count from structured API, never parses Qwen prose or duplicates money/UUID',()=>{
  const data=packet(),before=JSON.stringify(data),view=chatPresentation(data)
  assert.match(view.summary,/8 bất động sản/);assert.match(view.summary,/3 lựa chọn/)
  assert.doesNotMatch(view.summary,/7080000000|property:unit|88,5|Original/)
  assert.deepEqual(view.cards.map(p=>p.id),data.recommendedProperties.map(p=>p.id))
  assert.equal(view.originalAnswer,data.answer);assert.equal(JSON.stringify(data),before)
  assert.equal(view.citations[0].sourceId,data.citations[0].sourceId);assert.equal(view.citations[0].contentHash,data.citations[0].contentHash)
  assert.equal(view.cards[0].price.text,'7,08 tỷ đồng');assert.equal(view.cards[0].price.exact,'7.080.000.000 đồng')
  assert.equal(view.cards[0].reason,'Mức phù hợp ngân sách: 88,5/100.')
})
test('compact VND prices are exact, never rounded, including unusual precision',()=>{
  for(const [value,wanted] of [['5500000000','5,5 tỷ đồng'],['950000000','950 triệu đồng'],['1250000000','1,25 tỷ đồng'],['1000000','1 triệu đồng'],['999999','999.999 đồng'],['2000000000.01','2.000.000.000,01 đồng']])assert.equal(compactChatPrice(value).text,wanted)
  for(const invalid of [-1,null,'NaN','1e9'])assert.throws(()=>compactChatPrice(invalid))
})
test('empty results and amenity sources remain distinct, no fake property or citations',()=>{
  const d=packet(0);d.generationMode='EVIDENCE_ONLY';d.retrievalMode='TOOL_EVIDENCE_ONLY';d.answer='Fixture no-match';d.evidence={responseKind:'NO_MATCHES',criteria:{budgetVnd:'2000000000'},generation:{accepted:false,reason:'NOT_NEEDED_FOR_EMPTY_SEARCH'},recommendationSearch:{performed:true,resultCount:0,sourcePath:'/api/v1/recommendations',criteriaHash:'b'.repeat(64)}}
  const view=chatPresentation(d);assert.equal(view.cards.length,0);assert.equal(view.citations.length,0);assert.equal(view.fallback,false);assert.match(view.summary,/chưa tìm thấy/)
  const amenity={...d,answer:'Unit evidence',evidence:{generation:{accepted:false}},citations:[{sourceId:'amenity:fixture',url:'/api/v1/amenities/fixture',kind:'AREA_AMENITY',scope:'PUBLIC',version:'UNIT',contentHash:'c'.repeat(64)}]}
  const a=chatPresentation(amenity);assert.match(a.summary,/1 nguồn/);assert.match(a.summary,/không phải khoảng cách/);assert.equal(a.fallback,true)
})
test('unsafe packet still rejected before presentation and hidden metadata preserved',()=>{
  const data=packet();data.mode='INTERNAL_RESEARCH';assert.throws(()=>chatPresentation(data))
  const price=packet();price.recommendedProperties[0].priceVnd='11000000000';assert.throws(()=>chatPresentation(price))
})
test('scroll follower detects user reading history without forcing position',()=>{
  assert.equal(isNearChatBottom({scrollHeight:2000,clientHeight:700,scrollTop:0}),false)
  assert.equal(isNearChatBottom({scrollHeight:2000,clientHeight:700,scrollTop:1270}),true)
  assert.equal(isNearChatBottom(null),true)
})
