/** Complete remaining non-generation checks; previously passed Qwen cases are not replayed. */
import {createRequire} from 'node:module'
import {execFileSync} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import fs from 'node:fs/promises'
const require=createRequire(new URL('../package.json',import.meta.url)),{chromium}=require('@playwright/test')
const root=fileURLToPath(new URL('../../../',import.meta.url)),out=process.argv[2],screens=out+'/RESPONSIVE_SCREENSHOTS'
const receipt={checks:[],cases:{},pageErrors:[],complete:false}
function check(name,ok){receipt.checks.push({name,pass:!!ok});if(!ok)throw Error(name)}
const browser=await chromium.launch({channel:'msedge',headless:true})
try{
 let page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',e=>receipt.pageErrors.push(e.message))
 await page.goto('http://127.0.0.1:5173/advisor/chat',{waitUntil:'domcontentloaded'});await page.locator('#chat-question').waitFor()
 await page.getByRole('button',{name:'Thu gọn danh sách hội thoại'}).click();await page.getByRole('button',{name:'Mở danh sách hội thoại'}).click()
 await page.getByRole('link',{name:'Tìm bằng bộ lọc',exact:true}).click();await page.getByRole('heading',{name:'Tìm không gian phù hợp với bạn'}).waitFor();await page.locator('.app-footer').waitFor()
 check('SPA navigation restores normal Advisor/footer and document scroll',await page.locator('.app-footer').isVisible()&&await page.locator('.messenger-layout').count()===0)
 for(const path of ['/home','/listings','/valuation','/login']){
  await page.goto('http://127.0.0.1:5173'+path,{waitUntil:'domcontentloaded'});await page.locator('h1:visible,h2:visible').first().waitFor();check('Existing '+path+' renders normally',await page.locator('h1:visible,h2:visible').first().isVisible())
 }
 await page.close()
 execFileSync(root+'/.scratch/rag-ollama-venv/Scripts/python.exe',['-X','utf8',out+'/start_fault.py'],{windowsHide:true})
 page=await browser.newPage({viewport:{width:1280,height:900}});page.on('pageerror',e=>receipt.pageErrors.push(e.message))
 const requests=[];page.on('request',r=>{if(r.url().endsWith('/api/chat')){const h=r.headers();requests.push({auth:!!h.authorization,cookie:!!h.cookie,key:!!h['x-smartprop-demo-key'],body:r.postDataJSON()})}})
 for(let i=0;i<30;i++){try{if((await page.request.get('http://127.0.0.1:5174/',{timeout:1000})).status()===200)break}catch{}await page.waitForTimeout(200)}
 await fs.writeFile(out+'/fault-mode.txt','runtime-unavailable');await page.goto('http://127.0.0.1:5174/advisor/chat',{waitUntil:'domcontentloaded'});await page.locator('#chat-question').waitFor()
 await page.locator('#chat-question').fill('Tôi có 10 tỷ, tìm bất động sản công khai.')
 let pending=page.waitForResponse(r=>r.url().endsWith('/api/chat')&&r.request().method()==='POST');await page.locator('#chat-question').press('Enter');let r=await pending,b=await r.json()
 await page.locator('[data-chat-fallback]').waitFor();receipt.cases.fallback={status:r.status(),body:b}
 check('Real dependency fallback is EVIDENCE_ONLY with 8 actual published results',r.status()===200&&b.generationMode==='EVIDENCE_ONLY'&&b.mode==='SAFE'&&b.recommendedProperties.length===8)
 check('Fallback shows Top3 and explicit non-Qwen label',await page.locator('[data-chat-property]').count()===3&&await page.locator('[data-chat-fallback]').innerText().then(t=>t.includes('tổng hợp trực tiếp')))
 await page.locator('[data-chat-answer] .ai-bubble').scrollIntoViewIfNeeded();await page.screenshot({path:screens+'/fallback.png'})
 await fs.writeFile(out+'/fault-mode.txt','corpus-unavailable');await page.locator('#chat-question').fill('Hải Châu có tiện ích gì?');pending=page.waitForResponse(r=>r.url().endsWith('/api/chat')&&r.request().method()==='POST');await page.locator('#chat-question').press('Enter');r=await pending
 await page.locator('[data-chat-error]').waitFor();check('Real upstream503 renders API-error bubble',r.status()===503&&await page.locator('[data-chat-error]').innerText().then(t=>t.includes('tạm gián đoạn')))
 await page.screenshot({path:screens+'/api-error.png'})
 check('Public frontend still omits credentials and whitelist stays fixed',requests.every(r=>!r.auth&&!r.cookie&&!r.key&&Object.keys(r.body).sort().join(',')==='question,requireGeneration'&&r.body.requireGeneration===false))
 const denied=await page.request.post('http://127.0.0.1:5173/api/chat/research',{data:{question:'blocked'}});check('Research route still blocked404',denied.status()===404)
 check('No runtime errors during remaining UI checks',receipt.pageErrors.length===0);receipt.complete=true
}catch(e){receipt.error=String(e);throw e}
finally{await browser.close();await fs.writeFile(out+'/remaining-e2e.json',JSON.stringify(receipt,null,2));console.log(JSON.stringify({complete:receipt.complete,passed:receipt.checks.filter(c=>c.pass).length,failed:receipt.checks.filter(c=>!c.pass).length,error:receipt.error}))}
