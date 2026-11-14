import { validPoint } from '../map/nearbyExplorer.js';
export const CHAT_POI_GROUPS = [
 ['education','Trường học'],['shopping','Chợ / siêu thị'],['health','Y tế'],['park','Công viên'],
 ['transport','Giao thông công cộng'],['dining','Ăn uống'],['bank','Ngân hàng'],['tourism','Du lịch'],['entertainment','Giải trí']
];
const mapping={SCHOOL:'education',KINDERGARTEN:'education',PRIMARY_SCHOOL:'education',SECONDARY_SCHOOL:'education',
 SUPERMARKET:'shopping',MARKET:'shopping',MALL:'shopping',HOSPITAL:'health',CLINIC:'health',PHARMACY:'health',
 PARK:'park',PUBLIC_TRANSPORT:'transport',RESTAURANT:'dining',CAFE:'dining',PLAYGROUND:'entertainment'};
export function groupsForNeeds(needs=[]){return [...new Set(needs.map(n=>mapping[n]).filter(Boolean))];}
export function nearestInGroups(data,groups){
 const seen=new Set();return groups.flatMap(group=>(data?.items||[]).filter(p=>
  validPoint(p)&&typeof p.name==='string'&&p.name.trim()&&p.categoryGroups?.includes(group)&&
  Number.isFinite(p.distanceMeters)&&p.distanceMeters>=0&&p.distanceMeters<=data.radiusMeters)
 .sort((a,b)=>a.distanceMeters-b.distanceMeters).slice(0,3).filter(p=>!seen.has(p.id)&&seen.add(p.id)));
}
