import {useEffect, useState} from 'react';
import {api} from '../auth/api.js';
import {hasNewNewsSnapshot} from './newsPresentation.js';
const categories=['Thị trường BĐS','Quy hoạch & hạ tầng','Chính sách & pháp lý','Dự án','Tin tức Đà Nẵng'];
export {categories};
export function useNews({featured=false,category='Tất cả',q='',sort='newest',page=0,revision=0}={}) {
  const [retry,setRetry]=useState(0),[state,setState]=useState({data:null,loading:true,error:''});
  const [now,setNow]=useState(Date.now);
  useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),60000);return()=>clearInterval(timer);},[]);
  useEffect(()=>{let active=true;setState(s=>({...s,loading:true,error:''}));
    const query=new URLSearchParams({category,q,sort,page:String(page),size:'12'});
    api(featured?'/news/featured':'/news?'+query,{authenticated:false}).then(data=>{if(active)setState({data,loading:false,error:''});}).catch(()=>{if(active)setState({data:null,loading:false,error:'Nguồn tin tức tạm thời không khả dụng. Vui lòng thử lại.'});});
    return()=>{active=false;};
  },[featured,category,q,sort,page,retry,revision]);
  return {...state,now,reload:()=>setRetry(n=>n+1)};
}
// Check metadata on tab return only; no network polling and no RSS refresh endpoint.
export function useNewsUpdateNotice(lastUpdatedAt) {
  const [available,setAvailable]=useState(false);
  useEffect(()=>{
    let active=true,pending=false,checkedAt=Date.now();
    setAvailable(false);
    const check=async()=>{
      if(document.visibilityState!=='visible'||pending||Date.now()-checkedAt<60000||!lastUpdatedAt)return;
      pending=true;checkedAt=Date.now();
      try{const sources=await api('/news/sources',{authenticated:false});if(active)setAvailable(hasNewNewsSnapshot(sources,lastUpdatedAt));}
      catch{/* Preserve the current articles; explicit update can retry. */}
      finally{pending=false;}
    };
    window.addEventListener('focus',check);document.addEventListener('visibilitychange',check);
    return()=>{active=false;window.removeEventListener('focus',check);document.removeEventListener('visibilitychange',check);};
  },[lastUpdatedAt]);
  return available;
}
export function safeNewsUrl(value){try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password?u.href:null;}catch{return null;}}
