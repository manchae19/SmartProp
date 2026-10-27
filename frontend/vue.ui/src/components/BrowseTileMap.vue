<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { projectPoint, unprojectPoint, visibleTiles } from '../services/postMap.js'
import { compactPrice } from '../services/property.js'
import { poiSymbol, poiLabel } from '../services/nearbyPlaces.js'
const props = defineProps({ points: { type: Array, default: () => [] }, selectedId: String, poiItems: { type: Array, default: () => [] }, selectedPoiId: String })
const emit = defineEmits(['select', 'select-poi'])
const host = ref(null), width = ref(600), height = ref(440), zoom = ref(12)
// Da Nang is a viewport only; every marker below comes from a public property DTO.
const center = ref({ latitude: 16.0544, longitude: 108.2022 }), failed = ref(false), attempt = ref(0)
const template = import.meta.env?.VITE_OSM_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
// Viewport tiles only; retain browser caching, Referer and visible attribution.
// https://operations.osmfoundation.org/policies/tiles/ (reviewed 2026-10-26)
const validTemplate = template.startsWith('https://') && ['{z}', '{x}', '{y}'].every(value => template.includes(value))
const tiles = computed(() => visibleTiles(center.value, zoom.value, width.value, height.value))
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
function fit() {
  const points = [...props.points, ...props.poiItems]
  if (!points.length) return
  const xs = points.map(p => projectPoint(p.latitude, p.longitude, 0).x), ys = points.map(p => projectPoint(p.latitude, p.longitude, 0).y)
  const west = Math.min(...xs), east = Math.max(...xs), north = Math.min(...ys), south = Math.max(...ys)
  center.value = unprojectPoint((west + east) / 2, (north + south) / 2, 0)
  zoom.value = Math.max(3, Math.min(16, Math.floor(Math.log2(Math.min(Math.max(80, width.value - 160) / Math.max(east - west, .001), Math.max(80, height.value - 130) / Math.max(south - north, .001))))))
}
function focus() {
  const point = props.poiItems.find(p => p.id === props.selectedPoiId) || props.points.find(p => p.id === props.selectedId)
  if (point) { center.value = { latitude: point.latitude, longitude: point.longitude }; zoom.value = Math.max(zoom.value, 15) }
}
function pan(dx, dy) { const c = projectPoint(center.value.latitude, center.value.longitude, zoom.value); center.value = unprojectPoint(c.x + dx, c.y + dy, zoom.value) }
function changeZoom(delta) { zoom.value = Math.max(3, Math.min(19, zoom.value + delta)) }
let observer, drag
function pointerDown(event) {
  if (event.button !== 0 || event.target.closest('[data-map-control]')) return
  drag = { x: event.clientX, y: event.clientY, center: { ...center.value } }; host.value.setPointerCapture(event.pointerId)
}
function pointerMove(event) {
  if (!drag) return
  const p = projectPoint(drag.center.latitude, drag.center.longitude, zoom.value)
  center.value = unprojectPoint(p.x - event.clientX + drag.x, p.y - event.clientY + drag.y, zoom.value)
}
function pointerUp(event) { drag = null; if (host.value.hasPointerCapture(event.pointerId)) host.value.releasePointerCapture(event.pointerId) }
function keyboard(event) {
  if (event.target !== host.value) return
  const moves = { ArrowLeft: [-80, 0], ArrowRight: [80, 0], ArrowUp: [0, -80], ArrowDown: [0, 80] }
  if (moves[event.key]) { event.preventDefault(); pan(...moves[event.key]) }
  else if (['+', '=', '-'].includes(event.key)) { event.preventDefault(); changeZoom(event.key === '-' ? -1 : 1) }
}
watch(() => props.points.map(p => `${p.id}:${p.latitude}:${p.longitude}`).join('|'), () => { fit(); focus() })
watch(() => props.selectedId, focus)
watch(() => props.selectedPoiId, focus)
onMounted(() => { observer = new ResizeObserver(entries => { const box = entries[0].contentRect; width.value = box.width; height.value = box.height }); observer.observe(host.value); width.value = host.value.clientWidth; height.value = host.value.clientHeight; fit(); focus() })
onBeforeUnmount(() => observer?.disconnect())
</script>
<template>
  <div ref="host" class="browse-map" role="region" tabindex="0" aria-label="Bản đồ tin công khai: kéo để di chuyển, phím mũi tên để dịch chuyển, cộng trừ để thu phóng" @pointerdown="pointerDown" @pointermove="pointerMove" @pointerup="pointerUp" @pointercancel="drag = null" @keydown="keyboard">
    <img v-for="tile in tiles" :key="attempt + ':' + tile.key" :src="tileUrl(tile)" alt="" draggable="false" referrerpolicy="strict-origin-when-cross-origin" class="map-tile" :style="{ left: tile.left + 'px', top: tile.top + 'px' }" @error="failed = true" />
    <button v-for="point in markers" :key="point.id" type="button" data-map-control class="price-pin" :class="{ selected: selectedId === point.id, rent: point.transactionType === 'RENT' }" :style="{ left: point.left + 'px', top: point.top + 'px' }" :aria-label="point.title + ' · ' + compactPrice(point)" :aria-pressed="selectedId === point.id" :data-property-id="point.id" @click="emit('select', point.id)">{{ compactPrice(point) }}</button>
    <button v-for="point in poiMarkers" :key="'poi:' + point.id" type="button" data-map-control class="poi-pin" :class="{ selected: selectedPoiId === point.id }" :style="{ left: point.left + 'px', top: point.top + 'px' }" :aria-label="point.name + ' · ' + poiLabel(point.category)" :title="point.name" :aria-pressed="selectedPoiId === point.id" :data-poi-id="point.id" @click="emit('select-poi', point.id)">{{ poiSymbol(point.category) }}</button>
    <div data-map-control class="map-controls"><button type="button" aria-label="Phóng to bản đồ" :disabled="zoom >= 19" @click="changeZoom(1)">+</button><button type="button" aria-label="Thu nhỏ bản đồ" :disabled="zoom <= 3" @click="changeZoom(-1)">−</button><button type="button" class="fit" aria-label="Xem tất cả ghim của trang hiện tại" @click="fit">⛶</button></div>
    <p v-if="failed || !validTemplate" data-map-control class="tile-error" role="status">Chưa tải đầy đủ nền bản đồ. <button type="button" @click="failed = false; attempt++">Thử lại</button></p>
    <a data-map-control href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer" class="map-attribution">© OpenStreetMap contributors</a>
  </div>
