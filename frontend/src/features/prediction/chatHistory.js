import {createStateStore} from '../../shared/state/createStateStore.js';

// No browser persistence. Both request and UI completion are bound to one identity.
export function createChatHistory(chat, request, identity) {
  const store = createStateStore({items:[], loading:false, selecting:false, error:null, loaded:false});
  let epoch = 0, listRun = 0, pending = null;
  function reset() {
    epoch++; listRun++; pending=null;
    store.set({items:[], loading:false, selecting:false, error:null, loaded:false});
  }
  async function refresh(force=false) {
    if (!identity()) return;
    if (pending) {
      const current = pending;
      await current;
      if (force) return refresh(true);
      return;
    }
    if (store.getSnapshot().loaded && !force) return;
    const owner=identity(), run=++listRun, current=epoch;
    store.edit(d=>{d.loading=true;d.error=null;});
    pending=(async()=>{
      try {
        const items=await request('/users/me/advisor-chats');
        if(current!==epoch || owner!==identity() || run!==listRun)return;
        if(!Array.isArray(items) || items.length>10 || items.some(i=>! /^[a-f0-9]{32}$/.test(i.id) || typeof i.title!=='string'))throw Error('Invalid history');
        store.edit(d=>{d.items=items;d.loaded=true;});
      } catch {
        if(current===epoch && owner===identity())store.edit(d=>d.error='Không tải được lịch sử hội thoại. Hãy thử lại.');
      } finally {
        if(current===epoch && run===listRun){pending=null;store.edit(d=>d.loading=false);}
      }
    })();
    return pending;
  }
  async function select(id) {
    if(chat.getSnapshot().state.busy || store.getSnapshot().selecting || !identity())return false;
    if(!/^[a-f0-9]{32}$/.test(id))return false;
    const owner=identity(), current=epoch;
    chat.getSnapshot().reset();
    chat.getSnapshot().updateState(d=>d.busy=true);
    store.edit(d=>{d.selecting=true;d.error=null;});
    try {
      const saved=await request('/users/me/advisor-chats/'+id);
      if(current!==epoch || owner!==identity())return false;
      if(saved.id!==id)throw Error('Invalid history');
      chat.getSnapshot().restore(saved);
      return true;
    }catch{
      if(current===epoch && owner===identity()){
        chat.getSnapshot().reset();
        store.edit(d=>d.error='Không mở được hội thoại hoặc bạn không còn quyền truy cập. Hãy chọn lại.');
      }
      return false;
    }finally{
      if(current===epoch)store.edit(d=>d.selecting=false);
    }
  }
  async function remove(id) {
    if(!identity() || chat.getSnapshot().state.busy || store.getSnapshot().selecting || !/^[a-f0-9]{32}$/.test(id)) return false;
    const owner=identity(), current=epoch;
    store.edit(d=>{d.selecting=true;d.error=null;});
    try {
      await request('/users/me/advisor-chats/'+id,{method:'DELETE'});
      if(current!==epoch || owner!==identity())return false;
      if(chat.getSnapshot().state.sessionId===id)chat.getSnapshot().reset();
      store.edit(d=>d.items=d.items.filter(x=>x.id!==id));
      await refresh(true);return true;
    }catch{if(current===epoch && owner===identity())store.edit(d=>d.error='Không xóa được hội thoại. Vui lòng thử lại.');return false;}
    finally{if(current===epoch)store.edit(d=>d.selecting=false);}
  }
  return {...store,refresh,select,reset,remove};
}
