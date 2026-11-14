import React from 'react'
import './LifestyleFields.css'

export const needGroups = [
  ['Mua sắm', [['MARKET','Chợ'],['SUPERMARKET','Siêu thị'],['MALL','Trung tâm thương mại'],['CONVENIENCE_STORE','Cửa hàng tiện lợi']]],
  ['Thể thao và vận động', [['GYM','Phòng gym'],['SPORTS_FIELD','Sân thể thao'],['POOL','Hồ bơi'],['PARK','Công viên hoặc đường đi bộ']]],
  ['Ăn uống', [['RESTAURANT','Quán ăn / nhà hàng'],['CAFE','Quán cà phê']]],
  ['Gia đình và giáo dục', [['KINDERGARTEN','Trường mầm non'],['PRIMARY_SCHOOL','Trường tiểu học'],['SECONDARY_SCHOOL','Trường trung học'],['PLAYGROUND','Khu vui chơi trẻ em']]],
  ['Y tế', [['HOSPITAL','Bệnh viện'],['CLINIC','Phòng khám'],['PHARMACY','Nhà thuốc']]],
  ['Đi lại', [['WORKPLACE','Gần khu vực làm việc'],['PUBLIC_TRANSPORT','Gần trạm xe buýt / phương tiện công cộng']]],
]
export const emptyLifestyle = () => ({familyStatus:null,hasChildren:null,childrenCount:null,ageGroup:null,occupation:'',workArea:'',selectedNeeds:[],primaryNeed:null,otherNeeds:'',enabled:false})
export default function LifestyleFields({value, onChange, disabled}) {
  const p={...emptyLifestyle(),...value}, selected=p.selectedNeeds||[]
  const change=(key,v)=>onChange({...p,[key]:v})
  const toggle=(key,checked)=>{
    const next=checked?[...selected,key]:selected.filter(v=>v!==key)
    onChange({...p,selectedNeeds:next,primaryNeed:next.includes(p.primaryNeed)?p.primaryNeed:null})
  }
  return <fieldset className="lifestyle-fields" disabled={disabled}>
    <legend>Nhu cầu sinh hoạt và cá nhân hóa</legend>
    <p>Chọn những tiện ích bạn quan tâm và ưu tiên quan trọng nhất. Bạn có thể bỏ trống các thông tin tùy chọn.</p>
    <div className="lifestyle-grid">
      <label>Tình trạng gia đình<select className="sp-input" value={p.familyStatus||''} onChange={e=>change('familyStatus',e.target.value||null)}><option value="">Chưa cung cấp</option><option value="MARRIED">Đã lập gia đình</option><option value="SINGLE">Chưa lập gia đình</option></select></label>
      <label>Có con chưa?<select className="sp-input" value={p.hasChildren==null?'':String(p.hasChildren)} onChange={e=>onChange({...p,hasChildren:e.target.value===''?null:e.target.value==='true',childrenCount:e.target.value==='true'?p.childrenCount:null})}><option value="">Chưa cung cấp</option><option value="true">Có con</option><option value="false">Chưa có con</option></select></label>
      {p.hasChildren===true&&<label>Số con<select className="sp-input" value={p.childrenCount||''} onChange={e=>change('childrenCount',e.target.value?Number(e.target.value):null)}><option value="">Chưa cung cấp</option>{[1,2,3,4,5].map(n=><option key={n} value={n}>{n}</option>)}</select></label>}
      <label>Nhóm tuổi (tùy chọn)<select className="sp-input" value={p.ageGroup||''} onChange={e=>change('ageGroup',e.target.value||null)}><option value="">Không muốn cung cấp</option><option value="UNDER_25">Dưới 25</option><option value="AGE_25_34">25–34</option><option value="AGE_35_44">35–44</option><option value="AGE_45_54">45–54</option><option value="AGE_55_PLUS">55 trở lên</option><option value="PREFER_NOT_TO_SAY">Không muốn cung cấp</option></select></label>
      <label>Công việc hiện tại<input className="sp-input" maxLength={120} value={p.occupation||''} onChange={e=>change('occupation',e.target.value)}/></label>
      <label>Khu vực làm việc / nơi thường đến<input className="sp-input" maxLength={180} value={p.workArea||''} onChange={e=>change('workArea',e.target.value)}/></label>
    </div>
    <div className="lifestyle-groups">{needGroups.map(([name,items])=><fieldset key={name}><legend>{name}</legend>{items.map(([key,label])=><label className="lifestyle-check" key={key}><input type="checkbox" checked={selected.includes(key)} onChange={e=>toggle(key,e.target.checked)}/>{label}</label>)}</fieldset>)}</div>
    <label>Ưu tiên nhất (tùy chọn)<select className="sp-input" value={p.primaryNeed||''} onChange={e=>change('primaryNeed',e.target.value||null)}><option value="">Chưa chọn</option>{needGroups.flatMap(([,items])=>items).filter(([key])=>selected.includes(key)).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
    <label>Nhu cầu khác<textarea className="sp-input" maxLength={500} value={p.otherNeeds||''} onChange={e=>change('otherNeeds',e.target.value)}/></label>
    <label className="lifestyle-check"><input type="checkbox" checked={p.enabled} onChange={e=>change('enabled',e.target.checked)}/>Cho phép chatbot dùng thông tin này để tư vấn</label>

    <button type="button" className="sp-button sp-button-secondary" onClick={()=>onChange(emptyLifestyle())}>Xóa thông tin nhu cầu</button>
    <small>Nhấn Lưu thay đổi để áp dụng việc xóa. Tắt cá nhân hóa sẽ ngừng dùng hồ sơ từ lượt chat tiếp theo.</small>
  </fieldset>
}
