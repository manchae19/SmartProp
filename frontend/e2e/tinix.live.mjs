// Opt-in: only a real, currently valid ADMIN session token issued by the live
// test Backend. No mocked profile, authentication, API response or listing.
import { chromium } from '@playwright/test'
import { spawn } from 'node:child_process'
import net from 'node:net'
import fs from 'node:fs/promises'
const target=process.env.SMARTPROP_DEV_API_TARGET,token=process.env.SMARTPROP_E2E_ADMIN_TOKEN
const out=process.argv[2]
if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(target||'')||!token||!process.env.SMARTPROP_INTERNAL_DEMO_KEY||!out)throw Error('Real Local ADMIN credentials and private proxy environment required; never send secrets to chat')
await fs.mkdir(out,{recursive:true})
const port=await new Promise((resolve,reject)=>{const s=net.createServer();s.on('error',reject);s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>resolve(p))})})
const vite=spawn(process.execPath,['node_modules/vite/bin/vite.js','--port',String(port),'--strictPort'],{cwd:process.cwd(),env:process.env,stdio:'ignore',windowsHide:true})
let browser
const result={status:'RUNNING',real_api:true,real_admin_session:true,cases:[]}
try {
  const base='http://127.0.0.1:'+port
  for(let i=0;i<120;i++){
    try{if((await fetch(base)).ok)break}catch{}
    if(vite.exitCode!=null)throw Error('Owned Vite failed')
    await new Promise(r=>setTimeout(r,500))
  }
  browser=await chromium.launch({channel:'msedge',headless:true})
  const page=await browser.newPage({viewport:{width:1440,height:1000}})
  const errors=[],privateHeader=[]
  page.on('pageerror',e=>errors.push(e.message))
  page.on('request',r=>{if(r.headers()['x-smartprop-demo-key'])privateHeader.push('SECRET_HEADER_EXPOSED')})
  await page.goto(base+'/advisor',{waitUntil:'networkidle'})
  // Validate the actual profile before populating the normal in-memory session.
  // No activity pulse, login, session extension or DB mutation is performed.
  await page.evaluate(async token=>{
    const r=await fetch('/api/v1/users/me',{headers:{Authorization:'Bearer '+token}})
    if(!r.ok)throw Error('Existing ADMIN session expired')
    const user=await r.json();if(user.role!=='ADMIN')throw Error('Actual ADMIN role required')
    const {session}=await import('/src/services/api.js');session.token=token;session.user=user;session.status='AUTHENTICATED'
  },token)
  await page.getByRole('button',{name:'Mở Internal Demo TiniX AI',exact:true}).click()
  for(const budget of [850000000,1750000000,2350000000,3780000000,5650000000,12400000000]){
    await page.locator('[name=budget]').fill(String(budget))
    const pending=page.waitForResponse(r=>r.url().endsWith('/api/v1/recommendations/research')&&r.request().method()==='POST')
    await page.getByRole('button',{name:'Tìm gợi ý phù hợp',exact:true}).click()
    const response=await pending,data=await response.json()
    if(response.status()!==200||data.mode!=='INTERNAL_DEMO'||response.request().postDataJSON().budgetVnd!==budget)throw Error('Actual ADMIN research API failed')
    if(data.topProperties.length>10||data.topAreas.length>5||data.topProperties.some(p=>p.priceVnd>budget))throw Error('Budget/top limits failed')
    await page.locator('[data-advisor-property]').first().waitFor()
    const tinix=data.topProperties.filter(p=>p.source.kind==='TINIX_AI')
    if(!tinix.length)throw Error('No actual TiniX recommendation to accept')
    for(const p of tinix){
      const card=page.locator('[data-advisor-property="'+p.id+'"]')
      if(!await card.getByText('Dữ liệu nghiên cứu TiniX AI — chưa xác minh',{exact:true}).isVisible())throw Error('Research label missing')
      if(!(await card.innerText()).includes(p.source.recordKey))throw Error('Internal ID missing')
      if(await card.getByRole('button',{name:'Xem trên bản đồ',exact:true}).count()||await card.locator('a[href]').count())throw Error('Fake map/source/contact offered for dataset')
    }
    if(await page.locator('[data-property-id^="tinix:"]').count())throw Error('Invented TiniX pin')
    result.cases.push({budgetVnd:budget,http:response.status(),topProperties:data.topProperties.length,topAreas:data.topAreas.length,tinixProperties:tinix.length})
  }
  await page.locator('.advisor-page').screenshot({path:out+'/tinix-admin-desktop.png'})
  for(const width of [390,360]){
    await page.setViewportSize({width,height:844})
    if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Research mobile overflow')
  }
  await page.locator('.advisor-page').screenshot({path:out+'/tinix-admin-mobile.png'})
  if(errors.length||privateHeader.length)throw Error('Browser errors or secret exposure')
  result.status='PASS';result.noFakeTinixPins=true;result.noSellerContact=true;result.noSecretHeaderFromBrowser=true;result.mobileNoOverflow=true
} finally {
  if(browser)await browser.close()
  vite.kill()
  await fs.writeFile(out+'/frontend-admin-live.json',JSON.stringify(result,null,2))
}
