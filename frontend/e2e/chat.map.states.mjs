/** Component/network regression restores a REAL captured chat packet, then aborts
 * and retries the actual map API. Core Qwen E2E is separate; no model call here. */
import {createRequire} from 'node:module'
import {fileURLToPath} from 'node:url'
import {execFileSync} from 'node:child_process'
import fs from 'node:fs/promises'
const require=createRequire(new URL('../package.json',import.meta.url)),{chromium}=require('@playwright/test')
const root=fileURLToPath(new URL('../../../',import.meta.url)),out=process.argv[2],result={checks:[],complete:false}
const captured=JSON.parse(await fs.readFile(out+'/chat-map-e2e.json','utf8')).cases.find(c=>c.key==='schools')
if(captured?.status!==200||captured.body.mode!=='SAFE')throw Error('Missing real successful capture')
const browser=await chromium.launch({channel:'msedge',headless:true}),page=await browser.newPage({viewport:{width:390,height:844}})
const check=(name,pass)=>{result.checks.push({name,pass:!!pass});if(!pass)throw Error(name)}
let chats=0,maps=0,mapReqs=0,release
const barrier=new Promise(r=>release=r)
page.on('request',r=>{if(r.url().endsWith('/api/chat'))chats++
 if(r.url().includes('/api/v1/amenities/map?'))mapReqs++})
