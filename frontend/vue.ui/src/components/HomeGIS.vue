<script setup>
import { computed, ref, watch, nextTick, onMounted, onBeforeUnmount, defineAsyncComponent } from 'vue'
import { api } from '../services/api.js'
import { compactPrice } from '../services/property.js'
import { publicMapPoint, locationLabel } from '../services/locationDisplay.js'
import { googlePointUrl } from '../services/googleMapsLocation.js'
import { nearbyPlaces, poiHasPoint, poiLabel } from '../services/nearbyPlaces.js'
import PrivateImage from './business/PrivateImage.vue'
const PropertyMap = defineAsyncComponent(() => import('./PropertyMap.vue'))
const props = defineProps({ items: { type: Array, default: () => [] }, selectedId: String, total: Number, mapLink: Object, busy: Boolean, error: String })
const emit = defineEmits(['update:selectedId', 'retry'])
const host = ref(null), activated = ref(false), pois = ref([]), poiBusy = ref(false), poiError = ref(''), category = ref(''), radius = ref('1000')
const showPois = ref(true), selectedPoiId = ref(null)
const selected = computed(() => props.items.find(item => item.id === props.selectedId) || null)
const points = computed(() => props.items.filter(publicMapPoint))
const categories = computed(() => [...new Set(pois.value.map(poi => poi.category).filter(Boolean))])
const visiblePois = computed(() => category.value ? pois.value.filter(poi => poi.category === category.value) : pois.value)
const mapPois = computed(() => showPois.value && publicMapPoint(selected.value) ? visiblePois.value.filter(poiHasPoint) : [])
const selectedPoi = computed(() => mapPois.value.find(poi => poi.id === selectedPoiId.value) || null)
let sequence = 0, observer
async function loadPois() {
  const run = ++sequence; pois.value = []; poiError.value = ''; poiBusy.value = false; category.value = ''; selectedPoiId.value = null
  if (!activated.value || !selected.value || !publicMapPoint(selected.value)) return
  poiBusy.value = true
  try {
    const result = await api(`/properties/${encodeURIComponent(selected.value.id)}/points-of-interest?radiusMeters=${radius.value}&limit=100`, { authenticated: false })
    if (run === sequence) pois.value = nearbyPlaces(result, radius.value)
  } catch { if (run === sequence) poiError.value = 'Chưa tải được tiện ích quanh tin đang chọn.' }
  finally { if (run === sequence) poiBusy.value = false }
}
watch(() => [props.selectedId, selected.value?.latitude, selected.value?.longitude, activated.value, radius.value], loadPois)
watch(mapPois, values => { if (!values.some(poi => poi.id === selectedPoiId.value)) selectedPoiId.value = null })
function selectPoi(id) { if (visiblePois.value.some(poi => poi.id === id && poiHasPoint(poi))) { showPois.value = true; selectedPoiId.value = id } }
function selectProperty(id) { selectedPoiId.value = null; emit('update:selectedId', id) }
watch(selectedPoiId, async id => {
  await nextTick()
  const list = host.value?.querySelector('.poi-list'), button = [...(host.value?.querySelectorAll('[data-poi-card]') || [])].find(element => element.dataset.poiCard === id)
  if (!list || !button) return
  const bounds = list.getBoundingClientRect(), item = button.getBoundingClientRect()
  if (item.top < bounds.top || item.bottom > bounds.bottom) list.scrollTo({ top: list.scrollTop + item.top - bounds.top - 12, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })
})
watch(() => props.selectedId, async () => {
  await nextTick()
  const list = host.value?.querySelector('.gis-list'), card = [...(host.value?.querySelectorAll('[data-gis-card]') || [])].find(element => element.dataset.gisCard === props.selectedId)
  if (!list || !card) return
  const bounds = list.getBoundingClientRect(), item = card.getBoundingClientRect()
  if (item.top < bounds.top || item.bottom > bounds.bottom) list.scrollTo({ top: list.scrollTop + item.top - bounds.top - 12, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })
})
onMounted(() => { observer = new IntersectionObserver(entries => { if (entries.some(entry => entry.isIntersecting)) { activated.value = true; observer.disconnect() } }, { rootMargin: '160px' }); observer.observe(host.value) })
onBeforeUnmount(() => { observer?.disconnect(); sequence++ })
const cover = item => (item.images?.find(image => image.cover) || item.images?.[0])?.url
const distance = value => value >= 1000 ? (value / 1000).toLocaleString('vi-VN', { maximumFractionDigits: 1 }) + ' km' : Math.round(value) + ' m'
</script>
<template>
  <div ref="host" class="home-gis">
    <div class="gis-toolbar"><p><span class="live-dot"></span> {{ points.length }} ghim / {{ items.length }} tin trên trang<span v-if="total != null"> · {{ total }} tin phù hợp</span></p><RouterLink v-if="mapLink" :to="mapLink">Mở GIS đầy đủ ↗</RouterLink></div>
    <div class="gis-legend" aria-label="Chú giải bản đồ"><span><i class="legend-sale"></i>Bán</span><span><i class="legend-rent"></i>Cho thuê</span><span><i class="legend-selected"></i>Tin đang chọn</span><span v-if="mapPois.length"><i class="legend-poi"></i>Tiện ích</span></div>
    <p v-if="error" role="alert" class="gis-message">{{ error }} <button @click="emit('retry')">Thử lại</button></p>
    <p v-if="busy" class="gis-message" role="status">Đang tải tin trên bản đồ…</p>
    <div class="gis-workspace">
      <div class="gis-map-pane">
        <PropertyMap v-if="activated" :items="items" :selected-id="selectedId" :poi-items="mapPois" :selected-poi-id="selectedPoiId" @select="selectProperty" @select-poi="selectPoi" />
        <button v-else class="map-activate" type="button" @click="activated = true">Mở bản đồ tương tác</button>
        <p v-if="!busy && !points.length" class="no-points">Chưa có tin có vị trí được phép hiển thị trong bộ lọc này. Không dùng ghim minh họa.</p>
      </div>
      <div class="gis-list" aria-label="Tin đăng đồng bộ với bản đồ">
        <p class="gis-list-label">TIN TRÊN TRANG HIỆN TẠI</p>
        <p v-if="!items.length && !busy" class="gis-message">Chưa có tin phù hợp.</p>
        <article v-for="item in items" :key="item.id" :class="{ active: selectedId === item.id }" :data-gis-card="item.id">
          <button type="button" class="select-property" :aria-pressed="selectedId === item.id" @click="selectProperty(item.id)"><span class="gis-thumb"><PrivateImage :src="cover(item)" :alt="item.title" /></span><span class="gis-card-text"><strong>{{ item.title }}</strong><span>{{ item.district || 'Chưa rõ khu vực' }}</span><b>{{ compactPrice(item) }}</b><small>{{ item.areaSqm }} m²<span v-if="item.bedrooms"> · {{ item.bedrooms }} PN</span></small></span></button>
          <RouterLink :to="'/listing/' + item.id" class="gis-detail">Xem chi tiết ↗</RouterLink>
        </article>
      </div>
    </div>
    <div class="selected-info" aria-live="polite"><template v-if="selected"><strong>{{ selected.title }}</strong><p>{{ [selected.address, selected.ward, selected.district, selected.city].filter(Boolean).join(', ') }}</p><p>{{ locationLabel(selected) }}</p><div class="selected-links"><RouterLink :to="'/listing/' + selected.id">Xem chi tiết tin đang chọn ↗</RouterLink><a v-if="publicMapPoint(selected)" :href="googlePointUrl(selected.latitude, selected.longitude)" target="_blank" rel="noopener noreferrer">Mở vị trí trên Google Maps ↗</a></div></template><p v-else>Chọn một tin hoặc ghim để xem vị trí và tiện ích.</p></div>
    <div class="nearby-panel">
      <div class="nearby-heading"><div><h3>Tiện ích quanh vị trí đang chọn</h3><p>Dữ liệu địa điểm từ Backend · khoảng cách đường thẳng, không phải quãng đường di chuyển.</p></div><label>Bán kính<select v-model="radius"><option value="1000">1 km</option><option value="3000">3 km</option><option value="5000">5 km</option></select></label></div>
      <p v-if="!selected || !publicMapPoint(selected)" class="gis-message">Chọn tin có tọa độ được phép hiển thị để tìm tiện ích.</p>
      <p v-else-if="poiBusy" role="status" class="gis-message">Đang tìm tiện ích…</p>
      <p v-else-if="poiError" role="alert" class="gis-message">{{ poiError }} <button type="button" @click="loadPois">Thử lại</button></p>
      <p v-else-if="!pois.length" class="gis-message">Chưa có dữ liệu tiện ích phù hợp trong bán kính đã chọn. Không suy đoán địa điểm hoặc khoảng cách.</p>
      <template v-else>
        <div class="poi-categories"><button type="button" :aria-pressed="!category" @click="category = ''">Tất cả</button><button v-for="value in categories" :key="value" type="button" :aria-pressed="category === value" @click="category = value">{{ poiLabel(value) }}</button></div>
        <div class="poi-map-tools"><button type="button" :aria-pressed="showPois" :disabled="!visiblePois.some(poiHasPoint)" @click="showPois = !showPois">{{ showPois ? 'Ẩn' : 'Hiện' }} tiện ích trên bản đồ</button><span>{{ mapPois.length }} địa điểm có tọa độ · Ghép theo tin đang chọn</span></div>
        <p v-if="selectedPoi" class="poi-selection" role="status">Đang xem <strong>{{ selectedPoi.name }}</strong> · {{ distance(selectedPoi.distanceMeters) }} đường thẳng từ vị trí tin đang chọn.</p>
        <ul class="poi-list"><li v-for="poi in visiblePois" :key="poi.id" :class="{ 'selected-poi': selectedPoiId === poi.id }"><button type="button" :disabled="!poiHasPoint(poi)" :aria-pressed="selectedPoiId === poi.id" :aria-label="'Xem ' + poi.name + ' trên bản đồ'" :data-poi-card="poi.id" @click="selectPoi(poi.id)"><span><strong>{{ poi.name }}</strong><small>{{ poiLabel(poi.category) }}<template v-if="!poiHasPoint(poi)"> · Chưa có tọa độ hợp lệ</template></small></span><b>{{ distance(poi.distanceMeters) }}</b></button></li></ul>
      </template>
    </div>
  </div>
