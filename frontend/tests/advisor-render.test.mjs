import test from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { publicAdvisorResponse } from '../src/features/prediction/advisor.js'

test('compiled Vue renders public areas, properties, scores, sources and warnings without HTML injection', async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  try {
    const component = (await vite.ssrLoadModule('/src/components/AdvisorResults.vue')).default
    // Isolated test fixtures only: never seed these records or intercept live API responses.
    const property = i => ({id:'property:'+i,title:i===0?'<img src=x onerror=alert(1)>':'Unit test '+i,propertyType:'HOUSE',priceVnd:2e9,areaSqm:80,district:'Cẩm Lệ',ward:null,
      score:85-i,source:{kind:'PROPERTY',name:'SmartProp',recordKey:String(i)},qualityStatus:'PLATFORM_PUBLISHED',verificationStatus:'PLATFORM_PUBLISHED',
      explanations:['Theo ngân sách đã nhập'],warnings:['Cần đối chiếu thông tin nguồn'],duplicateGroup:null})
    const area = i => ({district:'Test district '+i,ward:null,candidateCount:2,score:80-i,averageAskingPriceVnd:2e9,sources:['SmartProp'],unverifiedCount:0,needsReviewCount:0,explanations:['Có tin phù hợp'],warnings:['Giá rao tham khảo']})
    const result=publicAdvisorResponse({mode:'SAFE',method:'HEURISTIC_V1',eligibleCandidateCount:10,topAreas:Array.from({length:5},(_,i)=>area(i)),topProperties:Array.from({length:10},(_,i)=>property(i)),warnings:[]})
    const html = await renderToString(createSSRApp(component,{result,points:[],selectedId:'property:0'}))
    assert.equal((html.match(/data-advisor-area/g)||[]).length,5)
    assert.equal((html.match(/data-advisor-property=/g)||[]).length,10)
    assert.match(html,/role="meter"/);assert.match(html,/Theo ngân sách đã nhập/)
    assert.match(html,/Nguồn:.*SmartProp/s);assert.match(html,/Cần đối chiếu thông tin nguồn/)
    assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<img src=x/)
    assert.match(html,/Chưa có tọa độ công khai/)
    const selected=await renderToString(createSSRApp(component,{result,selectedId:'property:0',points:[{id:'property:0',title:'Unit test only',latitude:16.0544,longitude:108.2022,price:2e9,currency:'VND',priceUnit:'TOTAL',transactionType:'SALE'}]}))
    assert.match(selected,/data-property-id="property:0"/)
    assert.match(selected,/Đang chọn trên bản đồ/)
    assert.match(selected,/aria-pressed="true"/)
    const empty=await renderToString(createSSRApp(component,{result:{...result,eligibleCandidateCount:0,topAreas:[],topProperties:[]},points:[]}))
    assert.match(empty,/data-advisor-empty/);assert.match(empty,/Chưa có gợi ý công khai phù hợp/)
    assert.doesNotMatch(empty,/data-property-id=/)
  } finally { await vite.close() }
})
