import {reactive,onMounted,onBeforeUnmount,watch} from 'vue'
import {api,errorText} from './api.js'
import {createPagedResource} from './pagedResource.js'
export function useCollection(endpoint,summaryEndpoint,filters){const request=async(...args)=>{try{return await api(...args)}catch(e){e.message=errorText(e);throw e}};const state=createPagedResource(request,endpoint,filters,summaryEndpoint,reactive);let timer;watch(filters,()=>{clearTimeout(timer);state.invalidate();timer=setTimeout(()=>state.load(0),250)},{deep:true});onMounted(()=>state.reload());onBeforeUnmount(()=>{clearTimeout(timer);state.dispose()});return state}
export const ownStatus={draft:'DRAFT',showing:'PUBLISHED',pending:'PENDING',rejected:'REJECTED',hidden:'HIDDEN',closed:'CLOSED',expired:'EXPIRED'};
export const typeCode={'Nhà phố':'HOUSE','Căn hộ':'APARTMENT','Đất nền':'LAND','Biệt thự':'VILLA','Phòng trọ':'ROOM','Kho / Mặt bằng':'COMMERCIAL'};
