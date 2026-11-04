<script setup>
import {ref,computed,onMounted,onBeforeUnmount,watch} from 'vue'
import {validCoordinates} from '../property/postForm.js'
import {projectPoint,unprojectPoint,visibleTiles} from './postMap.js'
import {projectPreviewRegion} from './locationPreview.js'
const props=defineProps({latitude:{default:''},longitude:{default:''},disabled:Boolean,preview:Boolean,precision:String,previewRegion:Object})
const emit=defineEmits(['select'])
// This initial center is only a viewport. No point is selected until a deliberate action.
const center=ref(validCoordinates(props.latitude,props.longitude)?{latitude:Number(props.latitude),longitude:Number(props.longitude)}:{latitude:16.0544,longitude:108.2022})
const previewZoom=()=>props.preview?(props.precision==='APPROXIMATE_AREA'?13:props.precision==='APPROXIMATE_STREET'?15:17):17
const zoom=ref(validCoordinates(props.latitude,props.longitude)?previewZoom():13),host=ref(null),width=ref(600),failed=ref(false),attempt=ref(0),hint=ref(''),draggingPin=ref(null)
const height=320,tiles=computed(()=>visibleTiles(center.value,zoom.value,width.value,height))
const areaOverlay=computed(()=>props.preview?projectPreviewRegion(props.previewRegion,center.value,zoom.value,width.value,height):null)
const template=import.meta.env?.VITE_OSM_TILE_URL||'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const validTemplate=template.startsWith('https://')&&['{z}','{x}','{y}'].every(v=>template.includes(v))
function tileUrl(tile){return validTemplate?template.replace('{z}',tile.z).replace('{x}',tile.x).replace('{y}',tile.y):''}
const marker=computed(()=>{const point=draggingPin.value||{latitude:props.latitude,longitude:props.longitude};if(!validCoordinates(point.latitude,point.longitude))return null;const p=projectPoint(Number(point.latitude),Number(point.longitude),zoom.value),c=projectPoint(center.value.latitude,center.value.longitude,zoom.value);return {left:p.x-c.x+width.value/2,top:p.y-c.y+height/2}})
watch(()=>[props.latitude,props.longitude,props.preview,props.precision],()=>{if(validCoordinates(props.latitude,props.longitude)){center.value={latitude:Number(props.latitude),longitude:Number(props.longitude)};zoom.value=previewZoom()}})
let observer,drag
function pan(dx,dy){const c=projectPoint(center.value.latitude,center.value.longitude,zoom.value);center.value=unprojectPoint(c.x+dx,c.y+dy,zoom.value)}
function changeZoom(delta){if(!props.disabled)zoom.value=Math.max(3,Math.min(19,zoom.value+delta))}
function selectAt(x,y){if(props.disabled)return;const c=projectPoint(center.value.latitude,center.value.longitude,zoom.value),wx=c.x+x-width.value/2,wy=c.y+y-height/2,n=2**zoom.value,tx=((Math.floor(wx/256)%n)+n)%n,ty=Math.floor(wy/256),key=zoom.value+'/'+tx+'/'+ty;const tile=[...(host.value?.querySelectorAll('[data-tile-key]')||[])].find(image=>image.dataset.tileKey===key);if(!tile?.complete||!tile.naturalWidth){hint.value='Phần bản đồ này chưa tải được. Hãy kiểm tra kết nối và thử lại trước khi chọn ghim.';return}const point=unprojectPoint(wx,wy,zoom.value);if(!validCoordinates(point.latitude,point.longitude))return;hint.value='Đã đặt ghim. Kiểm tra địa chỉ rồi bấm Xác nhận vị trí.';emit('select',point)}
function pointerDown(event){if(props.disabled||event.button!==0||event.target.closest('[data-map-control]'))return;const box=host.value.getBoundingClientRect();drag={x:event.clientX,y:event.clientY,box,center:{...center.value},pin:!!event.target.closest('[data-location-pin]')};host.value.setPointerCapture(event.pointerId)}
function pointerMove(event){if(!drag)return;const p=projectPoint(drag.center.latitude,drag.center.longitude,zoom.value);if(drag.pin){draggingPin.value=unprojectPoint(p.x+event.clientX-drag.box.left-width.value/2,p.y+event.clientY-drag.box.top-height/2,zoom.value);return}center.value=unprojectPoint(p.x-(event.clientX-drag.x),p.y-(event.clientY-drag.y),zoom.value)}
function pointerUp(event){if(!drag)return;const start=drag;drag=null;draggingPin.value=null;if(start.pin||Math.hypot(event.clientX-start.x,event.clientY-start.y)<5)selectAt(event.clientX-start.box.left,event.clientY-start.box.top);try{host.value.releasePointerCapture(event.pointerId)}catch{}}
function cancelDrag(){drag=null;draggingPin.value=null}
function keyboard(event){if(props.disabled)return;const moves={ArrowLeft:[-64,0],ArrowRight:[64,0],ArrowUp:[0,-64],ArrowDown:[0,64]};if(moves[event.key]){event.preventDefault();pan(...moves[event.key])}else if(event.key==='Enter'||event.key===' '){event.preventDefault();selectAt(width.value/2,height/2)}else if(event.key==='+'||event.key==='='){event.preventDefault();changeZoom(1)}else if(event.key==='-'){event.preventDefault();changeZoom(-1)}}
function retry(){failed.value=false;hint.value='';attempt.value++}
onMounted(()=>{observer=new ResizeObserver(entries=>width.value=Math.max(1,entries[0].contentRect.width));observer.observe(host.value)})
onBeforeUnmount(()=>observer?.disconnect())
</script>
<template>
 <div class="manual-map-wrap">
  <p id="manual-map-help" class="map-help">Bấm bản đồ để đặt ghim, kéo để di chuyển bản đồ hoặc kéo ghim để chỉnh. Dùng phím mũi tên rồi Enter để chọn điểm giữa bản đồ.</p>
  <div ref="host" class="manual-map" tabindex="0" role="region" aria-label="Bản đồ chọn vị trí bất động sản" aria-describedby="manual-map-help" :aria-disabled="disabled||undefined" @pointerdown="pointerDown" @pointermove="pointerMove" @pointerup="pointerUp" @pointercancel="cancelDrag" @keydown="keyboard">
   <img v-for="tile in tiles" :key="attempt+':'+tile.key" :src="tileUrl(tile)" alt="" draggable="false" referrerpolicy="strict-origin-when-cross-origin" class="map-tile" :data-tile-key="tile.key" :style="{left:tile.left+'px',top:tile.top+'px'}" @error="failed=true" />
   <svg v-if="areaOverlay" class="location-area" :viewBox="'0 0 '+width+' '+height" role="img" aria-label="Vùng minh họa quanh ghim đề xuất" data-location-area="illustrative"><title>Vùng minh họa, không phải bán kính sai số đã xác minh</title><circle :cx="areaOverlay.cx" :cy="areaOverlay.cy" :r="areaOverlay.radius" /></svg>
   <span class="map-crosshair" aria-hidden="true">+</span>
   <span v-if="marker" data-location-pin class="location-pin" :style="{left:marker.left+'px',top:marker.top+'px'}" role="img" :aria-label="preview?'Ghim đề xuất chưa xác nhận':'Ghim vị trí đã chọn'" :class="{'preview-pin':preview}">●</span>
   <div data-map-control class="map-controls" @pointerdown.stop @keydown.stop><button type="button" :disabled="disabled||zoom>=19" aria-label="Phóng to bản đồ" @click="changeZoom(1)">+</button><button type="button" :disabled="disabled||zoom<=3" aria-label="Thu nhỏ bản đồ" @click="changeZoom(-1)">−</button></div>
   <button type="button" data-map-control class="choose-center" :disabled="disabled" @pointerdown.stop @keydown.stop @click="selectAt(width/2,height/2)">Đặt ghim ở dấu +</button>
   <a data-map-control href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer" class="map-attribution" @pointerdown.stop @keydown.stop>© OpenStreetMap contributors</a>
  </div>
  <p v-if="areaOverlay" class="area-explanation"><span aria-hidden="true" class="area-swatch"/><span>{{previewRegion.label}}</span></p>
  <p v-if="failed||!validTemplate" role="status" class="map-error">Chưa tải đầy đủ bản đồ. Kiểm tra mạng rồi <button type="button" class="underline" @click="retry">thử lại</button>. Chỉ chọn được ghim ở phần bản đồ đã tải.</p>
  <p v-if="hint" role="status" class="map-help">{{hint}}</p>
 </div>
