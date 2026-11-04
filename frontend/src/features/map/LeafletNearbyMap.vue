<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { POI_GROUPS, validPoint, distanceLabel } from './nearbyExplorer.js'
import { publicMapPoint } from './locationDisplay.js'
import { compactPrice } from '../property/property.js'
const props = defineProps({ items: { type: Array, default: () => [] }, selectedId: String, places: { type: Array, default: () => [] }, radius: { type: Number, default: 1000 }, showProperty: { type: Boolean, default: true }, showRadius: { type: Boolean, default: true }, activePoi: String, simple: Boolean })
const emit = defineEmits(['select', 'select-poi'])
const element = ref(null), ready = ref(false), mapError = ref(''), baseLayer = ref('street')
let map, street, properties, pois, circle, observer, tileErrors = 0, lastSelection = ''
const pins = new Map(), poiPins = new Map()
function icon(label, color, selected = false) {
  const span = document.createElement('span'); span.className = 'explorer-marker' + (selected ? ' is-selected' : '')
  span.style.setProperty('--pin-color', color); span.textContent = label
  return L.divIcon({ html: span, className: 'explorer-marker-wrap', iconSize: selected ? [42, 48] : [32, 38], iconAnchor: selected ? [21, 44] : [16, 35], popupAnchor: [0, -34] })
}
function popup(p, property = false) {
  const box = document.createElement('div'); box.className = 'explorer-popup'
  if (property && p.status === 'PUBLISHED') {
    const cover = p.images?.find(i => i.cover) || p.images?.[0]
    const prefix = '/api/v1/properties/' + encodeURIComponent(p.id) + '/images/'
    if (cover?.url?.startsWith(prefix) && cover.url.endsWith('/content')) {
      const photo = document.createElement('img'); photo.src = cover.url; photo.alt = p.title || 'Ảnh bất động sản'
      photo.className = 'explorer-popup-photo'; photo.loading = 'lazy'; photo.decoding = 'async'
      photo.addEventListener('error', () => photo.remove(), { once: true }); box.append(photo)
    }
  }
  const title = document.createElement('strong'); title.textContent = p.title || p.name; box.append(title)
  const text = document.createElement('p')
  text.textContent = property ? compactPrice(p) + (p.areaSqm ? ' · ' + p.areaSqm + ' m²' : '') : distanceLabel(p.distanceMeters) + ' · đường chim bay'
  box.append(text)
  if (property) { const link = document.createElement('a'); link.textContent = 'Xem chi tiết →'; link.href = '/listing/' + encodeURIComponent(p.id); box.append(link) }
  else if (p.address) { const address = document.createElement('small'); address.textContent = p.address; box.append(address) }
  return box
}
function draw() {
  if (!map) return
  const keepPropertyPopup = pins.get(props.selectedId)?.isPopupOpen()
  map.stop(); map.closePopup()
  properties.clearLayers(); pois.clearLayers(); pins.clear(); poiPins.clear()
  if (circle) { circle.remove(); circle = null }
  const selected = props.items.find(p => p.id === props.selectedId && publicMapPoint(p))
  for (const p of props.items.filter(publicMapPoint)) {
    const active = p.id === props.selectedId
    const marker = L.marker([Number(p.latitude), Number(p.longitude)], { icon: icon('⌂', active ? '#147d80' : '#234b70', active), zIndexOffset: active ? 500 : 0, title: p.title || 'Bất động sản', keyboard: true })
    marker.bindPopup(popup(p, true), { maxWidth: 260 }).on('click', () => emit('select', p.id))
    if (props.showProperty) marker.addTo(properties)
    pins.set(p.id, marker)
  }
  if (selected) {
    if (props.showRadius) circle = L.circle([Number(selected.latitude), Number(selected.longitude)], { radius: props.radius, color: '#4075f5', weight: 2, dashArray: '7 6', fillColor: '#5795f5', fillOpacity: .09, interactive: false }).addTo(map)
    for (const p of props.places.filter(validPoint)) {
      const group = POI_GROUPS.find(g => g.id === p.category) || POI_GROUPS[0]
      const marker = L.marker([Number(p.latitude), Number(p.longitude)], { icon: icon(group.icon, group.color), title: p.name, keyboard: true }).addTo(pois)
      marker.bindPopup(popup(p)).on('click', () => emit('select-poi', p.id)); poiPins.set(p.id, marker)
    }
    const key = selected.id + ':' + selected.latitude + ':' + selected.longitude + ':' + props.radius
    if (lastSelection !== key) {
      lastSelection = key
      map.fitBounds(L.latLng(Number(selected.latitude), Number(selected.longitude)).toBounds(props.radius * 2), { padding: [45, 45], maxZoom: 17, animate: false })
      if (props.showProperty) pins.get(selected.id)?.openPopup()
    }
    if (keepPropertyPopup && props.showProperty) pins.get(selected.id)?.openPopup()
  } else if (props.items.some(publicMapPoint)) {
    lastSelection = ''; map.fitBounds(L.latLngBounds(props.items.filter(publicMapPoint).map(p => [Number(p.latitude), Number(p.longitude)])), { padding: [45, 45], maxZoom: 14, animate: false })
  }
}
function center() {
  const p = props.items.find(p => p.id === props.selectedId)
  if (p && publicMapPoint(p)) { map?.setView([Number(p.latitude), Number(p.longitude)], 16); pins.get(p.id)?.openPopup() }
}
watch(() => [props.items, props.selectedId, props.places, props.radius, props.showProperty, props.showRadius], draw, { deep: true })
watch(() => props.activePoi, id => { const pin = poiPins.get(id); if (pin) { map.panTo(pin.getLatLng()); pin.openPopup() } })
onMounted(async () => {
  await nextTick()
  map = L.map(element.value, { zoomControl: false, scrollWheelZoom: true, wheelDebounceTime: 80, wheelPxPerZoomLevel: 100, preferCanvas: true, zoomAnimation: false, fadeAnimation: false, markerZoomAnimation: false })
  // Initial viewport only; no synthetic property marker is placed here.
  map.setView([16.06, 108.21], 12)
  L.control.zoom({ position: 'topright' }).addTo(map)
  L.control.scale({ imperial: false, position: 'bottomleft' }).addTo(map)
  street = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>' }).addTo(map)
  street.on('tileerror', () => { if (++tileErrors >= 4) mapError.value = 'Chưa tải được bản đồ nền. Kiểm tra kết nối và thử lại.' })
  street.on('tileload', () => { mapError.value = ''; tileErrors = 0 })
  properties = L.layerGroup().addTo(map); pois = L.layerGroup().addTo(map)
  observer = new ResizeObserver(() => map?.invalidateSize({ animate: false })); observer.observe(element.value)
  ready.value = true; draw()
})
function retryTiles() { tileErrors = 0; mapError.value = ''; street?.redraw() }
onBeforeUnmount(() => { observer?.disconnect(); map?.remove(); map = null })
</script>
<template>
  <div class="leaflet-explorer-shell">
    <div ref="element" class="leaflet-explorer-canvas" aria-label="Bản đồ bất động sản và tiện ích xung quanh" />
    <div v-if="!simple" class="map-layer-choice" aria-label="Lớp bản đồ"><button type="button" :aria-pressed="baseLayer==='street'">Bản đồ</button><button type="button" disabled title="Chưa cấu hình nguồn ảnh vệ tinh có giấy phép">Vệ tinh</button><button type="button" disabled title="Chưa cấu hình lớp vệ tinh và nhãn">Bản đồ lai</button></div>
    <button class="map-recenter" type="button" @click="center" aria-label="Đưa bản đồ về bất động sản đang chọn" title="Về vị trí tin đang chọn">⌖</button>
    <div v-if="mapError" class="map-tile-error" role="alert">{{mapError}} <button type="button" @click="retryTiles">Thử lại</button></div>
    <div v-if="!ready" class="map-boot">Đang mở bản đồ…</div>
  </div>
