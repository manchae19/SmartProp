import {areaInput,typeCodes} from './postForm.js'
export const categoryFor=type=>({HOUSE:'Nhà ở',VILLA:'Nhà ở',LAND:'Đất nền',APARTMENT:'Căn hộ chung cư'})[typeCodes[type]]
export function valuationInput(draft,location){
 const propertyType=typeCodes[draft.propertyType],area=areaInput(draft.area)
 if(draft.transactionType!=='Bán')return {reason:'Model hiện chỉ hỗ trợ tin bán.'}
 if(!categoryFor(draft.propertyType))return {reason:'Loại bất động sản này chưa được model hỗ trợ.'}
 if(!area||Number(area)<20||Number(area)>1000)return {reason:'Nhập diện tích từ 20 đến 1000 m² để xem giá tham khảo.'}
 if(!location)return {reason:'Chọn khu vực tham khảo phù hợp với địa chỉ của tin.'}
 const rooms=String(draft.bedrooms??'0');if(propertyType!=='LAND'&&(!/^\d+$/.test(rooms)||Number(rooms)>30))return {reason:'Số phòng ngủ nằm ngoài phạm vi model (0–30; 0 là chưa khai báo).'}
 return {body:{propertyType,transactionType:'SALE',areaSqm:Number(area),locationFeature:location,
  bedrooms:propertyType==='LAND'?null:Number(rooms),title:String(draft.title||''),description:String(draft.description||'')}}
}
// Ignore stale/unmounted requests; result state never has access to the posting draft.
export function createPreviewState(request,state){
 let revision=0,disposed=false
 return {
  invalidate(){revision++;state.result=null;state.error='';state.busy=false},
  dispose(){disposed=true;revision++},
  async preview(body){const current=++revision;state.result=null;state.error='';state.busy=true
   try{const result=await request(body);if(!disposed&&current===revision)state.result=result}
   catch(e){if(!disposed&&current===revision)state.error=e.message||'Giá tham khảo chưa sẵn sàng.'}
   finally{if(!disposed&&current===revision)state.busy=false}
  }
 }
}
export function exactVnd(value){try{return BigInt(value).toLocaleString('vi-VN')+' ₫'}catch{return '—'}}