</template>
<style scoped>
.poi-pin{position:absolute;transform:translate(-50%,-50%);display:grid;place-items:center;width:32px;height:32px;min-width:32px;min-height:32px;border:2px solid white;border-radius:10px;background:#8870ac;color:white;font-size:20px;line-height:1;box-shadow:0 2px 10px #142b4f40;z-index:2;cursor:pointer}.poi-pin.selected{background:#665086;outline:3px solid #8b76b450;outline-offset:3px;z-index:6}
.browse-map{position:absolute;inset:0;overflow:hidden;isolation:isolate;background:#e7ece6;cursor:grab;touch-action:none}.browse-map:active{cursor:grabbing}.map-tile{position:absolute;width:256px;height:256px;max-width:none;pointer-events:none;user-select:none}.price-pin{position:absolute;transform:translate(-50%,-100%);border:2px solid white;border-radius:20px;background:#142b4f;color:white;box-shadow:0 3px 12px #142b4f50;padding:7px 12px;font-size:11px;font-weight:700;white-space:nowrap;cursor:pointer;z-index:2}.price-pin:after{content:'';position:absolute;bottom:-6px;left:calc(50% - 5px);width:8px;height:8px;rotate:45deg;background:inherit;border-right:2px solid white;border-bottom:2px solid white}.price-pin.rent{background:#207760}.price-pin.selected{background:#b68a4c;z-index:5;outline:3px solid #b68a4c40;outline-offset:3px}.map-controls{position:absolute;right:12px;top:12px;display:grid;gap:4px;z-index:6}.map-controls button{width:36px;height:36px;border:1px solid #d7dce4;border-radius:8px;background:white;font-size:22px;color:#142b4f;cursor:pointer}.map-controls .fit{margin-top:5px}.map-controls button:disabled{opacity:.5}.map-attribution{position:absolute;bottom:0;right:0;padding:4px 7px;background:#fffffff0;font-size:10px;color:#142b4f;z-index:6}.tile-error{position:absolute;top:10px;left:10px;right:65px;background:#fffffff0;padding:9px;border-radius:9px;color:#993b20;font-size:12px;z-index:6}.tile-error button{text-decoration:underline;cursor:pointer} :focus-visible{outline:3px solid #b3915f;outline-offset:3px}
</style>
