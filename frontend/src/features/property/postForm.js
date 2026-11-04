export const postSteps = [
  {step:1,path:'/post',label:'Thông tin & giá'},
  {step:2,path:'/post/step-2',label:'Ảnh & vị trí'},
  {step:3,path:'/post/step-3',label:'Mô tả & liên hệ'},
]
export const typeCodes={'Nhà phố':'HOUSE','Căn hộ chung cư':'APARTMENT','Căn hộ':'APARTMENT','Đất nền':'LAND','Biệt thự':'VILLA','Phòng trọ':'ROOM','Kho / Mặt bằng':'COMMERCIAL'}
export const propertyOptions=[{label:'Nhà phố',value:'Nhà phố'},{label:'Căn hộ',value:'Căn hộ chung cư'},{label:'Đất nền',value:'Đất nền'},{label:'Biệt thự',value:'Biệt thự'},{label:'Phòng trọ',value:'Phòng trọ'},{label:'Kho / Mặt bằng',value:'Kho / Mặt bằng'}]
export const hasRooms=type=>typeCodes[type]!=='LAND'
export const isPublisher=user=>!!user?.id&&user.status==='ACTIVE'&&['BROKER','ADMIN'].includes(user.role)
export function decimalInput(raw,{units=false,maxInteger=10,positive=false}={}) {
  let text=String(raw??'').trim().toLowerCase();if(!text||text.length>100)return null
  let power=0
  if(units){text=text.replace(/\s*(?:vnđ|vnd|đồng|₫|đ)\s*$/u,'').trim();const m=text.match(/\s*(tỷ|tỉ|ty|triệu|trieu|nghìn|nghin|ngàn|ngan)\s*$/u);if(m){power=/^(tỷ|tỉ|ty)$/.test(m[1])?9:/^(triệu|trieu)$/.test(m[1])?6:3;text=text.slice(0,m.index).trim()}}
  text=text.replace(/\s/g,'');if(!/^\d[\d.,]*$/.test(text))return null
  if(text.includes('.')&&text.includes(',')){const decimal=text.lastIndexOf('.')>text.lastIndexOf(',')?'.':',';const group=decimal==='.'?',':'.';const parts=text.split(decimal);if(parts.length!==2||!new RegExp('^\\d{1,3}(?:\\'+group+'\\d{3})+$').test(parts[0])||!/^\d+$/.test(parts[1]))return null;text=parts[0].split(group).join('')+'.'+parts[1]}
  else if(/^\d{1,3}(?:[.,]\d{3})+$/.test(text))text=text.replace(/[.,]/g,'')
  else text=text.replace(',','.')
  if(!/^\d+(?:\.\d+)?$/.test(text))return null
  const [whole,fraction='']=text.split('.');const digits=BigInt(whole+fraction);const shift=power+2-fraction.length
  let cents;if(shift>=0)cents=digits*10n**BigInt(shift);else{const divisor=10n**BigInt(-shift);if(digits%divisor!==0n)return null;cents=digits/divisor}
  if((positive&&cents===0n)||cents>=10n**BigInt(maxInteger+2))return null
  const integer=cents/100n,tail=(cents%100n).toString().padStart(2,'0').replace(/0+$/,'');return integer.toString()+(tail?'.'+tail:'')
}
export const priceInput=raw=>decimalInput(raw,{units:true,maxInteger:16})
export const areaInput=raw=>decimalInput(raw,{positive:true,maxInteger:10})
export function validCoordinates(latitude,longitude){return latitude!==''&&latitude!=null&&longitude!==''&&longitude!=null&&Number.isFinite(Number(latitude))&&Number.isFinite(Number(longitude))&&Number(latitude)>=-90&&Number(latitude)<=90&&Number(longitude)>-180&&Number(longitude)<=180}