</template>
<style scoped>
.location-area{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:hidden}.location-area circle{fill:#16a34a;fill-opacity:.17;stroke:#15803d;stroke-width:2;stroke-dasharray:6 4;vector-effect:non-scaling-stroke}.area-explanation{display:flex;gap:9px;align-items:flex-start;margin:12px 0;padding:11px 13px;border:1px solid #b9dfc5;border-radius:10px;background:#f0faf3;color:#26573c;font-size:12px;line-height:1.7}.area-swatch{width:14px;height:14px;flex-shrink:0;border:1.5px dashed #15803d;border-radius:50%;background:#16a34a2b;margin-top:3px}
.preview-pin{background:#b77922!important}

.manual-map{height:320px;position:relative;overflow:hidden;isolation:isolate;background:#e9ece7;border:1px solid #d5dbd6;border-radius:14px;cursor:grab;touch-action:none;outline-offset:3px}.manual-map:active{cursor:grabbing}.manual-map:focus-visible{outline:3px solid #b48b51}.map-tile{position:absolute;width:256px;height:256px;max-width:none;user-select:none;pointer-events:none}.map-crosshair{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font:25px Arial;color:#243b55;text-shadow:0 0 3px white;pointer-events:none}.location-pin{position:absolute;transform:translate(-50%,-100%);width:30px;height:38px;line-height:28px;text-align:center;background:#1e325a;color:white;border:3px solid white;border-radius:50% 50% 50% 0;rotate:-45deg;box-shadow:0 2px 8px #0005;cursor:move;touch-action:none}.map-controls{position:absolute;right:10px;top:10px;display:grid;gap:3px}.map-controls button{width:34px;height:34px;border:1px solid #ccd3dc;background:white;color:#1e325a;font-size:22px;border-radius:7px}.choose-center{position:absolute;left:10px;bottom:28px;padding:8px 12px;border:1px solid #cbd1d8;border-radius:8px;background:white;color:#1e325a;font-size:12px}.map-attribution{position:absolute;bottom:0;right:0;padding:3px 6px;background:#fffe;color:#1e325a;font-size:13px}.map-help,.map-error{font-size:12px;line-height:1.6;color:#576777;margin:10px 0}.map-error{color:#9a3412}button:disabled{opacity:.5;cursor:not-allowed}
</style>
