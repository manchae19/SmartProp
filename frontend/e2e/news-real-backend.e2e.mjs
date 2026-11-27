/** Real Spring/MySQL integration. Supply synthetic fixtures in an isolated environment first. */
import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import fs from 'node:fs'
const require=createRequire(import.meta.url)
let chromium
try { ({chromium}=require('playwright')) }
catch { if(!process.env.PLAYWRIGHT_PATH)throw Error('Set PLAYWRIGHT_PATH to an installed Playwright package');({chromium}=require(process.env.PLAYWRIGHT_PATH)) }
const base=process.env.SMARTPROP_NEWS_E2E_BASE||'http://127.0.0.1:14137'
const api=process.env.SMARTPROP_NEWS_API||'http://127.0.0.1:18141'
for(const url of [base,api])assert.match(url,/^http:\/\/127[.]0[.]0[.]1:[0-9]{4,5}$/,'Isolated loopback URLs required')
const checks=[],exceptions=[]
async function get(path){const response=await fetch(api+'/api/v1'+path);assert.equal(response.status,200);return response.json()}
const list=await get('/news?size=12'),featured=await get('/news/featured'),sources=await get('/news/sources')
assert(Array.isArray(sources));assert(list.items.length>0,'Provision clearly labelled synthetic fixtures before running')
assert(list.items.every(a=>a.title.startsWith('SYNTHETIC')),'This runner requires synthetic test fixtures')
assert(!JSON.stringify(list).match(/rightsReference|syncLeaseToken|sourceRevision|httpEtag|lastError/));checks.push('contract-and-no-internal-metadata')
const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM?{executablePath:process.env.PLAYWRIGHT_CHROMIUM}:{channel:'chrome'})})
try {
 const page=await browser.newPage();page.on('pageerror',error=>exceptions.push(error.message))
 // No request interception: every News and supporting API request reaches real services.
 for(const width of [1440,768,390]) {
  await page.setViewportSize({width,height:1000});await page.goto(base+'/news')
  await page.waitForFunction(expected=>document.querySelectorAll('.news-list .news-card').length===expected,list.items.length)
  assert.equal(await page.locator('.news-list .news-card h3').first().innerText(),list.items[0].title)
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false)
  const link=page.locator('.news-list .news-card h3 a').first()
  assert.equal(await link.getAttribute('href'),list.items[0].articleUrl);assert.equal(await link.getAttribute('rel'),'noopener noreferrer')
  if(list.totalPages>1){await page.getByRole('button',{name:'Sau',exact:true}).click();await page.getByText(new RegExp('Trang 2 / '+list.totalPages)).waitFor()}
  await page.goto(base+'/news');await page.locator('.news-list .news-card').first().waitFor()
  const response=page.waitForResponse(r=>r.url().includes('/api/v1/news?')&&new URL(r.url()).searchParams.get('sort')==='oldest')
  await page.getByRole('combobox').selectOption('oldest');const oldest=await (await response).json()
  await page.waitForFunction(title=>document.querySelector('.news-list .news-card h3')?.textContent===title,oldest.items[0].title)
  const query=list.items[0].title;await page.getByPlaceholder('Tìm theo tiêu đề hoặc từ khóa').fill(query)
  const searchResponse=page.waitForResponse(r=>r.url().includes('/api/v1/news?')&&new URL(r.url()).searchParams.get('q')===query)
  await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click();const searched=await (await searchResponse).json()
  await page.waitForFunction(count=>document.querySelectorAll('.news-list .news-card').length===count,searched.items.length)
  await page.goto(base+'/home');await page.waitForFunction(count=>document.querySelectorAll('#news .news-card').length===count,featured.items.length)
  if(process.env.SMARTPROP_NEWS_EVIDENCE_DIR)await page.locator('#news').screenshot({path:process.env.SMARTPROP_NEWS_EVIDENCE_DIR+'/source-runner-home-'+width+'.png'})
  checks.push('real-api-ui-search-sort-pagination-attribution-home-'+width)
 }
 assert.equal(exceptions.length,0,exceptions.join('\n'));checks.push('zero-uncaught-page-exceptions')
} finally {await browser.close()}
const result={status:'FRESH_PASS',checks,exceptions,mockedNewsApi:false,api,base}
if(process.env.SMARTPROP_NEWS_EVIDENCE_DIR)fs.writeFileSync(process.env.SMARTPROP_NEWS_EVIDENCE_DIR+'/source-news-e2e.json',JSON.stringify(result,null,2))
console.log(JSON.stringify(result))
