import test from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { publicChatResponse } from '../src/services/chat.js'

test('compiled Chat UI escapes model/source text, renders citations and explicit fallback/empty state',async()=>{
  const vite=await createServer({server:{middlewareMode:true,hmr:false},appType:'custom'})
  try{
    const component=(await vite.ssrLoadModule('/src/components/ChatAnswer.vue')).default
    const d={mode:'SAFE',generationMode:'EVIDENCE_ONLY',retrievalMode:'TOOL_EVIDENCE_ONLY',answer:'<img src=x onerror=alert(1)> [amenity:unit]',recommendedProperties:[],citations:[{sourceId:'amenity:unit',scope:'PUBLIC',kind:'AREA_AMENITY',url:'https://unit.invalid/api/v1/amenities/unit',version:'fixture',contentHash:'a'.repeat(64)}],dataLimitations:['Không phải dữ liệu thật.'],evidence:{criteria:{budgetVnd:'2000000000'}}}
    const answerApp=createSSRApp(component,{result:publicChatResponse(d),messageId:1})
    answerApp.component('RouterLink',{props:['to'],setup:(props,{slots})=>()=>h('a',{href:props.to},slots.default?.())})
    const html=await renderToString(answerApp)
    assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<img src=x/);assert.match(html,/data-chat-fallback/);assert.match(html,/data-chat-empty/)
    assert.match(html,/href="\/api\/v1\/amenities\/unit"/);assert.match(html,/noopener noreferrer/);assert.match(html,/Phiên bản/);assert.match(html,/SHA-256/)
    assert.match(html,/không chứng minh khoảng cách/)
    const noMatches={...d,answer:'Chưa có kết quả kiểm thử cô lập.',citations:[],evidence:{responseKind:'NO_MATCHES',criteria:{budgetVnd:'2000000000'},generation:{accepted:false,reason:'NOT_NEEDED_FOR_EMPTY_SEARCH'},recommendationSearch:{performed:true,resultCount:0,sourcePath:'/api/v1/recommendations',criteriaHash:'d'.repeat(64)}}}
    const emptyApp=createSSRApp(component,{result:publicChatResponse(noMatches),messageId:2})
    emptyApp.component('RouterLink',{props:['to'],setup:(props,{slots})=>()=>h('a',{href:props.to},slots.default?.())})
    const noMatchHtml=await renderToString(emptyApp)
    assert.match(noMatchHtml,/Kết quả tra cứu dữ liệu công khai/);assert.match(noMatchHtml,/data-chat-empty/)
    assert.doesNotMatch(noMatchHtml,/data-chat-fallback|data-chat-sources|AI chưa sẵn sàng|Muốn tìm bất động sản/)
    const properties=Array.from({length:8},(_,i)=>({id:'property:unit-'+i,title:'Fixture listing '+i,priceVnd:'5500000000',areaSqm:'75',score:'83',ward:'Unit ward',district:'Unit district',source:{kind:'PROPERTY',name:'Unit',recordKey:'unit-'+i},qualityStatus:'PLATFORM_PUBLISHED',verificationStatus:'PLATFORM_PUBLISHED',explanations:['A fixture reason'],warnings:[]}))
    const data={...d,answer:'Fixture original detailed answer.',recommendedProperties:properties,citations:properties.map(p=>({sourceId:'recommendation:'+p.id,scope:'PUBLIC',kind:'RECOMMENDATION',url:'/api/v1/recommendations',version:'Unit',contentHash:'b'.repeat(64)})),evidence:{criteria:{budgetVnd:'10000000000'},generation:{accepted:false}}}
    const cardsApp=createSSRApp(component,{result:publicChatResponse(data),messageId:3})
    cardsApp.component('RouterLink',{props:['to'],setup:(props,{slots})=>()=>h('a',{href:props.to},slots.default?.())})
    const cardsHtml=await renderToString(cardsApp)
    assert.equal((cardsHtml.match(/data-chat-property=/g)||[]).length,3)
    assert.match(cardsHtml,/Xem tất cả 8 bất động sản/);assert.match(cardsHtml,/5,5 tỷ đồng/)
    assert.ok(cardsHtml.indexOf('data-chat-summary')<cardsHtml.indexOf('data-chat-properties'))
    assert.ok(cardsHtml.indexOf('data-chat-properties')<cardsHtml.indexOf('data-chat-sources'))
    assert.match(cardsHtml,/data-chat-original/);assert.match(cardsHtml,/Nguồn \(8\)/)
    const clarify={...d,answer:'B\u1ea1n \u0111ang n\u00f3i t\u1edbi b\u1ea5t \u0111\u1ed9ng s\u1ea3n n\u00e0o? H\u00e3y n\u00f3i r\u00f5 th\u1ee9 t\u1ef1.',citations:[],evidence:{responseKind:'CLARIFICATION_REQUIRED',clarification:'AMBIGUOUS_PROPERTY_REFERENCE',criteria:{budgetVnd:'2000000000'}}}
    const clarifyApp=createSSRApp(component,{result:publicChatResponse(clarify),messageId:4})
    clarifyApp.component('RouterLink',{props:['to'],setup:(props,{slots})=>()=>h('a',{href:props.to},slots.default?.())})
    const clarifyHtml=await renderToString(clarifyApp)
    // The question must be visible outside the collapsed panel and must not read as an outage.
    assert.match(clarifyHtml,/B\u1ea1n \u0111ang n\u00f3i t\u1edbi b\u1ea5t \u0111\u1ed9ng s\u1ea3n n\u00e0o/)
    assert.doesNotMatch(clarifyHtml,/data-chat-fallback|AI ch\u01b0a s\u1eb5n s\u00e0ng|data-chat-empty/)
    // No citations exist yet, so there is no panel to hide it in: the question is the card body.
    assert.doesNotMatch(clarifyHtml,/<details/);assert.ok(clarifyHtml.indexOf('data-chat-clarification')>0)
    const view=(await vite.ssrLoadModule('/user/views/ChatAdvisorView.vue')).default
    const app=createSSRApp(view);app.component('RouterLink',{props:['to'],setup:(props,{slots})=>()=>h('a',{href:props.to},slots.default?.())})
    const initial=await renderToString(app)
    assert.match(initial,/role="log"/);assert.match(initial,/id="chat-question"/);assert.match(initial,/maxlength="2000"/)
    assert.match(initial,/không lưu vào tài khoản/);assert.doesNotMatch(initial,/data-chat-answer/)
  }finally{await vite.close()}
})