</template>
<style scoped>
.gis-legend{display:flex;flex-wrap:wrap;gap:14px;padding:0 22px 16px;font-size:13px;color:#536178}.gis-legend>span{display:flex;align-items:center;gap:6px}.gis-legend i{width:9px;height:9px;border-radius:50%;display:inline-block}.legend-sale{background:#142b4f}.legend-rent{background:#207760}.legend-selected{background:#b68a4c}.legend-poi{background:#8870ac}.poi-list{max-height:300px;overflow-y:auto;padding:3px;scrollbar-width:thin}
.poi-map-tools{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin-top:12px;font-size:13px;color:#536178}.poi-map-tools button{padding:10px 14px;min-height:40px;border:1px solid #d7dce4;border-radius:10px;color:#142b4f;cursor:pointer}.poi-map-tools button[aria-pressed=true]{background:#eee9fa;border-color:#a89acb}.poi-map-tools button:disabled{opacity:.5;cursor:default}.poi-selection{padding:12px 15px;margin-top:14px;border-radius:10px;background:#f1edf8;color:#665287;font-size:12px;line-height:1.8}.poi-list>li>button{display:flex;width:100%;justify-content:space-between;align-items:center;gap:12px;text-align:left;cursor:pointer;padding:4px;min-height:44px}.poi-list>li>button:disabled{cursor:default;color:#536178}.poi-list>li.selected-poi{border-color:#8b76b4;background:#f5f1fb}
.selected-links{display:flex;gap:18px;flex-wrap:wrap;margin-top:7px}
.home-gis{background:white;border:1px solid #e7e1d7;border-radius:24px;overflow:hidden}.gis-toolbar{padding:18px 22px;display:flex;justify-content:space-between;align-items:center;gap:15px;flex-wrap:wrap;font-size:12px}.live-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#237c63;margin-right:6px}.gis-toolbar a,.gis-detail,.selected-info a{font-weight:650;color:#142b4f;text-decoration:underline;text-underline-offset:4px}.gis-workspace{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(0,1fr);border-block:1px solid #e7e1d7}.gis-map-pane{height:480px;position:relative;min-width:0;background:#e9ede8}.gis-list{max-height:480px;overflow:auto;padding:15px;scrollbar-width:thin}.gis-list-label{font-size:13px;letter-spacing:.16em;color:#84704f;margin-bottom:14px}.gis-list article{border:1px solid #e7e1d7;border-radius:12px;padding:8px;margin-bottom:10px}.gis-list article.active{background:#f5f0e7;border-color:#b3915f;box-shadow:0 0 0 1px #b3915f}.select-property{display:flex;width:100%;text-align:left;gap:12px;cursor:pointer;color:#142b4f;align-items:center;min-width:0}.gis-thumb{width:84px;height:90px;overflow:hidden;border-radius:8px;flex-shrink:0}.gis-thumb :deep(img){width:100%;height:100%;object-fit:cover}.gis-card-text{min-width:0;display:flex;flex-direction:column;gap:5px;font-size:13px;color:#536178}.gis-card-text strong{color:#142b4f;font-size:13px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.gis-card-text b{color:#b13724;font-size:15px}.gis-detail{display:block;text-align:right;margin-top:6px;font-size:13px;padding:5px}.selected-info{padding:18px 22px;background:#f8f6f1;font-size:12px;line-height:1.8;color:#536178}.selected-info strong{color:#142b4f;font-size:14px}.nearby-panel{padding:22px}.nearby-heading{display:flex;align-items:start;justify-content:space-between;gap:15px}.nearby-heading h3{font-size:17px;font-weight:650}.nearby-heading p{font-size:12px;color:#536178;line-height:1.8;margin-top:6px}.nearby-heading label{display:flex;align-items:center;gap:8px;flex-shrink:0;font-size:12px}.nearby-heading select{padding:10px;border:1px solid #dcd5ca;border-radius:8px;background:white}.gis-message{font-size:13px;color:#536178;padding:16px 0;line-height:1.8}.gis-message button{cursor:pointer;text-decoration:underline}.poi-categories{display:flex;gap:7px;flex-wrap:wrap;margin:18px 0}.poi-categories button{padding:8px 14px;border-radius:20px;border:1px solid #e7e1d7;font-size:12px;cursor:pointer}.poi-categories button[aria-pressed=true]{background:#142b4f;color:white}.poi-list{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:16px;list-style:none}.poi-list li{display:flex;gap:12px;align-items:center;justify-content:space-between;border:1px solid #e7e1d7;border-radius:12px;padding:12px;font-size:12px}.poi-list small{display:block;color:#536178;margin-top:4px}.poi-list b{white-space:nowrap;color:#237c63}.map-activate{position:absolute;inset:0;width:100%;cursor:pointer;color:#142b4f}.no-points{position:absolute;top:45%;left:15px;right:15px;padding:16px;border-radius:14px;background:#fffffff0;font-size:13px;text-align:center;pointer-events:none;z-index:8}:focus-visible{outline:3px solid #b3915f;outline-offset:2px}@media(max-width:900px){.gis-workspace{grid-template-columns:1fr}.gis-map-pane{height:410px}.gis-list{max-height:310px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.gis-list-label{grid-column:1/-1}.gis-list article{margin:0}.poi-list{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:540px){.gis-map-pane{height:360px}.gis-list{grid-template-columns:1fr;max-height:280px}.nearby-heading{flex-wrap:wrap}.nearby-panel,.selected-info{padding:17px}.poi-list{grid-template-columns:1fr}}
</style>
