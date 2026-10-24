// District strings remain the backend's district filter; no boundary/name migration.
export const districts=['Tất cả','Hải Châu','Thanh Khê','Sơn Trà','Ngũ Hành Sơn','Cẩm Lệ','Liên Chiểu','Hòa Vang','Hội An','Điện Bàn','Tam Kỳ','Núi Thành'];
export function districtValue(value){const s=String(Array.isArray(value)?value[0]||'':value||'').trim();return s&&s!=='Tất cả'&&s.length<=100?s:''}
export function districtLink(path,value){const district=districtValue(value);return {path,query:district?{district}:{}}}
export function mapPoints(items){return items.filter(p=>p.latitude!==null&&p.latitude!==undefined&&p.latitude!==''&&p.longitude!==null&&p.longitude!==undefined&&p.longitude!==''&&Number.isFinite(Number(p.latitude))&&Number.isFinite(Number(p.longitude))&&Math.abs(Number(p.latitude))<=90&&Math.abs(Number(p.longitude))<=180&&!(p.locationAccuracy==='BUILDING_ONLY'&&p.locationApproved!==true)).map(p=>({...p,latitude:Number(p.latitude),longitude:Number(p.longitude)}))}
