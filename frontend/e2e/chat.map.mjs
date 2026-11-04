/** Real sequential browser/API acceptance. No fulfilled/mock responses or DB mutations. */
import {createRequire} from 'node:module'
import {fileURLToPath} from 'node:url'
import {execFileSync} from 'node:child_process'
import fs from 'node:fs/promises'
const require=createRequire(new URL('../package.json',import.meta.url)),{chromium}=require('@playwright/test')
const root=fileURLToPath(new URL('../../../',import.meta.url)),out=process.argv[2]
const result={checks:[],cases:[],requests:[],errors:[],screenshots:[],complete:false}
const browser=await chromium.launch({channel:'msedge',headless:true})
const ctx=await browser.newContext({viewport:{width:1440,height:1000}}),page=await ctx.newPage()
page.on('pageerror',e=>result.errors.push(e.message))
page.on('request',r=>{if(r.url().includes('/api/chat')||r.url().includes('/api/v1/amenities/map')){const h=r.headers();result.requests.push({url:r.url(),method:r.method(),auth:!!h.authorization,cookie:!!h.cookie,key:!!h['x-smartprop-demo-key'],body:r.method()==='POST'?r.postDataJSON():null})}})
function check(name,pass,details){result.checks.push({name,pass:!!pass,details});if(!pass)throw Error(name)}
async function save(){await fs.writeFile(out+'/chat-map-e2e.json',JSON.stringify(result,null,2))}
async function shot(name){await page.screenshot({path:out+'/'+name+'.png'});result.screenshots.push(name+'.png')}
async function gate(){let g;for(let i=0;i<6;i++){g=JSON.parse(execFileSync(root+'/.scratch/rag-ollama-venv/Scripts/python.exe',['-X','utf8',out+'/gate.py'],{encoding:'utf8',windowsHide:true}));if(!g.pressure&&g.availableRamMiB>=g.minimumRamMiB&&g.commitHeadroomMiB>=4096&&g.vramTotalMiB-g.vramMiB>=3500)break;await page.waitForTimeout(5000)}check('Resource headroom before sequential Qwen call',!g.pressure&&g.availableRamMiB>=g.minimumRamMiB&&g.commitHeadroomMiB>=4096&&g.vramTotalMiB-g.vramMiB>=3500,g)}
async function geometry(label){const x=await page.evaluate(()=>{const c=document.querySelector('.composer-dock').getBoundingClientRect();return {w:innerWidth,h:innerHeight,bodyWidth:document.body.scrollWidth,bodyHeight:document.body.scrollHeight,composerBottom:c.bottom,composerTop:c.top}});check(label+': no page overflow and dock visible',x.bodyWidth<=x.w+1&&x.bodyHeight<=x.h+1&&x.composerBottom<=x.h+1,x)}
const cases=[
 {key:'hospitals',question:'Hải Châu có bệnh viện nào?',district:'Hải Châu',category:'HOSPITAL',count:2},
 {key:'schools',question:'Cẩm Lệ có trường học nào?',district:'Cẩm Lệ',category:'SCHOOL',count:5},
 {key:'general',question:'Sơn Trà có những tiện ích gì?',district:'Sơn Trà',category:'ALL',count:33},
 {key:'beaches',question:'Ngũ Hành Sơn có bãi biển nào?',district:'Ngũ Hành Sơn',category:'BEACH',count:4},
 {key:'house3b',question:'Tôi có 3 tỷ, muốn mua nhà ở Cẩm Lệ.'},
 {key:'property10b',question:'Tôi có 10 tỷ, gợi ý BĐS phù hợp.'},
 {key:'areaOnly',question:'Hải Châu có bãi biển nào?',district:'Hải Châu',category:'BEACH',count:0},
]
try{
 for(const [index,c] of cases.entries()){
  await page.goto('http://127.0.0.1:5173/advisor/chat',{waitUntil:'domcontentloaded'});await page.locator('#chat-question').waitFor()
  await gate()
  let release,handler,mapResponse
  if(c.district){
   mapResponse=page.waitForResponse(r=>r.url().includes('/api/v1/amenities/map?'),{timeout:95000})
   if(index===0){const barrier=new Promise(r=>release=r);handler=async route=>{await barrier;await route.continue()};await page.route('**/api/v1/amenities/map?*',handler)}
  }
  await page.locator('#chat-question').fill(c.question)
  const pending=page.waitForResponse(r=>r.url().endsWith('/api/chat')&&r.request().method()==='POST',{timeout:95000}),start=Date.now()
  await page.getByRole('button',{name:'Gửi câu hỏi',exact:true}).click()
  await page.locator('[data-chat-loading]').waitFor();check(c.key+': one request flight',await page.locator('#chat-question').isDisabled())
  const r=await pending,body=await r.json();const row={...c,status:r.status(),ms:Date.now()-start,body};result.cases.push(row)
  check(c.key+': actual HTTP200 Public SAFE',r.status()===200&&body.mode==='SAFE')
  await page.locator('[data-chat-answer]').waitFor();const ui=page.locator('[data-chat-answer]')
  check(c.key+': no research properties',body.recommendedProperties.every(p=>p.source.kind==='PROPERTY'&&p.verificationStatus==='PLATFORM_PUBLISHED'))
  check(c.key+': public citations',body.citations.every(c=>c.scope==='PUBLIC'&&/^[a-f0-9]{64}$/.test(c.contentHash)))
  if(release){await ui.locator('[data-amenity-loading]').waitFor();check('Map loading independent of retained answer',await ui.locator('[data-chat-summary]').isVisible());release()}
  if(c.district){
   const mr=await mapResponse;row.mapStatus=mr.status();row.map=await mr.json();if(handler)await page.unroute('**/api/v1/amenities/map?*',handler)
   check(c.key+': map API real selected geography/category',mr.status()===200&&row.map.district===c.district&&row.map.category===c.category&&row.map.items.length===c.count)
   await ui.locator('[data-chat-map]').waitFor();await ui.locator('[data-chat-map]').scrollIntoViewIfNeeded();await page.waitForTimeout(350)
   const mapped=await ui.locator('.browse-map').evaluate(el=>{let c=el.__vueParentComponent;while(c&&!('poiItems' in c.props))c=c.parent;return c?.props.poiItems.map(p=>({id:p.id,latitude:p.latitude,longitude:p.longitude,category:p.category,district:p.district}))})
   check(c.key+': renderer receives exact API coordinates without added points',JSON.stringify(mapped)===JSON.stringify(row.map.items.map(p=>({id:p.id,latitude:p.latitude,longitude:p.longitude,category:p.category,district:p.district}))))
   if(c.count){
    check(c.key+': summary names real returned amenity',await ui.locator('[data-chat-summary]').innerText().then(t=>row.map.items.some(p=>t.includes(p.name))))
    check(c.key+': summary map cards sources ordered',await ui.evaluate(el=>{const a=el.querySelector('[data-chat-summary]'),b=el.querySelector('[data-chat-map]'),c=el.querySelector('[data-amenity-cards]'),d=el.querySelector('[data-chat-sources]');return !!(a.compareDocumentPosition(b)&4)&&!!(b.compareDocumentPosition(c)&4)&&(!d||!!(c.compareDocumentPosition(d)&4))}))
    const pin=ui.locator('.poi-pin').first(),id=await pin.getAttribute('data-poi-id'),p=row.map.items.find(x=>x.id===id)
    await pin.click();await ui.locator('.poi-map-popup').waitFor()
    check(c.key+': marker popup name category source',await ui.locator('.poi-popup-title').innerText()===p.name&&await ui.locator('.poi-popup-source').getAttribute('href')===p.sourceUrl)
    check(c.key+': no property distance invented',await ui.locator('.poi-popup-dist').count()===0)
    await ui.locator('.poi-popup-close').click()
    const before=await ui.locator('.map-tile').first().getAttribute('src');await ui.getByRole('button',{name:'Phóng to bản đồ',exact:true}).click();check(c.key+': map zoom interactive',await ui.locator('.map-tile').first().getAttribute('src')!==before)
    await ui.getByRole('button',{name:'Xem tất cả ghim của trang hiện tại',exact:true}).click()
   }else{check('Area-only: true boundary and zero fake pins',await ui.locator('[data-map-boundary]').count()===1&&await ui.locator('.poi-pin,.price-pin').count()===0&&await ui.locator('[data-amenity-area-only]').isVisible())}
   await page.waitForFunction(()=>Array.from(document.querySelectorAll('.map-tile')).some(i=>i.complete&&i.naturalWidth===256),{timeout:20000})
   check(c.key+': actual OSM tiles loaded',await ui.locator('.map-tile').first().getAttribute('src').then(u=>u.startsWith('https://tile.openstreetmap.org/')))
   await geometry('Desktop '+c.key);await shot('desktop-'+c.key)
   if(index===0){
    await page.setViewportSize({width:390,height:844});await ui.locator('[data-chat-map]').scrollIntoViewIfNeeded();await geometry('Mobile hospital');await shot('mobile-hospital')
    await ui.locator('.poi-pin').first().click();await ui.locator('.poi-map-popup').waitFor();const popupBox=await ui.locator('.poi-map-popup').evaluate(e=>{const a=e.getBoundingClientRect(),b=e.closest('.browse-map').getBoundingClientRect(),s=getComputedStyle(e);return {popup:a.toJSON(),map:b.toJSON(),left:s.left,right:s.right,transform:s.transform,width:s.width}});check('Mobile popup fits map width',popupBox.popup.left>=popupBox.map.left-1&&popupBox.popup.right<=popupBox.map.right+1,popupBox);await shot('mobile-popup')
    await ui.locator('.poi-popup-close').click();await page.setViewportSize({width:320,height:740});await ui.locator('[data-chat-map]').scrollIntoViewIfNeeded();await geometry('Small mobile');await shot('mobile-320');await page.setViewportSize({width:1440,height:1000})
   }
  } else if(c.key==='property10b'){
    const ps=body.recommendedProperties;check('Property Top3 retained',ps.length>3&&JSON.stringify(await ui.locator('[data-chat-property]').evaluateAll(es=>es.map(e=>e.dataset.chatProperty)))===JSON.stringify(ps.slice(0,3).map(p=>p.id)))
    await ui.locator('[data-chat-expand]').click();check('Expand real properties without reranking',JSON.stringify(await ui.locator('[data-chat-property]').evaluateAll(es=>es.map(e=>e.dataset.chatProperty)))===JSON.stringify(ps.map(p=>p.id)))
    await ui.locator('[data-chat-expand]').click();await ui.locator('[data-chat-properties]').scrollIntoViewIfNeeded();await geometry('Property cards');await shot('desktop-properties')
    await page.setViewportSize({width:390,height:844});await ui.locator('[data-chat-properties]').scrollIntoViewIfNeeded();await geometry('Mobile property cards');await shot('mobile-properties');await page.setViewportSize({width:1440,height:1000})
  } else {check('Empty budget search no unrelated amenity map',!body.recommendedProperties.length&&await ui.locator('[data-chat-map]').count()===0);await shot('desktop-empty-budget')}
  // A category question with no matching POI must state the gap explicitly instead of
  // citing unrelated area evidence (this is why this case now carries zero citations).
  if(c.district && c.count===0)check(c.key+': explicit insufficiency without other-category citations',
    body.evidence.responseKind==='INSUFFICIENT_AMENITY_EVIDENCE'&&body.citations.length===0&&!body.recommendedProperties.length&&/Ch\u01b0a c\u00f3 b\u1eb1ng ch\u1ee9ng/i.test(body.answer)&&body.evidence.amenityIntent.categories.join()===c.category)
  if(body.citations.length){check(c.key+': citations technical metadata hidden by default',await ui.locator('[data-chat-sources]').getAttribute('open')===null&&!await ui.locator('.technical-source').first().isVisible());await ui.locator('[data-chat-sources]>summary').click();await ui.locator('.original-evidence').filter({has:page.locator('[data-chat-original]')}).locator('summary').click();check(c.key+': Qwen/source text untouched',await ui.locator('[data-chat-original]').innerText()===body.answer)}
  await save()
 }
 check('At least one real Qwen and E5_FAISS response',result.cases.some(c=>c.body.generationMode==='QWEN_GROUNDED_ANSWER'&&c.body.retrievalMode==='E5_FAISS'&&c.body.evidence.generation.accepted))
 check('No credentials/research controls forwarded',result.requests.every(r=>!r.auth&&!r.cookie&&!r.key&&(!r.body||Object.keys(r.body).every(k=>['question','requireGeneration'].includes(k)))))
 check('No browser runtime errors',result.errors.length===0,result.errors)
 result.complete=true
}catch(e){result.failure=e.message;await shot('failure').catch(()=>{});throw e}
finally{await save();await browser.close();console.log(JSON.stringify({complete:result.complete,checks:result.checks.length,failed:result.checks.filter(x=>!x.pass).map(x=>x.name),failure:result.failure}))}
