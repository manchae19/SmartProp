
import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import path from 'node:path'
import { tmpdir } from 'node:os'
import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { createServer } from 'node:net'
import assert from 'node:assert/strict'
import { createServer as viteServer } from 'vite'
import react from '@vitejs/plugin-react'

const chromium = process.env.WP02_CHROMIUM
assert.ok(chromium, 'Set WP02_CHROMIUM to the Chromium executable')
const tempRoot = path.resolve(tmpdir())
const profile = mkdtempSync(path.join(tempRoot, 'smartprop-wp02-chrome-'))
const wait = ms => new Promise(r => setTimeout(r, ms))
const socket = createServer().listen(0,'127.0.0.1')
await once(socket,'listening')
const port=socket.address().port
await new Promise(r => socket.close(r))
const vite=await viteServer({root:process.cwd(),configFile:false,plugins:[react()],server:{host:'127.0.0.1',port,strictPort:true}})
await vite.listen()
const chrome=spawn(chromium, ['--headless=new','--disable-gpu','--disable-extensions','--disable-background-networking',
  '--no-first-run','--remote-debugging-port=0','--remote-debugging-address=127.0.0.1',
  '--no-proxy-server','--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE 127.0.0.1','--user-data-dir='+profile,'about:blank'],{stdio:'ignore',windowsHide:true})
