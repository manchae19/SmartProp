import React,{lazy,Suspense,useEffect,useRef,useState,useSyncExternalStore} from 'react';
import {api,session} from '../auth/api.js';
import {CHAT_POI_GROUPS,groupsForNeeds,nearestInGroups} from './propertyNearby.js';
import {distanceLabel} from '../map/nearbyExplorer.js';
import './PropertyNearbyPanel.css';
const NearbyMap=lazy(()=>import('../map/LeafletNearbyMap.jsx'));
export default function PropertyNearbyPanel({property,needs}){
 const auth=useSyncExternalStore(session.subscribe,session.getSnapshot);
 const [open,setOpen]=useState(false),[radius,setRadius]=useState(1000),[groups,setGroups]=useState([]);
 const [profile,setProfile]=useState(null),[profileReady,setProfileReady]=useState(false);
 const [data,setData]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const [selected,setSelected]=useState(null),[mapOpen,setMapOpen]=useState(false),[retry,setRetry]=useState(0);
 const [route,setRoute]=useState(null),[routeTarget,setRouteTarget]=useState(null),[mode,setMode]=useState('walk');
 const [routeBusy,setRouteBusy]=useState(false),[routeError,setRouteError]=useState(''),[routeRetry,setRouteRetry]=useState(0);
 const routeSequence=useRef(0),mapHost=useRef(null);
 const sequence=useRef(0);
 const id=property?.source?.recordKey;
 const scope=auth.user?.id+':'+auth.status;
 useEffect(()=>{
  let active=true;setProfile(null);setProfileReady(false);setGroups([]);setData(null);
  if(!open)return()=>{active=false};
  if(auth.status!=='AUTHENTICATED'){setProfileReady(true);return()=>{active=false};}
  api('/users/me/advisor-context').then(p=>{if(active){setProfile(p);setProfileReady(true);}})
   .catch(()=>{if(active)setProfileReady(true)});
  return()=>{active=false};
 },[open,scope]);
 useEffect(()=>{
  if(!open||!profileReady)return;
  const chat=needs?.fromProfile&&!profile?.enabled?[]:needs?.priorities||[];
  const values=chat.length?chat:profile?.enabled?[profile.primaryNeed,...(profile.selectedNeeds||[])].filter(Boolean):[];
  setGroups(groupsForNeeds(values));
 },[open,profileReady,profile,needs]);
 useEffect(()=>{
  const request=++sequence.current;setData(null);setError('');setSelected(null);setMapOpen(false);setBusy(false);
  if(!open||!profileReady||!groups.length||!id)return;
  setBusy(true);
  const query=new URLSearchParams({radius:String(radius),categories:groups.join(','),verifiedOrigin:'true',allowEstimatedOrigin:'true'});
  api('/properties/'+encodeURIComponent(id)+'/nearby?'+query,{authenticated:false}).then(result=>{
   if(request!==sequence.current)return;
   if(result.propertyId!==id||result.radiusMeters!==radius||groups.some(g=>!result.categories?.includes(g)))throw Error('Kết quả không khớp căn nhà hoặc bán kính.');
   setData(result);
  }).catch(e=>{if(request===sequence.current)setError(e.message||'Không tải được tiện ích. Vui lòng thử lại.')})
   .finally(()=>{if(request===sequence.current)setBusy(false)});
  return()=>{sequence.current++};
 },[open,id,radius,groups.join(','),profileReady,retry,scope]);
 useEffect(()=>{
  const request=++routeSequence.current;setRoute(null);setRouteError('');setRouteBusy(false);
  if(!open||!mapOpen||!routeTarget||!data||data.propertyId!==id||data.radiusMeters!==radius||!data.items.some(p=>p.id===routeTarget))return;
  setRouteBusy(true);
  const query=new URLSearchParams({poiId:routeTarget,radius:String(radius),categories:groups.join(','),mode});
  api('/properties/'+encodeURIComponent(id)+'/route?'+query,{authenticated:false}).then(result=>{
   if(request!==routeSequence.current)return;
   if(result.propertyId!==id||result.poiId!==routeTarget||result.radiusMeters!==radius||result.mode!==mode||!['LineString','MultiLineString'].includes(result.geometry?.type)||!Number.isFinite(result.distanceMeters)||!Number.isFinite(result.durationSeconds))throw Error('Tuyến đường không khớp lựa chọn hiện tại.');
   setRoute(result);
  }).catch(e=>{if(request===routeSequence.current)setRouteError(e.message||'Chưa tải được tuyến đường.')})
   .finally(()=>{if(request===routeSequence.current)setRouteBusy(false)});
  return()=>{routeSequence.current++};
 },[open,mapOpen,routeTarget,mode,id,radius,groups.join(','),data,routeRetry]);
 function openMap(p){setSelected(p.id);setRouteTarget(p.id);setMapOpen(true);setTimeout(()=>mapHost.current?.scrollIntoView({behavior:'smooth',block:'nearest'}),0);}
 if(property?.source?.kind!=='PROPERTY')return <p className="chat-nearby-note">Tin nguồn ngoài chưa có vị trí căn nhà đủ điều kiện để tìm tiện ích.</p>;
 const places=nearestInGroups(data,groups),validOrigin=data?.location&&['EXACT_PROPERTY','BUILDING_ONLY','USER_PROVIDED'].includes(data.location.accuracy);
 const mapProperty={...property,id,title:property.title,price:property.priceVnd,latitude:data?.location?.latitude,longitude:data?.location?.longitude};
 function toggle(group){setGroups(previous=>previous.includes(group)?previous.filter(g=>g!==group):[...previous,group]);}
 return <div className="chat-nearby">
  <button type="button" aria-expanded={open} onClick={()=>setOpen(v=>!v)}>Tiện ích theo nhu cầu của bạn <span>{open?'Thu gọn −':'Mở để xem →'}</span></button>
  {!open&&<p className="chat-nearby-hint">Chọn để tải trường học, siêu thị và tiện ích phù hợp với nhu cầu của bạn.</p>}
  {open&&<section aria-label={'Tiện ích quanh '+property.title}>
   <div className="chat-nearby-options"><label>Bán kính <select value={radius} onChange={e=>setRadius(Number(e.target.value))}>{[500,1000,2000,5000].map(n=><option key={n} value={n}>{distanceLabel(n)}</option>)}</select></label><label>Di chuyển <select value={mode} onChange={e=>setMode(e.target.value)}><option value="walk">Đi bộ</option><option value="drive">Ô tô</option></select></label>
    <fieldset><legend>{groups.length?'Nhóm ưu tiên (nhóm đầu hiển thị trước)':'Chọn nhóm tiện ích để khám phá'}</legend>
    {CHAT_POI_GROUPS.map(([g,label])=><label key={g}><input type="checkbox" checked={groups.includes(g)} onChange={()=>toggle(g)}/>{label}{groups[0]===g?' · Ưu tiên nhất':''}</label>)}</fieldset></div>
   {busy&&<p role="status">Đang tải tiện ích…</p>}
   {error&&<p role="alert">{error} <button onClick={()=>setRetry(n=>n+1)}>Thử lại</button></p>}
   {data&&<>
    <p className="chat-nearby-note">{data.status==='LOCATION_UNAVAILABLE'?'Tin chưa có tọa độ hợp lệ.':!validOrigin?'Chưa hiển thị mét/km: ghim này do người đăng cung cấp và chưa được đối chiếu vị trí. Không phải hệ thống đã tìm rồi không có tiện ích.':data.location.accuracy==='BUILDING_ONLY'?'Vị trí cấp tòa nhà; khoảng cách tính từ tòa nhà, không phải căn hộ cụ thể.':data.location.accuracy==='USER_PROVIDED'?'Từ ghim người đăng · chưa xác minh vị trí căn nhà. Khoảng cách bên dưới chỉ là ước tính từ ghim này.':'Vị trí căn nhà đã có hồ sơ đối chiếu.'}</p>
    {data.location&&<small>Nguồn: {data.location.source==='PROPERTY_LISTING'?'Ghim người đăng':data.location.source} · {({USER_PROVIDED:'Chưa xác minh',EXACT_PROPERTY:'Đã đối chiếu vị trí',BUILDING_ONLY:'Cấp tòa nhà',UNKNOWN:'Chưa rõ độ chính xác',APPROXIMATE:'Vị trí khu vực'})[data.location.accuracy]||'Chưa rõ độ chính xác'}{data.location.reference&&<> · <a href={data.location.reference} target="_blank" rel="noopener noreferrer">Hồ sơ nguồn</a></>}</small>}
    {validOrigin&&<>
     <p>Khoảng cách đường chim bay · Tối đa 3 địa điểm gần nhất mỗi nhóm. Trường học chưa xác minh cấp học cụ thể.</p>
     {!places.length&&<p>Không tìm thấy tiện ích phù hợp trong bán kính đã chọn.</p>}
     {places.map(p=><article className="chat-nearby-place" key={p.id} data-poi-id={p.id}>
      <strong>{p.name}</strong><span>{CHAT_POI_GROUPS.find(([g])=>g===p.category)?.[1]||p.category} · <strong className="chat-nearby-distance">{data.location.accuracy==='USER_PROVIDED'?'≈ ':''}{distanceLabel(p.distanceMeters)}</strong></span>
      <small>Nguồn tọa độ: {p.provider} · Thời điểm tải: {new Date(data.fetchedAt).toLocaleString('vi-VN')}</small>
      <div><button type="button" onClick={()=>openMap(p)}>Xem bản đồ</button></div>
     </article>)}
     {mapOpen&&<div ref={mapHost} className="chat-nearby-map"><button type="button" onClick={()=>{setMapOpen(false);setRouteTarget(null)}}>Đóng bản đồ</button>
      {routeBusy&&<p role="status">Đang tìm đường {mode==='walk'?'đi bộ':'ô tô'}…</p>}
      {routeError&&<p role="alert">{routeError} <button type="button" onClick={()=>setRouteRetry(n=>n+1)}>Thử lại tuyến đường</button></p>}
      {route&&<p className="chat-route-summary"><strong>{distanceLabel(route.distanceMeters)}</strong> · Khoảng {Math.max(1,Math.ceil(route.durationSeconds/60))} phút · {mode==='walk'?'Đi bộ':'Ô tô'}<br/><small>Quãng đường theo mạng lưới đường, thời gian ước tính; không có giao thông thời gian thực.{route.origin.accuracy==='USER_PROVIDED'?' Xuất phát từ ghim người đăng, chưa xác minh vị trí căn nhà.':''}</small></p>}
<Suspense fallback={<p>Đang mở bản đồ…</p>}><NearbyMap items={[mapProperty]} selectedId={id} places={places} radius={radius} activePoi={selected} onSelectPoi={poiId=>{setSelected(poiId);if(routeTarget)setRouteTarget(poiId)}} route={route} simple /></Suspense></div>}
    </>}
    {data.truncated&&<p>Kết quả bị giới hạn bởi nguồn cung cấp; chưa phải toàn bộ tiện ích trong vùng.</p>}
    <div className="chat-nearby-credits">{data.attribution?.map(c=><a key={c.url} href={c.url} target="_blank" rel="noopener noreferrer">{c.label}</a>)}</div>
   </>}
  </section>}
 </div>;
}
