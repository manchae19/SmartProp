import fs from 'node:fs'
import path from 'node:path'
import {spawn} from 'node:child_process'
import assert from 'node:assert/strict'
import {fileURLToPath} from 'node:url'
import os from 'node:os'
import {connect} from './cdp.mjs'
const scriptDir=path.dirname(fileURLToPath(import.meta.url)),dir=fs.mkdtempSync(path.join(os.tmpdir(),'smartprop-auth-browser-')),frontend=path.resolve(scriptDir,'../../vue.ui'),backend=process.env.AUTH_TEST_BACKEND
if(!/^http:\/\/127\.0\.0\.1:[0-9]+$/.test(backend||'')||new URL(backend).port==='8080')throw Error('Browser writes must use isolated random backend port; real8080 forbidden')
const node=process.execPath,origin='http://127.0.0.1:5175',results=[],cookieFlags=[]
const pause=ms=>new Promise(r=>setTimeout(r,ms))
const env={...process.env,VITE_ENABLE_REFRESH:'true',VITE_API_BASE_URL:'/api/v1',SMARTPROP_DEV_API_TARGET:backend,VITE_GOOGLE_MAPS_API_KEY:''}
for(const key of Object.keys(env))if(/PASSWORD|SECRET|TOKEN|AUTH_TEST_/.test(key))delete env[key]
const viteOut=fs.openSync(path.join(dir,'vite-browser.log'),'w'),vite=spawn(node,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5175','--strictPort'],{cwd:frontend,env,windowsHide:true,stdio:['ignore',viteOut,viteOut]})
async function waitFor(fn,ms=20000){const end=Date.now()+ms;while(Date.now()<end){if(await fn())return;await pause(150)}throw Error('QA condition timed out')}
async function check(browser,name,fn){await fn();results.push({browser,name,pass:true});console.log('PASS '+browser+': '+name)}
async function launch(exe,label,port){
 const profile=path.join(dir,'profile-'+label);const child=spawn(exe,['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port='+port,'--user-data-dir='+profile,'about:blank'],{windowsHide:true,stdio:'ignore'})
 const base='http://127.0.0.1:'+port;await waitFor(()=>fetch(base+'/json/version').then(r=>r.ok).catch(()=>false));return {child,base,profile}
}
async function stop(browser){try{const v=await fetch(browser.base+'/json/version').then(r=>r.json()),ws=new WebSocket(v.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j});ws.send(JSON.stringify({id:1,method:'Browser.close'}));await new Promise(r=>{ws.onclose=r;setTimeout(r,2000)});ws.close()}catch{};await waitFor(()=>browser.child.exitCode!==null,8000).catch(()=>{})}
async function navigate(c,url){await c.send('Page.navigate',{url:origin+url})}
async function route(c,url){await c.evaluate(`document.querySelector('#app').__vue_app__.config.globalProperties.$router.push(${JSON.stringify(url)})`)}
async function auth(c){return c.evaluate(`import('/src/features/auth/api.js').then(m=>({status:m.session.status,role:m.session.user?.role,token:!!m.session.token}))`)}
async function reload(c){const loaded=new Promise(resolve=>c.on('Page.loadEventFired',resolve));await c.send('Page.reload',{ignoreCache:true});await Promise.race([loaded,pause(15000).then(()=>{throw Error('Reload load event timed out')})])}
async function account(c,role='BUYER'){await c.waitFor(`(async()=>{const {session}=await import('/src/features/auth/api.js');return session.status==='AUTHENTICATED'&&session.user?.role===${JSON.stringify(role)}&&document.querySelector('h1')?.textContent.trim()==='Hồ sơ cá nhân'})()`);assert.equal((await auth(c)).role,role)}
async function login(c,email,remember){await route(c,'/login');await c.waitFor(`!!document.querySelector('#email-input')`);await c.evaluate(`(()=>{for(const [selector,value] of ${JSON.stringify([['#email-input',email],['#password-input',process.env.AUTH_TEST_PASSWORD]])}){const e=document.querySelector(selector);e.value=value;e.dispatchEvent(new Event('input',{bubbles:true}))};const checkbox=document.querySelector('input[type="checkbox"]');if(checkbox.checked!==${remember})checkbox.click();document.querySelector('form').requestSubmit()})()`);await c.waitFor(`location.pathname==='/home'||location.pathname.startsWith('/admin')`);await route(c,'/account')}
async function flags(c,label,days){const r=await c.send('Network.getCookies',{urls:[origin+'/api/v1/auth/refresh']});const cookie=r.cookies.find(x=>x.name==='SMARTPROP_REFRESH');assert.ok(cookie);assert.equal(cookie.httpOnly,true);assert.equal(cookie.sameSite,'Lax');assert.equal(cookie.path,'/api/v1/auth');assert.equal(cookie.secure,false);const ttl=cookie.expires-Date.now()/1000;assert.ok(ttl>days*86400-90&&ttl<=days*86400+20);cookieFlags.push({browser:label,httpOnly:true,sameSite:cookie.sameSite,path:cookie.path,secure:false,maxDays:days});assert.equal(await c.evaluate(`document.cookie.includes('SMARTPROP_REFRESH')`),false);assert.equal(await c.evaluate(`localStorage.getItem('token')===null&&sessionStorage.getItem('refreshToken')===null`),true)}
const binaries=[['Chrome','C:/Program Files/Google/Chrome/Application/chrome.exe',49381],['Edge','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',49382]]
let active=null
try{
 await waitFor(()=>fetch(origin+'/login').then(r=>r.ok).catch(()=>false))
 for(const [label,exe,port] of binaries){
  if(!fs.existsSync(exe))throw Error(label+' browser binary missing')
  active=await launch(exe,label,port);let c=await connect(active.base),extra=null,offline=false;const refreshes=[]
  function observe(page){page.on('Network.requestWillBeSent',e=>{if(e.request.url===origin+'/api/v1/auth/refresh')refreshes.push(page===c?'main':'extra')});return page.send('Network.enable')}
  await observe(c);await c.send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});await navigate(c,'/login');await c.waitFor(`!!document.querySelector('#email-input')`)
  await login(c,process.env.AUTH_TEST_BUYER,true);await account(c)
  await check(label,'real login creates protected cookie and remembered30day session',()=>flags(c,label,30))
  const before=refreshes.length;await reload(c);await account(c);await check(label,'F5 restores BUYER and calls refresh once',async()=>assert.equal(refreshes.length-before,1))
  await route(c,'/favorites');await c.waitFor(`location.pathname==='/favorites'`);await route(c,'/account');await account(c);await check(label,'SPA navigation keeps session',async()=>assert.equal((await auth(c)).status,'AUTHENTICATED'))
  extra=await connect(active.base);await observe(extra);const simultaneous=refreshes.length;await Promise.all([reload(c),navigate(extra,'/account')]);await Promise.all([account(c),account(extra)]);await check(label,'new tab and simultaneous restoration share cookie without replay',async()=>assert.equal(refreshes.length-simultaneous,2))
  await extra.close();extra=null
  const auto=refreshes.length;await c.evaluate(`import('/src/features/auth/api.js').then(async m=>{m.session.token='invalid-access-fixture';await Promise.all(Array.from({length:5},()=>m.api('/users/me')))})`)
  await check(label,'five simultaneous401 requests cause one actual refresh',async()=>assert.equal(refreshes.length-auto,1))
  await c.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/auth/refresh'}]});c.on('Fetch.requestPaused',async e=>{if(offline)await c.send('Fetch.fulfillRequest',{requestId:e.requestId,responseCode:503,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from('{"message":"Synthetic temporary outage"}').toString('base64')});else await c.send('Fetch.continueRequest',{requestId:e.requestId})})
  offline=true;await c.evaluate(`import('/src/features/auth/api.js').then(async m=>{m.session.token='invalid-access-fixture';try{await m.api('/users/me')}catch{};return {status:m.session.status,hasUser:!!m.session.user,hasToken:!!m.session.token}}).then(s=>{if(s.status!=='UNAVAILABLE'||!s.hasUser||!s.hasToken)throw Error('Outage cleared session')})`)
  await c.waitFor(`document.body.textContent.includes('Chưa thể kiểm tra phiên')`);await check(label,'refresh503 preserves identity and shows recovery instead of login',async()=>assert.equal((await auth(c)).status,'UNAVAILABLE'))
  offline=false;await c.evaluate(`document.querySelector('button').click()`);await account(c);await c.send('Fetch.disable');await check(label,'retry after outage restores session without password',async()=>assert.equal((await auth(c)).status,'AUTHENTICATED'))
  await c.close();await stop(active);active=await launch(exe,label,port);c=await connect(active.base);await observe(c);await navigate(c,'/account');await account(c);await check(label,'full browser restart retains remembered login',async()=>assert.equal((await auth(c)).status,'AUTHENTICATED'))
  const screenshot=await c.send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(dir,label.toLowerCase()+'-restored.png'),Buffer.from(screenshot.data,'base64'))
  extra=await connect(active.base);await navigate(extra,'/account');await account(extra);await c.evaluate(`import('/src/features/auth/api.js').then(m=>m.logout())`);await extra.waitFor(`location.pathname==='/login'`);await check(label,'logout clears memory and synchronizes another tab',async()=>assert.equal((await auth(extra)).token,false));await extra.close();extra=null
  await reload(c);await c.waitFor(`location.pathname==='/login'`);await check(label,'logout thenF5 cannot restore revoked cookie',async()=>assert.equal((await auth(c)).status,'UNAUTHENTICATED'))
  await login(c,process.env.AUTH_TEST_BROKER,false);await account(c,'BROKER');await check(label,'BROKER default7day policy survivesF5',async()=>{await flags(c,label,7);await reload(c);await account(c,'BROKER')});
  await check(label,'write401 is renewed safely and one explicit DRAFT is created',async()=>{await c.evaluate(`import('/src/features/auth/api.js').then(async m=>{const before=(await m.api('/users/me/properties')).totalElements;const body={title:'Synthetic persistence retry fixture',propertyType:'APARTMENT',transactionType:'SALE',price:2000000000,currency:'VND',priceUnit:'TOTAL',areaSqm:80,city:'Da Nang',latitude:16.06,longitude:108.22};m.session.token='invalid-access-fixture';let code;try{await m.api('/properties',{method:'POST',body})}catch(e){code=e.code}if(code!=='AUTH_RETRY_REQUIRED'||(await m.api('/users/me/properties')).totalElements!==before)throw Error('Mutation was automatically retried');const result=await m.api('/properties',{method:'POST',body});if(result.property.status!=='DRAFT'||(await m.api('/users/me/properties')).totalElements!==before+1)throw Error('Explicit retry failed')})`)});
  await c.evaluate(`import('/src/features/auth/api.js').then(m=>m.logout())`)
  await login(c,process.env.AUTH_TEST_ADMIN,true);await account(c,'ADMIN');await check(label,'ADMIN ignores remember30days and caps cookie at8hours',()=>flags(c,label,1/3));await reload(c);await account(c,'ADMIN');await check(label,'ADMIN restores correct live role afterF5',async()=>assert.equal((await auth(c)).role,'ADMIN'))
  assert.deepEqual(c.errors,[]);await c.evaluate(`import('/src/features/auth/api.js').then(m=>m.logout())`);await c.close();await stop(active);active=null
 }
 fs.writeFileSync(path.join(dir,'browser-results.json'),JSON.stringify({passed:results.length,results,cookieFlags,backend:'isolated MySQL3307 test application, random HTTP port',productionRequests:0},null,2));console.log('BROWSER_EVIDENCE='+dir)
}catch(e){fs.writeFileSync(path.join(dir,'browser-failure.json'),JSON.stringify({message:e.message,results},null,2));throw e}
finally{if(active)await stop(active);vite.kill();fs.closeSync(viteOut)}
