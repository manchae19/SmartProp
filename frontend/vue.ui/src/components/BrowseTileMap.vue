<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { projectPoint, unprojectPoint, visibleTiles } from '../services/postMap.js'
import { compactPrice } from '../services/property.js'
import { poiSymbol, poiLabel, poiColor, poiColorBg, poiColorBorder } from '../services/nearbyPlaces.js'
import { googlePointUrl } from '../services/googleMapsLocation.js'
import PoiIcon from './PoiIcon.vue'

const props = defineProps({ points: { type: Array, default: () => [] }, selectedId: String, poiItems: { type: Array, default: () => [] }, selectedPoiId: String, boundary: { type: Object, default: null }, mapLabel: { type: String, default: 'Bản đồ tin công khai: kéo để di chuyển, phím mũi tên để dịch chuyển, cộng trừ để thu phóng' } })
const emit = defineEmits(['select', 'select-poi'])
const host = ref(null), width = ref(600), height = ref(440), zoom = ref(12)
// Da Nang is a viewport only; every marker below comes from a public property DTO.
const center = ref({ latitude: 16.0544, longitude: 108.2022 }), failed = ref(false), attempt = ref(0)
let observer = null
const template = import.meta.env?.VITE_OSM_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
// Viewport tiles only; retain browser caching, Referer and visible attribution.
// https://operations.osmfoundation.org/policies/tiles/ (reviewed 2026-10-26)
const validTemplate = template.startsWith('https://') && ['{z}', '{x}', '{y}'].every(value => template.includes(value))
const tiles = computed(() => visibleTiles(center.value, zoom.value, width.value, height.value))
const boundaryRings = computed(() => {
  const g = props.boundary
  return g?.type === 'Polygon' ? g.coordinates : g?.type === 'MultiPolygon' ? g.coordinates.flat() : []
})
const boundaryPath = computed(() => {
  const c = projectPoint(center.value.latitude, center.value.longitude, zoom.value)
  return boundaryRings.value.map(ring => ring.map(([lon,lat],i) => { const p = projectPoint(lat,lon,zoom.value); return `${i ? 'L' : 'M'}${p.x-c.x+width.value/2},${p.y-c.y+height.value/2}` }).join(' ') + 'Z').join(' ')
})
function tileUrl(tile) { return validTemplate ? template.replace('{z}', tile.z).replace('{x}', tile.x).replace('{y}', tile.y) : '' }
function markersFor(points) {
  const c = projectPoint(center.value.latitude, center.value.longitude, zoom.value), world = 256 * 2 ** zoom.value
  return points.map(point => {
    const p = projectPoint(point.latitude, point.longitude, zoom.value)
    let dx = p.x - c.x
    if (dx > world / 2) dx -= world
    if (dx < -world / 2) dx += world
    return { ...point, left: dx + width.value / 2, top: p.y - c.y + height.value / 2 }
  }).filter(point => point.left > -80 && point.left < width.value + 80 && point.top > -30 && point.top < height.value + 30)
}
const markers = computed(() => markersFor(props.points))
const poiMarkers = computed(() => markersFor(props.poiItems))
const selectedPoiMarker = computed(() => poiMarkers.value.find(p => p.id === props.selectedPoiId) || null)
const isPopupFlipped = computed(() => selectedPoiMarker.value && selectedPoiMarker.value.top < 135)

