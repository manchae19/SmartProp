<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { hasGoogleMapsKey, loadGoogleMaps, googleMapId } from './googleMaps.js'
import { mapPoints } from './districts.js'
import BrowseTileMap from './BrowseTileMap.vue'
import { price } from '../property/property.js'
import { locationLabel } from './locationDisplay.js'
import { poiHasPoint, poiSymbol, poiLabel, poiColor, poiSvgIcon } from './nearbyPlaces.js'

const props = defineProps({ items: { type: Array, default: () => [] }, selectedId: String, showCard: Boolean, poiItems: { type: Array, default: () => [] }, selectedPoiId: String })
const emit = defineEmits(['select', 'select-poi'])
const points = computed(() => mapPoints(props.items))
// An invalid/missing selected point must never be represented by another property's marker.
const selected = computed(() => props.selectedId ? points.value.find(point => point.id === props.selectedId) || null : points.value[0] || null)
const poiPoints = computed(() => selected.value ? props.poiItems.filter(p => poiHasPoint(p) && typeof p.id === 'string' && p.name) : [])
const container = ref(null), ready = ref(false), unavailable = ref(false)
let map = null, markers = [], maps = null, markerLibrary = null, disposed = false
function clear() { markers.forEach(marker => { marker.map = null }); markers = [] }
function focus() {
  if (!map) return
  if (props.selectedPoiId) {
    const poi = props.poiItems.find(p => p.id === props.selectedPoiId)
    if (poi) { map.panTo({ lat: poi.latitude, lng: poi.longitude }); map.setZoom(16) }
    return
  }
  const point = selected.value
  if (!point) return
  map.panTo({ lat: point.latitude, lng: point.longitude })
  map.setZoom(15)
}
function render() {
  if (!ready.value || !map || !markerLibrary) return
  clear()
  const bounds = new maps.LatLngBounds()
  for (const point of points.value) {
    const isSelected = selected.value?.id === point.id
    const pin = new markerLibrary.PinElement({
      background: isSelected ? '#b68a4c' : point.transactionType === 'RENT' ? '#207760' : '#142b4f',
      glyphColor: '#ffffff',
      borderColor: '#ffffff',
      scale: isSelected ? 1.25 : 1.0,
    })
    const marker = new markerLibrary.AdvancedMarkerElement({
      map,
      position: { lat: point.latitude, lng: point.longitude },
      title: point.title + ' · ' + price(point),
      gmpClickable: true,
      content: pin.element,
    })
    marker.propertyId = point.id
    marker.baseColor = point.transactionType === 'RENT' ? '#207760' : '#142b4f'
    marker.addListener('click', () => emit('select', point.id))
    markers.push(marker)
    bounds.extend({ lat: point.latitude, lng: point.longitude })
  }
  for (const point of poiPoints.value) {
    const content = document.createElement('div')
    const color = poiColor(point.category)
    const isSelected = props.selectedPoiId === point.id
    Object.assign(content.style, {
      color: 'white',
      background: color,
      border: isSelected ? '3px solid #10233f' : '2px solid white',
      borderRadius: '9px',
      width: isSelected ? '34px' : '28px',
      height: isSelected ? '34px' : '28px',
      display: 'grid',
      placeItems: 'center',
      boxShadow: '0 3px 10px rgba(0,0,0,0.3)',
      cursor: 'pointer',
      transform: isSelected ? 'scale(1.2)' : 'scale(1)',
      transition: 'all 0.15s ease'
    })
    content.innerHTML = poiSvgIcon(point.category)
    const marker = new markerLibrary.AdvancedMarkerElement({
      map,
      position: { lat: point.latitude, lng: point.longitude },
      title: point.name + ' · ' + poiLabel(point.category),
      gmpClickable: true,
      content
    })
    marker.poiId = point.id; marker.baseColor = color
    marker.addListener('click', () => emit('select-poi', point.id))
    markers.push(marker)
  }
  if (selected.value) focus()
  else if (points.value.length && !props.selectedId) map.fitBounds(bounds, 48)
}
watch([points, poiPoints], render)
watch(() => props.selectedId, focus)
watch(() => props.selectedPoiId, focus)
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
    <BrowseTileMap v-if="!ready" :points="points" :selected-id="selectedId" :poi-items="poiPoints" :selected-poi-id="selectedPoiId" @select="emit('select', $event)" @select-poi="emit('select-poi', $event)" />
    <p v-if="selectedId && !selected" class="absolute left-4 right-4 top-1/2 rounded-xl bg-white/95 p-4 text-sm text-[#142B4F]">Tin đang chọn chưa có vị trí được phép hiển thị; các ghim khác thuộc những tin khác.</p>
    <div v-if="showCard && selected" class="absolute bottom-24 left-4 right-4 z-10 max-w-sm rounded-2xl bg-white/95 p-4 text-[#142B4F] shadow-lg">
      <strong class="block text-sm">{{ selected.title }}</strong><p class="mt-1 text-sm font-semibold">{{ price(selected) }}</p><p class="mt-1 text-xs">{{ [selected.address, selected.ward, selected.district, selected.city].filter(Boolean).join(', ') }}</p><p class="mt-2 text-xs text-[#536178]">{{ locationLabel(selected) }}</p><RouterLink :to="'/listing/' + selected.id" class="mt-3 inline-block rounded-full bg-[#142B4F] px-4 py-2 text-xs font-semibold text-white">Xem chi tiết ↗</RouterLink>
    </div>
    <div class="absolute bottom-6 left-2 right-2 z-10 rounded bg-white/95 p-2 text-xs leading-5 text-[#142B4F]" role="status">
<p>{{ unavailable ? 'Google Maps tạm không khả dụng. ' : '' }}{{ points.length }} ghim tin trên trang<span v-if="poiPoints.length"> · {{ poiPoints.length }} tiện ích</span> · {{ ready ? 'Google Maps' : 'OpenStreetMap' }}. {{ selected ? locationLabel(selected) : 'Chỉ hiển thị tọa độ do Backend cung cấp.' }}</p>
      <p>Công cụ tìm địa chỉ: <a href="https://www.geoapify.com/" target="_blank" rel="noopener noreferrer" class="underline">Geoapify</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer" class="underline">© OpenStreetMap contributors</a></p>
    </div>
  </div>
</template>
