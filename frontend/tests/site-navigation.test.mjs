import test from 'node:test'
import assert from 'node:assert/strict'
import { siteNavigation, activeNavigation, canPublish, usesPageLayout, homeSectionId, navigationOffset } from '../src/lib/siteNavigation.js'
import { isPublisher } from '../src/features/property/postForm.js'
test('navigation preserves property filters and keeps project queries independent',()=>{
  const filters={keyword:'nhà',transactionType:'RENT',district:'Sơn Trà',propertyType:'APARTMENT',minPrice:'12000000',minArea:'30',bedrooms:'2'}
  const links=siteNavigation(filters)
  for(const key of ['home','properties','gis'])assert.deepEqual(links.find(link=>link.key===key).to.query,filters)
  assert.deepEqual(links.find(link=>link.key==='projects').to,{path:'/projects'})
})
test('active route and home section resolve to one primary item',()=>{
  for(const [path,hash,key]of [['/home','','home'],['/home','#account','home'],['/home','#lifestyle','home'],['/listings','','properties'],['/listing/uuid','','properties'],['/map','','gis'],['/projects/uuid','','projects'],['/home','#market','market'],['/valuation','','tools'],['/home','#valuation','home'],['/home','#properties','properties']]){
    const selected=siteNavigation().filter(link=>activeNavigation(link.key,{path,hash})).map(link=>link.key)
    assert.deepEqual(selected,[key])
  }
})
test('publisher navigation reuses existing ACTIVE role policy, without elevating BUYER',()=>{
  assert.equal(canPublish,isPublisher)
  for(const role of ['BROKER','ADMIN'])assert.equal(canPublish({id:'uuid',role,status:'ACTIVE'}),true)
  for(const user of [null,{id:'uuid',role:'BUYER',status:'ACTIVE'},{id:'uuid',role:'BROKER',status:'LOCKED'},{role:'ADMIN',status:'ACTIVE'}])assert.equal(canPublish(user),false)
})
test('all public and account pages use one layout; login/reset/admin retain independent layout',()=>{
  for(const path of ['/home','/listings','/map','/listing/uuid','/projects','/projects/uuid','/account','/account/messages','/favorites','/post','/verify-email'])assert.equal(usesPageLayout(path),true)
  for(const path of ['/login','/register','/reset-password','/admin','/admin/projects'])assert.equal(usesPageLayout(path),false)
})
test('search anchors resolve and removed financial anchors have no target',()=>{
  assert.equal(homeSectionId('#search'),'properties');for(const hash of ['#finance','#valuation','#investment'])assert.equal(homeSectionId(hash),null)
  for(const name of ['home','properties','gis','lifestyle','market','projects'])assert.equal(homeSectionId('#'+name),name)
  assert.equal(homeSectionId('#bad[selector'),null);assert.equal(homeSectionId(''),null)
})
test('navigation helper can be imported without a document in unit tests',()=>assert.equal(navigationOffset(),0))