function formatDistance(meters) {
  if (typeof meters !== 'number' || !Number.isFinite(meters) || meters < 0) return ''
  if (meters < 1000) return `${Math.round(meters)} m`
  return `${(meters / 1000).toFixed(1).replace('.', ',')} km`
}
function fit() {
  const points = [...props.points, ...props.poiItems, ...boundaryRings.value.flat().map(([longitude,latitude]) => ({latitude,longitude}))]
  if (!points.length) return
  const lats = points.map(point => point.latitude), lons = points.map(point => point.longitude)
  const minLat = Math.min(...lats), maxLat = Math.max(...lats), minLon = Math.min(...lons), maxLon = Math.max(...lons)
  center.value = { latitude: (minLat + maxLat) / 2, longitude: (minLon + maxLon) / 2 }
  let target = 16
  while (target > 3) {
    const p1 = projectPoint(maxLat, minLon, target), p2 = projectPoint(minLat, maxLon, target)
    if (Math.abs(p2.x - p1.x) <= Math.max(120, width.value - 60) && Math.abs(p2.y - p1.y) <= Math.max(120, height.value - 60)) break
    target--
  }
  zoom.value = Math.max(3, Math.min(18, target))
}
function focus() {
  const target = props.selectedPoiId ? props.poiItems.find(p => p.id === props.selectedPoiId) : props.points.find(p => p.id === props.selectedId)
  if (target) center.value = { latitude: target.latitude, longitude: target.longitude }
}
function pan(dx, dy) {
  const c = projectPoint(center.value.latitude, center.value.longitude, zoom.value)
  center.value = unprojectPoint(c.x + dx, c.y + dy, zoom.value)
}
function changeZoom(delta) {
  const next = Math.max(3, Math.min(19, zoom.value + delta))
  if (next !== zoom.value) zoom.value = next
}
let drag = null
function pointerDown(event) {
  if (event.target.closest('[data-map-control]')) return
  drag = { x: event.clientX, y: event.clientY, center: { ...center.value } }
  host.value?.setPointerCapture(event.pointerId)
}
function pointerMove(event) {
  if (!drag) return
  const p = projectPoint(drag.center.latitude, drag.center.longitude, zoom.value)
  center.value = unprojectPoint(p.x - event.clientX + drag.x, p.y - event.clientY + drag.y, zoom.value)
}
function pointerUp(event) { drag = null; if (host.value.hasPointerCapture(event.pointerId)) host.value.releasePointerCapture(event.pointerId) }
function keyboard(event) {
  if (event.key === 'Escape' && props.selectedPoiId) {
    emit('select-poi', null)
    return
  }
  if (event.target !== host.value) return
  const moves = { ArrowLeft: [-80, 0], ArrowRight: [80, 0], ArrowUp: [0, -80], ArrowDown: [0, 80] }
  if (moves[event.key]) { event.preventDefault(); pan(...moves[event.key]) }
  else if (['+', '=', '-'].includes(event.key)) { event.preventDefault(); changeZoom(event.key === '-' ? -1 : 1) }
}
watch(() => props.points.map(p => `${p.id}:${p.latitude}:${p.longitude}`).join('|'), () => { fit(); focus() })
watch(() => props.poiItems.map(p => `${p.id}:${p.latitude}:${p.longitude}`).join('|'), () => { fit(); focus() })
watch(() => props.selectedId, focus)
watch(() => props.selectedPoiId, focus)
watch(() => props.boundary, fit)
onMounted(() => { observer = new ResizeObserver(entries => { const box = entries[0].contentRect; width.value = box.width; height.value = box.height; fit(); focus() }); observer.observe(host.value); width.value = host.value.clientWidth; height.value = host.value.clientHeight; fit(); focus() })
onBeforeUnmount(() => observer?.disconnect())
</script>
<template>
  <div ref="host" class="browse-map" role="region" tabindex="0" :aria-label="mapLabel" @pointerdown="pointerDown" @pointermove="pointerMove" @pointerup="pointerUp" @pointercancel="drag = null" @keydown="keyboard">
    <img v-for="tile in tiles" :key="attempt + ':' + tile.key" :src="tileUrl(tile)" alt="" draggable="false" referrerpolicy="strict-origin-when-cross-origin" class="map-tile" :style="{ left: tile.left + 'px', top: tile.top + 'px' }" @error="failed = true" />
    <svg v-if="boundaryPath" class="boundary-overlay" :viewBox="`0 0 ${width} ${height}`" aria-hidden="true" data-map-boundary><path :d="boundaryPath" fill="#365a9220" stroke="#365a92" stroke-width="2" fill-rule="evenodd" /></svg>
    <button v-for="point in markers" :key="point.id" type="button" data-map-control class="price-pin" :class="{ selected: selectedId === point.id, rent: point.transactionType === 'RENT' }" :style="{ left: point.left + 'px', top: point.top + 'px' }" :aria-label="point.title + ' · ' + compactPrice(point)" :aria-pressed="selectedId === point.id" :data-property-id="point.id" @click="emit('select', point.id)">{{ compactPrice(point) }}</button>
    <button v-for="point in poiMarkers" :key="'poi:' + point.id" type="button" data-map-control class="poi-pin" :class="{ selected: selectedPoiId === point.id }" :style="{ left: point.left + 'px', top: point.top + 'px', backgroundColor: poiColor(point.category) }" :aria-label="point.name + ' · ' + (point.categoryLabel || poiLabel(point.category))" :title="point.name + ' (' + (point.categoryLabel || poiLabel(point.category)) + ')'" :aria-pressed="selectedPoiId === point.id" :data-poi-id="point.id" @click="emit('select-poi', selectedPoiId === point.id ? null : point.id)">
      <PoiIcon :category="point.category" class="size-3.5 text-white" />
    </button>
    <div v-if="selectedPoiMarker" data-map-control class="poi-map-popup" :class="{ flipped: isPopupFlipped }" :style="{ left: selectedPoiMarker.left + 'px', top: selectedPoiMarker.top + 'px' }" @pointerdown.stop>
      <div class="poi-popup-card">
        <div class="poi-popup-header">
          <span class="poi-popup-badge" :style="{ backgroundColor: poiColorBg(selectedPoiMarker.category), color: poiColor(selectedPoiMarker.category), borderColor: poiColorBorder(selectedPoiMarker.category) }">
            <PoiIcon :category="selectedPoiMarker.category" class="size-3" />
            <span>{{ selectedPoiMarker.categoryLabel || poiLabel(selectedPoiMarker.category) }}</span>
          </span>
          <button type="button" class="poi-popup-close" aria-label="Đóng bảng tiện ích" title="Đóng" @click.stop="emit('select-poi', null)">✕</button>
        </div>
        <div class="poi-popup-title">{{ selectedPoiMarker.name }}</div>
        <p v-if="selectedPoiMarker.address" class="poi-popup-source">{{ selectedPoiMarker.address }}</p>
        <a v-if="selectedPoiMarker.sourceName === 'openstreetmap_overpass' && /^https:\/\/www\.openstreetmap\.org\/(node|way|relation)\/[1-9][0-9]*$/.test(selectedPoiMarker.sourceUrl)" :href="selectedPoiMarker.sourceUrl" target="_blank" rel="noopener noreferrer" class="poi-popup-source">Nguồn: OpenStreetMap ↗</a>
        <div class="poi-popup-meta">
          <span v-if="selectedPoiMarker.distanceMeters" class="poi-popup-dist">
            <svg class="size-3.5 text-emerald-600 inline mr-1 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
            Cách BĐS ~{{ formatDistance(selectedPoiMarker.distanceMeters) }}
          </span>
          <a v-if="googlePointUrl(selectedPoiMarker.latitude, selectedPoiMarker.longitude)" :href="googlePointUrl(selectedPoiMarker.latitude, selectedPoiMarker.longitude)" target="_blank" rel="noopener noreferrer" class="poi-popup-link">Chỉ đường ↗</a>
        </div>
      </div>
      <div class="poi-popup-arrow"></div>
    </div>
    <div data-map-control class="map-controls"><button type="button" aria-label="Phóng to bản đồ" :disabled="zoom >= 19" @click="changeZoom(1)">+</button><button type="button" aria-label="Thu nhỏ bản đồ" :disabled="zoom <= 3" @click="changeZoom(-1)">−</button><button type="button" class="fit" aria-label="Xem tất cả ghim của trang hiện tại" @click="fit">⛶</button></div>
    <p v-if="failed || !validTemplate" data-map-control class="tile-error" role="status">Chưa tải đầy đủ nền bản đồ. <button type="button" @click="failed = false; attempt++">Thử lại</button></p>
    <a data-map-control href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer" class="map-attribution">© OpenStreetMap contributors</a>
  </div>
