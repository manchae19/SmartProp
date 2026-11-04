import test from 'node:test'
import assert from 'node:assert/strict'
import { chatRequest, publicChatResponse, citationHref, createChatClient, createChatSession, chatError, formatChatNumber, displayEvidenceText, CHAT_TIMEOUT_MS } from '../src/features/prediction/chat.js'
import { createHttpClient } from '../src/lib/httpClient.js'
import { publicChatProxy, publicChatBoundary } from '../build/chatProxy.mjs'
import { publicChatBody } from '../server/publicChat.mjs'

// Isolated fixtures ONLY. Not injected into a live API or used for live acceptance.
export const fixture = () => ({mode:'SAFE',answer:'Bằng chứng kiểm thử cô lập. [amenity:unit]',generationMode:'EVIDENCE_ONLY',retrievalMode:'TOOL_EVIDENCE_ONLY',recommendedProperties:[],
  citations:[{sourceId:'amenity:unit',scope:'PUBLIC',kind:'AREA_AMENITY',url:'https://unit.invalid/api/v1/amenities/unit',version:'unit:v1',contentHash:'a'.repeat(64)}],dataLimitations:['Fixture, không phải dữ liệu thật.'],evidence:{generation:{accepted:false}}})
const property = () => ({id:'property:unit',title:'Fixture only',source:{kind:'PROPERTY',name:'Unit',recordKey:'unit'},priceVnd:'2000000000.01',areaSqm:'80.5',score:'82.9',qualityStatus:'PLATFORM_PUBLISHED',verificationStatus:'PLATFORM_PUBLISHED',explanations:[],warnings:[]})
function withProperty() { const data=fixture(),p=property();data.recommendedProperties=[p];data.evidence.criteria={budgetVnd:'2000000001'};data.citations.push({sourceId:'recommendation:'+p.id,kind:'RECOMMENDATION',url:'https://unit.invalid/api/v1/recommendations',version:'unit:v1',contentHash:'b'.repeat(64),scope:'PUBLIC'});return data }

