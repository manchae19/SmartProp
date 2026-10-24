import {reactive,watch,onMounted,onBeforeUnmount} from 'vue'
import {api} from './api.js'
import {createPagedResource} from './pagedResource.js'
export function isPublicProperty(p,now=Date.now()){
 return !!p&&p.status==='PUBLISHED'&&!p.deletedAt&&!p.hiddenAt&&(p.expiresAt==null||Date.parse(p.expiresAt)>now)
}
export function usePublicListings(filters,{size=20,delay=180}={}){
 const request=async path=>{const result=await api(path,{authenticated:false});return {...result,items:(result.items||[]).filter(p=>isPublicProperty(p))}}
 const state=createPagedResource(request,'/properties',filters,null,reactive,{size});let timer
 watch(()=>JSON.stringify(filters()),()=>{clearTimeout(timer);state.invalidate();state.error='';state.busy=true;timer=setTimeout(()=>state.load(),delay)},{flush:'sync'})
 onMounted(()=>state.load());onBeforeUnmount(()=>{clearTimeout(timer);state.dispose()})
 return state
}
