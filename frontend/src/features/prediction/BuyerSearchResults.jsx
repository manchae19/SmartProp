import React, {useEffect,useState} from 'react';
import {SiteLink} from '../../app/navigation.jsx';
import {SelectedLand} from '../land/LandResults.jsx';
import {formatArea,formatVnd} from '../land/landApi.js';
import {selectChatLand} from './chatRuntime.js';
import PropertyNearbyPanel from './PropertyNearbyPanel.jsx';

export default function BuyerSearchResults({search,historical,sessionId,footer}) {
 const rows=search.rows||[];
 const [selected,setSelected]=useState(()=>rows.find(row=>row.land)?.land||null);
 useEffect(()=>{setSelected((search.rows||[]).find(row=>row.land)?.land||null)},[search]);
 const choose=row=>{setSelected(row.land);if(!historical)selectChatLand(row.land.landId,sessionId)};
 return <section className="buyer-search-results land-results" aria-label="Kết quả tìm kiếm theo ngân sách"><div className="land-results-grid">
  <div className="land-cards">{rows.map((row,index)=><article key={row.key} className={'land-card'+(selected?.sourceCode===row.land?.sourceCode?' is-active':'')}>
   <h3>{index+1}. {row.title}</h3>
   <p className="land-kind">{row.source==='SMARTPROP'?'Tin đăng SmartProp':'Dữ liệu đất Hòa Xuân'}</p>
   <p className="land-location">{row.location}</p><p className="land-area">Diện tích: {formatArea(row.area)}</p>
   <p className="land-price"><strong>{row.land?.priceDescription||formatVnd(row.price)}</strong></p>
   {row.land?.flood?.display&&<p className="land-flood">Ngập: {row.land.flood.display}{row.land.flood.isDemoAssumption?' · chưa xác minh thực tế':''}</p>}
   {row.overBudgetVnd>0&&<p className="quality-note">Tham khảo vượt ngân sách: +{formatVnd(row.overBudgetVnd)} (+{row.overBudgetPercent}%)</p>}
   {row.land?<div className="land-actions"><button type="button" onClick={()=>choose(row)} aria-pressed={selected?.sourceCode===row.land.sourceCode}>Xem vị trí và đường bao</button><a href={'/land/'+encodeURIComponent(row.id)} target="_blank" rel="noopener noreferrer">Xem chi tiết ↗</a></div>:<><div className="land-actions"><SiteLink to={'/listing/'+row.id}>Xem chi tiết ↗</SiteLink><SiteLink to={'/map?propertyId='+row.id}>Bản đồ</SiteLink></div><PropertyNearbyPanel property={row.property}/></>}
  </article>)}{footer}</div>
  {selected&&<aside className="land-selection-column"><SelectedLand key={selected.sourceCode} row={selected}/></aside>}
 </div></section>;
}
