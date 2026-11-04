import test from 'node:test'
import assert from 'node:assert/strict'
import {advisorRequest, publicAdvisorResponse, createAdvisorClient, advisorMapPoints, advisorMapData, advisorListingUrl, advisorError, advisorWarning} from '../src/features/prediction/advisor.js'
const form = {budgetBillions:'2',purpose:'LIVING',propertyType:'ALL',limit:10,minAreaSqm:'',district:'',ward:''}
const emptyResponse = () => ({mode:'SAFE',method:'HEURISTIC_V1',eligibleCandidateCount:0,topAreas:[],topProperties:[],warnings:[]})
const property = overrides => ({id:'property:one',title:'Unit-test property',propertyType:'HOUSE',priceVnd:2e9,areaSqm:80,score:82,
  source:{kind:'PROPERTY',name:'SmartProp',recordKey:'one'},qualityStatus:'PLATFORM_PUBLISHED',verificationStatus:'PLATFORM_PUBLISHED',explanations:['Fits budget'],warnings:[],...overrides})
const area = overrides => ({district:'Cẩm Lệ',ward:null,candidateCount:1,score:80,averageAskingPriceVnd:2e9,sources:['SmartProp'],unverifiedCount:0,needsReviewCount:0,explanations:['Fits budget'],warnings:[],...overrides})
test('dynamic budgets and optional filters create a whitelisted VND request', () => {
  assert.equal(advisorRequest(form).budgetVnd,2e9)
  assert.equal(advisorRequest({...form,budgetBillions:'5'}).budgetVnd,5e9)
  assert.deepEqual(advisorRequest({...form,district:' Cẩm Lệ ',minAreaSqm:'60',demoKey:'never-forward'}),
    {budgetVnd:2e9,purpose:'LIVING',propertyType:'ALL',limit:10,district:'Cẩm Lệ',minAreaSqm:60})
  for(const bad of [{budgetBillions:'0'},{budgetBillions:'NaN'},{purpose:'OTHER'},{limit:11},{minAreaSqm:'-1'}]) assert.throws(()=>advisorRequest({...form,...bad}))
})
test('public client sends neither credentials nor a source/demo flag', async () => {
  const response = emptyResponse()
  const load = createAdvisorClient(async(path,options)=>{assert.equal(path,'/recommendations');assert.equal(options.authenticated,false);assert.equal(options.headers,undefined);assert.equal(options.body.source,undefined);return response})
  assert.equal(await load(form),response)
})
test('public display refuses demo, unverified, rejected, holdout and review aggregates', () => {
  const empty = emptyResponse()
  assert.equal(publicAdvisorResponse(empty),empty)
  assert.throws(()=>publicAdvisorResponse({...empty,mode:'INTERNAL_DEMO'}))
  for(const p of [{qualityStatus:'VALID',verificationStatus:'UNVERIFIED'}, {qualityStatus:'REJECTED',verificationStatus:'VERIFIED'}, {qualityStatus:'VALID',verificationStatus:'VERIFIED',protectedHoldout:true}]) assert.throws(()=>publicAdvisorResponse({...empty,eligibleCandidateCount:1,topProperties:[p]}))
  assert.throws(()=>publicAdvisorResponse({...empty,topAreas:[{unverifiedCount:1,needsReviewCount:0}]}))
})
test('map never invents points or geocodes crawler addresses', async () => {
  let reads = 0
  assert.deepEqual(await advisorMapPoints([{source:{kind:'EXTERNAL'}}],()=>{reads++;throw Error()}),[])
  assert.equal(reads,0)
  const p={id:'p',title:'Fixture',priceVnd:2e9,source:{kind:'PROPERTY',recordKey:'property-id'}}
  assert.deepEqual(await advisorMapPoints([p],async()=>({id:'property-id',status:'PUBLISHED',latitude:16.05,longitude:108.2})),
    [{id:'p',title:'Fixture',price:2e9,currency:'VND',priceUnit:'TOTAL',transactionType:'SALE',latitude:16.05,longitude:108.2,locationLabel:'Vị trí do người đăng cung cấp; chưa xác minh độ chính xác'}])
  assert.deepEqual(await advisorMapPoints([p],async()=>({id:'property-id',status:'PUBLISHED'})),[])
  assert.deepEqual(await advisorMapPoints([p],async()=>{throw Error('offline')}),[])
})
test('source links cannot execute scripts', () => {
  assert.equal(advisorListingUrl({source:{kind:'EXTERNAL',detailUrl:'javascript:alert(1)'}}),null)
  assert.equal(advisorListingUrl({source:{kind:'EXTERNAL',detailUrl:'https://example.org/listing'}}),'https://example.org/listing')
})

