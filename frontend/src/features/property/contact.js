// A contact is fetched only by an explicit action, never by the public detail loader.
export function createContact(request, now = Date.now) {
  let generation = 0;
  const state = {busy:false, data:null, message:'', status:0, retryAt:0};
  function reset(){generation++;Object.assign(state,{busy:false,data:null,message:'',status:0,retryAt:0})}
  async function reveal(id){
    if(state.busy || now()<state.retryAt)return;
    const run=++generation;Object.assign(state,{busy:true,data:null,message:'',status:0});
    try { const data=await request('/properties/'+encodeURIComponent(id)+'/contact');
      if(run!==generation)return;
      state.data=data?.available?{available:true,contactName:data.contactName,contactPhone:data.contactPhone,contactEmail:data.contactEmail}:{available:false};
      if(!state.data.available)state.message='Chủ tin chưa cung cấp liên hệ.';
    }catch(e){if(run!==generation)return;state.status=e.status||0;
      state.message=({401:'Vui lòng đăng nhập để xem liên hệ.',403:'Tài khoản chưa được phép xem liên hệ.',404:'Tin hoặc liên hệ không còn khả dụng.',429:'Bạn đã xem quá nhiều liên hệ. Vui lòng chờ trước khi thử lại.'})[e.status]||'Chưa tải được liên hệ. Bạn có thể thử lại.';
      if(e.status===429)state.retryAt=now()+Math.max(1,Math.min(3600,e.retryAfter||60))*1000;
    }finally{if(run===generation)state.busy=false}
  }
  return {state,reset,reveal};
}
