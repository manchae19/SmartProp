import test from 'node:test'
import assert from 'node:assert/strict'
import { nearbyPath, filteredPlaces, distanceMeters, validPoint } from '../src/features/map/nearbyExplorer.js'
import { requestNearby } from '../src/features/map/nearbyRequest.js'
const id = 'a0000000-0000-0000-0000-000000000001', origin = { latitude: 16.06, longitude: 108.23 }
test('nearby request validates UUID radius and allowlisted categories', () => {
  assert.equal(nearbyPath('bad',1000,['park']),null); assert.equal(nearbyPath(id,999,['park']),null);assert.equal(nearbyPath(id,1000,['anything']),null)
  assert.match(nearbyPath(id,1000,['health','park']),/radius=1000&categories=health%2Cpark/)
})
test('unknown location never becomes a zero coordinate', () => { for (const p of [{latitude:null,longitude:null},{latitude:'',longitude:108},{}]) assert.equal(!!validPoint(p),false) })
test('only selected categories inside exact radius remain; distances recalculated', () => {
  const a={id:'a',name:'School',latitude:16.061,longitude:108.23,category:'education',distanceMeters:999999}
  const items=[a,a,{...a,id:'b',latitude:16.2},{...a,id:'c',category:'health'},{...a,id:'d',latitude:null}]
  const result=filteredPlaces(items,origin,500,['education']);assert.equal(result.length,1);assert.ok(result[0].distanceMeters>100&&result[0].distanceMeters<120)
  assert.deepEqual(filteredPlaces(items,null,500,['education']),[]);assert.equal(distanceMeters(origin,origin),0)
})
test('public nearby requests send no credentials or authorization', async () => {
  const value=await requestNearby('/properties/'+id+'/nearby',{fetcher:async(url,options)=>{assert.equal(options.credentials,'omit');assert.equal(options.headers.Authorization,undefined);return new Response(JSON.stringify({propertyId:id,items:[]}))}})
  assert.equal(value.propertyId,id)
})
test('quota retains HTTP status and retry-after; no implicit retry', async () => {
 let calls=0;await assert.rejects(requestNearby('/x',{fetcher:async()=>{calls++;return new Response(JSON.stringify({code:'RATE_LIMITED'}),{status:429,headers:{'Retry-After':'35'}})}}),e=>e.status===429&&e.retryAfter===35);assert.equal(calls,1)
})
test('bounded timeout and caller cancellation remain distinct',async()=>{
 const fetcher=(_url,{signal})=>new Promise((_resolve,reject)=>signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')),{once:true}))
 await assert.rejects(requestNearby('/x',{fetcher,timeoutMs:5}),e=>e.code==='NEARBY_TIMEOUT')
 const controller=new AbortController(),run=requestNearby('/x',{fetcher,signal:controller.signal});controller.abort();await assert.rejects(run,e=>e.name==='AbortError')
})
