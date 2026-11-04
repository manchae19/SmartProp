// Layout diagnosis only: restore a previously captured REAL session packet.
// Actual map API still runs; this is not a substitute for chat E2E acceptance.
import {createRequire} from 'node:module'
import fs from 'node:fs/promises'
const require=createRequire(new URL('../package.json',import.meta.url)),{chromium}=require('@playwright/test'),out=process.argv[2]
const stored=JSON.parse(await fs.readFile(out+'/chat-map-e2e.json','utf8')).cases[0]
const browser=await chromium.launch({channel:'msedge',headless:true}),page=await browser.newPage({viewport:{width:1440,height:1000}})
try{
 await page.goto('http://127.0.0.1:5173/advisor/chat');await page.locator('#chat-question').waitFor()
 await page.evaluate(async x=>{const {chatSession}=await import('/src/services/chatRuntime.js');chatSession.state.messages.push({id:100,role:'user',text:x.question},{id:101,role:'assistant',response:x.body})},stored)
 await page.locator('[data-chat-map]').waitFor();await page.locator('[data-chat-map]').scrollIntoViewIfNeeded();await page.locator('.poi-pin').first().click();await page.locator('.poi-map-popup').waitFor()
 await page.locator('.poi-popup-close').click();await page.getByRole('button',{name:'Phóng to bản đồ',exact:true}).click();await page.getByRole('button',{name:'Xem tất cả ghim của trang hiện tại',exact:true}).click()
 await page.setViewportSize({width:390,height:844});await page.locator('[data-chat-map]').scrollIntoViewIfNeeded();await page.locator('.poi-pin').first().click();await page.locator('.poi-map-popup').waitFor()
 const measure=()=>page.locator('.poi-map-popup').evaluate(e=>{const a=e.getBoundingClientRect(),m=e.closest('.browse-map'),b=m.getBoundingClientRect(),s=getComputedStyle(e);return {popup:a.toJSON(),map:b.toJSON(),scrollLeft:m.scrollLeft,scrollTop:m.scrollTop,position:s.position,margin:s.margin,transform:s.transform}})
 const before=await measure();await page.locator('.browse-map').evaluate(e=>e.style.overflow='clip');const after=await measure()
 const visible=await page.locator('.poi-map-popup').evaluate(e=>{const p=e.getBoundingClientRect(),m=e.closest('.browse-map').getBoundingClientRect(),t=document.querySelector('.chat-thread').getBoundingClientRect();return p.left>=m.left-1&&p.right<=m.right+1&&p.top>=t.top-1&&p.bottom<=t.bottom+1&&p.top>=m.top-1&&p.bottom<=m.bottom+1})
 await page.screenshot({path:out+'/mobile-popup-final.png'})
 const result={before,after,popupFullyVisible:visible,realPacketRestored:true,realMapApi:true};await fs.writeFile(out+'/popup-layout-final.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));if(!visible)throw Error('Popup not fully visible')
}finally{await browser.close()}