let ws
const cdpPending = new Map()
const exceptions = []
const requestUrls = new Map()
let sequence = 0
try {
  const portFile=path.join(profile,'DevToolsActivePort')
  let devPort
  for (let retry=0;retry<100&&!devPort;retry++) {
    try { devPort=Number(readFileSync(portFile,'utf8').split(/\r?\n/)[0]) } catch {}
    if (!devPort) await wait(100)
  }
  if (!devPort) throw Error('DevTools did not start')
  const list=await fetch('http://127.0.0.1:'+devPort+'/json/list').then(r=>r.json())
  ws=new WebSocket(list.find(t=>t.type==='page').webSocketDebuggerUrl)
  await once(ws,'open')
  ws.onmessage=event=>{
    const msg=JSON.parse(event.data)
        if (msg.method==='Runtime.exceptionThrown') { exceptions.push(msg.params.exceptionDetails); console.log('PAGE ERROR',JSON.stringify(msg.params.exceptionDetails)) }
    if (msg.method==='Network.responseReceived' && msg.params.response.status >= 400) console.log('HTTP ERROR',msg.params.response.status,msg.params.response.url)
    if (msg.method==='Network.requestWillBeSent') requestUrls.set(msg.params.requestId,msg.params.request.url)
    if (msg.method==='Network.loadingFailed') console.log('LOAD ERROR', msg.params.errorText,requestUrls.get(msg.params.requestId))
    if (msg.method==='Log.entryAdded') console.log('LOG',msg.params.entry.text)
    if(!msg.id)return
    const promise=cdpPending.get(msg.id)
    cdpPending.delete(msg.id)
    if(msg.error)promise.reject(Error(JSON.stringify(msg.error)))
    else promise.resolve(msg.result)
  }
  const send=(method,params={})=>new Promise((resolve,reject)=>{
    const id=++sequence
    cdpPending.set(id,{resolve,reject})
    ws.send(JSON.stringify({id,method,params}))
  })
  const ev=async expression=>{
    const payload=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true})
    if(payload.exceptionDetails)throw Error(JSON.stringify(payload.exceptionDetails))
    return payload.result.value
  }
  const until=async(expression,label=expression)=>{
    for(let i=0;i<150;i++){
      if(await ev(expression))return
      await wait(65)
    }
    throw Error(label+'\n'+(await ev('document.body.innerText')).slice(0,2200))
  }
  const select=(selector,value)=>ev('(function(){const x=document.querySelector('+JSON.stringify(selector)+');if(!x)throw Error("Missing selector");const proto=x.tagName==="SELECT"?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,"value").set.call(x,'+JSON.stringify(value)+');x.dispatchEvent(new Event(x.tagName==="SELECT"?"change":"input",{bubbles:true}));})()')
  const click=(selector)=>ev('document.querySelector('+JSON.stringify(selector)+').click()')
  const bodyText=word=>'document.body.innerText.includes('+JSON.stringify(word)+')'
  const request=()=>ev("requests.filter(x=>x.path.endsWith('/comparables')).at(-1).data")
  const present=async word=>await until(bodyText(word))
  await send('Log.enable'); await send('Runtime.enable')
  await send('Page.enable')
  await send('Network.enable')
  await send('Network.setBlockedURLs',{urls:['https://*']})
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false})
  const fixtureUrl='http://127.0.0.1:'+port+'/tests/browser/wp02-browser.html'
  for (let retry=0;retry<4;retry++) {
    await wait(800)
    const navigation=await send('Page.navigate',{url:fixtureUrl})
    await wait(600)
    if (!navigation.errorText && await ev('location.href') === fixtureUrl) break
    console.log('Retrying navigation', navigation.errorText ?? await ev('location.href'))
  }
  await until("typeof showFixture==='function'")
  await select('form label:first-child select','BUYER_BUDGET_SEARCH')
  await select('form input[type=number]','80')
  await select('form label:nth-child(6) input','4500000000')
  await click('form button[type=submit]')
  await present('Đang tìm bất động sản tương đồng')
  await present('Trung vị giá rao trên 6 tin')
  assert.deepEqual(await request(),{purpose:'BUYER_BUDGET_SEARCH',propertyType:'HOUSE',district:'Hải Châu',areaSqm:80,buyerBudgetVnd:4500000000,limit:5})
  console.log('PASS Direct Comparable API form / buyer budget / loading / cohort')
  const result = 'Trung vị giá rao trên 6 tin'
  const pending = "heldComparables.length === 1"
  const formButton = 'form button[type=submit]'
  const lookupButton = '.cmp-lookup'
  const absent = async () => {
    await ev('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    assert.equal(await ev(bodyText(result)), false, 'Previous comparable data is still visible')
  }
  const noRequest = async (selector) => {
    const before = await ev("requests.filter(x=>x.path.endsWith('/comparables')).length")
    await click(selector)
    await absent()
    assert.equal(await ev("requests.filter(x=>x.path.endsWith('/comparables')).length"), before)
  }
  // Same token, same actor. Revocation must remove a completed result and block a new request.
  await ev("setFixtureSession('BUYER')")
  await absent()
  await noRequest(formButton)
  await ev('broker()')
  await absent()
  await click(formButton)
  await present(result)
  for (const role of ['BROKER', 'ADMIN']) {
    await ev(`setFixtureSession('${role}')`)
    await click(formButton)
    await present(result)
    await ev('editFixtureAuthorization({transition:true})')
    await noRequest(formButton)
    await ev('editFixtureAuthorization({transition:false})')
    await absent()
  }
  await click(formButton)
  await present(result)
  await ev("editFixtureAuthorization({accountStatus:'LOCKED'})")
  await noRequest(formButton)
  await ev("editFixtureAuthorization({accountStatus:'ACTIVE'})")
  await absent()
  await click(formButton)
  await present(result)
  await ev('broker()')
  console.log('PASS Direct loaded result cleared on same-token downgrade and fresh request on restoration')

  await ev('holdComparables=true')
  await click(formButton)
  await until(pending)
  await ev("setFixtureSession('BUYER')")
  await ev('releaseComparable()')
  await absent()
  await ev('broker()')
  await absent()
  await click(formButton)
  await until(pending)
  await ev("setFixtureSession('BROKER','UNAVAILABLE')")
  await noRequest(formButton)
  await ev('releaseComparable()')
  await ev('broker()')
  await absent()
  console.log('PASS Direct pending response rejected after downgrade or non-authenticated session status')

  await click(formButton)
  await until(pending)
  await select('form input[type=number]','84')
  await until("!document.querySelector('form button[type=submit]').disabled")
  await ev('releaseComparable()')
  await absent()
  await ev('holdComparables=false')
  await click(formButton)
  await present(result)
  assert.equal((await request()).areaSqm, 84)
  console.log('PASS Direct criteria change invalidates the pending response')

  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true})
  assert.equal(await ev('document.querySelector(".cmp-card").scrollWidth <= document.querySelector(".cmp-card").clientWidth+1'),true)
  for (const [mode, text] of [['empty','Chưa có tin tương đồng'],['unavailable','Thử lại'],['research','nghiên cứu']]) {
    await ev('fixtureResponse='+JSON.stringify(mode))
    await click('form button[type=submit]')
    await present(text)
    assert.equal(await ev("document.querySelectorAll('[data-comparable-source=TINIX_RESEARCH]').length"),0)
  }
  console.log('PASS Responsive mobile / empty and insufficient / retry / research rejection')
  await ev("fixtureResponse='available';showFixture('listing')")
  await until("!!document.querySelector('.cmp-lookup')",'Property detail lookup missing')
  await click('.cmp-lookup')
  await present('Trung vị giá rao trên 6 tin')
  assert.equal((await request()).purpose,'SIMILAR_LISTING')
  assert.equal((await request()).propertyId,'10000000-0000-4000-8000-000000000000')
  console.log('PASS Actual ListingDetailView invokes SIMILAR_LISTING by property ID')
  await ev("setFixtureSession('BUYER')")
  await absent()
  await until("!document.querySelector('.cmp-lookup')")
  await ev('broker()')
  await until("!!document.querySelector('.cmp-lookup')")
  await absent()
  await ev('holdComparables=true')
  await click(lookupButton)
  await until(pending)
  // Both changes can happen before React renders. A new query must still be required.
  await ev("setFixtureSession('BUYER');broker()")
  await ev('releaseComparable()')
  await absent()
  await until("!!document.querySelector('.cmp-lookup')")
  await click(lookupButton)
  await until(pending)
  await ev('editFixtureAuthorization({sameAccountReplacement:true})')
  await ev('releaseComparable()')
  await absent()
  await until("!!document.querySelector('.cmp-lookup')")
  await click(lookupButton)
  await until(pending)
  await ev("editFixtureAuthorization({accountStatus:'LOCKED'});editFixtureAuthorization({accountStatus:'ACTIVE'})")
  await ev('releaseComparable()')
  await absent()
  await until("!!document.querySelector('.cmp-lookup')")
  await click(lookupButton)
  await until(pending)
  await ev('logoutFixture()')
  await absent()
  await until("!document.querySelector('.cmp-lookup')")
  await ev('broker()')
  await ev('releaseComparable()')
  await absent()
  await until("!!document.querySelector('.cmp-lookup')")
  await click(lookupButton)
  await until(pending)
  await ev("setFixtureSession('BROKER','AUTHENTICATED',2)")
  await ev('releaseComparable()')
  await absent()
  await until("!!document.querySelector('.cmp-lookup')")
  console.log('PASS Embedded lookup invalidates on downgrade/restoration, logout/login and same-token actor change')

  await ev('lookupCriteria(80)')
  await until(bodyText('Đối chiếu fixture'))
  await click(lookupButton)
  await until(pending)
  await ev('lookupCriteria(86)')
  await until("!!document.querySelector('.cmp-lookup')")
  await click(lookupButton)
  await until("heldComparables.length === 2")
  await ev('releaseComparable()')
  await absent()
  await ev('releaseComparable()')
  await present(result)
  assert.equal((await request()).areaSqm, 86)
  await ev('holdComparables=false')
  console.log('PASS Embedded lookup rejects the old criteria response and displays the new response')
  await ev("showFixture('valuation')")
  await until("!!document.querySelector('form button[type=submit]:not([disabled])')",'Standalone valuation form')
  await click('form button[type=submit]')
  await until("!!document.querySelector('.cmp-lookup')",'Standalone valuation lookup')
  await click('.cmp-lookup')
  await present('Trung vị giá rao trên 6 tin')
  assert.equal((await request()).purpose,'VALUATION_SUPPORT')
  assert.equal(Object.hasOwn(await request(),'priceVnd'),false)
  console.log('PASS Actual ValuationPanel independent evidence')
  await ev("showFixture('post')")
  await until("!!document.querySelector('[data-testid=valuation-preview]:not([disabled])')",'Posting form')
  await click('[data-testid=valuation-preview]')
  await until("!!document.querySelector('.cmp-lookup')",'Posting valuation lookup')
  await click('.cmp-lookup')
  await present('Trung vị giá rao trên 6 tin')
  assert.equal((await request()).purpose,'VALUATION_SUPPORT')
  assert.equal(Object.hasOwn(await request(),'priceVnd'),false)
  console.log('PASS Actual PostValuationPanel independent evidence')
  await ev("showFixture('advisor')")
  await present('Tin tương đồng theo giá rao')
  await present('Đối chiếu định giá bằng tin đăng')
  await present('Chưa đủ bằng chứng')
  assert.equal(await ev("document.querySelectorAll('[data-comparable-card]').length"),2)
  assert.deepEqual(await ev(`Array.from(document.querySelectorAll('[data-comparable-card]'), card =>
    ['Điểm tương đồng 92/100', 'Độ phủ thuộc tính 74%'].every(label => card.innerText.includes(label)))`), [true, true])
  console.log('PASS Advisor renders score and coverage for both comparable evidence purposes')
  await ev("showFixture('internal',true)")
  await until("!!document.querySelector('[data-comparable-source=TINIX_RESEARCH]')")
  await ev("showFixture('internal',false)")
  await until("!document.querySelector('[data-advisor-results]')")
  await ev("setFixtureSession('ADMIN');showFixture('legacy')")
  await until("!!document.querySelector('.research-controls')")
  await ev("editFixtureAuthorization({transition:true})")
  await until("!document.querySelector('.research-controls')")
  await ev("editFixtureAuthorization({transition:false})")
  await until("!!document.querySelector('.research-controls')")
  await ev("editFixtureAuthorization({accountStatus:'LOCKED'})")
  await until("!document.querySelector('.research-controls')")
  console.log('PASS Actual AdvisorResults purpose separation / research revocation')
  assert.deepEqual(exceptions, [])
} finally {
  ws?.close()
  await vite.close()
  if (chrome.exitCode === null && chrome.signalCode === null) {
    const stopped = once(chrome, 'exit')
    chrome.kill()
    await stopped
  }
  assert.equal(path.dirname(profile), tempRoot)
  rmSync(profile, { recursive: true, maxRetries: 8, retryDelay: 150 })
}
