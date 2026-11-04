import {createRequire} from 'node:module'
import fs from 'node:fs/promises'
const require=createRequire(new URL('../package.json',import.meta.url)),{chromium}=require('@playwright/test'),out=process.argv[2]
const browser=await chromium.launch({channel:'msedge',headless:true}),checks=[]
function check(name,ok){checks.push({name,pass:!!ok});if(!ok)throw Error(name)}
try{
 const page=await browser.newPage({viewport:{width:375,height:812},isMobile:true,hasTouch:true,reducedMotion:'reduce'})
 await fs.writeFile(out+'/fault-mode.txt','runtime-unavailable');await page.goto('http://127.0.0.1:5174/advisor/chat',{waitUntil:'domcontentloaded'});await page.locator('#chat-question').waitFor()
 let release;const barrier=new Promise(r=>release=r),hold=async route=>{await barrier;await route.continue()};await page.route('**/api/chat',hold)
 await page.locator('#chat-question').fill('Tôi có 10 tỷ, tìm bất động sản công khai.')
 const pending=page.waitForResponse(r=>r.url().endsWith('/api/chat')&&r.request().method()==='POST');await page.locator('#chat-question').press('Enter');await page.locator('.typing-bubble').waitFor()
 check('Reduced motion actually disables typing animation',await page.locator('.typing-bubble i').evaluateAll(els=>els.every(e=>getComputedStyle(e).animationName==='none')))
 release();await pending;await page.unroute('**/api/chat',hold);await page.locator('[data-chat-fallback]').waitFor()
 await page.locator('[data-chat-sources]>summary').click();await page.locator('.technical-source>summary').first().click()
 check('Long citation metadata does not overflow mobile',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
 await page.screenshot({path:out+'/RESPONSIVE_SCREENSHOTS/mobile-sources.png'})
 await page.setViewportSize({width:320,height:640});await page.waitForTimeout(100)
 check('Small 320px phone has visible composer and no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1&&document.querySelector('.composer-dock').getBoundingClientRect().bottom<=innerHeight))
 await page.screenshot({path:out+'/RESPONSIVE_SCREENSHOTS/mobile-small.png'})
 await page.getByRole('button',{name:'Mở hội thoại và gợi ý'}).click();await page.getByRole('dialog',{name:'Hội thoại và gợi ý'}).waitFor()
 check('Drawer starts focus on accessible close control',await page.getByRole('button',{name:'Đóng menu'}).evaluate(el=>el===document.activeElement))
 await page.keyboard.press('Escape');await page.getByRole('dialog',{name:'Hội thoại và gợi ý'}).waitFor({state:'hidden'})
 check('Escape closes drawer and restores trigger focus',await page.getByRole('button',{name:'Mở hội thoại và gợi ý'}).evaluate(el=>el===document.activeElement))
 check('Icon send has accessible name, correct placeholder and no unsupported upload UI',await page.locator('#chat-question').getAttribute('placeholder')==='Nhắn tin cho SmartProp AI...'&&await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).count()===1&&await page.locator('input[type=file]').count()===0)
}finally{await browser.close();await fs.writeFile(out+'/accessibility-e2e.json',JSON.stringify({checks,passed:checks.filter(c=>c.pass).length,failed:checks.filter(c=>!c.pass).length},null,2))}
console.log(JSON.stringify({passed:checks.filter(c=>c.pass).length,failed:checks.filter(c=>!c.pass).length}))
