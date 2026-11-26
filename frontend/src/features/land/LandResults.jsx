import { useCallback, useEffect, useState } from 'react';
import LandMap from './LandMap.jsx';
import { PRICE_TYPE_LABEL, formatArea, landDetailPath, validLand, loadRecord, landDisplayValue } from './landApi.js';
import './LandResults.css';

const KIND_LABEL = { PLANNING_CELL:'Ô quy hoạch',GULAND_PARCEL:'Thửa nguồn Guland',PROJECT_LOT:'Lô dự án',PROJECT_LOT_UNLOCATED:'Lô dự án · chưa định vị' };
function LandCard({row,index,active,onShow}) {
 return <article className={'land-card'+(active?' is-active':'')} data-land-card={row.sourceCode}>
  <header><span className="land-rank">{index}</span><h3>{row.displayName} · {row.sourceCode}</h3></header>
  <p className="land-kind">{KIND_LABEL[row.kind]}</p><p className="land-location">{row.location}</p>
  <p className="land-area">Diện tích: {formatArea(row.computedAreaSqm)||'Chưa có dữ liệu'}</p>
  <p className="land-price"><strong>{row.priceDescription||'Chưa có giá'}</strong></p>
  <div className="land-actions"><button type="button" onClick={()=>onShow(row)} aria-pressed={active}>Xem vị trí và đường bao</button><a href={landDetailPath(row)} target="_blank" rel="noopener noreferrer" className="land-detail-link">Xem chi tiết ↗</a></div>
 </article>;
}
function ProfileField({label,value,demo}) {return <div><dt>{label}</dt><dd>{landDisplayValue(value)??'Chưa xác minh'}</dd></div>}
export function SelectedLand({row}) {
 const [selectedId,setSelectedId]=useState(row.landId);
 const pickOnMap=useCallback(feature=>{const id=feature.sourceCode||feature.landId||feature.id;if(id)setSelectedId(id)},[]);
 const [record,setRecord]=useState(null),[error,setError]=useState(''),[attempt,setAttempt]=useState(0);
 useEffect(()=>{const controller=new AbortController();setRecord(null);setError('');loadRecord(selectedId,{signal:controller.signal}).then(setRecord).catch(e=>{if(e.name!=='AbortError')setError(e.message)});return()=>controller.abort()},[selectedId,attempt]);
 if(error)return <section className="land-selected" role="alert"><h3>Đang chọn: {row.displayName}</h3><p>{error}</p><button type="button" onClick={()=>setAttempt(x=>x+1)}>Thử lại hồ sơ</button></section>;
 if(!record)return <section className="land-selected" role="status">Đang tải hồ sơ {row.displayName}…</section>;
 const d=record.documents||{},f=record.flood||{};
 return <section className="land-selected" data-selected-land={record.sourceCode}>
  <h3>Đang chọn: {record.displayName}</h3>
  <LandMap key={record.landId} recordId={record.sourceCode} located={record.located} height={430} showAllFlood onSelect={pickOnMap} />
  <p className="land-map-pick-hint">Bấm vào ô đất trên bản đồ để xem thông tin ô đó bên dưới.</p>
  <dl className="land-selected-profile" aria-live="polite"><ProfileField label="Tên / mã đất" value={record.displayName+' · '+record.sourceCode}/><ProfileField label="Vị trí" value={record.location}/><ProfileField label="Loại đất" value={d.landType} demo={d.demo}/><ProfileField label="Dự án liên quan" value={record.cadastral?.projectName || record.planning?.plans?.map(x=>x.name).filter(Boolean).join('; ') || null}/><ProfileField label="Diện tích" value={formatArea(record.cadastral?.areaSqm)}/><ProfileField label="Giá" value={record.price?.display}/><ProfileField label="Giấy tờ chính chủ" value={d.ownershipDocument} demo={d.demo}/><ProfileField label="Thu hồi / giải tỏa" value={d.recovery} demo={d.demo&&d.recovery!=='Chưa xác minh'}/><ProfileField label="Tranh chấp / thế chấp" value={d.dispute===d.mortgage?d.dispute:`${d.dispute} / ${d.mortgage}`}/><ProfileField label="Bồi thường" value={d.compensation}/><ProfileField label="Ngập lụt" value={f.display} demo={f.isDemoAssumption}/></dl>
  <small className="land-data-note">Dữ liệu trình diễn có giá và pháp lý giả lập; chưa xác minh thực tế.</small>
  <details className="land-source"><summary>Nguồn dữ liệu</summary><p>{f.detail}</p>{(f.records||[]).map(x=><p key={x.id}>“{x.location_text}” · {x.publication_date}. {/https?:\/\//.test(x.source_url||'')&&<a href={x.source_url} target="_blank" rel="noopener noreferrer">Nguồn ngập ↗</a>}</p>)}{(record.sources||[]).map(url=><p key={url}>{/^https?:\/\//.test(url)&&<a href={url} target="_blank" rel="noopener noreferrer">{url}</a>}</p>)}<p>Demo là giả định, chưa xác minh thực tế. Ô quy hoạch không phải ranh thửa địa chính; dải 80 m không phải ranh ngập thực đo.</p></details>
 </section>;
}
function FloodList({ land, onMap }) {
  return <section className="land-flood-list" aria-label="Danh mục vị trí nguy cơ ngập">
    {land.floodRecords.map(f => <article key={f.id} className="land-card">
      <h3>{f.location_text}</h3>
      <p className="land-location">{f.typeLabel} · {f.current_unit || 'Chưa rõ phường hiện tại'} · Quận/huyện theo nguồn: {f.source_district || f.district || 'toàn thành phố'}</p>
      <details className="land-source"><summary>Nguồn</summary>
        <p>{f.source_title} ({f.publication_date}{f.source_page ? ', trang ' + f.source_page : ''})</p>
        {f.source_url && <a href={f.source_url} target="_blank" rel="noopener noreferrer">Mở văn bản nguồn</a>}
        <p>Mã nguồn: {f.id}</p>
      </details>
      <div className="land-actions"><button type="button" onClick={() => onMap([f.id])}>Xem trên bản đồ</button></div>
    </article>)}
    {land.floodAllIds?.length > 0 && <button type="button" className="land-all-flood" onClick={() => onMap(land.floodAllIds)}>Xem tất cả {land.floodTotal} vị trí trên bản đồ</button>}
  </section>;
}

export default function LandResults({land,onSelect,footer}) {
 const [selected,setSelected]=useState(()=>land?.selectedId||land?.rows?.[0]?.sourceCode||null);
 const [floodIds,setFloodIds]=useState(null);
 useEffect(()=>{setSelected(land?.selectedId||land?.rows?.[0]?.sourceCode||null);setFloodIds(null)},[land]);
 if(!validLand(land))return null;
 const rows=land.rows,current=rows.find(r=>r.sourceCode===selected)||null;
 const choose=row=>{setFloodIds(null);setSelected(row.sourceCode);onSelect?.(row)};
 return <div className="land-results" data-land-results={land.kind}>
  {!!land.unappliedConditions?.length&&<details className="land-source"><summary>Điều kiện chưa áp dụng</summary><ul>{land.unappliedConditions.map(x=><li key={x}>{x}</li>)}</ul></details>}
  {!!rows.length&&<div className="land-results-grid"><div className="land-cards">{rows.map((row,i)=><LandCard key={row.sourceCode} row={row} index={i+1} active={row.sourceCode===selected} onShow={choose}/>)}{footer}</div><aside className="land-selection-column">{current&&<SelectedLand key={current.sourceCode} row={current}/>}</aside></div>}
  {land.kind==='FLOOD_CATALOG'&&<FloodList land={land} onMap={ids=>{setSelected(null);setFloodIds(ids)}}/>}
  {!current&&floodIds&&<LandMap key={floodIds.join(',')} floodIds={floodIds} height={400}/>}
 </div>;
}
