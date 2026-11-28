import {useEffect,useState} from 'react';
import {SiteLink,useRouteState} from '../../app/navigation.jsx';
import LandMap from './LandMap.jsx';
import {formatArea,formatVnd,loadRecord,landFetch,landDisplayValue,PRICE_TYPE_LABEL} from './landApi.js';
import './LandDetailView.css';
const KIND={PLANNING_CELL:'Ô quy hoạch tham khảo · không phải thửa địa chính chính thức',GULAND_PARCEL:'Thửa theo nguồn Guland · chưa xác minh địa chính',PROJECT_LOT:'Lô thuộc dự án · chưa xác minh địa chính',PROJECT_LOT_UNLOCATED:'Lô dự án · chưa định vị'};
const AREA={COMPUTED_FROM_PLANNING_CELL:'Tính từ đường bao ô quy hoạch (không phải diện tích sổ đỏ)',LISTING:'Theo tin nguồn (chưa xác minh đo đạc)',SOURCE_PARCEL:'Theo nguồn Guland · chưa xác minh địa chính'};
const RELATION={DIRECT_SOURCE_MATCH:'Khớp tên đường và địa bàn theo nguồn',SOURCE_TEXT_MENTION:'Nguồn nhắc tuyến đường liên quan',ILLUSTRATIVE_CORRIDOR:'Dải minh họa 80 m · không phải ranh ngập thực đo',USER_APPROVED_DEMO_SCENARIO:'Giả định kịch bản trình diễn · không xác nhận an toàn ngập',UNLOCATED:'Chưa định vị'};
function Row({label,value,demo}){return <div className="land-row"><dt>{label}</dt><dd>{value==null||value===''?'Chưa xác minh':landDisplayValue(value)}{demo&&<span className="land-demo-tag">Giả định</span>}</dd></div>}
function SourceLink({url,children}){return /^https?:\/\//i.test(url||'')?<a href={url} target="_blank" rel="noopener noreferrer">{children||'Mở nguồn ↗'}</a>:null}
function Overview({record}){
 const [state,setState]=useState({loading:true});
 useEffect(()=>{const c=new AbortController();setState({loading:true});landFetch('/records/'+encodeURIComponent(record.landId)+'/overview',{signal:c.signal}).then(data=>{if(data.landId!==record.landId||data.dataVersion!==record.dataVersion||typeof data.text!=='string')throw Error('MISMATCH');setState({data})}).catch(error=>{if(error.name!=='AbortError')setState({error:true})});return()=>c.abort()},[record.landId,record.dataVersion]);
 return <section className="land-overview" aria-labelledby="land-overview-title"><h2 id="land-overview-title">Tổng quan hồ sơ</h2>{state.loading?<p role="status" className="land-overview-loading">Đang chuẩn bị tổng quan… Các thông tin và bản đồ bên dưới vẫn có thể xem.</p>:state.error?<p role="status">Chưa tải được tổng quan. Bạn vẫn có thể xem dữ liệu hồ sơ bên dưới.</p>:<p>{state.data.text}</p>}</section>
}
export default function LandDetailView(){
 const route=useRouteState(),id=String(route.params.id||'');
 const [record,setRecord]=useState(null),[error,setError]=useState(''),[attempt,setAttempt]=useState(0);
 useEffect(()=>{const c=new AbortController();setRecord(null);setError('');loadRecord(id,{signal:c.signal}).then(setRecord).catch(e=>{if(e.name!=='AbortError')setError(e.message)});return()=>c.abort()},[id,attempt]);
 useEffect(()=>{if(record)document.title=record.displayName+' · SmartProp'},[record]);
 if(error)return <main className="land-detail land-load" role="alert"><h1>Chưa mở được hồ sơ</h1><p>{error}</p><button onClick={()=>setAttempt(x=>x+1)}>Thử lại</button><SiteLink to="/advisor/chat">Quay lại tư vấn</SiteLink></main>;
 if(!record)return <main className="land-detail land-load" role="status">Đang tải hồ sơ đất…</main>;
 const c=record.cadastral||{},d=record.documents||{},p=record.planning||{},f=record.flood||{},env=record.environment||{},price=record.price||{},point=record.pointOnSurface;
 const project=c.projectName||(p.plans||[]).map(x=>x.name||x.id).filter(Boolean).join('; ');
 const priceTypes=[...new Set((price.evidence||[]).map(x=>PRICE_TYPE_LABEL[x.type]||landDisplayValue(x.label)))].join(' · ');
 return <main className="land-detail">
  <nav className="land-crumbs"><SiteLink to="/advisor/chat">Tư vấn bất động sản</SiteLink><span> / Hòa Xuân / Hồ sơ đất</span></nav>
  <header className="land-head"><div><span className="land-kind-label">{KIND[record.kind]}</span><h1>{record.displayName}</h1><p>{record.location}</p><p className="land-code">{record.sourceCode}</p></div><div className="land-head-value"><strong>{price.display||'Chưa có giá'}</strong><span>{priceTypes||'Chưa có căn cứ giá'}</span><b>{formatArea(c.areaSqm)||'Chưa có diện tích'}</b></div></header>
  <section className="land-governance-banner" role="note" data-land-governance-notice=""><strong>Cảnh báo dữ liệu giả lập (Demo):</strong> Hồ sơ Hòa Xuân này chỉ phục vụ trình diễn kỹ thuật. Ô quy hoạch không phải thửa địa chính chính thức; các trường giấy tờ, quy hoạch thu hồi, ngập và mức giá giả lập/lịch sử/theo đường không phải xác nhận pháp lý, không xác nhận an toàn ngập và không phải giá thị trường hay giá giao dịch.</section>
  <div className="land-layout"><div className="land-sections">
   <Overview key={record.landId} record={record}/>
   <section aria-labelledby="land-main-title"><h2 id="land-main-title">Thông tin chính</h2><dl>
    <Row label="Loại đất" value={d.landType} demo={d.demo}/><Row label="Dự án / đồ án" value={project}/>
    <Row label="Giấy chứng nhận" value={d.ownershipDocument} demo={d.demo&&d.ownershipDocument!=='Chưa xác minh'}/>
    <Row label="Quy hoạch" value={p.sourceLabel}/><Row label="Thu hồi / giải tỏa" value={d.recovery} demo={d.demo&&d.recovery!=='Chưa xác minh'}/>
    <Row label="Ngập" value={f.display} demo={f.isDemoAssumption}/>
   </dl></section>
   <details className="land-fold"><summary>Chi tiết giá</summary>
    {!(price.evidence||[]).length&&<p>Chưa có dữ liệu giá đủ căn cứ.</p>}
    {(price.evidence||[]).map((e,i)=>{const unit=e.unitPriceVndPerSqm||(e.unitPriceMillionPerSqm?e.unitPriceMillionPerSqm*1000000:null);return <article key={i} className="land-price-row"><h3>{PRICE_TYPE_LABEL[e.type]||e.label}</h3><dl><Row label="Tổng giá theo căn cứ" value={formatVnd(e.valueVnd)}/><Row label="Đơn giá" value={unit?Number(unit).toLocaleString('vi-VN')+' đồng/m²':null}/><Row label="Ngày nguồn" value={e.date}/>{unit&&c.areaSqm&&<Row label="Cách tính" value={`${Number(c.areaSqm).toLocaleString('vi-VN')} m² × ${Number(unit).toLocaleString('vi-VN')} đồng/m²; làm tròn đến đồng`}/>}<Row label="Bản chất giá" value={e.type==='SIMULATED_DEMO'?'Giá giả lập trình diễn, không phải giá thị trường':e.label}/><Row label="Mẫu tham khảo" value={e.sampleCount}/><Row label="Mức tin cậy theo nguồn" value={e.confidence}/></dl>{(e.sources||[]).filter(Boolean).map((url,j)=><p key={url}><SourceLink url={url}>Nguồn giá {j+1} ↗</SourceLink></p>)}</article>})}
   </details>
   <details className="land-fold"><summary>Thông tin bổ sung — chưa xác minh</summary><h3>Địa chính và hình học</h3><dl>
    <Row label="Căn cứ diện tích" value={AREA[c.areaBasis]}/><Row label="Block" value={c.block}/><Row label="Số lô" value={c.lotNumbers?.join(', ')}/><Row label="Tờ bản đồ" value={c.sheet}/><Row label="Số thửa" value={c.parcel}/><Row label="Chiều ngang" value={c.widthMeters}/><Row label="Chiều dài" value={c.lengthMeters}/><Row label="Hướng" value={c.direction}/><Row label="Điểm trong hình nguồn" value={point?`${point[1].toFixed(6)}, ${point[0].toFixed(6)}`:'Chưa định vị'}/><Row label="Ranh giới" value={!record.located?'Chưa có hình học để định vị':record.kind==='PLANNING_CELL'?'Ô quy hoạch, không phải ranh thửa địa chính':'Theo nguồn, chưa xác minh địa chính'}/>
   </dl><h3>Pháp lý</h3><dl><Row label="Chủ sử dụng" value={d.owner}/><Row label="Tranh chấp" value={d.dispute}/><Row label="Thế chấp" value={d.mortgage}/><Row label="Hạn chế chuyển nhượng" value={d.transferRestrictions}/><Row label="Nghĩa vụ tài chính" value={d.financialObligations}/><Row label="Bồi thường" value={d.compensation}/></dl>
   <h3>Chỉ tiêu xây dựng</h3><dl><Row label="Nội dung quy hoạch nguồn" value={p.text}/><Row label="Mở rộng đường" value={p.roadExpansion}/><Row label="Diện tích ảnh hưởng" value={p.affectedAreaSqm}/><Row label="Mật độ xây dựng" value={p.buildingDensity}/><Row label="Số tầng" value={p.floors}/><Row label="Chiều cao" value={p.heightMeters}/><Row label="Chỉ giới" value={p.buildingLine}/><Row label="Khoảng lùi" value={p.setbackMeters}/></dl>
   <h3>Môi trường</h3><dl><Row label="Cao độ" value={env.elevationMeters}/><Row label="Độ dốc" value={env.slopeDegrees}/><Row label="Mức liên quan ngập" value={RELATION[f.relation]}/><Row label="Thoát nước" value={env.drainage}/><Row label="Nguy cơ sạt lở" value={env.landslideRisk}/></dl></details>
   <details className="land-fold land-sources"><summary>Nguồn, phương pháp và giới hạn dữ liệu</summary><p>Dữ liệu trình diễn có giá và thuộc tính giả lập, không xác nhận giấy tờ hoặc hiện trạng thực tế. Ô quy hoạch không phải thửa địa chính hay lô bán riêng đã xác nhận. Dải xanh 80 m minh họa tuyến tham chiếu, không phải ranh ngập thực đo.</p><p>{f.detail}</p>{(f.records||[]).map(x=><p key={x.id}>“{x.location_text}” · {x.publication_date||'Chưa rõ ngày'} · {x.source_title}. <SourceLink url={x.source_url}/></p>)}{(record.sources||[]).map(url=><p key={url}><SourceLink url={url}/></p>)}<p>Phiên bản dữ liệu: {record.dataVersion}.</p></details>
  </div><aside className="land-aside"><h2>Vị trí và đường bao</h2><LandMap recordId={record.sourceCode} located={record.located} height={520}/><p className="land-map-caption">{record.located?'Hình học theo nguồn · chưa xác minh địa chính.':'Chưa có vị trí để hiển thị bản đồ.'}</p></aside></div>
 </main>;
}