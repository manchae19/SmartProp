/** Real multi-turn UI acceptance. Sequential, resource-gated, no mocks. */
import {createRequire} from 'node:module'
import {fileURLToPath} from 'node:url'
import {execFileSync} from 'node:child_process'
import fs from 'node:fs/promises'
const require=createRequire(new URL('../package.json',import.meta.url)),{chromium}=require('@playwright/test')
const root=fileURLToPath(new URL('../../../',import.meta.url)),out=process.argv[2]
const result={checks:[],turns:[],complete:false}
const check=(n,pass,details)=>{result.checks.push({name:n,pass:!!pass,details});if(!pass)throw Error(n)}
const browser=await chromium.launch({channel:'msedge',headless:true}),page=await browser.newPage({viewport:{width:1440,height:1000}})
const chats=[]
page.on('request',r=>{if(r.url().endsWith('/api/chat')&&r.method()==='POST')chats.push(r.postDataJSON())})
async function gate(){
  const g=JSON.parse(execFileSync(root+'/.scratch/rag-ollama-venv/Scripts/python.exe',['-X','utf8',out+'/gate.py'],{encoding:'utf8',windowsHide:true}))
  check('Resource headroom',!g.pressure&&g.availableRamMiB>=1536,g)
}
async function send(question){
  await page.locator('#chat-question').fill(question)
  const pending=page.waitForResponse(r=>r.url().endsWith('/api/chat')&&r.request().method()==='POST',{timeout:180000})
  await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click()
  await page.locator('[data-chat-loading]').waitFor()
  const r=await pending,body=await r.json()
  await page.locator('[data-chat-answer]').last().waitFor()
  result.turns.push({question,status:r.status(),turn:body.evidence?.session?.turn,answer:body.answer,
    properties:body.recommendedProperties.map(p=>p.id),kind:body.evidence?.responseKind,gen:body.generationMode})
  return body
}
try{
  await page.goto('http://127.0.0.1:5173/advisor/chat');await page.locator('#chat-question').waitFor()
  await gate()
  const t1=await send('Tôi có 10 tỷ, muốn mua nhà ở Hải Châu để ở.')
  check('Turn 1: SAFE answer',t1.mode==='SAFE')
  check('Turn 1: session issued',!!t1.evidence.session.id)
  check('Turn 1: real results',t1.recommendedProperties.length>=1)
  check('Turn 1: DOM shows summary then map then cards',await page.locator('[data-chat-answer]').last().evaluate(el=>{
    const s=el.querySelector('[data-chat-summary]'),m=el.querySelector('[data-chat-map]'),c=el.querySelector('[data-chat-properties]')
    return !!s&&(!m||!!(s.compareDocumentPosition(m)&4))&&(!c||!m||!!(m.compareDocumentPosition(c)&4))}))
  const sid=t1.evidence.session.id

  const t2=await send('Nếu tăng ngân sách lên 20 tỷ thì sao?')
  check('Turn 2: same session',t2.evidence.session.id===sid)
  check('Turn 2: turn counter advanced',t2.evidence.session.turn===2)
  check('Turn 2: budget carried forward',String(t2.evidence.session.context.criteria.budgetVnd)==='20000000000')
  check('Turn 2: district retained',t2.evidence.session.context.criteria.district==='Hải Châu')
  check('Turn 2: type retained',t2.evidence.session.context.criteria.propertyType==='HOUSE')

  const t3=await send('Căn thứ hai có phù hợp không?')
  check('Turn 3: narrowed to one property',t3.recommendedProperties.length===1)
  check('Turn 3: it is the second of the previous list',t3.recommendedProperties[0].id===t2.recommendedProperties[1].id)
  check('Turn 3: reference stored',t3.evidence.session.context.referencedPropertyId==='recommendation:'+t3.recommendedProperties[0].id)

  const t4=await send('Vì sao căn này được xếp hạng cao?')
  check('Turn 4: same property retained',t4.recommendedProperties[0].id===t3.recommendedProperties[0].id)
  check('Turn 4: Qwen answered',t4.generationMode==='QWEN_GROUNDED_ANSWER')

  const t5=await send('Có bệnh viện nào trong khu vực đó?')
  check('Turn 5: district inherited',t5.evidence.amenityIntent.district==='Hải Châu')
  check('Turn 5: amenity citations present',t5.citations.length>=1)
  // The map is fetched after the answer renders, so wait for the verified card instead of
  // sampling the DOM immediately (an instant count races the amenity request).
  const mapCard=page.locator('[data-chat-answer]').last().locator('[data-chat-map]')
  await mapCard.waitFor({timeout:45000}).catch(()=>{})
  check('Turn 5: map card rendered',await mapCard.count()===1)
  // Amenity cards are siblings of the map card inside the section, not children of it.
  const amenitySection=page.locator('[data-chat-answer]').last().locator('[data-chat-amenities]')
  check('Turn 5: map lists the verified OSM amenities of the inherited district',
    (await amenitySection.locator('[data-amenity-card]').count())>0 && (await amenitySection.innerText()).includes('Hải Châu'))

  const t6=await send('Hiển thị chúng trên bản đồ.')
  check('Turn 6: map request answered from verified evidence',t6.citations.length>=1)

  // Turn 6 re-displayed the full verified set, so "căn này" is genuinely ambiguous:
  // the advisor must ask instead of guessing (requirement 6), and the UI must show no card.
  const t7=await send('Căn này có phù hợp không?')
  check('Turn 7: ambiguity asks for clarification',t7.evidence.responseKind==='CLARIFICATION_REQUIRED')
  check('Turn 7: ambiguity code',t7.evidence.clarification==='AMBIGUOUS_PROPERTY_REFERENCE')
  check('Turn 7: no property chosen',t7.recommendedProperties.length===0)
  check('Turn 7: no property card rendered',await page.locator('[data-chat-answer]').last().locator('[data-chat-property]').count()===0)
  check('Turn 7: clarification text shown',/bất động sản nào/i.test(await page.locator('[data-chat-answer]').last().locator('[data-chat-summary]').innerText()) ||
    /bất động sản nào/i.test(await page.locator('[data-chat-answer]').last().innerText()))

  // The user can still pin the reference explicitly, and it resolves to that one property.
  const t7b=await send('Căn thứ hai thì sao?')
  check('Turn 7b: ordinal resolves after clarification',t7b.recommendedProperties.length===1)
  check('Turn 7b: it is the second of the last verified set',t7b.recommendedProperties[0].id===t6.recommendedProperties[1].id)

  // Reset: the UI must start a fresh server session.
  await page.getByRole('button',{name:'Tạo hội thoại mới',exact:true}).click()
  await page.locator('#chat-question').waitFor()
  check('Reset: thread cleared',await page.locator('[data-chat-answer]').count()===0)
  await gate()
  const t8=await send('Căn thứ hai có phù hợp không?')
  check('Reset: brand new session',t8.evidence.session.turn===1)
  check('Reset: new id issued',t8.evidence.session.id!==sid)

  // The browser must never ship context or authority.
  for(const body of chats){
    const keys=Object.keys(body).sort().join(',')
    check('Payload whitelist: '+keys,keys==='question,requireGeneration'||keys==='question,requireGeneration,sessionId',keys)
  }
  result.complete=true
}catch(e){result.failure=e.message;await page.screenshot({path:out+'/multiturn-failure.png'}).catch(()=>{})}
finally{await fs.writeFile(out+'/multiturn-e2e.json',JSON.stringify(result,null,2));console.log(JSON.stringify({complete:result.complete,checks:result.checks.length,failed:result.checks.filter(c=>!c.pass).map(c=>c.name),failure:result.failure}));await browser.close()}
