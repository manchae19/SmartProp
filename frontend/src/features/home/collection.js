import {listingStatus} from '../property/property.js'
import {adapt,money,reasons,date} from '../../lib/legacy.js'
// Presentation fields for the team's collection layouts; never substitute demo listings.
export function collectionProperty(input,index=0){
 const a=adapt(input),p=a.raw,expired=listingStatus(p)==='EXPIRED';
 return {...a,name:a.title,price:a.priceValue,priceText:money(p),area:p.areaSqm??null,
 beds:p.bedrooms??0,baths:p.bathrooms??0,district:p.district||'',
 bedrooms:p.bedrooms??0,bathrooms:p.bathrooms??0,address:a.location,
 legal:'Chưa có thông tin',status:expired?'expired':a.status,statusText:expired?'Hết hạn':a.statusText,
 label:a.type,number:String(index+1).padStart(2,'0'),savedOrder:index,
 saved:'Đã lưu',priceUnit:'',views:null,saves:null};
}
export function collectionReport(r){return {...r,raw:r,title:'Báo cáo tin '+r.propertyId,
 location:'',reason:reasons[r.reasonCode]||r.reasonCode,sentAt:date(r.createdAt),
 status:r.status==='RESOLVED'?'resolved':r.status==='REJECTED'?'rejected':'processing',
 statusLabel:({OPEN:'Mới gửi',PROCESSING:'Đang xử lý',RESOLVED:'Đã xử lý',REJECTED:'Từ chối'})[r.status]||r.status,
 update:date(r.updatedAt),result:r.resolutionNote||'',image:null};}
