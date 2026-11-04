/** Final-code mobile recommendation proof; one real request, never mocked. */
import {createRequire} from 'node:module'
import {execFileSync} from 'node:child_process'
import fs from 'node:fs/promises'
const require=createRequire(new URL('../package.json',import.meta.url)),{chromium}=require('@playwright/test'),out=process.argv[2]
const root=new URL('../../../',import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,'$1').replace(/\/$/,'')
const browser=await chromium.launch({channel:'msedge',headless:true});let result
try{
 const page=await browser.newPage({viewport:{width:375,height:812},isMobile:true,hasTouch:true,deviceScaleFactor:1})
 await page.goto('http://127.0.0.1:5173/advisor/chat',{waitUntil:'domcontentloaded'});await page.locator('#chat-question').waitFor()
 const gate=JSON.parse(execFileSync(root+'/.scratch/rag-ollama-venv/Scripts/python.exe',['-X','utf8',out+'/gate_probe.py'],{encoding:'utf8',windowsHide:true}))
 if(gate.availableRamMiB<gate.minimumRamMiB||gate.commitHeadroomMiB<4096||gate.pressureObserved)throw Error('Resource admission stop')
 await page.locator('#chat-question').fill('Tôi có 10 tỷ, gợi ý bất động sản phù hợp.')
 const pending=page.waitForResponse(r=>r.url().endsWith('/api/chat')&&r.request().method()==='POST',{timeout:95000}),start=Date.now()
 await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click();const response=await pending,body=await response.json()
 await page.locator('[data-chat-answer]').waitFor({timeout:5000})
 result={status:response.status(),elapsedMs:Date.now()-start,body,gate,overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),cards:await page.locator('[data-chat-property]').count()}
 result.pass=result.status===200&&body.mode==='SAFE'&&body.generationMode==='QWEN_GROUNDED_ANSWER'&&body.evidence.generation.eval_count>0&&result.cards===8&&!result.overflow&&body.citations.every(c=>c.url.startsWith('/api/v1/'))
 await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo(0,0)});await page.screenshot({path:out+'/mobile-recommendation-final.png',fullPage:true})
 if(!result.pass)throw Error('Final mobile proof failed')
}finally{await browser.close();if(result)await fs.writeFile(out+'/final-mobile-proof.json',JSON.stringify(result,null,2))}
console.log(JSON.stringify({pass:result.pass,status:result.status,cards:result.cards,elapsedMs:result.elapsedMs}))
