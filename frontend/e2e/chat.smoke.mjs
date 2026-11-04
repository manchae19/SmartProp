import {createRequire} from 'node:module'
import fs from 'node:fs/promises'
const require=createRequire(new URL('../package.json',import.meta.url));const {chromium}=require('@playwright/test')
const out=process.argv[2],browser=await chromium.launch({channel:'msedge',headless:true}),checks=[],errors=[]
try{
  const page=await browser.newPage({viewport:{width:1366,height:900}});page.on('pageerror',e=>errors.push(e.message))
  for(const path of ['/home','/advisor','/valuation','/listings','/login','/advisor/chat']){
    const response=await page.goto('http://127.0.0.1:5173'+path,{waitUntil:'domcontentloaded'});await page.locator('#page-content, form').first().waitFor();await page.waitForTimeout(250)
    checks.push({path,status:response.status(),pass:response.status()===200&&await page.locator('h1,h2').count()>0})
  }
  await page.getByRole('button',{name:'Mở menu điều hướng'}).click()
  const link=page.getByRole('navigation',{name:'Điều hướng website trong menu'}).getByRole('link',{name:'Tư vấn BĐS',exact:true})
  checks.push({name:'Navigation recognizes /advisor/chat active',pass:await link.getAttribute('aria-current')==='page'})
  checks.push({name:'Existing pages no runtime errors',pass:errors.length===0})
}finally{await browser.close();await fs.writeFile(out+'/smoke-results.json',JSON.stringify({checks,errors,passed:checks.filter(c=>c.pass).length,failed:checks.filter(c=>!c.pass).length},null,2))}
if(checks.some(c=>!c.pass))throw Error('Smoke checks failed')
console.log(JSON.stringify({passed:checks.length,failed:0}))
