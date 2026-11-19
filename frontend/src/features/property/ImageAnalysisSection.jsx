import { useEffect, useState, useSyncExternalStore } from 'react';
import { api, session } from '../auth/api.js';
export default function ImageAnalysisSection({propertyId, own=false}) {
  const auth=useSyncExternalStore(session.subscribe,session.getSnapshot);
  const [data,setData]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[revision,setRevision]=useState(0);
  useEffect(()=>{let active=true;setData(null);setError('');if(!propertyId)return;setBusy(true);
    api('/properties/'+encodeURIComponent(propertyId)+'/image-analysis',{authenticated:!!auth.token}).then(v=>{if(active)setData(v);}).catch(()=>{if(active)setError('Chưa tải được kết quả phân tích ảnh.');}).finally(()=>{if(active)setBusy(false);});
    return ()=>{active=false;};
  },[propertyId,auth.token,revision]);
  async function retry(){setBusy(true);setError('');try{await api('/properties/'+encodeURIComponent(propertyId)+'/image-analysis/retry',{method:'POST'});setRevision(v=>v+1);}catch{setError('Chưa thể yêu cầu phân tích. Kiểm tra quyền truy cập hoặc cấu hình dịch vụ.');}finally{setBusy(false);}}
  if(!propertyId)return null;
  return <section className="bg-brand-card rounded-3xl p-6 sm:p-8 border border-brand-line" aria-label="Phân tích ảnh bất động sản">
    <h2 className="font-bold mb-3">Nhận diện nội dung ảnh</h2>
    {busy&&<p role="status">Đang tải kết quả…</p>}
    {error&&<p role="alert">{error} <button onClick={()=>setRevision(v=>v+1)}>Thử lại</button></p>}
    {data&&<><p>{({UNAVAILABLE:'Phân tích ảnh chưa sẵn sàng trên môi trường này.',PENDING:'Ảnh đang chờ phân tích.',ANALYZING:'Đang phân tích ảnh.',COMPLETED:'Đã có kết quả nhận diện.',FAILED:'Chưa phân tích được ảnh.'})[data.status]||'Trạng thái: '+data.status}</p>
      {(data.images||[]).map((image,index)=><div key={image.propertyImageId||index} className="mt-3"><strong>Ảnh {index+1}</strong><p>{Object.entries(image.countsByLabel||{}).map(([label,count])=>label+': '+count).join(' · ')||'Chưa có đối tượng được nhận diện.'}</p></div>)}
      <p className="text-xs mt-3">Kết quả nhận diện tự động từ ảnh, không xác minh hiện trạng, pháp lý hoặc số phòng thực tế.</p>
      {(own||auth.user?.role==='ADMIN')&&data.status!=='UNAVAILABLE'&&<button className="listing-ai-action mt-3" disabled={busy} onClick={retry}>Yêu cầu phân tích lại</button>}
    </>}
  </section>;
}