test('chat request whitelist and public endpoint cannot carry caller research settings', async()=>{
  assert.deepEqual(chatRequest('  Tôi có 2 tỷ  '),{question:'Tôi có 2 tỷ',requireGeneration:false})
  for(const q of ['', ' '.repeat(5), 'a'.repeat(2001)])assert.throws(()=>chatRequest(q))
  const send=createChatClient(async(path,options)=>{assert.equal(path,'/chat');assert.equal(options.authenticated,false);assert.deepEqual(Object.keys(options.body).sort(),['question','requireGeneration']);assert.equal(options.headers,undefined);return fixture()})
  assert.equal((await send('câu hỏi')).mode,'SAFE')
})
test('all public surfaces block research, holdout, review, duplicate and fabricated prices',()=>{
  for(const mutate of [d=>d.mode='INTERNAL_RESEARCH',d=>d.answer='TINIX_AI private',d=>d.evidence.private='sampleListingCount',d=>d.citations[0].scope='INTERNAL_RESEARCH',d=>d.recommendedProperties[0].verificationStatus='UNVERIFIED',d=>d.recommendedProperties[0].qualityStatus='REJECTED',d=>d.recommendedProperties[0].qualityStatus='NEEDS_REVIEW',d=>d.recommendedProperties[0].protectedHoldout=true,d=>d.recommendedProperties[0].groupHasHoldout=true,d=>d.recommendedProperties[0].priceVnd='2000000001.01',d=>d.recommendedProperties[0].score=null,d=>d.recommendedProperties.push(d.recommendedProperties[0])]){
    const d=withProperty();mutate(d);assert.throws(()=>publicChatResponse(d))
  }
  assert.equal(publicChatResponse(withProperty()).recommendedProperties.length,1)
  const aggregate=fixture();aggregate.evidence.topAreas=[{unverifiedCount:0,needsReviewCount:0}]
  assert.equal(publicChatResponse(aggregate),aggregate)
  aggregate.evidence.topAreas[0].unverifiedCount=1;assert.throws(()=>publicChatResponse(aggregate))
})
test('citation links use canonical public routes, block injection/research and require each property citation',()=>{
  const d=withProperty();assert.equal(citationHref(d.citations[0],d.recommendedProperties),'/api/v1/amenities/unit')
  assert.equal(citationHref(d.citations[1],d.recommendedProperties),'/listing/unit')
  for(const url of ['javascript:alert(1)','https://unit.invalid/api/v1/amenities/research/areas','https://u:p@unit.invalid/api/v1/amenities/unit','https://unit.invalid/api/v1/amenities/unit?key=private']){
    const copy=fixture();copy.citations[0].url=url;assert.throws(()=>publicChatResponse(copy))
  }
  d.citations.pop();assert.throws(()=>publicChatResponse(d))
})
test('Qwen output requires actual generation, cited verbatim text; legitimate no-evidence fallback is allowed',()=>{
  const d=fixture();d.generationMode='QWEN_GROUNDED_ANSWER';assert.throws(()=>publicChatResponse(d))
  d.evidence.generation={accepted:true,eval_count:4,sentences:[{sourceId:'amenity:unit',text:'Bằng chứng kiểm thử cô lập.'}]};assert.equal(publicChatResponse(d),d)
  d.evidence.generation.sentences[0].text='Giá tự tạo 1 đồng';assert.throws(()=>publicChatResponse(d))
  const empty=fixture();empty.citations=[];assert.equal(publicChatResponse(empty),empty)
})
test('exact decimal display avoids float rounding and accepts API decimal strings',()=>{
  assert.equal(formatChatNumber('2000000000.01'),'2.000.000.000,01');assert.equal(formatChatNumber('80.500'),'80,5')
  for(const v of ['NaN',null,-1,'1e12'])assert.throws(()=>formatChatNumber(v))
})
test('tool-only empty search is validated explicitly, not confused with a model outage',()=>{
  const d=fixture();d.citations=[];d.answer='Kết quả tra cứu kiểm thử cô lập.'
  d.evidence={responseKind:'NO_MATCHES',criteria:{budgetVnd:'2000000000'},generation:{accepted:false,reason:'NOT_NEEDED_FOR_EMPTY_SEARCH'},recommendationSearch:{performed:true,resultCount:0,sourcePath:'/api/v1/recommendations',criteriaHash:'d'.repeat(64)}}
  assert.equal(publicChatResponse(d),d);assert.equal(publicChatBody(d).citations.length,0)
  for(const mutate of [v=>v.evidence.recommendationSearch.performed=false,v=>v.evidence.recommendationSearch.resultCount=2,v=>v.evidence.generation.accepted=true,v=>v.evidence.recommendationSearch.sourcePath='/api/v1/recommendations/research']){
    const value=structuredClone(d);mutate(value);assert.throws(()=>publicChatResponse(value))
  }
})
test('human-readable evidence labels preserve numbers and the underlying text/hash',()=>{
  const raw='HOSPITAL, PUBLIC_TRANSPORT; CORRIDOR_DIRECT, DIRECT_WARD_EVIDENCE. POI: 6. Giá 2000000000 đồng.'
  const result=displayEvidenceText(raw)
  assert.match(result,/cơ sở y tế/);assert.match(result,/giao thông công cộng/);assert.match(result,/tuyến đường/);assert.match(result,/phường\/xã/)
  assert.match(result,/địa điểm tiện ích: 6/);assert.match(result,/2000000000 đồng/)
  assert.match(raw,/HOSPITAL/)
})
test('one session flight, explicit retry only, cooldown, bounded history and no storage',async()=>{
  let release, calls=0, clock=10000
  const session=createChatSession(()=>{calls++;return new Promise(resolve=>release=resolve)},{now:()=>clock})
  const first=session.submit('câu hỏi');assert.equal(session.state.busy,true)
  assert.equal(await session.submit('gửi trùng'),false);assert.equal(calls,1);session.clear();assert.equal(session.state.messages.length,1)
  release(fixture());assert.equal(await first,true);assert.equal(session.state.messages.length,2)
  let failures=0;const retry=createChatSession(async()=>{failures++;throw {code:'NETWORK_ERROR'}},{now:()=>clock})
  await retry.submit('lỗi mạng');assert.equal(failures,1);assert.equal(await retry.retry(),false);assert.equal(failures,1)
  clock+=5001;await retry.retry();assert.equal(failures,2);assert.equal(retry.state.messages.length,1)
  const bounded=createChatSession(async()=>fixture());for(let i=0;i<15;i++)await bounded.submit('q'+i)
  assert.equal(bounded.state.messages.length,24);assert.equal(bounded.state.trimmed,true)
})
test('different failure classes and bounded timeout; no auth/refresh side effects',async()=>{
  assert.match(chatError({code:'NETWORK_ERROR'}).text,/kết nối/);assert.match(chatError({code:'REQUEST_TIMEOUT'}).text,/90 giây/)
  assert.equal(chatError({code:'UNSAFE_CHAT_RESPONSE'}).retry,false);assert.equal(chatError({status:403}).retry,false)
  assert.equal(chatError({status:429,retryAfter:999999}).delayMs,120000);assert.equal(CHAT_TIMEOUT_MS,90000)
  const session={token:'fixture-token',status:'AUTHENTICATED'}
  const client=createHttpClient({baseUrl:'/api',session,timeoutForPath:()=>20,fetcher:async(url,options)=>new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>reject(Object.assign(Error(),{name:'AbortError'}))))})
  await assert.rejects(client.request('/chat',{authenticated:false}),e=>e.code==='REQUEST_TIMEOUT')
  assert.equal(session.token,'fixture-token');assert.equal(session.status,'AUTHENTICATED')
})
test('public401 cannot expire login; existing protected-write refresh never resubmits the write',async()=>{
  let expired=0
  const session={token:'unit-old-token',status:'AUTHENTICATED'}
  const publicClient=createHttpClient({baseUrl:'/api',session,expired:()=>expired++,fetcher:async()=>Response.json({message:'unit unauthorized'},{status:401})})
  await assert.rejects(publicClient.request('/chat',{authenticated:false}),e=>e.status===401)
  assert.equal(expired,0);assert.equal(session.token,'unit-old-token')
  const calls=[]
  const client=createHttpClient({baseUrl:'/api',session,refreshEnabled:true,fetcher:async(url,options)=>{
    calls.push({url,method:options.method})
    if(url.endsWith('/auth/csrf'))return Response.json({headerName:'X-Unit-CSRF',token:'fixture'})
    if(url.endsWith('/auth/refresh'))return Response.json({accessToken:'unit-renewed',user:{id:'unit'}})
    return Response.json({message:'unit expired'},{status:401})
  }})
  await assert.rejects(client.request('/protected-unit-write',{method:'POST',body:{fixture:true}}),e=>e.code==='AUTH_RETRY_REQUIRED')
  assert.equal(calls.filter(c=>c.url.endsWith('/protected-unit-write')).length,1);assert.equal(session.token,'unit-renewed')
})
test('proxy strips all credentials and boundary rejects every non-public chat route',()=>{
  const config=publicChatProxy('http://127.0.0.1:18001');assert.equal(config.proxyTimeout,90000);assert.equal(config.rewrite('/api/chat'),'/chat')
  const removed=[],handlers={};config.configure({on:(name,handler)=>handlers[name]=handler});handlers.proxyReq({removeHeader:n=>removed.push(n),setHeader(){}});assert.deepEqual(removed,['Authorization','Cookie','X-SmartProp-Demo-Key','X-Session-Activity'])
  assert.equal(config.selfHandleResponse,true);assert.equal(typeof handlers.proxyRes,'function')
  assert.throws(()=>publicChatProxy('https://external.invalid'))
  let middleware;publicChatBoundary().configureServer({middlewares:{use:fn=>middleware=fn}})
  for(const url of ['/api/chat/research','/api/chat/health','/api/chat%2Fresearch']){
    const res={setHeader(){},end(){this.ended=true}};middleware({url,method:'POST'},res,()=>assert.fail());assert.equal(res.statusCode,404)
  }
  let next=false;middleware({url:'/api/chat',method:'POST'},{},()=>next=true);assert.equal(next,true)
})
test('server boundary rejects private payloads before browser and canonicalizes citations without changing facts',()=>{
  const d=withProperty(),result=publicChatBody(d)
  assert.equal(result.citations[0].url,'/api/v1/amenities/unit');assert.equal(result.citations[1].url,'/api/v1/recommendations')
  assert.equal(result.citations[0].contentHash,d.citations[0].contentHash);assert.deepEqual(result.recommendedProperties,d.recommendedProperties)
  assert.equal(publicChatResponse(result),result)
  for(const mutate of [v=>v.mode='INTERNAL_RESEARCH',v=>v.answer='TINIX_AI',v=>v.citations[0].scope='INTERNAL_RESEARCH',v=>v.recommendedProperties[0].verificationStatus='UNVERIFIED',v=>v.evidence.demoKey='fixture-private',v=>v.evidence.dbPassword='fixture-private']){
    const v=withProperty();mutate(v);assert.throws(()=>publicChatBody(v))
  }
})

