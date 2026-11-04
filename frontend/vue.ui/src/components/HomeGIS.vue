<script setup>
import { computed, ref, watch, nextTick, onMounted, onBeforeUnmount, defineAsyncComponent } from 'vue'
import { api } from '../services/api.js'
import { compactPrice } from '../services/property.js'
import { publicMapPoint, locationLabel } from '../services/locationDisplay.js'
import { googlePointUrl } from '../services/googleMapsLocation.js'
import { nearbyPlaces, poiHasPoint, poiLabel, poiColor, poiColorBg, poiColorBorder } from '../services/nearbyPlaces.js'
import PrivateImage from './business/PrivateImage.vue'
import PoiIcon from './PoiIcon.vue'

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
function selectPoi(id) {
  if (!id) { selectedPoiId.value = null; return }
  if (visiblePois.value.some(poi => poi.id === id && poiHasPoint(poi))) { showPois.value = true; selectedPoiId.value = id }
}
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
    <div class="gis-legend" aria-label="Chú giải bản đồ">
      <span><i class="legend-sale"></i>Bán</span>
      <span><i class="legend-rent"></i>Cho thuê</span>
      <span><i class="legend-selected"></i>BĐS đang chọn</span>
      <span v-if="mapPois.length" class="hidden sm:inline-block text-slate-300">|</span>
      <span v-if="mapPois.length" class="legend-poi-item"><i style="background:#2563eb"></i>Trường học</span>
      <span v-if="mapPois.length" class="legend-poi-item"><i style="background:#e11d48"></i>Y tế</span>
      <span v-if="mapPois.length" class="legend-poi-item"><i style="background:#059669"></i>Công viên/Biển</span>
      <span v-if="mapPois.length" class="legend-poi-item"><i style="background:#d97706"></i>Siêu thị/Chợ</span>
      <span v-if="mapPois.length" class="legend-poi-item"><i style="background:#7c3aed"></i>Giao thông</span>
    </div>
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
        <div class="poi-categories">
          <button type="button" :aria-pressed="!category" @click="category = ''" class="category-btn">
            <span>Tất cả</span>
            <span class="count-badge">{{ pois.length }}</span>
          </button>
          <button v-for="value in categories" :key="value" type="button" :aria-pressed="category === value" @click="category = value" class="category-btn">
            <PoiIcon :category="value" class="size-3.5" />
            <span>{{ poiLabel(value) }}</span>
            <span class="count-badge">{{ pois.filter(p => p.category === value).length }}</span>
          </button>
        </div>
        <div class="poi-map-tools">
          <button type="button" :aria-pressed="showPois" :disabled="!visiblePois.some(poiHasPoint)" @click="showPois = !showPois">{{ showPois ? 'Ẩn' : 'Hiện' }} tiện ích trên bản đồ</button>
          <span>{{ mapPois.length }} địa điểm có tọa độ · Ghép theo tin đang chọn</span>
        </div>
        <div v-if="selectedPoi" class="poi-selection" role="status">
          <div class="poi-selection-icon" :style="{ backgroundColor: poiColor(selectedPoi.category) }">
            <PoiIcon :category="selectedPoi.category" class="size-4 text-white" />
          </div>
          <div class="poi-selection-content">
            <p>Đang chọn <strong>{{ selectedPoi.name }}</strong> ({{ poiLabel(selectedPoi.category) }})</p>
            <span>Khoảng cách: <strong>{{ distance(selectedPoi.distanceMeters) }}</strong> đường thẳng từ bất động sản</span>
          </div>
        </div>
        <ul class="poi-list">
          <li v-for="poi in visiblePois" :key="poi.id" :class="{ 'selected-poi': selectedPoiId === poi.id }" class="poi-item">
            <button type="button" :disabled="!poiHasPoint(poi)" :aria-pressed="selectedPoiId === poi.id" :aria-label="'Xem ' + poi.name + ' trên bản đồ'" :data-poi-card="poi.id" @click="selectPoi(poi.id)" class="poi-card-button">
              <div class="poi-icon-box" :style="{ backgroundColor: poiColorBg(poi.category), color: poiColor(poi.category), borderColor: poiColorBorder(poi.category) }">
                <PoiIcon :category="poi.category" class="size-4" />
              </div>
              <div class="poi-text">
                <strong class="poi-name" :title="poi.name">{{ poi.name }}</strong>
                <div class="poi-sub">
                  <span class="poi-badge" :style="{ backgroundColor: poiColorBg(poi.category), color: poiColor(poi.category), borderColor: poiColorBorder(poi.category) }">
                    {{ poiLabel(poi.category) }}
                  </span>
                  <small v-if="!poiHasPoint(poi)" class="text-slate-400">Chưa có tọa độ</small>
                </div>
              </div>
              <div class="poi-distance">
                <svg class="size-3 inline-block mr-0.5 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                <b>{{ distance(poi.distanceMeters) }}</b>
              </div>
            </button>
          </li>
        </ul>
      </template>
    </div>
  </div>