</template>
<style scoped>
.boundary-overlay{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1}
.poi-pin{
  position:absolute;
  transform:translate(-50%,-50%);
  display:grid;
  place-items:center;
  width:28px;
  height:28px;
  min-width:28px;
  min-height:28px;
  border:2px solid white;
  border-radius:9px;
  color:white;
  box-shadow:0 2px 8px rgba(16,35,63,0.35);
  z-index:6;
  cursor:pointer;
  transition:all .18s cubic-bezier(0.4, 0, 0.2, 1);
}
.poi-pin:hover{
  transform:translate(-50%,-60%) scale(1.22);
  box-shadow:0 6px 14px rgba(16,35,63,0.45);
  z-index:12;
}
.poi-pin.selected{
  transform:translate(-50%,-65%) scale(1.35);
  box-shadow:0 0 0 3px #10233f, 0 8px 18px rgba(16,35,63,0.55);
  z-index:15;
}
.poi-map-popup{position:absolute;z-index:25;pointer-events:auto;user-select:text;animation:poiPopIn .18s cubic-bezier(.16,1,.3,1)}
.poi-map-popup:not(.flipped){transform:translate(-50%,calc(-100% - 20px))}
.poi-map-popup.flipped{transform:translate(-50%,20px)}
@keyframes poiPopIn{from{opacity:0;transform:translate(-50%,calc(-100% - 12px)) scale(.92)}to{opacity:1;transform:translate(-50%,calc(-100% - 20px)) scale(1)}}
.poi-popup-card{background:#ffffff;border-radius:12px;padding:10px 14px;box-shadow:0 12px 30px -4px rgba(16,35,63,.3),0 4px 10px -2px rgba(16,35,63,.12);border:1.5px solid #e2e8f0;min-width:190px;max-width:270px;text-align:left}
.poi-popup-header{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:5px}
.poi-popup-badge{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:650;padding:2px 7px;border-radius:9999px;border:1px solid currentColor}
.poi-popup-close{width:20px;height:20px;display:flex;align-items:center;justify-content:center;border:none;background:#f1f5f9;color:#64748b;border-radius:50%;font-size:11px;cursor:pointer;line-height:1;transition:all .15s ease;padding:0}
.poi-popup-close:hover{background:#e2e8f0;color:#0f172a}
.poi-popup-title{font-size:13.5px;font-weight:700;color:#10233f;line-height:1.35;margin-bottom:6px;word-break:break-word}
.poi-popup-meta{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:11.5px;padding-top:5px;border-top:1px dashed #e2e8f0}
.poi-popup-dist{display:inline-flex;align-items:center;color:#475569;font-weight:500}
.poi-popup-link{color:#2563eb;font-weight:600;text-decoration:none;white-space:nowrap}
.poi-popup-link:hover{text-decoration:underline;color:#1d4ed8}
.poi-popup-arrow{position:absolute;left:50%;transform:translateX(-50%);width:0;height:0}
.poi-map-popup:not(.flipped) .poi-popup-arrow{bottom:-7px;border-left:7px solid transparent;border-right:7px solid transparent;border-top:7px solid #ffffff;filter:drop-shadow(0 2px 2px rgba(16,35,63,.15))}
.poi-map-popup.flipped .poi-popup-arrow{top:-7px;border-left:7px solid transparent;border-right:7px solid transparent;border-bottom:7px solid #ffffff;filter:drop-shadow(0 -2px 2px rgba(16,35,63,.15))}
.browse-map{position:absolute;inset:0;overflow:hidden;isolation:isolate;background:#e7ece6;cursor:grab;touch-action:none}.browse-map:active{cursor:grabbing}.map-tile{position:absolute;width:256px;height:256px;max-width:none;pointer-events:none;user-select:none}.price-pin{position:absolute;transform:translate(-50%,-100%);border:2px solid white;border-radius:20px;background:#142b4f;color:white;box-shadow:0 3px 12px #142b4f50;padding:7px 12px;font-size:13px;font-weight:700;white-space:nowrap;cursor:pointer;z-index:2}.price-pin:after{content:'';position:absolute;bottom:-6px;left:calc(50% - 5px);width:8px;height:8px;rotate:45deg;background:inherit;border-right:2px solid white;border-bottom:2px solid white}.price-pin.rent{background:#207760}.price-pin.selected{background:#b68a4c;color:#10233f;z-index:5;outline:3px solid #b68a4c40;outline-offset:3px}.map-controls{position:absolute;right:12px;top:12px;display:grid;gap:4px;z-index:6}.map-controls button{width:36px;height:36px;border:1px solid #d7dce4;border-radius:8px;background:white;font-size:22px;color:#142b4f;cursor:pointer}.map-controls .fit{margin-top:5px}.map-controls button:disabled{opacity:.5}.map-attribution{position:absolute;bottom:0;right:0;padding:4px 7px;background:#fffffff0;font-size:13px;color:#142b4f;z-index:6}.tile-error{position:absolute;top:10px;left:10px;right:65px;background:#fffffff0;padding:9px;border-radius:9px;color:#993b20;font-size:12px;z-index:6}.tile-error button{text-decoration:underline;cursor:pointer} :focus-visible{outline:3px solid #b3915f;outline-offset:3px}
</style>