test('explicit POI category packets must cite only in-category POI evidence',()=>{
  const base=()=>{const d=fixture();d.evidence.amenityIntent={district:'Cẩm Lệ',categories:['SCHOOL']};return d}
  // AREA_AMENITY alongside an explicit category intent is refused (the original defect).
  assert.throws(()=>publicChatResponse(base()))
  const ok=()=>{const d=base();d.citations=[{sourceId:'poi-map:unit',scope:'PUBLIC',kind:'POI_EVIDENCE',url:'https://unit.invalid/api/v1/amenities/district-cam-le',version:'unit:v1',contentHash:'c'.repeat(64)}];return d}
  assert.equal(publicChatResponse(ok()).citations.length,1)
  // No category named: area evidence stays allowed.
  const mixed=fixture();mixed.evidence.amenityIntent={district:'Sơn Trà',categories:[]}
  assert.equal(publicChatResponse(mixed).citations[0].kind,'AREA_AMENITY')
  // Qwen sentence backed by an area source is refused under an explicit category.
  const generated=ok();generated.generationMode='QWEN_GROUNDED_ANSWER'
  generated.answer='Bằng chứng kiểm thử cô lập. [amenity:unit]'
  generated.citations.push({sourceId:'amenity:unit',scope:'PUBLIC',kind:'AREA_AMENITY',url:'https://unit.invalid/api/v1/amenities/unit',version:'unit:v1',contentHash:'a'.repeat(64)})
  generated.evidence.generation={accepted:true,eval_count:5,sentences:[{text:'Bằng chứng kiểm thử cô lập.',sourceId:'amenity:unit'}]}
  assert.throws(()=>publicChatResponse(generated))
  // Malformed intent is refused outright.
  for(const bad of [null,{categories:'SCHOOL'},{categories:['school']},{categories:['SCHOOL']},{district:'',categories:['SCHOOL']}]){
    const d=ok();d.evidence.amenityIntent=bad;assert.throws(()=>publicChatResponse(d))
  }
})

