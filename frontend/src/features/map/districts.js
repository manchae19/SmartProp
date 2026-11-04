import {publicMapPoint} from './locationDisplay.js'
// District strings remain the backend's district filter; no boundary/name migration.
export const districts=['Tất cả','Hải Châu','Thanh Khê','Sơn Trà','Ngũ Hành Sơn','Cẩm Lệ','Liên Chiểu','Hòa Vang','Hội An','Điện Bàn','Tam Kỳ','Núi Thành'];
export function districtValue(value){const s=String(Array.isArray(value)?value[0]||'':value||'').trim();return s&&s!=='Tất cả'&&s.length<=100?s:''}
export function districtLink(path,value){const district=districtValue(value);return {path,query:district?{district}:{}}}
export function mapPoints(items){return items.filter(publicMapPoint).map(p=>({...p,latitude:Number(p.latitude),longitude:Number(p.longitude)}))}