</template>
<style scoped>
.gis-legend{display:flex;flex-wrap:wrap;align-items:center;gap:14px;padding:0 22px 16px;font-size:13px;color:#536178}
.gis-legend>span{display:flex;align-items:center;gap:6px}
.gis-legend i{width:10px;height:10px;border-radius:50%;display:inline-block}
.legend-sale{background:#142b4f}
.legend-rent{background:#207760}
.legend-selected{background:#b68a4c}
.legend-poi-item{font-size:12px;color:#64748b}

.poi-categories{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0}
.category-btn{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border-radius:9999px;border:1px solid #e2e8f0;background:white;font-size:13px;font-weight:600;color:#1e325a;cursor:pointer;transition:all .15s ease}
.category-btn:hover{background:#f8fafc;border-color:#cbd5e1}
.category-btn[aria-pressed=true]{background:#142b4f;color:white;border-color:#142b4f;box-shadow:0 2px 6px rgba(20,43,79,.25)}
.count-badge{font-size:11px;padding:1px 6px;border-radius:9999px;background:rgba(0,0,0,.06)}
.category-btn[aria-pressed=true] .count-badge{background:rgba(255,255,255,.25);color:white}

.poi-map-tools{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin-top:12px;font-size:13px;color:#536178}
.poi-map-tools button{padding:9px 14px;min-height:38px;border:1px solid #d7dce4;border-radius:10px;color:#142b4f;cursor:pointer;font-weight:600;font-size:13px;transition:all .15s ease}
.poi-map-tools button[aria-pressed=true]{background:#142b4f;color:white;border-color:#142b4f}
.poi-map-tools button:disabled{opacity:.5;cursor:default}

.poi-selection{display:flex;align-items:center;gap:12px;padding:12px 16px;margin-top:14px;border-radius:12px;background:#f8f6f0;border:1px solid #e7d9bd;color:#142b4f;font-size:13px}
.poi-selection-icon{width:32px;height:32px;min-width:32px;border-radius:8px;display:grid;place-items:center}
.poi-selection-content p{margin:0;font-weight:500}
.poi-selection-content span{font-size:12px;color:#536178}

.poi-list{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:16px;list-style:none;max-height:380px;overflow-y:auto;padding:4px;scrollbar-width:thin}
.poi-item{border:1px solid #e7e1d7;border-radius:14px;background:white;transition:all .18s ease;overflow:hidden}
.poi-item:hover{border-color:#b3915f;box-shadow:0 4px 12px rgba(20,43,79,.06);transform:translateY(-1px)}
.poi-item.selected-poi{border-color:#142b4f;box-shadow:0 0 0 2px #142b4f25,0 4px 12px rgba(20,43,79,.1);background:#fafaf9}
.poi-card-button{display:flex;width:100%;align-items:center;gap:12px;padding:12px;text-align:left;cursor:pointer;border:none;background:transparent}
.poi-icon-box{width:38px;height:38px;min-width:38px;border-radius:10px;display:grid;place-items:center;border:1px solid;transition:transform .15s ease}
.poi-item:hover .poi-icon-box{transform:scale(1.08)}
.poi-text{min-width:0;flex:1;display:flex;flex-direction:column;gap:4px}
.poi-name{color:#142b4f;font-size:13px;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}
.poi-sub{display:flex;align-items:center;gap:6px}
.poi-badge{font-size:11px;font-weight:600;padding:1px 7px;border-radius:6px;border:1px solid}
.poi-distance{white-space:nowrap;font-size:13px;color:#059669;font-weight:700;display:flex;align-items:center;padding-left:6px}

.selected-links{display:flex;gap:18px;flex-wrap:wrap;margin-top:7px}
.home-gis{background:white;border:1px solid #e7e1d7;border-radius:24px;overflow:hidden}
.gis-toolbar{padding:18px 22px;display:flex;justify-content:space-between;align-items:center;gap:15px;flex-wrap:wrap;font-size:12px}
.live-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#237c63;margin-right:6px}
.gis-toolbar a,.gis-detail,.selected-info a{font-weight:650;color:#142b4f;text-decoration:underline;text-underline-offset:4px}
.gis-workspace{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(0,1fr);border-block:1px solid #e7e1d7}
.gis-map-pane{height:480px;position:relative;min-width:0;background:#e9ede8}
.gis-list{max-height:480px;overflow:auto;padding:15px;scrollbar-width:thin}
.gis-list-label{font-size:13px;letter-spacing:.16em;color:#84704f;margin-bottom:14px}
.gis-list article{border:1px solid #e7e1d7;border-radius:12px;padding:8px;margin-bottom:10px}
.gis-list article.active{background:#f5f0e7;border-color:#b3915f;box-shadow:0 0 0 1px #b3915f}
.select-property{display:flex;width:100%;text-align:left;gap:12px;cursor:pointer;color:#142b4f;align-items:center;min-width:0}
.gis-thumb{width:84px;height:90px;overflow:hidden;border-radius:8px;flex-shrink:0}
.gis-thumb :deep(img){width:100%;height:100%;object-fit:cover}
.gis-card-text{min-width:0;display:flex;flex-direction:column;gap:5px;font-size:13px;color:#536178}
.gis-card-text strong{color:#142b4f;font-size:13px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.gis-card-text b{color:#b13724;font-size:15px}
.gis-detail{display:block;text-align:right;margin-top:6px;font-size:13px;padding:5px}
.selected-info{padding:18px 22px;background:#f8f6f1;font-size:12px;line-height:1.8;color:#536178}
.selected-info strong{color:#142b4f;font-size:14px}
.nearby-panel{padding:22px}
.nearby-heading{display:flex;align-items:start;justify-content:space-between;gap:15px}
.nearby-heading h3{font-size:17px;font-weight:650}
.nearby-heading p{font-size:12px;color:#536178;line-height:1.8;margin-top:6px}
.nearby-heading label{display:flex;align-items:center;gap:8px;flex-shrink:0;font-size:12px}
.nearby-heading select{padding:10px;border:1px solid #dcd5ca;border-radius:8px;background:white}
.gis-message{font-size:13px;color:#536178;padding:16px 0;line-height:1.8}
.gis-message button{cursor:pointer;text-decoration:underline}
.map-activate{position:absolute;inset:0;width:100%;cursor:pointer;color:#142b4f}
.no-points{position:absolute;top:45%;left:15px;right:15px;padding:16px;border-radius:14px;background:#fffffff0;font-size:13px;text-align:center;pointer-events:none;z-index:8}
:focus-visible{outline:3px solid #b3915f;outline-offset:2px}
@media(max-width:900px){
  .gis-workspace{grid-template-columns:1fr}
  .gis-map-pane{height:410px}
  .gis-list{max-height:310px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
  .gis-list-label{grid-column:1/-1}
  .gis-list article{margin:0}
  .poi-list{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media(max-width:540px){
  .gis-map-pane{height:360px}
  .gis-list{grid-template-columns:1fr;max-height:280px}
  .nearby-heading{flex-wrap:wrap}
  .nearby-panel,.selected-info{padding:17px}
  .poi-list{grid-template-columns:1fr}
}
</style>