export function formatDecimal(value){if(value==null)return '—';const [whole,part]=String(value).split('.');return whole.replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(part?','+part:'')}
export function addressSignature(draft){return JSON.stringify(['address','city','district','ward'].map(k=>String(draft[k]||'')))}
export function locationSignature(draft){return JSON.stringify([addressSignature(draft),Number(draft.latitude),Number(draft.longitude)])}
export function locationConfirmed(draft){return validCoordinates(draft.latitude,draft.longitude)&&draft.confirmedLocation===locationSignature(draft)}
const meta={propertyType:[1,'Loại bất động sản'],transactionType:[1,'Nhu cầu'],title:[1,'Tiêu đề'],price:[1,'Giá'],priceUnit:[1,'Đơn vị giá'],area:[1,'Diện tích'],areaSqm:[1,'Diện tích'],bedrooms:[1,'Phòng ngủ'],bathrooms:[1,'Phòng tắm'],address:[2,'Địa chỉ'],city:[2,'Thành phố'],district:[2,'Quận/huyện'],ward:[2,'Phường/xã'],latitude:[2,'Vị trí'],longitude:[2,'Vị trí'],location:[2,'Vị trí'],images:[2,'Ảnh tin đăng'],description:[3,'Mô tả'],contactName:[3,'Tên liên hệ'],contactPhone:[3,'Số điện thoại'],phone:[3,'Số điện thoại'],contactEmail:[3,'Email liên hệ'],contact:[3,'Email liên hệ'],consent:[3,'Xác nhận đăng tin'],floor:[3,'Thông tin tầng'],block:[3,'Tòa / block'],direction:[3,'Hướng nhà'],declaredAmenities:[3,'Tiện ích']}
export function fieldIssue(field,message){const [step,label]=meta[field]||[3,'Thông tin tin đăng'];return {field:({areaSqm:'area',latitude:'location',longitude:'location',contactPhone:'phone',contactEmail:'contact'})[field]||field,step,label,message}}
export function validatePost(draft,{steps=[1,2,3],imageCount=0,requireImages=false}={}){
  const issues=[],add=(field,message)=>issues.push(fieldIssue(field,message))
  if(steps.includes(1)){
    if(!typeCodes[draft.propertyType])add('propertyType','Chọn loại bất động sản hợp lệ.')
    if(!['Bán','Cho thuê'].includes(draft.transactionType))add('transactionType','Chọn Bán hoặc Cho thuê.')
    if(!String(draft.title||'').trim()||String(draft.title).length>255)add('title','Nhập tiêu đề từ 1 đến 255 ký tự.')
    if(priceInput(draft.price)===null)add('price','Nhập giá VND hợp lệ, ví dụ 2,5 tỷ hoặc 12.000.000; tối đa 2 số thập phân.')
    if(draft.transactionType==='Cho thuê'&&!['PER_MONTH','PER_YEAR','PER_DAY','TOTAL'].includes(draft.rentUnit))add('priceUnit','Chọn đơn vị giá thuê.')
    if(areaInput(draft.area)===null)add('area','Diện tích phải lớn hơn 0, tối đa 2 số thập phân; ví dụ 86,3 m².')
    if(hasRooms(draft.propertyType))for(const field of ['bedrooms','bathrooms'])if(draft[field]!==''&&draft[field]!=null&&(!/^\d+$/.test(String(draft[field]))||Number(draft[field])>32767))add(field,'Nhập số nguyên từ 0 đến 32767 hoặc để trống.')
  }
  if(steps.includes(2)){
    if(String(draft.address||'').length>4000)add('address','Địa chỉ tối đa 4000 ký tự.')
    if(!String(draft.city||'').trim()||String(draft.city).length>100)add('city','Nhập thành phố, tối đa 100 ký tự.')
    for(const field of ['district','ward'])if(String(draft[field]||'').length>100)add(field,'Tối đa 100 ký tự.')
    if(!locationConfirmed(draft))add('location','Chọn ghim và bấm “Xác nhận vị trí”. Đổi địa chỉ cần chọn và xác nhận lại; chưa thể lưu nháp tài khoản nếu thiếu vị trí.')
    if(requireImages&&imageCount<1)add('images','Thêm ít nhất một ảnh trước khi gửi duyệt. Lưu nháp không bắt buộc ảnh.')
    if(imageCount>30)add('images','Mỗi tin có tối đa 30 ảnh.')
  }
  if(steps.includes(3)){
    if(String(draft.description||'').length>20000)add('description','Mô tả tối đa 20000 ký tự.')
    if(String(draft.contactName||'').length>150)add('contactName','Tên liên hệ tối đa 150 ký tự.')
    if(String(draft.phone||'').length>30||!/^[+0-9 ()-]*$/.test(draft.phone||''))add('phone','Số điện thoại tối đa 30 ký tự, chỉ gồm số, +, khoảng trắng, ngoặc hoặc gạch nối.')
    if(draft.contact&&(draft.contact.length>254||!/^\S+@[^\s@]+\.[^\s@]+$/.test(draft.contact)))add('contact','Nhập email hợp lệ hoặc để trống.')
    for(const [field,max]of [['floor',30],['block',50],['direction',30]])if(String(draft[field]||'').length>max)add(field,'Tối đa '+max+' ký tự.')
    if((draft.selectedAmenities||[]).length>50||(draft.selectedAmenities||[]).some(v=>!String(v).trim()||String(v).length>80))add('declaredAmenities','Tối đa 50 tiện ích, mỗi mục từ 1 đến 80 ký tự.')
  }
  return issues
}
export function buildPostPayload(draft){return {
 title:String(draft.title).trim(),description:draft.description||'',propertyType:typeCodes[draft.propertyType],transactionType:draft.transactionType==='Bán'?'SALE':'RENT',
 price:priceInput(draft.price),currency:'VND',priceUnit:draft.transactionType==='Bán'?'TOTAL':draft.rentUnit,areaSqm:areaInput(draft.area),
 bedrooms:hasRooms(draft.propertyType)?Number(draft.bedrooms||0):0,bathrooms:hasRooms(draft.propertyType)?Number(draft.bathrooms||0):0,
 address:String(draft.address||'').trim(),city:String(draft.city||'').trim(),district:String(draft.district||'').trim(),ward:String(draft.ward||'').trim(),
 latitude:Number(draft.latitude),longitude:Number(draft.longitude),contactName:draft.contactName||'',contactPhone:draft.phone||'',contactEmail:draft.contact||null,
 floor:draft.floor||'',block:draft.block||'',direction:draft.direction||'',declaredAmenities:[...new Set((draft.selectedAmenities||[]).map(v=>v.trim()))]
}}
export function payloadFromManaged(item){const p=item.property;return {
 title:p.title,description:p.description||'',propertyType:p.propertyType,transactionType:p.transactionType,price:String(p.priceExact??p.price),currency:p.currency,priceUnit:p.priceUnit,areaSqm:String(p.areaSqmExact??p.areaSqm),
 bedrooms:p.bedrooms||0,bathrooms:p.bathrooms||0,address:p.address||'',city:p.city,district:p.district||'',ward:p.ward||'',latitude:Number(p.latitude),longitude:Number(p.longitude),
 contactName:item.contactName||'',contactPhone:item.contactPhone||'',contactEmail:item.contactEmail||null,floor:p.floor||'',block:p.block||'',direction:p.direction||'',declaredAmenities:p.declaredAmenities||[]
}}
export function samePayload(left,right){return Object.keys(left).every(k=>k==='declaredAmenities'?JSON.stringify([...left[k]].sort())===JSON.stringify([...(right[k]||[])].sort()):['price','areaSqm'].includes(k)?canonicalDecimal(left[k])===canonicalDecimal(right[k]):left[k]===right[k])}

function canonicalDecimal(value){let s=String(value);return s.includes('.')?s.replace(/0+$/,'').replace(/\.$/,''):s}
