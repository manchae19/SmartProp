/** Real live acceptance. No route.fulfill, fake answer or replacement property. */
import {createRequire} from 'node:module'
import {fileURLToPath} from 'node:url'
import fs from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
const root=fileURLToPath(new URL('../../../',import.meta.url))
const require=createRequire(new URL('../package.json',import.meta.url))
const {chromium}=require('@playwright/test')
const out=process.argv[2]
if(!out)throw Error('Explicit evidence output directory required')
await fs.mkdir(out,{recursive:true})
const results={checks:[],responses:{},screenshots:[],pageErrors:[],chatRequests:[],completed:false}
function check(name,ok,details){results.checks.push({name,pass:!!ok,details});if(!ok)throw Error(name)}
async function save(){await fs.writeFile(out+'/e2e-results.json',JSON.stringify(results,null,2))}
async function shot(page,name,fullPage=true){if(fullPage){await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo(0,0)});await page.waitForTimeout(100)}await page.screenshot({path:out+'/'+name+'.png',fullPage});results.screenshots.push(name+'.png')}
function gate(){const raw=execFileSync(root+'/.scratch/rag-ollama-venv/Scripts/python.exe',['-X','utf8',out+'/gate_probe.py'],{encoding:'utf8',windowsHide:true});const s=JSON.parse(raw);check('Resource admission before live inference',!s.pressureObserved&&s.availableRamMiB>=s.minimumRamMiB&&s.commitHeadroomMiB>=4096&&s.vramTotalMiB-s.vramMiB>=3500,s)}
function listen(page){page.on('pageerror',e=>results.pageErrors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/api/chat')){const h=r.headers();results.chatRequests.push({url:r.url(),method:r.method(),authorizationPresent:!!h.authorization,cookiePresent:!!h.cookie,demoKeyPresent:!!h['x-smartprop-demo-key'],payload:r.postDataJSON()})}})}
async function answer(page,name,question,{hold=false,expectGeneration=true}={}){
  if(expectGeneration)gate()
  const previousAnswers=await page.locator('[data-chat-answer]').count()
  await page.getByRole('textbox',{name:'Câu hỏi của bạn',exact:true}).fill(question)
  let release,handler
  if(hold){const barrier=new Promise(r=>release=r);handler=async route=>{await barrier;await route.continue()};await page.route('**/api/chat',handler)}
  const started=Date.now(),pending=page.waitForResponse(r=>r.url().endsWith('/api/chat')&&r.request().method()==='POST',{timeout:95000})
  await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click()
  if(expectGeneration){await page.locator('[data-chat-loading]').waitFor();check(name+': input locked while processing',await page.locator('#chat-question').isDisabled())}
  if(hold){const count=results.chatRequests.length;await page.locator('.chat-composer').evaluate(f=>{f.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));f.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))});await page.waitForTimeout(1200);check('Repeated submit cannot create a second flight',results.chatRequests.length===count);await shot(page,'desktop-loading',false);release()}
  const response=await pending,body=await response.json()
  if(handler)await page.unroute('**/api/chat',handler)
  results.responses[name]={status:response.status(),elapsedMs:Date.now()-started,request:response.request().postDataJSON(),body}
  const validMode=expectGeneration?body.generationMode==='QWEN_GROUNDED_ANSWER'&&body.retrievalMode==='E5_FAISS'&&body.evidence.generation.accepted&&body.evidence.generation.eval_count>0:body.generationMode==='EVIDENCE_ONLY'&&body.evidence.responseKind==='NO_MATCHES'&&body.retrievalMode==='TOOL_EVIDENCE_ONLY'&&!body.evidence.generation.accepted
  check(name+': truthful public result HTTP200',response.status()===200&&body.mode==='SAFE'&&validMode)
  check(name+': response has no private records',!/(TINIX_AI|tinix:|INTERNAL_RESEARCH|INTERNAL_DEMO|\bUNVERIFIED\b|raw_payload|sampleListingCount)/i.test(JSON.stringify(body))&&body.evidence.topAreas.every(a=>a.unverifiedCount===0&&a.needsReviewCount===0))
  await page.waitForFunction(n=>document.querySelectorAll('[data-chat-answer]').length>n,previousAnswers,{timeout:5000})
  const ui=page.locator('[data-chat-answer]').last()
  check(name+': supported answer visible',await ui.evaluate((el,texts)=>texts.every(t=>el.textContent.includes(t)),expectGeneration?body.evidence.generation.sentences.map(s=>s.text):[body.answer]))
  check(name+': property cards match actual response',await ui.locator('[data-chat-property]').count()===body.recommendedProperties.length)
  check(name+': citations reflect actual evidence',expectGeneration?body.citations.length>0&&await ui.locator('[data-chat-citation]').count()>0:body.citations.length===0&&await ui.locator('[data-chat-sources]').count()===0)
  check(name+': internal API origins absent from browser payload',body.citations.every(c=>c.url.startsWith('/api/v1/'))&&!/https?:\/\/(?:127[.]|localhost)/i.test(JSON.stringify(body)))
  check(name+': no Research UI',await page.getByText('Mở Internal Demo TiniX AI',{exact:true}).count()===0)
  await save();return {body,ui}
}
const browser=await chromium.launch({channel:'msedge',headless:true})
try{
  let context=await browser.newContext({viewport:{width:1440,height:1000}})
  await context.addCookies([{name:'chat_test_not_secret',value:'unit-cookie',url:'http://127.0.0.1:5173'}])
  let page=await context.newPage();listen(page)
  await page.goto('http://127.0.0.1:5173/advisor',{waitUntil:'domcontentloaded'})
  await page.locator('[data-chat-entry]').click();await page.getByRole('heading',{name:'Hỏi về không gian sống của bạn',exact:true}).waitFor()
  check('Advisor navigation opens chat route',new URL(page.url()).pathname==='/advisor/chat')
  await shot(page,'desktop-initial')
  const {body,ui}=await answer(page,'desktop_recommendation','Tôi có 10 tỷ, gợi ý bất động sản phù hợp và giải thích điểm đề xuất.',{hold:true})
  check('Positive public recommendations exist',body.recommendedProperties.length>0)
  const decimal=v=>String(v).replace(/(\.\d*?)0+$/,'$1').replace(/\.$/,'')
  const sig=ps=>ps.map(p=>[p.id,decimal(p.priceVnd),decimal(p.areaSqm),decimal(p.score)])
  const direct=await page.request.post('http://127.0.0.1:8080/api/v1/recommendations',{data:body.evidence.criteria});const actual=await direct.json()
  check('IDs/order/price/area/score equal real Hybrid API',direct.status()===200&&JSON.stringify(sig(body.recommendedProperties))===JSON.stringify(sig(actual.topProperties)))
  const first=body.recommendedProperties[0]
  const money=String(first.priceVnd).split('.')[0].replace(/\B(?=(\d{3})+(?!\d))/g,'.')
  check('Real price displayed in VND',await ui.locator('[data-chat-property]').first().innerText().then(t=>t.includes(money+' đồng')))
  await ui.scrollIntoViewIfNeeded();await shot(page,'desktop-recommendation')
  const before=await page.locator('[data-chat-answer]').count()
  await page.getByRole('link',{name:/Tìm bằng bộ lọc/}).click();await page.locator('[data-chat-entry]').click()
  check('Conversation survives SPA navigation in same tab',await page.locator('[data-chat-answer]').count()===before)
  // Network failure is real cancellation, not a fabricated HTTP response.
  const abort=route=>route.abort('failed');await page.route('**/api/chat',abort)
  await page.locator('#chat-question').fill('Tôi có 10 tỷ, gợi ý bất động sản phù hợp.')
  await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();await page.locator('[data-chat-error]').waitFor()
  check('Network error has distinct explanation',await page.locator('[data-chat-error]').innerText().then(t=>t.includes('Không kết nối')))
  const attempts=results.chatRequests.length;await page.waitForTimeout(1000);check('No automatic retry',results.chatRequests.length===attempts)
  await shot(page,'desktop-network-error',false);await page.unroute('**/api/chat',abort)
  const retry=page.getByRole('button',{name:'Thử lại câu hỏi',exact:true});await retry.waitFor();await page.waitForFunction(()=>!document.querySelector('[data-chat-error] button')?.disabled,{timeout:8000})
  gate();const retried=page.waitForResponse(r=>r.url().endsWith('/api/chat')&&r.request().method()==='POST',{timeout:95000});await retry.click();const rr=await retried,rb=await rr.json()
  results.responses.manual_retry={status:rr.status(),body:rb};check('Explicit retry reaches actual Qwen',rr.status()===200&&rb.generationMode==='QWEN_GROUNDED_ANSWER'&&rb.evidence.generation.eval_count>0)
  await page.waitForFunction(()=>!document.querySelector('#chat-question').disabled)
  const empty=await answer(page,'desktop_empty_2b','Tôi có 2 tỷ, có bất động sản công khai phù hợp không?',{expectGeneration:false})
  check('Real Safe empty state',empty.body.recommendedProperties.length===0&&await empty.ui.locator('[data-chat-empty]').isVisible())
  await shot(page,'desktop-empty')
  for(const route of ['/api/chat/research','/api/chat/health','/api/chat%2Fresearch']){const r=await page.request.post('http://127.0.0.1:5173'+route,{data:{question:'blocked'}});check('Proxy boundary '+route,r.status()===404)}
  await context.close()
  context=await browser.newContext({viewport:{width:375,height:812},isMobile:true,hasTouch:true,deviceScaleFactor:1});page=await context.newPage();listen(page)
  await page.goto('http://127.0.0.1:5173/advisor/chat',{waitUntil:'domcontentloaded'});await page.locator('#chat-question').waitFor()
  check('Reload/new tab has no stored conversation',await page.locator('[data-chat-message]').count()===0)
  await page.getByRole('button',{name:'Hải Châu có bằng chứng bệnh viện nào?'}).click();check('Question suggestion fills input',await page.locator('#chat-question').inputValue()==='Hải Châu có bằng chứng bệnh viện nào?')
  const amenity=await answer(page,'mobile_amenity','Hải Châu có bằng chứng bệnh viện nào?')
  const href=await amenity.ui.locator('[data-chat-citation]').first().getAttribute('href')
  check('Amenity citation points to same-origin public API',href.startsWith('/api/v1/amenities/')&&!href.includes('research'))
  const cr=await page.request.get('http://127.0.0.1:5173'+href);check('Citation public API HTTP200',cr.status()===200&&!/sampleListingCount|raw_payload/.test(await cr.text()))
  check('Mobile portrait no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
  await shot(page,'mobile-portrait')
  await page.setViewportSize({width:812,height:375});check('Mobile landscape no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await shot(page,'mobile-landscape')
  await context.close()
  // Production preview + actual isolated FastAPI faults. No route.fulfill/mock response.
  execFileSync(root+'/.scratch/rag-ollama-venv/Scripts/python.exe',['-X','utf8',out+'/start_fault.py'],{windowsHide:true})
  context=await browser.newContext({viewport:{width:1280,height:900}});page=await context.newPage();listen(page)
  await fs.writeFile(out+'/fault-mode.txt','runtime-unavailable')
  for(let i=0;i<30;i++){try{const probe=await page.request.get('http://127.0.0.1:5174/',{timeout:1000});if(probe.status()===200)break}catch{}await new Promise(resolve=>setTimeout(resolve,200))}
  await page.goto('http://127.0.0.1:5174/advisor/chat',{waitUntil:'domcontentloaded'});await page.locator('#chat-question').waitFor()
  await page.locator('#chat-question').fill('Tôi có 10 tỷ, tìm bất động sản công khai.')
  const fallback=page.waitForResponse(r=>r.url().endsWith('/api/chat')&&r.request().method()==='POST');await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();const fr=await fallback,fb=await fr.json();results.responses.isolated_fallback={status:fr.status(),body:fb}
  await page.locator('[data-chat-fallback]').waitFor();check('Real dependency-fault fallback rendered distinctly',fr.status()===200&&fb.generationMode==='EVIDENCE_ONLY'&&fb.recommendedProperties.length===8)
  await shot(page,'fallback-real-evidence')
  await fs.writeFile(out+'/fault-mode.txt','corpus-unavailable');await page.locator('#chat-question').fill('Hải Châu có tiện ích gì?')
  const failed=page.waitForResponse(r=>r.url().endsWith('/api/chat')&&r.request().method()==='POST');await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();const fail=await failed
  await page.locator('[data-chat-error]').waitFor();check('Actual FastAPI503 has API-error UX',fail.status()===503&&await page.locator('[data-chat-error]').innerText().then(t=>t.includes('tạm gián đoạn')))
  await shot(page,'api-error-503',false)
  await fs.writeFile(out+'/fault-mode.txt','runtime-unavailable')
  check('Chat requests contain no auth/cookie/demo credentials',results.chatRequests.every(r=>!r.authorizationPresent&&!r.cookiePresent&&!r.demoKeyPresent))
  check('Every frontend payload is public whitelist only',results.chatRequests.filter(r=>r.payload).every(r=>Object.keys(r.payload).sort().join(',')==='question,requireGeneration'&&r.payload.requireGeneration===false))
  check('No browser runtime errors',results.pageErrors.length===0)
  results.completed=true;await context.close()
}catch(error){results.error=String(error);throw error}
finally{await save();await browser.close();console.log(JSON.stringify({completed:results.completed,passed:results.checks.filter(c=>c.pass).length,failed:results.checks.filter(c=>!c.pass).length,error:results.error}))}