try{
 await page.goto('http://127.0.0.1:5173/advisor/chat');await page.locator('#chat-question').waitFor()
 const g=JSON.parse(execFileSync(root+'/.scratch/rag-ollama-venv/Scripts/python.exe',['-X','utf8',out+'/gate.py'],{encoding:'utf8',windowsHide:true}));result.resourceGate=g
 check('Headroom for browser-only map network regression; no model call',!g.pressure&&g.availableRamMiB>=1536&&g.commitHeadroomMiB>=1536)
 await page.route('**/api/v1/amenities/map?*',async route=>{maps++;if(maps===1)await route.abort('failed');else{await barrier;await route.continue()}})
 result.chat={status:captured.status,body:captured.body,origin:'Real successful chat-map-e2e.json schools capture; not a new inference'}
 await page.evaluate(async x=>{const {chatSession}=await import('/src/services/chatRuntime.js');chatSession.state.messages.push({id:100,role:'user',text:x.question},{id:101,role:'assistant',response:x.body})},captured)
 check('Restored actual Public SAFE conversation without invoking model',result.chat.body.mode==='SAFE'&&chats===0)
 await page.locator('[data-amenity-error]').waitFor();await page.locator('[data-amenity-error]').scrollIntoViewIfNeeded()
 check('Map failure retains answer and offers manual retry',await page.locator('[data-chat-summary]').count()===1&&await page.getByRole('button',{name:'Thử lại bản đồ',exact:true}).isVisible())
 await page.waitForTimeout(1100);check('No automatic retry or new chat request',maps===1&&chats===0)
 await page.screenshot({path:out+'/mobile-map-error.png'})
 const retryResponse=page.waitForResponse(r=>r.url().includes('/api/v1/amenities/map?'))
 await page.getByRole('button',{name:'Thử lại bản đồ',exact:true}).click();await page.locator('[data-amenity-loading]').waitFor()
 check('Bounded map retry shows loading without resending chat',maps===2&&chats===0)
 release();const m=await retryResponse;result.map={status:m.status(),body:await m.json()}
 await page.locator('[data-chat-map]').waitFor();await page.locator('[data-chat-map]').scrollIntoViewIfNeeded()
 check('Manual retry uses actual map API and source points',m.status()===200&&result.map.body.items.length===5&&result.map.body.items.every(p=>p.category==='SCHOOL'&&p.district==='Cẩm Lệ'&&p.reviewStatus==='VALID'))
 check('Retry clears error without duplicating chat',await page.locator('[data-amenity-error]').count()===0&&chats===0&&maps===2)
 check('No horizontal overflow',await page.evaluate(()=>document.body.scrollWidth<=innerWidth+1))
 await page.screenshot({path:out+'/mobile-map-recovered.png'})
 // Verify HTTP 503 API unavailable state and manual retry recovery
 let mode503=true
 await page.route('**/api/v1/amenities/map?*',async route=>{maps++;if(mode503)await route.fulfill({status:503,headers:{'cache-control':'no-store'},body:''});else await route.continue()})
 await page.evaluate(async x=>{const {chatSession}=await import('/src/services/chatRuntime.js');chatSession.state.messages.push({id:102,role:'user',text:'Hải Châu có bệnh viện nào? Hiển thị trên bản đồ.'},{id:103,role:'assistant',response:x.body})},captured)
 const secondAnswer=page.locator('[data-chat-answer]').nth(1)
 await secondAnswer.locator('[data-amenity-error]').waitFor()
 check('Map API HTTP 503 shows bounded error state and preserves answer',await secondAnswer.locator('[data-chat-summary]').isVisible()&&await secondAnswer.getByRole('button',{name:'Thử lại bản đồ',exact:true}).isVisible()&&chats===0)
 mode503=false
 const retry503=page.waitForResponse(r=>r.url().includes('/api/v1/amenities/map?')&&r.status()===200)
 await secondAnswer.getByRole('button',{name:'Thử lại bản đồ',exact:true}).click()
 const m503=await retry503,b503=await m503.json()
 await secondAnswer.locator('[data-chat-map]').waitFor()
 check('Exact prompt "Hải Châu có bệnh viện nào? Hiển thị trên bản đồ." recovers with 2 VALID hospitals',b503.district==='Hải Châu'&&b503.category==='HOSPITAL'&&b503.items.length===2&&chats===0)
 await page.unroute('**/api/v1/amenities/map?*')
 // Verify tile network failure and manual tile retry
 let blockTiles=true
 await page.route('https://tile.openstreetmap.org/**',async route=>{if(blockTiles)await route.abort('failed');else await route.continue()})
 await secondAnswer.getByRole('button',{name:'Phóng to bản đồ',exact:true}).click()
 await secondAnswer.locator('.tile-error').waitFor()
 check('OSM tile network error shows tile retry banner without losing POI pins',await secondAnswer.locator('.tile-error').isVisible()&&await secondAnswer.locator('.poi-pin').count()===2)
 blockTiles=false
 await secondAnswer.locator('.tile-error button').click()
 await page.waitForFunction(()=>document.querySelectorAll('[data-chat-answer]')[1]?.querySelector('.tile-error')===null,{timeout:10000})
 check('Manual tile retry clears tile error banner',await secondAnswer.locator('.tile-error').count()===0)
 await page.unroute('https://tile.openstreetmap.org/**')
 // Verify narrow ward/street query shows explicit empty state without map API call or fake pins
 const mapsBeforeEmpty=mapReqs
 check('Map request counter is live before empty-state test',mapReqs>=3)
 await page.evaluate(async x=>{const {chatSession}=await import('/src/services/chatRuntime.js');chatSession.state.messages.push({id:104,role:'user',text:'Phường Hòa Xuân Cẩm Lệ có trường học nào?'},{id:105,role:'assistant',response:x.body})},captured)
 const thirdAnswer=page.locator('[data-chat-answer]').nth(2)
 await thirdAnswer.locator('[data-amenity-empty]').waitFor()
 check('Narrow ward query renders explicit empty state without calling map API or inventing pins',mapReqs===mapsBeforeEmpty&&await thirdAnswer.locator('[data-chat-map]').count()===0&&await thirdAnswer.locator('[data-amenity-empty]').innerText().then(t=>t.includes('phường/xã')))
 // Verify Public SAFE / Research isolation on frontend & backend routes
 const deniedChatResearch=await page.request.post('http://127.0.0.1:5173/api/chat/research',{data:{question:'blocked'}})
 const deniedAmenityResearch=await page.request.get('http://127.0.0.1:5173/api/v1/amenities/research/summary')
 check('Public SAFE / Research isolation blocks research endpoints',deniedChatResearch.status()===404&&[401,403].includes(deniedAmenityResearch.status()))
 // Verify non-regression across other Vue routes and footer restoration
 await page.setViewportSize({width:1440,height:1000})
 const pageErrors=[];page.on('pageerror',e=>pageErrors.push(e.message))
 await page.goto('http://127.0.0.1:5173/advisor',{waitUntil:'domcontentloaded'})
 await page.locator('h1:visible,h2:visible').first().waitFor()
 await page.locator('.app-footer').waitFor()
 check('Leaving chat restores normal layout and footer on /advisor',await page.locator('.app-footer').isVisible()&&await page.locator('.messenger-page').count()===0)
 for(const routePath of ['/home','/listings','/market','/valuation','/login']){
  await page.goto('http://127.0.0.1:5173'+routePath,{waitUntil:'domcontentloaded'})
  await page.locator('h1:visible,h2:visible').first().waitFor()
  check('Existing Vue route '+routePath+' renders without regression',await page.locator('h1:visible,h2:visible').first().isVisible())
 }
 check('Zero runtime errors across state and route regression checks',pageErrors.length===0)
 result.complete=true
}catch(e){result.failure=e.message;throw e}
finally{release();await browser.close();await fs.writeFile(out+'/map-states-e2e.json',JSON.stringify(result,null,2));console.log(JSON.stringify({complete:result.complete,checks:result.checks.length,failure:result.failure}))}
