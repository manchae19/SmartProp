import {reactive,watch} from '../../shared/state/store.js';import {api,session} from '../auth/api.js';
export const notifications=reactive({count:null,error:false});let sequence=0;
watch(()=>session.user?.id,()=>{sequence++;notifications.count=null;notifications.error=false});
export async function refreshUnread(){if(!session.token)return;const run=++sequence;try{const result=await api('/users/me/notifications/unread-count');if(run===sequence){notifications.count=result.count;notifications.error=false}}catch{if(run===sequence){notifications.error=true;notifications.count=null}}}
