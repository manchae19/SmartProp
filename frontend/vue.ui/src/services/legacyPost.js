import {reactive,ref,computed,watch,nextTick} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import {api,session,errorText} from './api.js'
import {validateFiles} from './property.js'
import {postSteps,typeCodes,validatePost,fieldIssue,isPublisher,addressSignature,locationSignature,validCoordinates,buildPostPayload,payloadFromManaged,samePayload} from './postForm.js'

const initial=()=>({transactionType:'Bán',rentUnit:'PER_MONTH',propertyType:'Nhà phố',district:'',city:'Da Nang',ward:'',valuationLocation:'',title:'',area:'',price:'',bedrooms:'',bathrooms:'',address:'',latitude:'',longitude:'',confirmedLocation:'',description:'',contactName:'',phone:'',contact:'',floor:'',block:'',direction:'',selectedAmenities:[],accepted:false})
const cleanState=()=>({busy:false,error:'',notice:'',issues:[],loaded:false,loadError:false,conflict:false,complete:false,localSaved:false,localSaveError:false,lostFiles:0,savedAt:null,uncertainCreate:null,uncertainUpload:null})
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const uncertain=e=>!e.status||e.status>=500||e.status===408
function restoredDraft(value){
 const restored=initial();if(!value||typeof value!=='object')return restored
 for(const name of Object.keys(restored)){
  const item=value[name]
  if(name==='accepted')restored[name]=item===true
  else if(name==='selectedAmenities')restored[name]=Array.isArray(item)?item.filter(v=>typeof v==='string'):[]
  else if(typeof item==='string'||typeof item==='number')restored[name]=String(item)
 }
 return restored
}

