<script setup>
import {computed,ref,watch,onMounted,onBeforeUnmount} from 'vue'
import {hasGoogleMapsKey,loadGoogleMaps,googleMapId} from '../services/googleMaps.js'
import {mapPoints} from '../services/districts.js'
import {mapUrl} from '../services/property.js'
const props=defineProps({items:{type:Array,default:()=>[]},selectedId:String}),emit=defineEmits(['select']);
const points=computed(()=>mapPoints(props.items)),selected=computed(()=>points.value.find(p=>p.id===props.selectedId)||points.value[0]);
const container=ref(null),ready=ref(false),unavailable=ref(false);let map,markerLibrary,maps,markers=[],disposed=false;
function clear(){for(const marker of markers){maps?.event?.clearInstanceListeners(marker);marker.map=null}markers=[]}
function render(){if(!map||!markerLibrary)return;clear();const bounds=new maps.LatLngBounds();for(const p of points.value){const pin=new markerLibrary.AdvancedMarkerElement({map,position:{lat:p.latitude,lng:p.longitude},title:p.title||'Bất động sản',gmpClickable:true});pin.addListener('click',()=>emit('select',p.id));markers.push(pin);bounds.extend({lat:p.latitude,lng:p.longitude})}if(points.value.length===1){map.setCenter({lat:points.value[0].latitude,lng:points.value[0].longitude});map.setZoom(15)}else if(points.value.length)map.fitBounds(bounds,48)}
watch(points,render);watch(()=>props.selectedId,()=>{const p=selected.value;if(map&&p)map.panTo({lat:p.latitude,lng:p.longitude})});
onMounted(async()=>{if(!hasGoogleMapsKey()&&!globalThis.google?.maps?.importLibrary)return;try{maps=await loadGoogleMaps();markerLibrary=await maps.importLibrary('marker');if(disposed)return;map=new maps.Map(container.value,{center:{lat:16.06,lng:108.22},zoom:12,mapId:googleMapId(),streetViewControl:false,fullscreenControl:true});ready.value=true;render()}catch{unavailable.value=true}});
onBeforeUnmount(()=>{disposed=true;clear();if(map)maps?.event?.clearInstanceListeners(map);map=null});
</script>
<template><div class="absolute inset-0 bg-[#e7e2d8]"><div ref="container" class="h-full w-full" aria-label="Bản đồ bất động sản"></div>
<div v-if="!ready" class="absolute inset-0"><iframe v-if="selected" :src="mapUrl(selected)" title="Vị trí tin đăng" class="h-full w-full border-0" loading="lazy"></iframe><p v-else class="p-8">Chưa có tọa độ hợp lệ để hiển thị.</p></div>
<p class="absolute bottom-2 left-2 right-2 z-10 rounded bg-white/95 p-3 text-xs" role="status">{{ready?points.length+' điểm trên trang hiện tại.':(unavailable?'Google Maps tạm không khả dụng. ':'Chưa cấu hình Google Maps. ')+'Bản đồ dự phòng chỉ ghim tin đang chọn; chọn tin khác từ danh sách.'}}</p>
</div></template>
