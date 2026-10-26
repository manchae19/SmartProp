<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { hasGoogleMapsKey, loadGoogleMaps, googleMapId } from '../services/googleMaps.js'
import { mapPoints } from '../services/districts.js'
import { mapUrl, price } from '../services/property.js'
import { locationLabel } from '../services/locationDisplay.js'

const props = defineProps({ items: { type: Array, default: () => [] }, selectedId: String, showCard: Boolean })
const emit = defineEmits(['select'])
const points = computed(() => mapPoints(props.items))
// An invalid/missing selected point must never be represented by another property's marker.
const selected = computed(() => props.selectedId ? points.value.find(point => point.id === props.selectedId) || null : points.value[0] || null)
const container = ref(null), ready = ref(false), unavailable = ref(false)
let map, markerLibrary, maps, markers = [], disposed = false

function clear() {
  for (const marker of markers) { maps?.event?.clearInstanceListeners(marker); marker.map = null }
  markers = []
}
function focus() {
  const point = selected.value
  if (!map) return
  if (point) {
    map.panTo({ lat: point.latitude, lng: point.longitude })
    map.setZoom(Math.max(map.getZoom?.() || 15, 15))
  }
  for (const marker of markers) {
    const active = !!point && marker.propertyId === point.id
    marker.zIndex = active ? 100 : 1
    if (marker.content) {
      marker.content.style.background = active ? '#b3915f' : '#142b4f'
      marker.content.style.transform = active ? 'scale(1.18)' : 'scale(1)'
      marker.content.setAttribute('aria-label', (active ? 'Tin đang chọn: ' : '') + marker.title)
    }
  }
}
function render() {
  if (!map || !markerLibrary) return
  clear()
  const bounds = new maps.LatLngBounds()
  for (const point of points.value) {
    const content = document.createElement('div')
    content.textContent = '●'
    Object.assign(content.style, { color: 'white', background: '#142b4f', border: '3px solid white', borderRadius: '50%', width: '30px', height: '30px', textAlign: 'center', lineHeight: '24px', boxShadow: '0 2px 8px #0005' })
    const marker = new markerLibrary.AdvancedMarkerElement({ map, position: { lat: point.latitude, lng: point.longitude }, title: point.title || 'Bất động sản', gmpClickable: true, content })
    marker.propertyId = point.id
    marker.addListener('click', () => emit('select', point.id))
    markers.push(marker)
    bounds.extend({ lat: point.latitude, lng: point.longitude })
  }
  if (selected.value) focus()
  else if (points.value.length && !props.selectedId) map.fitBounds(bounds, 48)
}
watch(points, render)
watch(() => props.selectedId, focus)
onMounted(async () => {
  if (!hasGoogleMapsKey() && !globalThis.google?.maps?.importLibrary) return
  try {
    maps = await loadGoogleMaps()
    markerLibrary = await maps.importLibrary('marker')
    if (disposed) return
    const point = selected.value
    map = new maps.Map(container.value, { center: point ? { lat: point.latitude, lng: point.longitude } : { lat: 16.06, lng: 108.22 }, zoom: point ? 15 : 12, mapId: googleMapId(), streetViewControl: false, fullscreenControl: true })
    ready.value = true
    render()
  } catch { if (!disposed) unavailable.value = true }
})
onBeforeUnmount(() => { disposed = true; clear(); if (map) maps?.event?.clearInstanceListeners(map); map = null })
</script>

<template>
  <div class="absolute inset-0 bg-[#e7e2d8]">
    <div ref="container" class="h-full w-full" aria-label="Bản đồ bất động sản"></div>
    <div v-if="!ready" class="absolute inset-0"><iframe v-if="selected" :key="selected.id" :src="mapUrl(selected)" title="Vị trí tin đăng đang chọn" class="h-full w-full border-0" loading="lazy"></iframe><p v-else class="p-8">Tin đang chọn chưa có tọa độ hợp lệ để hiển thị.</p></div>
    <p v-if="ready && selectedId && !selected" class="absolute left-4 right-4 top-1/2 rounded-xl bg-white/95 p-4 text-sm text-[#142B4F]">Tin đang chọn chưa có vị trí được phép hiển thị; các ghim khác thuộc những tin khác.</p>
    <div v-if="showCard && selected" class="absolute bottom-24 left-4 right-4 z-10 max-w-sm rounded-2xl bg-white/95 p-4 text-[#142B4F] shadow-lg">
      <strong class="block text-sm">{{ selected.title }}</strong><p class="mt-1 text-sm font-semibold">{{ price(selected) }}</p><p class="mt-1 text-xs">{{ [selected.address, selected.ward, selected.district, selected.city].filter(Boolean).join(', ') }}</p><p class="mt-2 text-xs text-[#637083]">{{ locationLabel(selected) }}</p><RouterLink :to="'/listing/' + selected.id" class="mt-3 inline-block rounded-full bg-[#142B4F] px-4 py-2 text-xs font-semibold text-white">Xem chi tiết ↗</RouterLink>
    </div>
    <div class="absolute bottom-2 left-2 right-2 z-10 rounded bg-white/95 p-2 text-[10px] leading-5 text-[#142B4F]" role="status">
      <p>{{ ready ? points.length + ' điểm trên trang hiện tại.' : (unavailable ? 'Google Maps tạm không khả dụng. ' : '') + 'Bản đồ dự phòng ghim tin đang chọn.' }} {{ selected ? locationLabel(selected) : 'Không dùng vị trí mặc định thay cho bất động sản.' }}</p>
      <p>Công cụ tìm địa chỉ: <a href="https://www.geoapify.com/" target="_blank" rel="noopener noreferrer" class="underline">Geoapify</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer" class="underline">© OpenStreetMap contributors</a></p>
    </div>
  </div>
</template>