// One editor for the existing posting routes. Injected dependencies also allow mock-only verification.
export function createPostEditor({request=api,getActor=()=>session.user,getStorage=()=>globalThis.sessionStorage,urls=globalThis.URL,clock=()=>Date.now()}={}){
 const draft=reactive(initial()),state=reactive(cleanState()),managed=ref(null),images=ref([]),coverKey=ref(''),removed=ref([])
 let actor='',slot='',key='',epoch=0,hydrating=false,serial=0
 const imageCount=computed(()=>images.value.length)
 const dirty=computed(()=>!!managed.value&&(!samePayload(buildPostPayload(draft),payloadFromManaged(managed.value))||removed.value.length>0||images.value.some(e=>!e.server)||JSON.stringify(images.value.map(e=>e.server?.id))!==JSON.stringify(managed.value.property.images.map(e=>e.id))||images.value.find(e=>e.key===coverKey.value)?.server?.id!==managed.value.property.images.find(e=>e.cover)?.id))
 function permitted(){return isPublisher(getActor())&&String(getActor().id)===actor}
 function assertRun(run){if(run!==epoch||!permitted())throw Object.assign(Error('Phiên đăng tin đã thay đổi.'),{stale:true})}
 function checkItem(value){if(!value?.property||!uuid.test(value.property.id)||String(value.ownerId)!==actor)throw Error('Không thể sử dụng tin không thuộc tài khoản hiện tại.');return value}
 async function call(run,p,o){assertRun(run);const result=await request(p,o);assertRun(run);return result}
 function release(entry){if(entry.preview){urls?.revokeObjectURL?.(entry.preview);entry.preview=''}}
 function clearMemory(){images.value.forEach(release);images.value=[];managed.value=null;coverKey.value='';removed.value=[];hydrating=true;Object.assign(draft,initial());hydrating=false;Object.assign(state,cleanState())}
 function bindActor(){const next=isPublisher(getActor())?String(getActor().id):'';if(next!==actor){epoch++;key='';slot='';actor=next;clearMemory()}}
 function persist(){if(hydrating||!key||!permitted()||!state.loaded)return;try{getStorage()?.setItem(key,JSON.stringify({actor,draft:{...draft},managed:managed.value,order:images.value.filter(e=>e.server).map(e=>e.server.id),coverId:images.value.find(e=>e.key===coverKey.value)?.server?.id,removed:removed.value,pendingFileCount:images.value.filter(e=>!e.server).length+state.lostFiles,uncertainCreate:state.uncertainCreate,uncertainUpload:state.uncertainUpload,savedAt:state.savedAt,complete:state.complete}));state.localSaved=!!getStorage();state.localSaveError=false}catch{state.localSaved=false;state.localSaveError=true}}
 function setManaged(value){managed.value=checkItem(value);const byId=new Map(value.property.images.map(i=>[i.id,i]));for(const entry of images.value)if(entry.server&&byId.has(entry.server.id))entry.server=byId.get(entry.server.id);persist()}
 function fill(value){const p=value.property;hydrating=true;Object.assign(draft,initial(),{transactionType:p.transactionType==='SALE'?'Bán':'Cho thuê',rentUnit:p.transactionType==='RENT'?p.priceUnit:'PER_MONTH',propertyType:Object.keys(typeCodes).find(k=>typeCodes[k]===p.propertyType)||'',title:p.title,price:String(p.priceExact??p.price),area:String(p.areaSqmExact??p.areaSqm),bedrooms:p.bedrooms??'',bathrooms:p.bathrooms??'',address:p.address||'',city:p.city||'Da Nang',district:p.district||'',ward:p.ward||'',latitude:p.latitude,longitude:p.longitude,description:p.description||'',contactName:value.contactName||'',phone:value.contactPhone||'',contact:value.contactEmail||'',floor:p.floor||'',block:p.block||'',direction:p.direction||'',selectedAmenities:p.declaredAmenities||[]});draft.confirmedLocation=validCoordinates(p.latitude,p.longitude)?locationSignature(draft):'';hydrating=false}
 function serverImages(value){images.value.forEach(release);images.value=value.property.images.map(i=>({key:i.id,server:i}));coverKey.value=images.value.find(e=>e.server.cover)?.key||images.value[0]?.key||'';removed.value=[]}
 async function initialize(editId){
  bindActor();if(!permitted())return
  const next=editId?String(editId):'new';if(next!=='new'&&!uuid.test(next)){state.loadError=true;state.error='Mã tin không hợp lệ.';return}
  if(state.loaded&&(slot===next||managed.value?.property.id===next)){
   if(slot!==next){const oldKey=key;slot=next;key='smartprop:posting:v2:'+actor+':'+slot;persist();try{getStorage()?.removeItem(oldKey)}catch{}}return
  }
  persist();epoch++;const run=epoch;clearMemory();slot=next;key='smartprop:posting:v2:'+actor+':'+slot
  hydrating=true;draft.contactName=getActor().fullName||'';draft.phone=getActor().phone||'';draft.contact=getActor().email||'';hydrating=false
  let saved;try{saved=JSON.parse(getStorage()?.getItem(key)||'null')}catch{}
  if(saved&&String(saved.actor)===actor){
   hydrating=true;Object.assign(draft,restoredDraft(saved.draft));hydrating=false
   if(saved.managed&&String(saved.managed.ownerId)===actor&&uuid.test(saved.managed.property?.id||'')&&Array.isArray(saved.managed.property.images))managed.value=saved.managed
   state.uncertainCreate=saved.uncertainCreate||null;state.uncertainUpload=saved.uncertainUpload||null;state.lostFiles=Number(saved.pendingFileCount)||0;state.savedAt=saved.savedAt||null;state.complete=!!saved.complete
  }
  state.busy=true
  try{
   const id=next==='new'?managed.value?.property.id:next
   if(id){const fresh=checkItem(await call(run,'/users/me/properties/'+id));const previous=managed.value;managed.value=fresh
    if(!saved||!previous){fill(fresh);serverImages(fresh);state.complete=false}
    else{serverImages(fresh);const byId=new Map(images.value.map(e=>[e.server.id,e]));removed.value=(Array.isArray(saved.removed)?saved.removed:[]).filter(id=>byId.has(id));images.value=(Array.isArray(saved.order)?saved.order:[]).filter(id=>byId.has(id)&&!removed.value.includes(id)).map(id=>byId.get(id));for(const [id,e]of byId)if(!images.value.includes(e)&&!removed.value.includes(id))images.value.push(e);coverKey.value=images.value.find(e=>e.server.id===saved.coverId)?.key||images.value.find(e=>e.server.cover)?.key||images.value[0]?.key||''
     if(previous.property.contentVersion!==fresh.property.contentVersion){state.conflict=true;state.error='Tin trên máy chủ đã thay đổi. Nội dung bạn nhập được giữ; hãy đối chiếu phiên bản mới trước khi lưu.'}
     if(!['PENDING','PUBLISHED'].includes(fresh.property.status))state.complete=false
    }
   }
   assertRun(run);state.loaded=true;if(state.lostFiles)state.notice='Đã khôi phục nội dung trên trình duyệt; '+state.lostFiles+' ảnh chưa tải cần chọn lại.';persist()
  }catch(e){if(!e.stale){state.loadError=true;state.error=errorText(e)}}finally{if(run===epoch)state.busy=false}
 }
 watch(()=>addressSignature(draft),()=>{if(hydrating)return;draft.latitude='';draft.longitude='';draft.confirmedLocation='';persist()},{flush:'sync'})
 watch(draft,()=>{if(!hydrating){persist();if(state.issues.length){const fields=new Set(state.issues.map(i=>i.field));state.issues=validatePost(draft,{imageCount:imageCount.value,requireImages:false}).filter(i=>fields.has(i.field))}}},{deep:true,flush:'sync'})
 function selectLocation(point){if(state.busy||!validCoordinates(point.latitude,point.longitude))return;draft.latitude=Number(point.latitude);draft.longitude=Number(point.longitude);draft.confirmedLocation='';persist()}
 function clearLocation(){if(state.busy)return;draft.latitude='';draft.longitude='';draft.confirmedLocation='';persist()}
 function confirmLocation(){if(state.busy||!String(draft.address).trim()||!validCoordinates(draft.latitude,draft.longitude))return false;draft.confirmedLocation=locationSignature(draft);state.notice='Đã xác nhận ghim cho địa chỉ hiện tại.';persist();return true}
 async function chooseFiles(list){if(state.busy)return;state.busy=true;state.error='';const run=epoch;try{const chosen=Array.from(list);validateFiles(chosen);if(chosen.length+images.value.length>30)throw Error('Tối đa 30 ảnh/tin.');for(const file of chosen)if(typeof globalThis.createImageBitmap==='function'){const bitmap=await createImageBitmap(file);const good=bitmap.width<=12000&&bitmap.height<=12000&&bitmap.width*bitmap.height<=40000000;bitmap.close();if(!good)throw Error('Ảnh tối đa 12000 px mỗi chiều và 40 triệu pixel.')}assertRun(run);for(const file of chosen){const entry={key:'local-'+(++serial),file,preview:urls?.createObjectURL?.(file)||''};images.value.push(entry);if(!coverKey.value)coverKey.value=entry.key}state.notice='Ảnh mới được giữ trong tab này; bấm Lưu nháp để tải lên tài khoản.';state.lostFiles=0;persist()}catch(e){if(!e.stale){state.error=e.message||'Không đọc được ảnh. Hãy chọn JPEG/PNG hợp lệ.';state.issues=[fieldIssue('images',state.error)]}}finally{if(run===epoch)state.busy=false}}
 function removeImage(keyValue){if(state.busy)return;const i=images.value.findIndex(e=>e.key===keyValue);if(i<0)return;const [entry]=images.value.splice(i,1);if(entry.server)removed.value.push(entry.server.id);release(entry);if(coverKey.value===entry.key)coverKey.value=images.value[0]?.key||'';persist()}
 function moveImage(keyValue,offset){if(state.busy)return;const i=images.value.findIndex(e=>e.key===keyValue),j=i+offset;if(i<0||j<0||j>=images.value.length)return;[images.value[i],images.value[j]]=[images.value[j],images.value[i]];persist()}
 function chooseCover(keyValue){if(!state.busy&&images.value.some(e=>e.key===keyValue)){coverKey.value=keyValue;persist()}}
 async function mine(run){const items=[];for(let page=0;page<50;page++){const result=await call(run,'/users/me/properties?size=100&page='+page);items.push(...result.items);if(page+1>=result.totalPages)return items}throw Error('Danh sách quá lớn để đối chiếu an toàn. Vui lòng kiểm tra Tin đăng của tôi.')}
 async function resolveCreate(run){const pending=state.uncertainCreate;if(!pending)return null;const matches=(await mine(run)).filter(i=>String(i.ownerId)===actor&&!pending.beforeIds.includes(i.property.id)&&samePayload(pending.body,payloadFromManaged(i)));if(matches.length!==1)throw Error('Chưa xác định được kết quả tạo nháp. Nội dung vẫn được giữ. Kiểm tra Tin đăng của tôi rồi bấm “Đối chiếu kết quả”; hệ thống chưa tạo thêm tin để tránh trùng.');const value=checkItem(matches[0]);setManaged(value);state.uncertainCreate=null;persist();return value}
 async function current(run){return checkItem(await call(run,'/users/me/properties/'+managed.value.property.id))}
 async function mutate(run,p,options,accept){try{return checkItem(await call(run,p,options))}catch(e){if(!uncertain(e))throw e;try{const fresh=await current(run);if(await accept(fresh))return fresh;if(fresh.property.contentVersion!==managed.value.property.contentVersion)state.conflict=true}catch(check){if(check.stale)throw check}throw e}}
 async function digest(blob){return Array.from(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256',await blob.arrayBuffer())),v=>v.toString(16).padStart(2,'0')).join('')}
 async function resolveUpload(run){const pending=state.uncertainUpload;if(!pending)return;const fresh=await current(run);const candidates=fresh.property.images.filter(i=>!pending.beforeIds.includes(i.id));const found=[];for(const image of candidates){const blob=await call(run,image.url.replace(/^\/api\/v1/,''),{responseType:'blob'});if(await digest(blob)===pending.hash)found.push(image)}if(found.length!==1)throw Error('Chưa xác nhận được ảnh tải lên. Hãy đối chiếu kết quả hoặc kiểm tra tin trên tài khoản; ảnh trong form được giữ và chưa tải lặp.');const entry=images.value.find(e=>e.key===pending.key);if(entry){entry.server=found[0];entry.file=null;release(entry)}else if(!images.value.some(e=>e.server?.id===found[0].id)){images.value.push({key:found[0].id,server:found[0]});state.lostFiles=Math.max(0,state.lostFiles-1)}setManaged(fresh);state.uncertainUpload=null;persist()}
 async function save(submit=false){
  if(state.busy||state.complete)return false
  if(!permitted()||!state.loaded||state.loadError){state.error='Không có quyền hoặc chưa tải được tin. Nội dung form được giữ.';return false}
  state.issues=validatePost(draft,{imageCount:imageCount.value,requireImages:submit});if(submit&&!draft.accepted)state.issues.push(fieldIssue('consent','Xác nhận quyền đăng và tính chính xác của thông tin trước khi gửi duyệt.'))
  if(state.issues.length){state.notice='Nội dung được giữ trên trình duyệt; chưa lưu nháp tài khoản.';return false}
  if(state.conflict){state.error='Hãy đối chiếu phiên bản máy chủ trước khi lưu lại.';return false}
  state.busy=true;state.error='';state.notice='';const run=epoch,body=buildPostPayload(draft)
  try{
   if(state.uncertainCreate)await resolveCreate(run)
   if(state.uncertainUpload)await resolveUpload(run)
   if(!managed.value){const before=await mine(run);state.uncertainCreate={body,beforeIds:before.map(i=>i.property.id)};persist();try{setManaged(await call(run,'/properties',{method:'POST',body}));state.uncertainCreate=null;persist()}catch(e){if(e.stale)throw e;if(!uncertain(e)){state.uncertainCreate=null;persist();throw e}await resolveCreate(run)}}
   else if(!samePayload(body,payloadFromManaged(managed.value))||(!submit&&managed.value.property.status!=='DRAFT')){const p=managed.value.property;setManaged(await mutate(run,'/properties/'+p.id+'?expectedVersion='+p.contentVersion,{method:'PATCH',body},fresh=>fresh.property.status==='DRAFT'&&samePayload(body,payloadFromManaged(fresh))))}
   while(removed.value.length){const id=removed.value[0],p=managed.value.property;if(p.images.some(i=>i.id===id))setManaged(await mutate(run,'/properties/'+p.id+'/images/'+id+'?expectedVersion='+p.contentVersion,{method:'DELETE'},fresh=>!fresh.property.images.some(i=>i.id===id)));removed.value.shift();persist()}
   for(const entry of images.value.filter(e=>!e.server)){
    const p=managed.value.property,hash=await digest(entry.file);assertRun(run);const data=new FormData();data.append('file',entry.file);state.uncertainUpload={key:entry.key,hash,beforeIds:p.images.map(i=>i.id)};persist()
    try{const result=checkItem(await call(run,'/properties/'+p.id+'/images?expectedVersion='+p.contentVersion,{method:'POST',body:data}));const fresh=result.property.images.filter(i=>!p.images.some(old=>old.id===i.id));if(fresh.length!==1)throw Error('Không xác định được ảnh vừa tải.');entry.server=fresh[0];entry.file=null;release(entry);setManaged(result);state.uncertainUpload=null;persist()}
    catch(e){if(e.stale)throw e;if(!uncertain(e)){state.uncertainUpload=null;persist();throw e}await resolveUpload(run)}
   }
   const ids=images.value.map(e=>e.server.id)
   if(ids.length&&JSON.stringify(ids)!==JSON.stringify(managed.value.property.images.map(i=>i.id))){const p=managed.value.property;setManaged(await mutate(run,'/properties/'+p.id+'/images/order',{method:'PUT',body:{expectedVersion:p.contentVersion,imageIds:ids}},fresh=>JSON.stringify(fresh.property.images.map(i=>i.id))===JSON.stringify(ids)))}
   const cover=images.value.find(e=>e.key===coverKey.value)?.server
   if(cover&&!managed.value.property.images.find(i=>i.id===cover.id)?.cover){const p=managed.value.property;setManaged(await mutate(run,'/properties/'+p.id+'/images/'+cover.id,{method:'PATCH',body:{expectedVersion:p.contentVersion,cover:true}},fresh=>fresh.property.images.some(i=>i.id===cover.id&&i.cover)))}
   if(submit){const p=managed.value.property;if(!['PENDING','PUBLISHED'].includes(p.status))setManaged(await mutate(run,'/properties/'+p.id+'/submit',{method:'POST',body:{expectedVersion:p.contentVersion}},fresh=>['PENDING','PUBLISHED'].includes(fresh.property.status)));state.complete=true;state.notice='Đã gửi tin để quản trị viên kiểm duyệt.'}
   else state.notice='Đã lưu đầy đủ nội dung và ảnh hiện tại vào nháp tài khoản.'
   assertRun(run);state.savedAt=clock();persist();return true
  }catch(e){if(!e.stale){if(e.status===409)state.conflict=true;state.error=errorText(e);if(e.fields)state.issues=Object.entries(e.fields).map(([field,message])=>fieldIssue(field,message));persist()}return false}finally{if(run===epoch)state.busy=false}
 }
 async function checkResult(){if(state.busy||!permitted())return;state.busy=true;state.error='';const run=epoch;try{if(state.uncertainCreate)await resolveCreate(run);if(state.uncertainUpload)await resolveUpload(run);state.notice='Đã đối chiếu kết quả. Kiểm tra lại thông tin rồi bấm Lưu nháp hoặc Gửi duyệt.'}catch(e){if(!e.stale)state.error=errorText(e)}finally{if(run===epoch)state.busy=false}}
 async function reviewVersion(){if(state.busy||!managed.value)return;state.busy=true;const run=epoch;try{const fresh=await current(run);const old=managed.value.property.images.map(i=>i.id),next=fresh.property.images.map(i=>i.id);if(JSON.stringify(old)!==JSON.stringify(next)){state.error='Ảnh trên máy chủ đã thay đổi. Hãy mở tin tài khoản để đối chiếu; nội dung form vẫn được giữ.';return}setManaged(fresh);state.conflict=false;state.error='';state.notice='Đã lấy phiên bản mới, giữ nội dung bạn nhập. Kiểm tra lại trước khi lưu đè thay đổi của tin.'}catch(e){if(!e.stale)state.error=errorText(e)}finally{if(run===epoch)state.busy=false}}
 function reset(){if(state.busy)return;try{if(key)getStorage()?.removeItem(key)}catch{}epoch++;key='';slot='';clearMemory()}
 function editAgain(){state.complete=false;draft.accepted=false;persist()}
 return {draft,state,managed,images,coverKey,imageCount,dirty,bindActor,initialize,persist,selectLocation,clearLocation,confirmLocation,chooseFiles,removeImage,moveImage,chooseCover,save,checkResult,reviewVersion,reset,editAgain}
}

const editor=createPostEditor()
watch(()=>[session.user?.id,session.user?.role,session.user?.status],()=>editor.bindActor(),{flush:'sync'})
export function usePost(){
 const router=useRouter(),route=useRoute()
 watch(()=>[route.query.edit,session.user?.id],()=>editor.initialize(route.query.edit),{immediate:true})
 async function focusIssue(){await nextTick();if(route.hash.startsWith('#post-'))document.getElementById(route.hash.slice(1))?.focus({preventScroll:true})}
 watch(()=>route.hash,focusIssue,{immediate:true})
 async function goStep(step,field){if(editor.state.busy)return;const target=postSteps[step-1];if(target){await router.push({path:target.path,query:route.query,hash:field?'#post-'+field:''});await focusIssue()}}
 async function goNext(){const current=postSteps.find(s=>s.path===route.path)?.step||1;editor.state.issues=validatePost(editor.draft,{steps:Array.from({length:current},(_,i)=>i+1),imageCount:editor.imageCount.value});if(editor.state.issues.length){const first=editor.state.issues[0];await goStep(first.step,first.field)}else await goStep(Math.min(current+1,3))}
 async function saveDraft(submit=false){const success=await editor.save(submit);if(editor.managed.value&&route.query.edit!==editor.managed.value.property.id)await router.replace({path:route.path,query:{...route.query,edit:editor.managed.value.property.id},hash:route.hash});if(editor.state.issues.length){const first=editor.state.issues[0];await goStep(first.step,first.field)}return success}
 async function startNew(){editor.reset();await router.replace('/post');await editor.initialize()}
 return {...editor,goStep,goNext,saveDraft,startNew}
}
