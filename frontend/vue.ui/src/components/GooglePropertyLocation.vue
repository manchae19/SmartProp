<script setup>
import {ref,computed,onMounted,onBeforeUnmount,watch,nextTick} from 'vue'
import {loadGoogleMaps,googleMapId,hasGoogleMapsKey} from '../services/googleMaps.js'
import {coordinatesFromPlace} from '../services/googleMapsLocation.js'
import {validCoordinates} from '../services/postForm.js'
import ManualLocationMap from './ManualLocationMap.vue'
const props=defineProps({address:{default:''},latitude:{default:''},longitude:{default:''},confirmed:Boolean,disabled:Boolean})
const emit=defineEmits(['select','confirm','invalidate'])
const searchHost=ref(null),mapHost=ref(null),ready=ref(false),loading=ref(false),selecting=ref(false),message=ref(''),suggestion=ref('')
const selected=computed(()=>validCoordinates(props.latitude,props.longitude))
let map,marker,autocomplete,disposed=false,revision=0;const cleanup=[]
function updateMarker(){if(!map||!marker)return;if(!selected.value){if(!suggestion.value)marker.map=null;return}const p={lat:Number(props.latitude),lng:Number(props.longitude)};marker.position=p;marker.map=map}
function movePin(latitude,longitude){if(props.disabled)return;revision++;selecting.value=false;suggestion.value='';emit('select',{latitude,longitude});message.value='Đã chọn ghim. Kiểm tra đúng địa chỉ và bấm Xác nhận vị trí.'}
function unavailable(){if(disposed)return;ready.value=false;suggestion.value='';if(marker)marker.map=null;message.value='Bản đồ Google chưa sẵn sàng. Bạn có thể đặt ghim trên bản đồ thủ công bên dưới.'}
async function initialize(){
 if(loading.value||disposed)return
 if(!hasGoogleMapsKey()&&!globalThis.google?.maps?.importLibrary)return
 loading.value=true;message.value=''
 try{
  const maps=await loadGoogleMaps();const [{Map:GoogleMap},{AdvancedMarkerElement}]=await Promise.all([maps.importLibrary('maps'),maps.importLibrary('marker')]);if(disposed)return
  ready.value=true;await nextTick();if(disposed)return
  const center=selected.value?{lat:Number(props.latitude),lng:Number(props.longitude)}:{lat:16.0544,lng:108.2022}
  map=new GoogleMap(mapHost.value,{center,zoom:selected.value?17:13,mapId:googleMapId(),mapTypeControl:false,streetViewControl:false,fullscreenControl:true,gestureHandling:'cooperative'})
  marker=new AdvancedMarkerElement({gmpDraggable:true,title:'Kéo ghim đến bất động sản rồi xác nhận vị trí'})
  const dragged=()=>{const p=marker.position;if(p)movePin(typeof p.lat==='function'?p.lat():p.lat,typeof p.lng==='function'?p.lng():p.lng)}
  if(marker.addEventListener){marker.addEventListener('gmp-dragend',dragged);cleanup.push(()=>marker.removeEventListener('gmp-dragend',dragged))}
  if(marker.addListener){const listener=marker.addListener('dragend',dragged);cleanup.push(()=>listener.remove())}
  const listener=map.addListener('click',event=>{if(event.latLng)movePin(event.latLng.lat(),event.latLng.lng())});cleanup.push(()=>listener.remove())
  updateMarker()
  try{
   const {PlaceAutocompleteElement}=await maps.importLibrary('places');if(disposed)return
   autocomplete=new PlaceAutocompleteElement({includedRegionCodes:['vn'],locationBias:{center:{lat:16.0544,lng:108.2022},radius:30000}})
   autocomplete.placeholder='Tìm địa chỉ để đưa bản đồ đến gần bất động sản';autocomplete.setAttribute('aria-label','Tìm địa chỉ trên Google Maps');searchHost.value.replaceChildren(autocomplete)
   autocomplete.addEventListener('input',()=>{revision++;selecting.value=false})
   autocomplete.addEventListener('gmp-error',()=>message.value='Dịch vụ tìm địa chỉ gặp lỗi. Kiểm tra kết nối, thử lại hoặc đặt ghim trực tiếp trên bản đồ.')
   autocomplete.addEventListener('gmp-select',async event=>{
    if(props.disabled)return;const current=++revision;selecting.value=true;suggestion.value='';message.value='';emit('invalidate')
    try{
     if(!event.placePrediction)throw Object.assign(Error(),{notFound:true})
     const place=event.placePrediction.toPlace();await place.fetchFields({fields:['formattedAddress','location','viewport','types']});if(disposed||current!==revision)return
     let point;try{point=coordinatesFromPlace(place)}catch{throw Object.assign(Error(),{notFound:true})}
     // Places content is transient: display it on Google only, never serialize it into the draft.
     suggestion.value=place.formattedAddress;marker.position={lat:point.latitude,lng:point.longitude};marker.map=map
     if(place.viewport)map.fitBounds(place.viewport);else{map.setCenter(marker.position);map.setZoom(17)}
     const precise=(place.types||[]).some(t=>['street_address','premise','subpremise'].includes(t))
     message.value=precise?'Đã tìm được gợi ý. Bấm bản đồ hoặc kéo ghim đến đúng bất động sản, rồi xác nhận.':'Kết quả chỉ xác định đường hoặc khu vực. Hãy chỉnh ghim đến đúng bất động sản trước khi xác nhận.'
    }catch(e){if(!disposed&&current===revision)message.value=e.notFound?'Không tìm thấy vị trí phù hợp cho địa chỉ này. Thử gợi ý khác hoặc đặt ghim trực tiếp.':'Không kết nối được dịch vụ tìm địa chỉ. Hãy thử lại hoặc đặt ghim trực tiếp trên bản đồ.'}finally{if(!disposed&&current===revision)selecting.value=false}
   })
  }catch{message.value='Gợi ý địa chỉ chưa sẵn sàng. Bạn vẫn có thể bấm bản đồ hoặc kéo ghim để chọn vị trí.'}
 }catch{unavailable()}finally{if(!disposed)loading.value=false}
}
watch(()=>[props.latitude,props.longitude],updateMarker)
watch(()=>props.address,()=>{revision++;suggestion.value='';message.value='Địa chỉ đã thay đổi. Hãy chọn và xác nhận lại ghim.';if(marker&&!selected.value)marker.map=null})
onMounted(()=>{globalThis.addEventListener('smartprop:google-maps-unavailable',unavailable);initialize()})
onBeforeUnmount(()=>{disposed=true;revision++;globalThis.removeEventListener('smartprop:google-maps-unavailable',unavailable);cleanup.forEach(fn=>fn());if(marker)marker.map=null;searchHost.value?.replaceChildren()})
</script>
<template>
 <div id="post-location" tabindex="-1" class="location-picker">
  <p class="location-guide">Chọn đúng vị trí bất động sản rồi xác nhận. Bạn không cần nhập kinh độ hoặc vĩ độ.</p>
  <div v-show="ready" ref="searchHost" class="google-search" :inert="disabled||undefined"/>
  <p v-if="ready&&suggestion" class="location-guide">Gợi ý trên Google: {{suggestion}}. Giữ địa chỉ tin đăng do bạn nhập ở trên.</p>
  <p v-if="loading||selecting" role="status" class="location-guide">{{loading?'Đang tải bản đồ…':'Đang tìm vị trí địa chỉ…'}}</p>
  <div v-show="ready" ref="mapHost" class="google-map" aria-label="Bản đồ Google chọn vị trí" />
  <template v-if="!ready&&!loading"><p class="location-guide">Gợi ý địa chỉ tự động chưa sẵn sàng. Đặt ghim thủ công trên bản đồ dưới đây.</p><ManualLocationMap :latitude="latitude" :longitude="longitude" :disabled="disabled" @select="movePin($event.latitude,$event.longitude)" /></template>
  <p v-if="message" role="status" class="location-message">{{message}}</p>
  <p v-if="!selected&&!suggestion" class="location-guide">Chưa chọn vị trí. Tâm bản đồ đang xem không được lưu thành vị trí của tin.</p>
  <div class="confirm-location" :class="{confirmed}"><div><strong>{{confirmed?'Đã xác nhận vị trí':selected?'Ghim đã chọn · cần xác nhận':'Chưa xác nhận vị trí'}}</strong><p>{{address||'Nhập địa chỉ đầy đủ trước khi xác nhận ghim.'}}</p></div><button type="button" :disabled="disabled||!selected||!String(address).trim()" @click="$emit('confirm')">{{confirmed?'Xác nhận lại':'Xác nhận vị trí'}}</button></div>
 </div>
</template>
<style scoped>
.location-guide,.location-message{font-size:12px;line-height:1.6;color:#586679;margin:10px 0}.location-message{color:#74552c}.google-map{height:320px;border-radius:14px;margin-top:12px}.google-search{margin:12px 0}.confirm-location{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:14px;border:1px solid #d9dfe7;border-radius:12px;margin-top:12px;color:#1e325a}.confirm-location strong{font-size:13px}.confirm-location p{font-size:12px;margin:4px 0 0;color:#5c6b7c;overflow-wrap:anywhere}.confirm-location button{flex-shrink:0;border:0;background:#1e325a;color:white;border-radius:9px;padding:11px 14px;font:inherit;font-size:12px}.confirm-location button:disabled{opacity:.5;cursor:not-allowed}.confirmed{background:#edf8f2;border-color:#a4cfb6}@media(max-width:600px){.confirm-location{align-items:stretch;flex-direction:column}.confirm-location button{width:100%}}
</style>
