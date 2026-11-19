import {useEffect, useState, useSyncExternalStore} from 'react';
import {api, session, errorText} from '../auth/api.js';
import {SiteLink} from '../../app/navigation.jsx';
import PrivateImage from '../../shared/components/PrivateImage.jsx';

const labels = {PENDING:'Đang chờ kiểm tra', SCANNING:'Đang kiểm tra ảnh', CLEAN:'Không phát hiện ảnh trùng',
  MATCHES:'Có ảnh tương đồng', FAILED:'Không thể kiểm tra', NO_IMAGES:'Chưa có ảnh để kiểm tra'};

export default function ImageScanSection({propertyId}) {
  const auth = useSyncExternalStore(session.subscribe, session.getSnapshot);
  const [scan, setScan] = useState(null), [error, setError] = useState(''), [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true, timer;
    setScan(null); setError('');
    async function load() {
      try {
        const result = await api('/properties/'+encodeURIComponent(propertyId)+'/image-scan', {authenticated:!!auth.token});
        if (!active) return;
        setScan(result); setError('');
        if (['PENDING','SCANNING'].includes(result.status)) timer = setTimeout(load, 2500);
      } catch (e) { if (active) setError(errorText(e)); }
    }
    if (propertyId) load();
    return () => { active = false; clearTimeout(timer); };
  }, [propertyId, auth.token, revision]);
  if (!propertyId) return null;
  const matches = (scan?.images || []).flatMap(image => [...(image.matches || []), ...(image.intraMatches || [])]
    .map(match => ({...match, sourceImageId:image.imageId}))).slice(0, 20);
  return <section className="bg-brand-card rounded-3xl p-6 border border-brand-line" data-sp-image-scan="">
    <h2 className="font-bold">Kiểm tra ảnh trùng</h2>
    <p className="text-sm mt-2" role="status">{error ? 'Chưa tải được kết quả kiểm tra.' : labels[scan?.status] || 'Đang tải kết quả…'}</p>
    {error && <button type="button" onClick={()=>setRevision(value=>value+1)}>Thử lại</button>}
    {matches.map((match, index) => <div key={[match.sourceImageId, match.imageId, index].join(':')} className="flex gap-3 mt-3">
      <PrivateImage src={match.imageUrl} alt="Ảnh đối chiếu" className="w-14 h-14 rounded-xl object-cover" />
      <div><p>{match.classification?.startsWith('INTRA_') ? 'Ảnh trùng trong cùng tin' : 'Ảnh tương đồng với tin khác'}</p>
        {Number.isFinite(Number(match.similarity)) && match.similarity != null && <p>{Math.round(Number(match.similarity)*100)}%</p>}
        {typeof match.listingUrl === 'string' && /^\/listing\/[a-f0-9-]{36}$/i.test(match.listingUrl) &&
          <SiteLink to={match.listingUrl}>Xem tin liên quan{match.listingCode ? ' '+match.listingCode : ''}</SiteLink>}
      </div>
    </div>)}
    <p className="text-xs mt-3">So khớp ảnh nội bộ của các tin công khai; đây là tín hiệu tham khảo, không phải kết luận gian lận.</p>
    {scan?.limitations?.[0] && <p className="text-xs mt-2">{scan.limitations[0]}</p>}
  </section>;
}
