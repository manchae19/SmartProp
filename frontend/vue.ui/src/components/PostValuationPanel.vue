<script setup>
import {computed,reactive,ref,watch,onMounted,onBeforeUnmount} from 'vue'
import {api} from '../services/api.js'
import {categoryFor,valuationInput,createPreviewState,exactVnd} from '../services/valuation.js'
const props=defineProps({draft:{type:Object,required:true}})
const options=ref(null),optionsError=ref(''),loading=ref(false)
const state=reactive({busy:false,result:null,error:''})
const preview=createPreviewState(body=>api('/properties/valuation-preview',{method:'POST',body}),state)
let disposed=false
const locations=computed(()=>options.value?.categories?.find(c=>c.category===categoryFor(props.draft.propertyType))?.locations||[])
const location=computed(()=>locations.value.includes(props.draft.valuationLocation)?props.draft.valuationLocation:'')
const input=computed(()=>valuationInput(props.draft,location.value))
function pickDistrict(){const district=props.draft.district==='Hoà Vang'?'Hòa Vang':props.draft.district
 if(!locations.value.includes(props.draft.valuationLocation))props.draft.valuationLocation=locations.value.includes(district)?district:''}
watch([locations,()=>props.draft.district],pickDistrict,{immediate:true})
watch(()=>JSON.stringify([input.value,props.draft.propertyType,props.draft.district,props.draft.price,props.draft.address,props.draft.latitude,props.draft.longitude]),()=>preview.invalidate(),{flush:'sync'})
async function loadOptions(){loading.value=true;optionsError.value=''
 try{const value=await api('/properties/valuation-options');if(!disposed)options.value=value}
 catch(e){if(!disposed)optionsError.value=e.message}
 finally{if(!disposed)loading.value=false}
}
onMounted(loadOptions);onBeforeUnmount(()=>{disposed=true;preview.dispose()})
const featureLabels={areaSqm:'Diện tích (m²)',locationFeature:'Khu vực',rooms:'Phòng ngủ',floors:'Số tầng',access_type:'Đường tiếp cận',house_subtype:'Kiểu nhà'}
const missingLabel=value=>({...featureLabels,ward_source:'Phường/xã',access_type:'Đường tiếp cận',house_subtype:'Kiểu nhà'})[value]||value
const featureValue=value=>({alley:'Trong kiệt/hẻm',frontage:'Mặt tiền',villa:'Biệt thự',house_c4:'Nhà cấp 4'})[value]||value
</script>
<template>
 <section data-testid="valuation-panel" class="bg-[#1E325A] text-white rounded-[22px] p-6">
  <h2 class="text-xs tracking-[0.18em] text-white/60">GIÁ THAM CHIẾU XGBOOST · v6</h2>
  <div data-testid="valuation-price" aria-live="polite" class="text-xl font-light mt-3 break-words">{{state.result?.available?exactVnd(state.result.predictedAskingPriceVnd):'—'}}</div>
  <p class="text-xs text-white/70 mt-2">Giá rao ước tính; giá chào của bạn được giữ nguyên.</p>
  <label class="block mt-5 text-xs">Khu vực tham khảo
   <select data-testid="valuation-location" :value="location" @change="draft.valuationLocation=$event.target.value" class="mt-2 w-full bg-white text-[#1E325A] rounded-lg p-2" :disabled="loading||!locations.length">
    <option value="">Chọn đúng khu vực</option><option v-for="item in locations" :key="item" :value="item">{{item}}</option>
   </select>
  </label>
  <p class="text-xs text-white/60 mt-2">Địa bàn theo dữ liệu model. Hãy chọn khu vực tương ứng với địa chỉ thực tế.</p>
  <p v-if="optionsError" role="status" class="mt-3 text-xs text-amber-200">{{optionsError}} <button type="button" class="underline" @click="loadOptions">Thử lại</button></p>
  <p v-else-if="input.reason" class="mt-3 text-xs text-white/80">{{input.reason}}</p>
  <button type="button" data-testid="valuation-preview" :disabled="loading||state.busy||!options||!!input.reason" @click="preview.preview(input.body)" class="mt-4 w-full rounded-full border border-white/40 py-2 text-xs disabled:opacity-50">{{state.busy?'Đang tính…':'Xem giá tham khảo'}}</button>
  <p v-if="state.error" role="status" class="mt-3 text-xs text-amber-200">{{state.error}}</p>
  <p v-if="state.result&&!state.result.available" role="status" class="mt-3 text-xs">{{state.result.reason}}</p>
  <div v-if="state.result?.available" class="mt-5 border-t border-white/10 pt-4 text-xs space-y-2">
   <h3 class="font-semibold">Thông tin model đã dùng</h3>
   <p v-for="(value,key) in state.result.featuresUsed" :key="key">{{featureLabels[key]||key}}: {{featureValue(value)}}</p>
   <p v-if="state.result.missingFeatures?.length">Chưa có: {{state.result.missingFeatures.map(missingLabel).join(', ')}}</p>
   <p v-for="(warning,index) in state.result.warnings" :key="index" class="text-amber-200">{{warning}}</p>
  </div>
  <p class="mt-5 text-xs text-white/60 leading-relaxed">Thông tin tham khảo, không phải kết quả thẩm định chính thức. Không có kết quả vẫn có thể lưu hoặc gửi tin.</p>
 </section>
</template>
