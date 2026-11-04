/** Messenger acceptance on live Public FastAPI; never route.fulfill or seed data. */
import {createRequire} from 'node:module'
import {fileURLToPath} from 'node:url'
import {execFileSync} from 'node:child_process'
import fs from 'node:fs/promises'
const require=createRequire(new URL('../package.json',import.meta.url)),{chromium}=require('@playwright/test')
const root=fileURLToPath(new URL('../../../',import.meta.url)),out=process.argv[2],screens=out+'/RESPONSIVE_SCREENSHOTS'
const result={checks:[],cases:{},screenshots:[],requests:[],pageErrors:[],complete:false}
const browser=await chromium.launch({channel:'msedge',headless:true})
function check(name,pass,details){result.checks.push({name,pass:!!pass,details});if(!pass)throw Error(name)}
async function save(){await fs.writeFile(out+'/messenger-e2e.json',JSON.stringify(result,null,2))}
async function shot(page,name){await page.screenshot({path:screens+'/'+name+'.png'});result.screenshots.push(name+'.png')}
function listen(page){page.on('pageerror',e=>result.pageErrors.push(e.message));page.on('request',r=>{if(r.url().endsWith('/api/chat')){const h=r.headers();result.requests.push({url:r.url(),auth:!!h.authorization,cookie:!!h.cookie,key:!!h['x-smartprop-demo-key'],body:r.postDataJSON()})}})}
async function gate(){let g;const observations=[];for(let i=0;i<6;i++){g=JSON.parse(execFileSync(root+'/.scratch/rag-ollama-venv/Scripts/python.exe',['-X','utf8',out+'/gate.py'],{encoding:'utf8',windowsHide:true}));observations.push(g);if(!g.pressure&&g.availableRamMiB>=g.minimumRamMiB&&g.commitHeadroomMiB>=4096&&g.vramTotalMiB-g.vramMiB>=3500)break;await new Promise(r=>setTimeout(r,5000))}check('Resource gate before serial Qwen request',!g.pressure&&g.availableRamMiB>=g.minimumRamMiB&&g.commitHeadroomMiB>=4096&&g.vramTotalMiB-g.vramMiB>=3500,{observations})}
const responseWait=page=>page.waitForResponse(r=>r.url().endsWith('/api/chat')&&r.request().method()==='POST',{timeout:95000})
async function ready(page){await page.goto('http://127.0.0.1:5173/advisor/chat',{waitUntil:'domcontentloaded'});await page.locator('#chat-question').waitFor()}
async function send(page,name,question,{generation=false,hold=false,readHistory=false}={}){
 if(generation)await gate()
 const count=await page.locator('[data-chat-answer]').count();await page.locator('#chat-question').fill(question)
 let release,handler
 if(hold){const barrier=new Promise(r=>release=r);handler=async route=>{await barrier;await route.continue()};await page.route('**/api/chat',handler)}
 const pending=responseWait(page),start=Date.now();await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click()
 if(hold){
  await page.locator('[data-chat-loading]').waitFor();check('Typing indicator has AI avatar and exactly three animated dots',await page.locator('[data-chat-loading] .message-avatar').count()===1&&await page.locator('.typing-bubble i').count()===3)
  check('Send/input disabled for one pending flight',await page.locator('#chat-question').isDisabled()&&await page.getByRole('button',{name:'Đang xử lý câu hỏi',exact:true}).isDisabled())
  const n=result.requests.length;await page.locator('.chat-composer').evaluate(form=>{form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))});await page.waitForTimeout(200);check('Duplicate submit creates no extra request',result.requests.length===n)
  if(readHistory){await page.locator('.chat-thread').evaluate(el=>{el.scrollTop=0});await page.waitForTimeout(100)}
  await shot(page,readHistory?'desktop-reading-history':'desktop-typing');release()
 }
 const r=await pending,b=await r.json();if(handler)await page.unroute('**/api/chat',handler)
 result.cases[name]={status:r.status(),ms:Date.now()-start,body:b};check(name+': HTTP200 SAFE',r.status()===200&&b.mode==='SAFE')
 await page.waitForFunction(n=>document.querySelectorAll('[data-chat-answer]').length>n,count,{timeout:6000})
 if(generation)check(name+': actual Qwen/FAISS completed',b.generationMode==='QWEN_GROUNDED_ANSWER'&&b.retrievalMode==='E5_FAISS'&&b.evidence.generation.accepted&&b.evidence.generation.eval_count>0)
 check(name+': no private research packet',!/(TINIX_AI|tinix:|INTERNAL_RESEARCH|INTERNAL_DEMO|\bUNVERIFIED\b|raw_payload|sampleListingCount)/i.test(JSON.stringify(b)))
 await save();return {body:b,ui:page.locator('[data-chat-answer]').nth(count)}
}
async function geometry(page){return page.evaluate(()=>{const b=s=>document.querySelector(s).getBoundingClientRect().toJSON();return {width:innerWidth,height:innerHeight,bodyHeight:document.documentElement.scrollHeight,scrollWidth:document.documentElement.scrollWidth,thread:b('.chat-thread'),composer:b('.composer-dock'),input:b('#chat-question'),header:b('.conversation-header')}})}
try{
 let context=await browser.newContext({viewport:{width:1440,height:1000}});let page=await context.newPage();listen(page);await ready(page)
 check('Messenger header shows identity without fake online state',await page.getByRole('heading',{name:'SmartProp AI Advisor',exact:true}).isVisible()&&await page.getByText('Trợ lý tư vấn bất động sản',{exact:true}).isVisible()&&await page.getByText(/Đang trực tuyến|Online/i).count()===0)
 check('Desktop session sidebar and clear action exist',await page.locator('.desktop-chat-panel').isVisible()&&await page.getByRole('button',{name:'Tạo hội thoại mới'}).isVisible())
 await shot(page,'desktop-initial')
 await page.getByRole('button',{name:'Thu gọn danh sách hội thoại'}).click();check('Sidebar collapses',await page.locator('.desktop-chat-panel').count()===0);await page.getByRole('button',{name:'Mở danh sách hội thoại'}).click()
 check('Send blocks empty input',await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).isDisabled())
 await page.locator('#chat-question').fill('Dòng một');const h1=await page.locator('#chat-question').evaluate(e=>e.clientHeight);await page.locator('#chat-question').press('Shift+Enter');await page.locator('#chat-question').pressSequentially('Dòng hai')
 check('Shift+Enter preserves newline and autogrows',await page.locator('#chat-question').inputValue().then(v=>v.includes('\n'))&&await page.locator('#chat-question').evaluate(e=>e.clientHeight)>h1)
 await page.locator('#chat-question').fill(Array.from({length:20},()=> 'Dòng kiểm tra').join('\n'));check('Textarea growth is bounded',await page.locator('#chat-question').evaluate(e=>e.clientHeight<=130))
 const empty=await send(page,'empty_2b','Tôi có 2 tỷ, có bất động sản công khai phù hợp không?')
 check('Relevance fix preserved: no unrelated POI or bogus AI failure',empty.body.evidence.responseKind==='NO_MATCHES'&&empty.body.generationMode==='EVIDENCE_ONLY'&&await empty.ui.locator('[data-chat-property],[data-chat-sources],[data-chat-fallback]').count()===0&&!/Quảng trường|CORRIDOR_DIRECT/.test(empty.body.answer))
 await shot(page,'desktop-empty')
 const positive=await send(page,'recommendation_10b','Tôi có 10 tỷ, gợi ý bất động sản phù hợp.',{generation:true,hold:true})
 const ps=positive.body.recommendedProperties,n=ps.length;check('Real positive properties available',n>3)
 check('Default cards are the actual Top3 in API order',JSON.stringify(await positive.ui.locator('[data-chat-property]').evaluateAll(els=>els.map(e=>e.dataset.chatProperty)))===JSON.stringify(ps.slice(0,3).map(p=>p.id)))
 const summary=await positive.ui.locator('[data-chat-summary]').innerText();check('Summary derives true count and avoids duplicate UUID/price/breakdown',summary.includes(String(n)+' bất động sản')&&!summary.includes(ps[0].id)&&!summary.includes(String(ps[0].priceVnd))&&!/Thành phần điểm|CORRIDOR|budgetFit/.test(summary))
 check('Compact price and score use structured facts',await positive.ui.locator('.card-price').first().innerText().then(t=>/tỷ đồng|triệu đồng/.test(t))&&await positive.ui.locator('.card-score').first().innerText().then(t=>t.includes(String(ps[0].score).replace('.',','))))
 check('Source panel collapsed, original text hidden by default',await positive.ui.locator('[data-chat-sources]').getAttribute('open')===null&&!await positive.ui.locator('[data-chat-original]').isVisible())
 check('Summary then cards then citations in DOM',await positive.ui.evaluate(el=>{const a=el.querySelector('[data-chat-summary]'),b=el.querySelector('[data-chat-properties]'),c=el.querySelector('[data-chat-sources]');return !!(a.compareDocumentPosition(b)&Node.DOCUMENT_POSITION_FOLLOWING)&&!!(b.compareDocumentPosition(c)&Node.DOCUMENT_POSITION_FOLLOWING)}))
 await page.locator('.chat-thread').evaluate(el=>{el.scrollTop=el.querySelector('[data-chat-properties]').offsetTop-200});await shot(page,'desktop-top3')
 await positive.ui.getByRole('button',{name:'Xem tất cả '+n+' bất động sản',exact:true}).click()
 check('Expand shows all actual IDs without reranking',JSON.stringify(await positive.ui.locator('[data-chat-property]').evaluateAll(es=>es.map(e=>e.dataset.chatProperty)))===JSON.stringify(ps.map(p=>p.id)))
 let box=await geometry(page);check('Long conversation scrolls inside frame, composer remains docked',box.bodyHeight<=box.height+1&&box.thread.bottom<=box.composer.top+1&&box.composer.bottom<=box.height&&await page.locator('.chat-thread').evaluate(e=>e.scrollHeight>e.clientHeight))
 await shot(page,'desktop-expanded')
 await positive.ui.getByRole('button',{name:'Thu gọn danh sách',exact:true}).click();check('Collapse restores Top3',await positive.ui.locator('[data-chat-property]').count()===3)
 await positive.ui.locator('[data-chat-sources]>summary').click();await positive.ui.getByText('Xem phản hồi Qwen nguyên văn đã kiểm tra',{exact:true}).click()
 check('Validated Qwen original retained verbatim',await positive.ui.locator('[data-chat-original]').innerText()===positive.body.answer)
 const firstHref=await positive.ui.locator('[data-chat-citation]').first().getAttribute('href');check('Property citation opens valid real listing',firstHref==='/listing/'+encodeURIComponent(ps[0].source.recordKey))
 const detail=await page.request.get('http://127.0.0.1:8080/api/v1/properties/'+encodeURIComponent(ps[0].source.recordKey));check('Property source URL has real API record',detail.status()===200)
 await positive.ui.locator('.technical-source>summary').first().click();check('Technical provenance available only when expanded',await positive.ui.locator('.technical-source').first().innerText().then(t=>t.includes(positive.body.citations[0].sourceId)&&t.includes(positive.body.citations[0].contentHash)))
 await shot(page,'desktop-sources')
 await positive.ui.locator('[data-chat-sources]>summary').click()
 const api=await page.request.post('http://127.0.0.1:8080/api/v1/recommendations',{data:positive.body.evidence.criteria});const direct=await api.json(),sig=rows=>rows.map(p=>[p.id,Number(p.priceVnd),Number(p.areaSqm),Number(p.score)])
 check('Structured facts equal native Hybrid API',api.status()===200&&JSON.stringify(sig(ps))===JSON.stringify(sig(direct.topProperties)))
 const amenity=await send(page,'amenity_history','Hải Châu có bằng chứng bệnh viện nào?',{generation:true,hold:true,readHistory:true})
 check('Incoming answer does not hijack reading position',await page.locator('.chat-thread').evaluate(e=>e.scrollTop<100)&&await page.getByRole('button',{name:'Tin nhắn mới',exact:true}).isVisible())
 await page.getByRole('button',{name:'Tin nhắn mới',exact:true}).click();check('Explicit new-message button returns to bottom',await page.locator('.chat-thread').evaluate(e=>e.scrollHeight-e.clientHeight-e.scrollTop<90))
 await amenity.ui.locator('[data-chat-sources]>summary').click();const href=await amenity.ui.locator('[data-chat-citation]').first().getAttribute('href');const source=await page.request.get('http://127.0.0.1:5173'+href);check('Area citation stays public and resolves',href.startsWith('/api/v1/amenities/')&&source.status()===200)
 await shot(page,'desktop-area-evidence')
 // Actual network cancellation, no fabricated response. Manual retry uses cheap live NO_MATCHES.
 const abort=route=>route.abort('failed');await page.route('**/api/chat',abort);await page.locator('#chat-question').fill('Tôi có 2 tỷ, tìm bất động sản công khai.');await page.locator('#chat-question').press('Enter');await page.locator('[data-chat-error]').waitFor();check('Network failure is an in-thread error bubble',await page.locator('[data-chat-error]').innerText().then(t=>t.includes('Không kết nối')))
 const attempts=result.requests.length;await page.waitForTimeout(300);check('No automatic retry',result.requests.length===attempts);await shot(page,'desktop-network-error');await page.unroute('**/api/chat',abort)
 const retry=page.getByRole('button',{name:'Thử lại',exact:true});await page.waitForFunction(()=>!document.querySelector('[data-chat-error] button')?.disabled,{timeout:8000});const pending=responseWait(page);await retry.click();const r=await pending,b=await r.json();check('Manual retry uses real safe empty search',r.status()===200&&b.evidence.responseKind==='NO_MATCHES');await page.waitForFunction(()=>!document.querySelector('#chat-question').disabled)
 await page.setViewportSize({width:375,height:812});await page.waitForTimeout(200);box=await geometry(page)
 check('Mobile header/bubbles/composer fit viewport without page overflow',box.scrollWidth<=box.width+1&&box.bodyHeight<=box.height+1&&box.composer.bottom<=box.height&&box.input.bottom<=box.composer.bottom)
 await page.getByRole('button',{name:'Mở hội thoại và gợi ý'}).click();check('Mobile sidebar opens native accessible drawer',await page.getByRole('dialog',{name:'Hội thoại và gợi ý'}).isVisible());await shot(page,'mobile-drawer')
 await page.getByRole('dialog',{name:'Hội thoại và gợi ý'}).getByRole('button',{name:'Khám phá tiện ích khu vực'}).click();check('Drawer suggestion fills real composer',await page.locator('#chat-question').inputValue()==='Hải Châu có bằng chứng bệnh viện nào?');await page.locator('#chat-question').fill('')
 // Reduced viewport simulates keyboard space only, not a physical-device keyboard claim.
 await page.setViewportSize({width:375,height:470});await page.locator('#chat-question').focus();await page.waitForTimeout(150);box=await geometry(page)
 check('Composer remains visible in reduced keyboard-sized viewport',box.composer.bottom<=470&&box.input.bottom<=470&&box.thread.height>80);await shot(page,'mobile-keyboard-sized')
 await page.setViewportSize({width:375,height:812});await page.waitForTimeout(150)
 await positive.ui.locator('.ai-bubble').scrollIntoViewIfNeeded();await shot(page,'mobile-top3')
 await positive.ui.getByRole('button',{name:'Xem tất cả '+n+' bất động sản'}).click();check('Mobile expands all cards inside same message',await positive.ui.locator('[data-chat-property]').count()===n);await positive.ui.getByRole('button',{name:'Thu gọn danh sách'}).click()
 await page.setViewportSize({width:812,height:375});await page.waitForTimeout(150);box=await geometry(page);check('Landscape fits without horizontal or document scroll',box.scrollWidth<=box.width+1&&box.bodyHeight<=box.height+1);await shot(page,'mobile-landscape')
 await page.emulateMedia({reducedMotion:'reduce'});const animation=await page.evaluate(()=>{const style=[...document.styleSheets].flatMap(s=>{try{return [...s.cssRules].map(r=>r.cssText)}catch{return []}}).join('');return style.includes('prefers-reduced-motion')});check('Reduced motion rules provided',animation)
 await page.setViewportSize({width:375,height:812});await page.getByRole('button',{name:'Tạo hội thoại mới'}).click();check('New conversation clears only current in-tab messages',await page.locator('[data-chat-message]').count()===0);await shot(page,'mobile-empty')
 const denied=await page.request.post('http://127.0.0.1:5173/api/chat/research',{data:{question:'blocked'}});check('Research route remains blocked404',denied.status()===404)
 await page.goto('http://127.0.0.1:5173/advisor',{waitUntil:'domcontentloaded'});await page.getByRole('heading',{name:'Tìm không gian phù hợp với bạn'}).waitFor();await page.locator('.app-footer').waitFor();check('Leaving chat restores normal page footer and Advisor',await page.locator('.app-footer').isVisible())
 await context.close()
 // Isolated real dependency-fault app, unchanged RAG code, real SQL/corpus. No fake answer.
 execFileSync(root+'/.scratch/rag-ollama-venv/Scripts/python.exe',['-X','utf8',out+'/start_fault.py'],{windowsHide:true})
 context=await browser.newContext({viewport:{width:1280,height:900}});page=await context.newPage();listen(page)
 for(let i=0;i<30;i++){try{if((await page.request.get('http://127.0.0.1:5174/',{timeout:1000})).status()===200)break}catch{}await page.waitForTimeout(200)}
 await page.goto('http://127.0.0.1:5174/advisor/chat',{waitUntil:'domcontentloaded'});await page.locator('#chat-question').waitFor()
 await fs.writeFile(out+'/fault-mode.txt','runtime-unavailable');await page.locator('#chat-question').fill('Tôi có 10 tỷ, tìm bất động sản công khai.');let pending2=responseWait(page);await page.locator('#chat-question').press('Enter');let fr=await pending2,fb=await fr.json();await page.locator('[data-chat-fallback]').waitFor();result.cases.isolated_fallback={status:fr.status(),body:fb};check('Real dependency failure fallback is labeled and Top3 cards work',fr.status()===200&&fb.generationMode==='EVIDENCE_ONLY'&&await page.locator('[data-chat-property]').count()===3);await shot(page,'fallback')
 await fs.writeFile(out+'/fault-mode.txt','corpus-unavailable');await page.locator('#chat-question').fill('Hải Châu có tiện ích gì?');pending2=responseWait(page);await page.locator('#chat-question').press('Enter');fr=await pending2;await page.locator('[data-chat-error]').waitFor();check('Actual upstream503 renders distinct API-error bubble',fr.status()===503&&await page.locator('[data-chat-error]').innerText().then(t=>t.includes('tạm gián đoạn')));await shot(page,'api-error')
 check('No credentials or research switch in public chat requests',result.requests.every(r=>!r.auth&&!r.cookie&&!r.key&&Object.keys(r.body).sort().join(',')==='question,requireGeneration'&&r.body.requireGeneration===false))
 check('No browser runtime errors',result.pageErrors.length===0);result.complete=true;await context.close()
}catch(error){result.error=String(error);throw error}
finally{await save();await browser.close();console.log(JSON.stringify({complete:result.complete,passed:result.checks.filter(c=>c.pass).length,failed:result.checks.filter(c=>!c.pass).length,error:result.error}))}
