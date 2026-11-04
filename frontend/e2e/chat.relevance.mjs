/** Live regression for empty-budget intent and localized evidence. No fake responses. */
import {createRequire} from 'node:module'
import {execFileSync} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import fs from 'node:fs/promises'
const require=createRequire(new URL('../package.json',import.meta.url)),{chromium}=require('@playwright/test')
const root=fileURLToPath(new URL('../../../',import.meta.url)),out=process.argv[2],checks=[],responses={}
const browser=await chromium.launch({channel:'msedge',headless:true});let complete=false,error
function check(name,ok){checks.push({name,pass:!!ok});if(!ok)throw Error(name)}
async function save(){await fs.writeFile(out+'/live-results.json',JSON.stringify({complete,error,checks,responses,passed:checks.filter(c=>c.pass).length,failed:checks.filter(c=>!c.pass).length},null,2))}
async function screenshot(page,name){await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo(0,0)});await page.screenshot({path:out+'/'+name+'.png',fullPage:true})}
function gate(){const s=JSON.parse(execFileSync(root+'/.scratch/rag-ollama-venv/Scripts/python.exe',['-X','utf8',out+'/gate_probe.py'],{encoding:'utf8',windowsHide:true}));check('Resources sufficient before Qwen',!s.pressureObserved&&s.availableRamMiB>=s.minimumRamMiB&&s.commitHeadroomMiB>=4096)}
async function ask(page,name,question,generation=false){
 if(generation)gate()
 await page.locator('#chat-question').fill(question)
 const offset=(await fs.stat(out+'/chat-api.log')).size,start=Date.now()
 const pending=page.waitForResponse(r=>r.url().endsWith('/api/chat')&&r.request().method()==='POST',{timeout:95000})
 await page.locator('#chat-question').press('Enter')
 const r=await pending,body=await r.json();responses[name]={status:r.status(),ms:Date.now()-start,request:r.request().postDataJSON(),body,diagnostics:(await fs.readFile(out+'/chat-api.log','utf8')).slice(offset)}
 check(name+': HTTP200 SAFE',r.status()===200&&body.mode==='SAFE')
 await page.waitForFunction(n=>document.querySelectorAll('[data-chat-answer]').length>=n,Object.keys(responses).length,{timeout:5000})
 await save();return {body,ui:page.locator('[data-chat-answer]').last(),log:responses[name].diagnostics}
}
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}})
 await page.goto('http://127.0.0.1:5173/advisor/chat',{waitUntil:'domcontentloaded'});await page.locator('#chat-question').waitFor()
 const empty=await ask(page,'empty_2b','Tôi có 2 tỷ, có bất động sản công khai phù hợp không?')
 check('No-match is authoritative tool result, not claimed Qwen/failure',empty.body.evidence.responseKind==='NO_MATCHES'&&empty.body.generationMode==='EVIDENCE_ONLY'&&empty.body.evidence.generation.accepted===false)
 check('Empty search skips Qwen/E5 entirely',empty.log.includes('no_match_response')&&!empty.log.includes('ollama_generation')&&!empty.log.includes('semantic_retrieval'))
 check('No fabricated or unrelated citations',empty.body.citations.length===0&&empty.body.evidence.retrievedSourceIds.length===0&&!/Quảng trường|PUBLIC_TRANSPORT|CORRIDOR|POI/.test(empty.body.answer))
 check('Relevant follow-up preserves budget and market limitation',empty.body.answer.includes('2.000.000.000 đồng')&&empty.body.answer.includes('nhà ở, căn hộ hay đất nền')&&empty.body.answer.includes('không phải kết luận về toàn bộ thị trường'))
 check('No duplicate empty panel, bogus sources or outage label',await empty.ui.locator('[data-chat-empty]').count()===1&&await empty.ui.locator('[data-chat-fallback],[data-chat-sources]').count()===0)
 check('Correct tool result label',await empty.ui.innerText().then(t=>t.includes('Kết quả tra cứu dữ liệu công khai')&&!t.includes('AI chưa sẵn sàng')))
 await screenshot(page,'empty-desktop')
 const strict=await page.request.post('http://127.0.0.1:8001/chat',{data:{question:'Tôi có 2 tỷ, tìm nhà.',requireGeneration:true}});check('Strict cannot falsely claim generation for skipped empty search',strict.status()===503)
 const amenity=await ask(page,'explicit_hospital','Tôi có 2 tỷ, Hải Châu có bệnh viện nào?',true)
 check('Explicit amenity request still uses real Qwen and FAISS',amenity.body.generationMode==='QWEN_GROUNDED_ANSWER'&&amenity.body.retrievalMode==='E5_FAISS'&&amenity.body.evidence.generation.eval_count>0&&amenity.body.citations.length>0)
 const visible=await amenity.ui.locator('.answer-text').first().innerText()
 check('Evidence labels localized without raw technical codes',visible.includes('cơ sở y tế')&&!/HOSPITAL|DIRECT_WARD_EVIDENCE|CORRIDOR_DIRECT|\bPOI\b/.test(visible))
 const raw=amenity.ui.getByText('Xem nguyên văn bằng chứng',{exact:true});await raw.click()
 check('Original model evidence remains auditable',await amenity.ui.locator('details .answer-text').innerText()===amenity.body.answer)
 await raw.click();await screenshot(page,'amenities-localized')
 const positive=await ask(page,'positive_10b','Tôi có 10 tỷ, gợi ý bất động sản phù hợp.',true)
 check('Positive Qwen recommendation unchanged and cited',positive.body.generationMode==='QWEN_GROUNDED_ANSWER'&&positive.body.evidence.generation.eval_count>0&&positive.body.recommendedProperties.length===8&&positive.body.citations.length>=8)
 const direct=await page.request.post('http://127.0.0.1:8080/api/v1/recommendations',{data:positive.body.evidence.criteria});const d=await direct.json()
 const sig=ps=>ps.map(p=>[p.id,Number(p.priceVnd),Number(p.areaSqm),Number(p.score)])
 check('Actual prices, IDs/order/area/score match Hybrid API',direct.status()===200&&JSON.stringify(sig(d.topProperties))===JSON.stringify(sig(positive.body.recommendedProperties)))
 check('Public never substitutes private records',Object.values(responses).every(r=>!/(TINIX_AI|tinix:|INTERNAL_RESEARCH|\bUNVERIFIED\b)/.test(JSON.stringify(r.body))))
 await page.setViewportSize({width:375,height:812})
 check('Mobile answer layout does not overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
 await screenshot(page,'positive-mobile')
 const denied=await page.request.post('http://127.0.0.1:5173/api/chat/research',{data:{question:'blocked'}});check('Public proxy Research remains blocked',denied.status()===404)
 complete=true
}catch(e){error=String(e);throw e}
finally{await browser.close();await save();console.log(JSON.stringify({complete,passed:checks.filter(c=>c.pass).length,failed:checks.filter(c=>!c.pass).length,error}))}
