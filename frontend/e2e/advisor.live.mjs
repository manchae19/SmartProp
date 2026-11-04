import {createRequire} from 'node:module'
import {pathToFileURL,fileURLToPath} from 'node:url'
import fs from 'node:fs/promises'
const root=fileURLToPath(new URL('../../../',import.meta.url)).replaceAll('\\','/').replace(/\/$/,'')
const require=createRequire(pathToFileURL(root+'/frontend/vue.ui/package.json'))
const {chromium}=require('@playwright/test')
const base=process.argv[2],output=process.argv[3]
await fs.mkdir(output,{recursive:true})
if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(base))throw Error('Loopback only')
const browser=await chromium.launch({channel:'msedge',headless:true})
const results={status:'RUNNING',real_api:true,cases:[],screenshots:[],checks:{}}
try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}})
  const errors=[],badHeaders=[]
  page.on('pageerror',e=>errors.push(e.message))
  page.on('request',r=>{if(r.headers()['x-smartprop-demo-key'] || r.url().endsWith('/api/v1/recommendations') && r.headers().authorization)badHeaders.push(r.url())})
  await page.goto(base+'/home',{waitUntil:'networkidle'})
  await page.locator('[data-advisor-home]').click()
  await page.getByRole('heading',{name:'Tìm không gian phù hợp với bạn'}).waitFor()
  if(!await page.getByRole('textbox',{name:/Ngân sách tối đa \(VNĐ\)/}).isVisible())throw Error('Budget must be labeled in VND')
  if(!await page.locator('[data-advisor-header]').isVisible())throw Error('Desktop Header Advisor entry missing')
  results.checks.homeAndHeaderNavigation=true
  // Delay the real request (never mock a response) to observe loading and disabled controls.
  let release
  const held=new Promise(resolve=>{release=resolve})
  const slow=async route=>{await held;await route.continue()}
  await page.route('**/api/v1/recommendations',slow)
  const first=page.waitForResponse(r=>r.url().endsWith('/api/v1/recommendations')&&r.request().method()==='POST')
  await page.getByRole('button',{name:'Tìm gợi ý phù hợp',exact:true}).click()
  await page.locator('.loading-panel').waitFor()
  if(!await page.locator('[name=budget]').isDisabled())throw Error('Loading does not disable filters')
  release();await first;await page.locator('[data-advisor-empty]').waitFor()
  await page.unroute('**/api/v1/recommendations',slow)
  results.checks.loading=true
  for(const [budget,purpose,type] of [['750000000','LIVING','ALL'],['1250000000','INVESTMENT','HOUSE'],['2350000000','RENTAL','APARTMENT'],['3780000000','LIVING','LAND'],['4650000000','LIVING','ALL'],['8900000000','LIVING','ALL'],['15500000000','LIVING','ALL']]) {
    await page.locator('[name=budget]').fill(budget)
    await page.locator('[name=purpose]').selectOption(purpose)
    await page.locator('[name=propertyType]').selectOption(type)
    const pending=page.waitForResponse(r=>r.url().endsWith('/api/v1/recommendations')&&r.request().method()==='POST')
    await page.getByRole('button',{name:'Tìm gợi ý phù hợp'}).click()
    const response=await pending,data=await response.json(),request=response.request().postDataJSON()
    if(response.status()!==200||data.mode!=='SAFE'||request.budgetVnd!==Number(budget))throw Error('Actual API contract failed')
    if(request.purpose!==purpose||request.propertyType!==type||request.source||request.demoKey)throw Error('Wrong request / source selection')
    if(data.topProperties.some(p=>p.verificationStatus==='UNVERIFIED'||p.qualityStatus==='REJECTED'))throw Error('Unsafe data in real API')
    if(!data.topProperties.length)await page.locator('[data-advisor-empty]').waitFor()
    else await page.locator('[data-advisor-property]').first().waitFor()
    results.cases.push({budgetVnd:request.budgetVnd,purpose,type,httpStatus:response.status(),topProperties:data.topProperties.length,topAreas:data.topAreas.length})
  }
  await page.locator('[name=district]').fill('Cẩm Lệ')
  await page.getByText(/Bạn đã thay đổi bộ lọc/).waitFor()
  await page.locator('[name=minAreaSqm]').fill('60')
  await page.locator('[name=limit]').selectOption('5')
  const filtered=page.waitForResponse(r=>r.url().endsWith('/api/v1/recommendations')&&r.request().method()==='POST')
  await page.getByRole('button',{name:'Tìm gợi ý phù hợp',exact:true}).click()
  const filteredResponse=await filtered,filterBody=filteredResponse.request().postDataJSON()
  if(filteredResponse.status()!==200||filterBody.district!=='Cẩm Lệ'||filterBody.minAreaSqm!==60||filterBody.limit!==5)throw Error('Optional filters failed')
  await page.getByRole('heading',{name:'Kết quả tư vấn',exact:true}).waitFor()
  results.checks.optionalFiltersAndStaleCriteria=true
  // Abort only this network request to test offline UX; retry then uses the real API.
  const offline=route=>route.abort('failed')
  await page.route('**/api/v1/recommendations',offline)
  await page.getByRole('button',{name:'Tìm gợi ý phù hợp',exact:true}).click()
  await page.getByRole('alert').waitFor()
  await page.unroute('**/api/v1/recommendations',offline)
  const retry=page.waitForResponse(r=>r.url().endsWith('/api/v1/recommendations')&&r.request().method()==='POST')
  await page.getByRole('button',{name:'Thử lại',exact:true}).click()
  if((await retry).status()!==200)throw Error('Retry did not reach real API')
  await page.locator('[data-advisor-empty], [data-advisor-property]').first().waitFor()
  results.checks.offlineAndRealRetry=true
  // Use existing public records at an explicit higher budget; never seed or enable demo.
  await page.locator('[name=budget]').fill('10000000000')
  await page.locator('[name=propertyType]').selectOption('ALL')
  await page.locator('[name=district]').fill('')
  await page.locator('[name=ward]').fill('')
  await page.locator('[name=minAreaSqm]').fill('')
  await page.locator('[name=limit]').selectOption('10')
  const positive=page.waitForResponse(r=>r.url().endsWith('/api/v1/recommendations')&&r.request().method()==='POST')
  await page.getByRole('button',{name:'Tìm gợi ý phù hợp',exact:true}).click()
  const positiveResponse=await positive,actual=await positiveResponse.json()
  if(positiveResponse.status()!==200||actual.mode!=='SAFE')throw Error('Positive safe request failed')
  if(actual.topProperties.length) {
    await page.locator('[data-advisor-property]').first().waitFor()
    const first=actual.topProperties[0],second=actual.topProperties[1]
    const firstCard=page.locator('[data-advisor-property="'+first.id+'"]')
    await firstCard.getByRole('button',{name:'Xem trên bản đồ',exact:true}).click()
    await page.locator('[data-property-id="'+first.id+'"].selected').waitFor()
    if(!await firstCard.evaluate(el=>el.classList.contains('selected')))throw Error('List-to-map selection failed')
    await page.getByRole('button',{name:'Xem tất cả ghim của trang hiện tại',exact:true}).click()
    const reverse=second||first
    await page.locator('[data-property-id="'+reverse.id+'"]').click()
    const reverseCard=page.locator('[data-advisor-property="'+reverse.id+'"]')
    if(!await reverseCard.evaluate(el=>el.classList.contains('selected')))throw Error('Map-to-list selection failed')
    const realCoordinates=[]
    for(const property of actual.topProperties.filter(p=>p.source.kind==='PROPERTY')) {
      const detailResponse=await page.request.get(base+'/api/v1/properties/'+encodeURIComponent(property.source.recordKey))
      if(detailResponse.status()!==200)throw Error('Public property detail unavailable')
      const detail=await detailResponse.json()
      if(detail.id!==property.source.recordKey||detail.status!=='PUBLISHED'||!Number.isFinite(detail.latitude)||!Number.isFinite(detail.longitude))throw Error('Property coordinates not public/valid')
      realCoordinates.push({id:property.id,latitude:detail.latitude,longitude:detail.longitude})
    }
    results.positiveSafe={properties:actual.topProperties.length,areas:actual.topAreas.length,realCoordinates}
    results.checks.realListMapTwoWaySelection=true
    await page.getByRole('button',{name:'Xem tất cả ghim của trang hiện tại',exact:true}).click()
  } else results.positiveSafe={properties:0,areas:actual.topAreas.length,note:'No public records at10B; do not fabricate data'}
  const map=page.getByRole('region',{name:/Bản đồ tin công khai/})
  await map.scrollIntoViewIfNeeded()
  if(!await page.locator('[data-advisor-property]').count() && await page.locator('[data-property-id]').count())throw Error('Map must not invent property points')
  if(!await page.getByRole('link',{name:'© OpenStreetMap contributors'}).isVisible())throw Error('Map attribution missing')
  await page.waitForFunction(()=>[...document.querySelectorAll('img.map-tile')].some(i=>i.complete&&i.naturalWidth>0),undefined,{timeout:8000}).catch(()=>{})
  results.mapTiles=await page.locator('img.map-tile').evaluateAll(images=>({requested:images.length,loaded:images.filter(i=>i.complete&&i.naturalWidth>0).length,failed:images.filter(i=>i.complete&&i.naturalWidth===0).length}))
  if(!results.mapTiles.loaded)throw Error('OpenStreetMap tiles did not load; check network access, do not replace with fake imagery')
  await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo({top:0,behavior:'instant'})})
  await page.screenshot({path:output+'/advisor-desktop.png',fullPage:true});results.screenshots.push('advisor-desktop.png')
  await page.setViewportSize({width:390,height:844})
  await page.locator('#advisor-title').scrollIntoViewIfNeeded()
  await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo({top:0,behavior:'instant'})})
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Mobile horizontal overflow')
  await page.screenshot({path:output+'/advisor-mobile.png',fullPage:true});results.screenshots.push('advisor-mobile.png')
  await page.locator('[data-app-menu-trigger]').click()
  await page.getByRole('dialog').getByRole('link',{name:'Tư vấn BĐS',exact:true}).click()
  if(!page.url().includes('/advisor'))throw Error('Mobile navigation failed')
  results.checks.mobileNavigation=true
  await page.getByRole('button',{name:'Đặt lại',exact:true}).click()
  if(await page.locator('[name=budget]').inputValue()!=='2.000.000.000'||await page.locator('[name=district]').inputValue()!=='')throw Error('Reset failed')
  await page.locator('[name=budget]').fill('0')
  await page.getByRole('button',{name:'Tìm gợi ý phù hợp',exact:true}).click()
  await page.getByRole('alert').waitFor()
  results.checks.resetAndValidation=true
  let invalidRequests=0
  const countInvalid=r=>{if(r.url().endsWith('/api/v1/recommendations')&&r.method()==='POST')invalidRequests++}
  page.on('request',countInvalid)
  for(const value of ['-1','bad','1000000000000000']) {
    await page.locator('[name=budget]').fill(value)
    await page.getByRole('button',{name:'Tìm gợi ý phù hợp',exact:true}).click()
    await page.getByRole('alert').waitFor()
  }
  await page.locator('[name=budget]').fill('')
  await page.getByRole('button',{name:'Tìm gợi ý phù hợp',exact:true}).click()
  if(await page.locator('[name=budget]').evaluate(el=>el.checkValidity()))throw Error('Empty budget accepted')
  page.off('request',countInvalid)
  if(invalidRequests)throw Error('Invalid budget reached real API')
  results.checks.invalidBudgetsBlockedBeforeRequest=true
  await page.setViewportSize({width:360,height:800})
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('360px horizontal overflow')
  if(badHeaders.length||errors.length)throw Error('Browser errors or demo credential leak: '+JSON.stringify(errors))
  if(await page.locator('input[type=password]').count())throw Error('Advisor must not request a demo key')
  const valuation=await page.request.get(base+'/valuation')
  if(valuation.status()!==200)throw Error('Existing frontend route unavailable')
  results.status='PASS';results.browserErrors=[];results.noDemoKeySent=true;results.noFakeMapPins=true;results.mobileNoOverflow=true
} finally {
  await fs.writeFile(output+'/advisor-browser-result.json',JSON.stringify(results,null,2))
  await browser.close()
}