test('conversation context: opaque session id round-trips and resets',async()=>{
  const seen=[]
  const sid='a'.repeat(32)
  const send=async request=>{seen.push(request);const packet=fixture();packet.evidence.session={id:sid,turn:seen.length,context:{}};return packet}
  const session=createChatSession(send)
  await session.submit('Tôi có 2 tỷ, tìm nhà ở Cẩm Lệ.')
  assert.equal(seen[0].sessionId,undefined,'first turn must not invent an id')
  assert.deepEqual(Object.keys(seen[0]).sort(),['question','requireGeneration'])
  assert.equal(session.state.sessionId,sid)
  await session.submit('Nếu tăng ngân sách lên 6 tỷ thì sao?')
  assert.equal(seen[1].sessionId,sid,'follow-up must reuse the server-issued id')
  assert.equal(session.state.messages.filter(m=>m.role==='user')[1].sessionTurn,'followup')
  // A fresh conversation must not inherit the previous context.
  session.clear()
  assert.equal(session.state.sessionId,null)
  await session.submit('Bắt đầu lại.')
  assert.equal(seen[2].sessionId,undefined)
})
test('session id is validated and never carries client-side context',()=>{
  assert.throws(()=>chatRequest('x','not-a-session'),e=>e.code==='INVALID_CHAT_SESSION')
  assert.throws(()=>chatRequest('x','A'.repeat(32)),e=>e.code==='INVALID_CHAT_SESSION')
  const body=chatRequest('x','b'.repeat(32))
  assert.deepEqual(Object.keys(body).sort(),['question','requireGeneration','sessionId'])
  assert.equal(body.sessionId,'b'.repeat(32))
  // No transcript, criteria, scope or research flag may be sent from the browser.
  for(const banned of ['messages','history','mode','research','budgetVnd','district','context'])assert.equal(banned in body,false)
})
