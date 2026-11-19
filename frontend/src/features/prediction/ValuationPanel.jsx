import {useEffect, useRef, useState, useSyncExternalStore} from 'react';
import {SiteLink} from '../../app/navigation.jsx';
import {buildValuationPayload, createValuationClient, featureLabels, formatPrice, locationLabel, warningLabel} from './valuation.js';
import {normalizeShapFactors, missingFeatureLabels, v13AssumptionNotes} from './valuationPresentation.js';
import {parseQuickAddress, normalizeQuickAddress} from './quickAddress.js';
import {session, errorText} from '../auth/api.js';
import {createHistoryClient} from './history.js';
import './ValuationPanel.css';

const defaults={category:'Nhà ở', area_sqm:'', location_feature:'', ward:'', rooms:'', floors:'', access_type:'', house_subtype:''};
export default function ValuationPanel({initialInput={}, historyEnabled=false, demo=false, onSaved, onOptionsLoaded, ...attributes}) {
  const auth=useSyncExternalStore(session.subscribe,session.getSnapshot);
  const [client]=useState(()=>createValuationClient()), [history]=useState(()=>createHistoryClient());
  const [form,setForm]=useState(()=>({...defaults,...initialInput})), [options,setOptions]=useState(null);
  const [loading,setLoading]=useState(true), [optionsError,setOptionsError]=useState(''), [error,setError]=useState('');
  const [busy,setBusy]=useState(false), [result,setResult]=useState(null), [model,setModel]=useState('v6');
  const [saving,setSaving]=useState(false), [saved,setSaved]=useState(false), [saveError,setSaveError]=useState('');
  const [address,setAddress]=useState(''), [addressNote,setAddressNote]=useState(''), [reload,setReload]=useState(0);
  const request=useRef(null), revision=useRef(0), inputSnapshot=useRef(null), saveKey=useRef(null), callbacks=useRef({});
  callbacks.current={onSaved,onOptionsLoaded};
  const initialKey=JSON.stringify(initialInput);
  function invalidate() {
    revision.current++; request.current?.abort(); setBusy(false); setResult(null); setError('');
    setSaved(false); setSaving(false); setSaveError(''); inputSnapshot.current=null; saveKey.current=null;
  }
  useEffect(()=>{invalidate();setForm({...defaults,...JSON.parse(initialKey)});},[initialKey]);
  useEffect(()=>{
    const controller=new AbortController(); setLoading(true); setOptionsError('');
    client.getOptions({signal:controller.signal}).then(data=>{
      if(controller.signal.aborted)return;
      setOptions(data); callbacks.current.onOptionsLoaded?.(data.location_labels??{});
      setModel(data.v1_3?.available && data.v1_3.supported_categories?.includes(JSON.parse(initialKey).category || defaults.category) ? 'v1_3' : 'v6');
    }).catch(e=>{if(!controller.signal.aborted)setOptionsError(e.message);})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return()=>controller.abort();
  },[client,reload]);
  useEffect(()=>{setSaved(false);setSaving(false);setSaveError('');},[auth.token]);
  useEffect(()=>()=>{revision.current++;request.current?.abort();},[]);
  const locations=options?.categories.find(item=>item.category===form.category)?.locations??[];
  const v13Available=options?.v1_3?.available && (options.v1_3.supported_categories??[]).includes(form.category);
  const optionalInputs=model==='v1_3' && options?.v1_3?.real_features_enabled;
  function change(key,value) {
    invalidate();
    if(key==='category' && !(options?.v1_3?.supported_categories??[]).includes(value))setModel('v6');
    setForm(previous=>{
      const next={...previous,[key]:value};
      if(key==='category') {
        if(value==='Đất nền'){next.rooms='';next.bathrooms='';}
        if(value!=='Nhà ở'){next.floors='';next.house_subtype='';}
        if(value==='Căn hộ chung cư'){next.access_type='';next.road_width_m='';next.frontage_width_m='';}
        if(!options?.categories.find(item=>item.category===value)?.locations.includes(next.location_feature))next.location_feature='';
      }
      return next;
    });
  }
  function quickFill() {
    const parsed=parseQuickAddress(address);
    const location=parsed?.district && locations.find(code=>normalizeQuickAddress(locationLabel(code,options?.location_labels))===normalizeQuickAddress(parsed.district));
    if(!location){setAddressNote('Chưa nhận diện được địa bàn được hỗ trợ. Bạn chọn thủ công bên dưới.');return;}
    invalidate();setForm(previous=>({...previous,location_feature:location,ward:parsed.ward||''}));
    setAddressNote('Đã điền địa bàn từ địa chỉ. Bạn kiểm tra lại trước khi ước tính.');
  }
  async function estimate(event) {
    event.preventDefault();invalidate();
    if(!options)return;
    if(model==='v1_3'&&!v13Available){setError('Mô hình thử nghiệm chưa sẵn sàng cho loại tài sản này. Bạn có thể chọn V6.');return;}
    let payload;
    try{payload=buildValuationPayload(form,options,!!optionalInputs);}catch(e){setError(e.message);return;}
    const current=revision.current, controller=new AbortController();request.current=controller;setBusy(true);
    try{
      const data=await (model==='v1_3'?client.predictV13(payload,{signal:controller.signal}):client.predict(payload,{signal:controller.signal}));
      if(current!==revision.current||controller.signal.aborted)return;
      setResult(data);inputSnapshot.current=payload;saveKey.current=crypto.randomUUID();
    }catch(e){if(current===revision.current&&!controller.signal.aborted)setError(e.message);}
    finally{if(current===revision.current)setBusy(false);}
  }
  async function save() {
    if(!auth.token||!inputSnapshot.current||saving||saved||result?.model_version!=='v6')return;
    const current=revision.current, token=auth.token;setSaving(true);setSaveError('');
    try{await history.save(inputSnapshot.current,saveKey.current);if(current===revision.current&&session.getSnapshot().token===token){setSaved(true);callbacks.current.onSaved?.();}}
    catch(e){if(current===revision.current&&session.getSnapshot().token===token)setSaveError(errorText(e));}
    finally{if(current===revision.current&&session.getSnapshot().token===token)setSaving(false);}
  }
  function field(key,label,{type='text',min,max,step,choices}={}) {
    return <label className="block text-sm" key={key}>{label}
      {choices ? <select className="valuation-input mt-2" value={form[key]??''} onChange={e=>change(key,e.target.value)}><option value="">Chưa rõ</option>{choices.map(([value,text])=><option key={value} value={value}>{text}</option>)}</select>
        : <input className="valuation-input mt-2" type={type} min={min} max={max} step={step} value={form[key]??''} placeholder="Chưa rõ" onChange={e=>change(key,e.target.value)}/>}
    </label>;
  }
  const factors=normalizeShapFactors(result?.shap_explanation,result?.features_used);
  const assumptions=result?.model_version==='v1.3'?v13AssumptionNotes(result.features_used):[];
  return <section {...attributes} className={'rounded-3xl border border-brand-line p-5 sm:p-8 '+(attributes.className||'')} data-sp-018bbc28="">
    {loading&&<p role="status">Đang tải lựa chọn định giá…</p>}
    {optionsError&&<p role="alert">{optionsError} <button type="button" onClick={()=>{invalidate();setReload(value=>value+1);}}>Thử lại</button></p>}
    {options&&<form onSubmit={estimate}>
      <label className="block text-sm">Mô hình tham khảo
        <select className="valuation-input mt-2" value={model} onChange={e=>{invalidate();setModel(e.target.value);}}>
          <option value="v6">V6</option><option value="v1_3" disabled={!v13Available}>V1.3 · thử nghiệm{!v13Available?' · chưa sẵn sàng':''}</option>
        </select>
      </label>
      {!options.v1_3?.available&&<p className="text-sm mt-2">V1.3 chưa sẵn sàng trên môi trường này; bạn có thể dùng V6.</p>}
      <div className="mt-4"><label className="block text-sm">Điền nhanh địa bàn từ địa chỉ<input className="valuation-input mt-2" value={address} maxLength={500} onChange={e=>{setAddress(e.target.value);setAddressNote('');}}/></label>
        <button type="button" className="mt-2 underline" onClick={quickFill}>Điền địa bàn</button><p role="status" className="text-sm">{addressNote}</p></div>
      <div className="grid sm:grid-cols-2 gap-4 mt-5">
        {field('category','Loại tài sản',{choices:options.categories.map(item=>[item.category,item.category])})}
        {field('area_sqm','Diện tích (m²)',{type:'number',min:20,max:1000,step:'any'})}
        {field('location_feature','Địa bàn',{choices:locations.map(code=>[code,locationLabel(code,options.location_labels)])})}
        {field('ward','Phường/xã · tùy chọn')}
        {form.category!=='Đất nền'&&field('rooms','Phòng ngủ · tùy chọn',{type:'number',min:1,max:30,step:1})}
        {form.category==='Nhà ở'&&field('floors','Số tầng nhà · tùy chọn',{type:'number',min:1,max:20,step:'any'})}
        {form.category!=='Căn hộ chung cư'&&field('access_type','Lối vào · tùy chọn',{choices:Object.entries(options.access_types)})}
        {form.category==='Nhà ở'&&field('house_subtype','Loại nhà chi tiết · tùy chọn',{choices:Object.entries(options.house_subtypes)})}
        {optionalInputs&&<>
          {form.category!=='Căn hộ chung cư'&&field('road_width_m','Chiều rộng đường/hẻm (m)',{type:'number',min:0.1,max:100,step:'any'})}
          {form.category!=='Căn hộ chung cư'&&field('frontage_width_m','Bề ngang mặt tiền (m)',{type:'number',min:0.1,max:500,step:'any'})}
          {field('street_name','Tên đường · tùy chọn')}{field('project_name','Dự án · tùy chọn')}
          {form.category!=='Đất nền'&&field('bathrooms','Phòng tắm · tùy chọn',{type:'number',min:1,max:30,step:1})}
          {field('house_direction','Hướng nhà · tùy chọn')}{field('balcony_direction','Hướng ban công · tùy chọn')}
        </>}
      </div>
      <button className="rounded-full border px-5 py-3 mt-5" type="submit" disabled={busy}>{busy?'Đang ước tính…':'Ước tính giá rao'}</button>
    </form>}
    <div aria-live="polite" className="mt-5">
      {error&&<p role="alert">{error}</p>}
      {result&&<div data-testid="valuation-result"><p>Giá rao ước tính · {result.model_version}</p><p className="text-3xl font-semibold mt-2" data-testid="estimated-price">{formatPrice(result.predicted_asking_price_vnd)}</p>
        <h3 className="font-semibold mt-5">Thông tin đã dùng</h3><dl className="grid sm:grid-cols-2 gap-3 mt-3">{Object.entries(result.features_used??{}).filter(([,value])=>value!=null).map(([key,value])=><div key={key}><dt className="text-sm">{featureLabels[key]||key}</dt><dd>{String(key==='location_feature'?locationLabel(value,options?.location_labels):value)}</dd></div>)}</dl>
        {!!result.missing_features?.length&&<p className="text-sm mt-3">Thông tin còn thiếu: {missingFeatureLabels(result.missing_features).join(', ')}.</p>}
        {factors.length>0&&<div className="mt-5"><h3 className="font-semibold">Yếu tố tác động đến giá (SHAP)</h3><ul className="space-y-2 mt-3">{factors.map((factor,index)=><li key={factor.feature_name+index}>{factor.displayLabel}: {factor.displayImpact}</li>)}</ul><p className="text-xs mt-2">SHAP giải thích mô hình, không chứng minh quan hệ nhân quả hoặc độ chính xác của giá.</p></div>}
        {[...(result.warnings??[]),...assumptions].map((note,index)=><p key={index} className="text-sm mt-2">{warningLabel(note)}</p>)}
        {historyEnabled&&!demo&&(result.model_version==='v6' ? auth.token ? <button type="button" className="underline mt-4" disabled={saving||saved} onClick={save}>{saved?'Đã lưu kết quả':saving?'Đang lưu…':'Lưu kết quả'}</button> : <SiteLink to="/login?next=/valuation">Đăng nhập để lưu kết quả</SiteLink> : <p className="text-sm mt-4">Kết quả V1.3 đang ở chế độ thử nghiệm; lịch sử hiện hỗ trợ kết quả V6.</p>)}
        {saveError&&<p role="alert">{saveError}</p>}
      </div>}
    </div>
    <p className="text-xs mt-6">Giá rao ước tính để tham khảo, không phải giá giao dịch thực tế hoặc kết luận thẩm định.</p>
  </section>;
}
