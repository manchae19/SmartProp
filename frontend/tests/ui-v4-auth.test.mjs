import test from 'node:test'
import assert from 'node:assert/strict'
import {createHttpClient} from '../src/lib/httpClient.js'
import {safeLoginDestination} from '../src/features/auth/authNavigation.js'
import {validateAvatar} from '../src/features/account/avatar.js'

test('login destination only uses existing local app routes',()=>{
 for(const next of ['https://evil.invalid','//evil.invalid','/\\evil.invalid','/auth/google/complete','/login',' /account','/not-a-route'])assert.equal(safeLoginDestination(next,'BUYER'),'/home')
 assert.equal(safeLoginDestination('/valuation','BUYER'),'/valuation');assert.equal(safeLoginDestination('/account/messages','BUYER'),'/account/messages');assert.equal(safeLoginDestination(undefined,'ADMIN'),'/admin')
})
test('Google completes through CSRF-protected POST and stores access token only in session memory',async()=>{
 const session={token:null,user:null,status:'INITIALIZING'},calls=[]
 const fetcher=async(url,options)=>{calls.push({url,options});return new Response(JSON.stringify(url.endsWith('/csrf')?{token:'synthetic-csrf',headerName:'X-CSRF-TOKEN'}:{accessToken:'synthetic-access-only',user:{id:44,role:'BUYER'}}),{status:200,headers:{'Content-Type':'application/json'}})}
 const client=createHttpClient({baseUrl:'/api/v1',session,refreshEnabled:true,fetcher});await client.google()
 assert.deepEqual(calls.map(c=>[c.url,c.options.method]),[['/api/v1/auth/csrf','GET'],['/api/v1/auth/oauth2/complete','POST']]);assert.equal(calls[1].options.headers['X-CSRF-TOKEN'],'synthetic-csrf');assert.ok(calls.every(c=>c.options.credentials==='include'));assert.ok(calls.every(c=>!c.url.includes('synthetic-access')));assert.equal(session.token,'synthetic-access-only');assert.equal(session.status,'AUTHENTICATED')
})
test('ambiguous Google completion is not retried or turned into a successful login',async()=>{
 const calls=[],session={token:null,user:null};const client=createHttpClient({baseUrl:'/api/v1',session,refreshEnabled:true,fetcher:async(url)=>{calls.push(url);if(url.endsWith('/csrf'))return new Response(JSON.stringify({token:'csrf',headerName:'X-CSRF-TOKEN'}));throw Error('offline')}})
 await assert.rejects(()=>client.google());assert.equal(calls.filter(p=>p.endsWith('/complete')).length,1);assert.equal(session.token,null)
})

test('Google completion replaces an existing different account and never sends its bearer token',async()=>{
 const session={token:'previous-account-access',user:{id:1,role:'ADMIN'},status:'AUTHENTICATED'},calls=[]
 const client=createHttpClient({baseUrl:'/api/v1',session,refreshEnabled:true,fetcher:async(url,options)=>{calls.push({url,options});return new Response(JSON.stringify(url.endsWith('/csrf')?{token:'csrf',headerName:'X-CSRF-TOKEN'}:{accessToken:'new-google-account-access',user:{id:45,role:'BUYER'}}))}})
 await client.google();assert.equal(session.user.id,45);assert.equal(session.user.role,'BUYER');assert.equal(session.token,'new-google-account-access');assert.equal(calls.find(c=>c.url.endsWith('/complete')).options.headers.Authorization,undefined)
})
test('avatar validation rejects mismatched signatures and oversize uploads before preview',async()=>{
 await assert.rejects(()=>validateAvatar(new File(['<svg/>'],'image.png',{type:'image/png'})),/định dạng/)
 await assert.rejects(()=>validateAvatar(new File(['<svg/>'],'image.svg',{type:'image/svg+xml'})),/JPG/)
 await assert.rejects(()=>validateAvatar(new File([new Uint8Array(5*1024*1024+1)],'big.png',{type:'image/png'})),/5 MB/)
})
test('decoded avatar dimensions are checked and preview bitmap resources are released',async()=>{
 const original=globalThis.createImageBitmap;let closed=0;const file=new File([new Uint8Array([137,80,78,71,13,10,26,10])],'avatar.png',{type:'image/png'})
 try{globalThis.createImageBitmap=async()=>({width:128,height:128,close(){closed++}});await validateAvatar(file);assert.equal(closed,1);globalThis.createImageBitmap=async()=>({width:6000,height:128,close(){closed++}});await assert.rejects(()=>validateAvatar(file),/4096/);assert.equal(closed,2)}finally{globalThis.createImageBitmap=original}
})