</template>
<style>
.leaflet-explorer-shell{height:100%;min-height:400px;position:relative;background:#e7eceb}.leaflet-explorer-canvas{height:100%;width:100%;min-height:400px;z-index:0}.map-layer-choice{position:absolute;top:16px;left:16px;z-index:500;display:flex;background:white;padding:5px;border-radius:12px;box-shadow:0 3px 18px #17234d20;gap:3px}.map-layer-choice button{padding:9px 12px;border-radius:8px;font-size:12px;font-weight:600;color:#29335a}.map-layer-choice button[aria-pressed=true]{background:#5638d8;color:white}.map-layer-choice button:disabled{color:#8791a4;cursor:not-allowed}.map-recenter{position:absolute;right:11px;top:90px;background:white;color:#263363;z-index:500;width:34px;height:36px;font-size:25px;border-radius:5px;box-shadow:0 1px 5px #0004}.map-tile-error{position:absolute;top:145px;left:20px;right:20px;z-index:500;padding:12px;background:#fff4e3;color:#664518;border-radius:8px;font-size:12px}.map-tile-error button{text-decoration:underline}.map-boot{position:absolute;inset:0;display:grid;place-items:center;background:#eef0f4}.explorer-marker-wrap{background:transparent;border:0}.explorer-marker{display:grid;place-items:center;width:32px;height:32px;border:3px solid white;border-radius:50% 50% 50% 7px;box-shadow:0 2px 7px #17234d55;background:var(--pin-color);color:white;font-family:system-ui;font-size:17px;transform:rotate(-12deg)}.explorer-marker.is-selected{width:42px;height:42px;border-width:4px;font-size:24px;box-shadow:0 0 0 8px #7459ee33,0 4px 10px #17234d55}.explorer-popup{color:#17264a;line-height:1.6;min-width:140px}.explorer-popup strong{font-size:13px}.explorer-popup p{margin:7px 0;font-size:12px}.explorer-popup a{color:#5638d8!important;font-weight:700}.explorer-popup small{display:block;max-width:240px}.leaflet-explorer-shell .leaflet-control-attribution{font-size:10px!important}.leaflet-explorer-shell .leaflet-control-zoom a{color:#28335f}

.leaflet-explorer-shell{background:#e7efeb}.map-layer-choice{border:1px solid #e2e9e5;padding:6px;border-radius:14px;box-shadow:0 5px 22px #142b4f17}
.map-layer-choice button[aria-pressed=true]{background:#173a50;box-shadow:0 2px 5px #173a5020}.map-layer-choice button{padding:10px 13px}
.map-recenter{color:#1a555f;border-radius:10px;width:36px;height:38px;border:1px solid #e1e7e4}
.explorer-marker{box-shadow:0 3px 9px #142b4f3b;transform:none;border-width:3px}.explorer-marker.is-selected{box-shadow:0 0 0 9px #147d8026,0 5px 16px #142b4f33}
.explorer-popup{min-width:190px;padding:5px;line-height:1.6}.explorer-popup strong{font-size:14px}.explorer-popup p{color:#52737c;font-size:13px}
.explorer-popup a{display:inline-block;background:#173a50;padding:7px 12px;color:#fff!important;border-radius:9px;font-size:12px}
.leaflet-explorer-shell .leaflet-popup-content-wrapper{border-radius:16px;box-shadow:0 10px 35px #142b4f2a}
.leaflet-explorer-shell .leaflet-control-zoom{border:1px solid #dbe5e1;border-radius:11px;overflow:hidden;box-shadow:0 4px 18px #142b4f20}
.leaflet-explorer-shell .leaflet-control-zoom a{width:36px;height:36px;line-height:36px;color:#214656}
.explorer-popup-photo{width:100%;height:120px;object-fit:cover;border-radius:10px;margin-bottom:10px;display:block}
</style>