test('Vietnamese decimals and small budgets preserve VND without scientific or grouped input', () => {
  assert.equal(advisorRequest({...form,budgetBillions:'2,5'}).budgetVnd,2.5e9)
  assert.equal(advisorRequest({...form,budgetBillions:'0.000000001'}).budgetVnd,1)
  for(const budgetBillions of ['1e3','-2','1,000,000','Infinity','2.0000000001'])assert.throws(()=>advisorRequest({...form,budgetBillions}))
})

test('valid public platform and verified external contracts are accepted', () => {
  const external=property({id:'external:two',source:{kind:'EXTERNAL',name:'Source',recordKey:'two'},qualityStatus:'VALID',verificationStatus:'VERIFIED'})
  const data={...emptyResponse(),eligibleCandidateCount:2,topProperties:[property(),external],topAreas:[area()]}
  assert.equal(publicAdvisorResponse(data),data)
})

test('wrong source/status pairs and malformed public results fail closed', () => {
  for(const overrides of [{source:{kind:'UNKNOWN'}},{priceVnd:-1},{areaSqm:NaN},{score:101},{warnings:null},{explanations:'not an array'}, {source:{kind:'EXTERNAL',name:'S',recordKey:'one'}}, {is_protected_holdout:true}]) {
    assert.throws(()=>publicAdvisorResponse({...emptyResponse(),eligibleCandidateCount:1,topProperties:[property(overrides)]}))
  }
  for(const overrides of [{score:-1},{candidateCount:0},{unverifiedCount:1},{needsReviewCount:1},{sources:null},{warnings:null}])assert.throws(()=>publicAdvisorResponse({...emptyResponse(),topAreas:[area(overrides)]}))
})

test('duplicates and excessive lists cannot render as public results', () => {
  assert.throws(()=>publicAdvisorResponse({...emptyResponse(),eligibleCandidateCount:2,topProperties:[property(),property()]}))
  const external=id=>property({id,duplicateGroup:'g',source:{kind:'EXTERNAL',name:'S',recordKey:id},qualityStatus:'VALID',verificationStatus:'VERIFIED'})
  assert.throws(()=>publicAdvisorResponse({...emptyResponse(),eligibleCandidateCount:2,topProperties:[external('a'),external('b')]}))
  assert.throws(()=>publicAdvisorResponse({...emptyResponse(),topAreas:Array.from({length:6},()=>area())}))
})

test('map rejects mismatched, private, placeholder and non-Mercator coordinates', async () => {
  const p=property()
  for(const detail of [{id:'wrong',status:'PUBLISHED',latitude:16,longitude:108},{id:'one',status:'DRAFT',latitude:16,longitude:108},
    {id:'one',status:'PUBLISHED',latitude:0,longitude:0},{id:'one',status:'PUBLISHED',latitude:86,longitude:108},
    {id:'one',status:'PUBLISHED',latitude:'16',longitude:108},{id:'one',status:'PUBLISHED',latitude:16,longitude:181},
    {id:'one',status:'PUBLISHED',latitude:16,longitude:108,locationVisibility:'HIDDEN'},
    {id:'one',status:'PUBLISHED',latitude:16,longitude:108,locationAccuracy:'BUILDING_ONLY',locationApproved:false}])assert.deepEqual(await advisorMapPoints([p],async()=>detail),[])
})

test('partial coordinate failure preserves real mapped points and reports retryable failures', async () => {
  const data=await advisorMapData([property(),property({id:'b',source:{kind:'PROPERTY',recordKey:'two'}})],async path=>{
    if(path.endsWith('/two'))throw Error('offline')
    return {id:'one',status:'PUBLISHED',latitude:16.05,longitude:108.2}
  })
  assert.equal(data.points.length,1);assert.equal(data.failedCount,1);assert.equal(data.unlocatedCount,1)
})

test('service failures and technical warnings have public-facing wording', () => {
  assert.match(advisorError({status:503,message:'private stack'}),/tạm gián đoạn/)
  assert.doesNotMatch(advisorError({status:503,message:'private stack'}),/stack/)
  assert.match(advisorError({status:403}),/công khai/)
  assert.match(advisorError({status:401}),/công khai chưa sẵn sàng/)
  assert.match(advisorError({status:429}),/chờ/)
  assert.doesNotMatch(advisorWarning('HEURISTIC_V1: example'),/HEURISTIC/)
  assert.match(advisorWarning('RENTAL là mua'),/ngân sách mua/)
})
