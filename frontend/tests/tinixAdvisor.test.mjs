import test from 'node:test'
import assert from 'node:assert/strict'
import { createResearchAdvisorClient, researchAdvisorResponse } from '../src/features/prediction/tinixAdvisor.js'
import { publicAdvisorResponse, advisorMapData, advisorListingUrl } from '../src/features/prediction/advisor.js'
const id = 'a'.repeat(64)
const row = () => ({ id:'tinix:'+id,title:'Research fixture',source:{kind:'TINIX_AI',name:'TiniX AI',recordKey:id,detailUrl:null},propertyType:'HOUSE',priceVnd:1750000000,areaSqm:80.125,score:80,district:'Hải Châu',qualityStatus:'HYBRID_ELIGIBLE_RESEARCH',verificationStatus:'UNVERIFIED',duplicateGroup:'g',explanations:['Matches'],warnings:['Dữ liệu nghiên cứu TiniX AI — chưa xác minh.'] })
const response = () => ({ mode:'INTERNAL_DEMO',method:'HEURISTIC_V1',criteria:{budgetVnd:1750000000},eligibleCandidateCount:1,topProperties:[row()],topAreas:[],warnings:['Research only'] })
test('research uses authenticated endpoint and never forwards demo secret or user-selected mode', async () => {
  const client=createResearchAdvisorClient(async (path,options) => {
    assert.equal(path,'/recommendations/research');assert.equal(options.authenticated,true);assert.equal(options.headers,undefined)
    assert.equal(options.body.budgetVnd,1750000000);assert.equal(options.body.demoKey,undefined)
    return response()
  })
  await client({budgetVnd:'1.750.000.000',purpose:'LIVING',propertyType:'ALL',limit:10,demoKey:'discard'})
})
test('public validator still blocks all TiniX and demo responses', () => {
  assert.throws(()=>publicAdvisorResponse(response()))
  assert.throws(()=>publicAdvisorResponse({...response(),mode:'SAFE'}))
})
test('research gate refuses held, review, duplicate, fabricated-link and over-budget rows', () => {
  assert.equal(researchAdvisorResponse(response()).topProperties.length,1)
  for(const change of [{protectedHoldout:true},{qualityStatus:'NEEDS_REVIEW'},{verificationStatus:'VERIFIED'},{source:{...row().source,detailUrl:'https://example.invalid/fake'}},{priceVnd:1750000001}])assert.throws(()=>researchAdvisorResponse({...response(),topProperties:[{...row(),...change}]}))
  assert.throws(()=>researchAdvisorResponse({...response(),topProperties:[row(),row()]}))
})
test('TiniX never gets an invented source URL, contact or GIS marker', async () => {
  assert.equal(advisorListingUrl(row()),null)
  const data=await advisorMapData([row()],()=>{throw Error('Must not geocode dataset')})
  assert.deepEqual(data.points,[]);assert.equal(data.unlocatedCount,1)
})
