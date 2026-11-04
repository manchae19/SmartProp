import test from 'node:test'
import assert from 'node:assert/strict'
import {canApply,reviewActions,applicationPayload,applicationStatuses,canRequestBroker,brokerErrorKind,brokerErrorText} from '../src/features/broker/brokerApplication.js'
import {createHttpClient} from '../src/lib/httpClient.js'
const buyer={id:7,role:'BUYER',status:'ACTIVE'}
test('only eligible buyer application states permit submission',()=>{
  for(const status of ['NOT_REQUESTED','REJECTED','NEEDS_INFORMATION'])assert.equal(canApply({status,canPublish:false},buyer),true)
  for(const status of ['PENDING','APPROVED','SUSPENDED'])assert.equal(canApply({status,canPublish:false},buyer),false)
  assert.equal(canApply(null,buyer),false);assert.equal(canApply({status:'NOT_REQUESTED',canPublish:true},buyer),false)
})
test('admin actions never expose arbitrary role changes',()=>{
  assert.deepEqual(reviewActions('PENDING'),['APPROVE','REJECT','REQUEST_INFORMATION'])
  assert.deepEqual(reviewActions('APPROVED'),['SUSPEND']);assert.deepEqual(reviewActions('SUSPENDED'),['APPROVE']);assert.deepEqual(reviewActions('REJECTED'),[])
})
test('payload trims strings keeps consent explicit and uses latest application version',()=>{
  const form={applicantType:'AGENT',displayName:' Unit ',contactPhone:' 0901234567 ',operatingArea:' Hải Châu ',requestMessage:' Request ',responsibilityAccepted:true}
  const body=applicationPayload(form,{status:'NEEDS_INFORMATION',canPublish:false,application:{contentVersion:9}},buyer)
  assert.equal(body.expectedVersion,9);assert.equal(body.displayName,'Unit');assert.equal(body.responsibilityAccepted,true);assert.equal(body.role,undefined)
  assert.equal(applicationPayload(form,{status:'NOT_REQUESTED',canPublish:false},buyer).expectedVersion,undefined)
  assert.throws(()=>applicationPayload(form,{status:'PENDING',canPublish:false},buyer))
})
test('all workflow states have clear labels including information request and suspension',()=>{
  for(const status of ['NOT_REQUESTED','PENDING','APPROVED','REJECTED','NEEDS_INFORMATION','SUSPENDED'])assert.ok(applicationStatuses[status])
})
test('only ACTIVE BUYER can request even when application payload claims no publish permission',()=>{
  const state={status:'NOT_REQUESTED',canPublish:false}
  assert.equal(canRequestBroker(buyer),true)
  for(const user of [null,{}, {...buyer,id:null},{...buyer,role:'ADMIN'},{...buyer,role:'BROKER'},{...buyer,status:'LOCKED'}]){
    assert.equal(canRequestBroker(user),false);assert.equal(canApply(state,user),false)
    assert.throws(()=>applicationPayload({},state,user))
  }
})
for(const [status,code,kind] of [[400,'VALIDATION_ERROR','validation'],[403,'FORBIDDEN','forbidden'],[404,'NOT_FOUND','not-found'],[409,'CONFLICT','conflict'],[422,'VALIDATION_ERROR','validation'],[500,'INTERNAL_ERROR','server'],[503,'FEATURE_DISABLED','disabled'],[503,'FEATURE_UNAVAILABLE','unavailable']]){
  test(`HTTP ${status} ${code} preserves transport status and has distinct broker error`,async()=>{
    const client=createHttpClient({baseUrl:'http://mock.invalid/api/v1',session:{token:'test-fixture'},fetcher:async()=>new Response(JSON.stringify({code,message:'PRIVATE_INTERNAL_FIXTURE',fields:{contactPhone:'bad'}}),{status,headers:{'Content-Type':'application/json'}})})
    const error=await client.request('/users/me/broker-application').then(()=>assert.fail('Expected failure'),e=>e)
    assert.equal(error.status,status);assert.equal(error.code,code);assert.equal(brokerErrorKind(error),kind)
    const text=brokerErrorText(error);assert.ok(text.includes('HTTP '+status));assert.equal(text.includes('PRIVATE_INTERNAL_FIXTURE'),false)
    if(kind==='validation')assert.ok(text.includes('Số điện thoại'))
    if(kind==='disabled')assert.ok(text.includes('FEATURE_DISABLED'))
  })
}
test('login and profile client regression preserves buyer role and authenticated GET',async()=>{
  const calls=[],session={token:null,user:null}
  const client=createHttpClient({baseUrl:'http://mock.invalid/api/v1',session,fetcher:async(url,opts)=>{calls.push({url,opts});return new Response(JSON.stringify(url.endsWith('/auth/login')?{accessToken:'fixture-session',user:buyer}:buyer),{status:200})}})
  const logged=await client.login({email:'fixture@example.invalid',password:'synthetic-input'})
  session.token=logged.accessToken;session.user=logged.user
  assert.equal((await client.request('/users/me')).role,'BUYER')
  assert.equal(calls[0].opts.headers.Authorization,undefined);assert.equal(calls[1].opts.headers.Authorization,'Bearer fixture-session')
  assert.equal(calls[1].opts.method,'GET')
})
