// Refresh is explicit opt-in. Tokens stay in memory; cookie is HttpOnly and never read here.
export function createHttpClient({baseUrl,session,refreshEnabled=false,fetcher=(...args)=>fetch(...args),expired=()=>{},clear=()=>{},lock=null}){
 let refreshFlight=null,epoch=0;
 async function send(path,{method='GET',body,authenticated=true,responseType='json',headers:extra={}}={}){
  const headers={Accept:'application/json',...extra};const multipart=typeof FormData!=='undefined'&&body instanceof FormData;
  if(body!==undefined&&!multipart)headers['Content-Type']='application/json';if(authenticated&&session.token)headers.Authorization='Bearer '+session.token;
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
  try{const response=await fetcher(baseUrl+path,{method,headers,body:body===undefined?undefined:multipart?body:JSON.stringify(body),signal:controller.signal,...(refreshEnabled?{credentials:'include'}:{})});
   const data=response.status===204?null:response.ok&&responseType==='blob'?await response.blob():await response.json().catch(()=>null);
   if(!response.ok){const e=Error(data?.message||'Yêu cầu thất bại ('+response.status+')');e.status=response.status;e.code=data?.code;e.fields=data?.fields||{};const retry=response.headers.get('Retry-After');e.retryAfter=retry&&/^\d+$/.test(retry)?Number(retry):undefined;throw e}return data;
  }catch(e){if(e.status)throw e;throw Error(e.name==='AbortError'?'Yêu cầu quá thời gian. Vui lòng thử lại.':'Không thể kết nối máy chủ. Vui lòng kiểm tra kết nối.')}finally{clearTimeout(timeout)}
 }
 const csrf=()=>send('/auth/csrf',{authenticated:false});
 async function rotate(){const current=epoch;const run=async()=>{const c=await csrf();const result=await send('/auth/refresh',{method:'POST',authenticated:false,headers:{[c.headerName]:c.token}});if(current!==epoch)throw Object.assign(Error('Phiên đã thay đổi.'),{status:401});session.token=result.accessToken;session.user=result.user;return result};if(!refreshFlight)refreshFlight=(lock?lock(run):run()).finally(()=>refreshFlight=null);return refreshFlight}
 function invalidate(){epoch++}
 function expire(){invalidate();clear();expired()}
 async function request(path,options={}){const sentToken=session.token,current=epoch;try{return await send(path,options)}catch(e){
  if(options.authenticated!==false&&e.status===401){
   if(refreshEnabled&&sentToken&&current===epoch){try{if(session.token===sentToken)await rotate();if(current!==epoch)throw e;return await send(path,options)}catch(next){if(current===epoch)expire();throw next}}
   if(current===epoch)expire();
  }throw e;
 }}
 async function logout(){if(refreshEnabled){const c=await csrf();await send('/auth/logout',{method:'POST',authenticated:false,headers:{[c.headerName]:c.token}})}else await request('/auth/logout',{method:'POST'});invalidate();clear()}
 return {request,logout,invalidate,restore:async()=>{if(!refreshEnabled)return false;try{await rotate();return true}catch{return false}},login:body=>send('/auth/login',{method:'POST',authenticated:false,body,headers:refreshEnabled?{'X-Refresh-Session':'true'}:{}})};
}
