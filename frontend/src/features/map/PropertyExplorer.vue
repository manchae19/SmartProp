<script setup>
import { ref, computed, onBeforeUnmount, nextTick, watch } from 'vue'
import LeafletNearbyMap from './LeafletNearbyMap.vue'
import PrivateImage from '../../components/PrivateImage.vue'
import ContactPanel from '../property/ContactPanel.vue'
import { publicMapPoint, locationLabel } from './locationDisplay.js'
import { compactPrice, price, types, displayDecimal } from '../property/property.js'
import { POI_GROUPS, DEFAULT_GROUPS, RADII, filteredPlaces, distanceLabel } from './nearbyExplorer.js'
import { useNearbyPlaces } from './useNearbyPlaces.js'
const props = defineProps({ items: { type: Array, default: () => [] }, selectedId: String, allowNearby: { type: Boolean, default: true }, compact: Boolean, preview: Boolean, exploreLink: Object })
const emit = defineEmits(['select'])
const radius = ref(1000), groups = ref([...DEFAULT_GROUPS]), showProperty = ref(true), showRadius = ref(!props.preview), activePoi = ref(null), expanded = ref(false), panel = ref(null), expandButton = ref(null)
const property = computed(() => props.items.find(p => p.id === props.selectedId) || null)
const origin = computed(() => publicMapPoint(property.value) ? property.value : null)
const nearby = useNearbyPlaces(() => origin.value, () => radius.value, () => groups.value, () => props.allowNearby)
const places = computed(() => filteredPlaces(nearby.data.value?.items, origin.value, radius.value, groups.value))
const featuredPlaces = computed(() => props.preview ? places.value.slice(0, 4) : places.value)
const image = computed(() => property.value?.images?.find(i => i.cover || i.isCover)?.url || property.value?.images?.[0]?.url || property.value?.coverImageUrl || '')
const groupLabel = id => POI_GROUPS.find(g => g.id === id)?.label || 'Tiện ích'
let previousOverflow = '', previousFocus
async function toggleExpanded() {
  expanded.value = !expanded.value
  if (expanded.value) { previousOverflow = document.body.style.overflow; previousFocus = document.activeElement; document.body.style.overflow = 'hidden'; await nextTick(); panel.value?.focus() }
  else { document.body.style.overflow = previousOverflow; await nextTick(); previousFocus?.focus() }
}
function keyboard(e) {
  if (e.key === 'Escape' && expanded.value) { e.preventDefault(); toggleExpanded() }
  if (e.key !== 'Tab' || !expanded.value) return
  const elements = [...panel.value.querySelectorAll('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),[tabindex="0"]')].filter(el => el.getClientRects().length)
  const first = elements[0], last = elements.at(-1)
  if (e.shiftKey && (document.activeElement === first || document.activeElement === panel.value)) { e.preventDefault(); last?.focus() }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus() }
}
watch(() => props.selectedId, () => { activePoi.value = null })
onBeforeUnmount(() => { if (expanded.value) document.body.style.overflow = previousOverflow })
</script>
<template>
  <Teleport to="body" :disabled="!expanded">
    <section ref="panel" tabindex="-1" class="property-explorer" :class="{ 'is-expanded': expanded, 'is-compact': compact, 'is-preview': preview }" :role="expanded?'dialog':undefined" :aria-modal="expanded?'true':undefined" aria-label="Bản đồ và tiện ích bất động sản" @keydown="keyboard">
      <aside class="explorer-sidebar">
        <RouterLink v-if="!preview" to="/listings" class="explorer-back">← Quay lại kết quả tìm kiếm</RouterLink>
        <div v-if="items.length>1" class="explorer-picker"><label for="explorer-property">Tin đăng đang xem</label><select id="explorer-property" :value="selectedId || ''" @change="emit('select', $event.target.value)"><option value="" disabled>Chọn tin đăng</option><option v-for="p in items" :key="p.id" :value="p.id">{{p.title}}</option></select></div>
        <template v-if="property">
          <h2>{{property.title}}</h2>
          <div class="explorer-price" :title="price(property)">{{compactPrice(property)}}</div>
          <details v-if="!preview" class="explorer-exact"><summary>Giá đầy đủ</summary>{{price(property)}}</details>
          <div class="explorer-photo"><PrivateImage :key="property.id" :src="image" :alt="property.title" /></div>
          <div class="explorer-facts"><div><strong>{{displayDecimal(property.areaSqm)}} m²</strong><span>Diện tích</span></div><div><strong>{{types[property.propertyType] || 'Chưa rõ'}}</strong><span>Loại hình</span></div><div v-if="property.bedrooms!=null"><strong>{{property.bedrooms}}</strong><span>Phòng ngủ</span></div></div>
          <h3>{{preview?'Tiện ích nổi bật':'Vị trí & khoảng cách'}}</h3>
          <p v-if="!preview" class="explorer-address">⌖ {{[property.address,property.ward,property.district,property.city].filter(Boolean).join(', ') || 'Chưa có địa chỉ công bố'}}</p>
          <p v-if="!preview" class="explorer-location-note">{{locationLabel(property)}}</p>
          <p v-if="!origin" class="explorer-notice">Tin chưa có vị trí công khai phù hợp. Không đặt ghim thay thế.</p>
          <p v-else-if="!allowNearby" class="explorer-notice">Tiện ích chỉ được truy vấn cho tin đang công khai.</p>
          <p v-if="nearby.busy.value" role="status" class="explorer-notice">Đang tìm tiện ích trong {{distanceLabel(radius)}}…</p>
          <div v-if="nearby.error.value" role="alert" class="explorer-warning">{{nearby.error.value}} <button type="button" @click="nearby.retry">Thử lại</button></div>
          <p v-else-if="origin && allowNearby && !nearby.busy.value && groups.length && nearby.data.value && !places.length" class="explorer-notice">Chưa tìm thấy tiện ích phù hợp trong phạm vi đã chọn.</p>
          <p v-if="!groups.length" class="explorer-notice">Bật một nhóm tiện ích để tìm quanh tin đăng.</p>
          <ol class="explorer-pois"><li v-for="p in featuredPlaces" :key="p.id"><button type="button" :class="{ active: activePoi===p.id }" @click="activePoi=p.id"><span class="poi-dot" :style="{background:POI_GROUPS.find(g=>g.id===p.category)?.color}">{{POI_GROUPS.find(g=>g.id===p.category)?.icon}}</span><span><strong>{{p.name}}</strong><small>{{groupLabel(p.category)}}</small></span><b v-if="!preview">{{distanceLabel(p.distanceMeters)}}</b></button></li></ol>
          <p v-if="!preview && nearby.data.value" class="explorer-source">Đường chim bay · {{places.length}} tiện ích · Dữ liệu có thể chưa đầy đủ{{nearby.data.value.truncated?' (đã giới hạn kết quả)':''}}.<br>Cập nhật truy vấn: {{new Date(nearby.data.value.fetchedAt).toLocaleString('vi-VN')}}{{nearby.data.value.cacheHit?' · Bộ nhớ đệm':''}}</p>
          <RouterLink :to="'/listing/'+property.id" class="explorer-detail">Xem chi tiết tin →</RouterLink>
          <ContactPanel v-if="allowNearby && !preview" :property-id="property.id" />
        </template>
        <p v-else class="explorer-notice">Chọn một tin đăng có tọa độ để khám phá tiện ích xung quanh.</p>
      </aside>
      <div class="explorer-map-column">
        <header class="explorer-map-toolbar"><div><span class="gis-dot"></span><strong>{{preview?"Khám phá không gian sống":"GIS Explorer"}}</strong><span class="explorer-subtitle">{{preview?"Chạm vào ghim để xem tin đăng":"Bất động sản & tiện ích quanh bạn"}}</span></div><RouterLink v-if="preview" :to="exploreLink || {path:'/map',query:selectedId?{propertyId:selectedId}:{}}" class="explorer-launch">Khám phá GIS đầy đủ ↗</RouterLink><button v-else ref="expandButton" type="button" @click="toggleExpanded" :aria-expanded="expanded">{{expanded?'✕ Thu nhỏ':'⛶ Mở rộng'}}</button></header>
        <div class="explorer-map-content">
          <LeafletNearbyMap :simple="preview" :items="items" :selected-id="origin?.id" :places="featuredPlaces" :radius="radius" :show-property="showProperty" :show-radius="showRadius" :active-poi="activePoi" @select="emit('select',$event)" @select-poi="activePoi=$event" />
          <div v-if="!preview" class="explorer-layers"><h3>Lớp hiển thị</h3><label><input v-model="showProperty" type="checkbox"> Bất động sản</label><label v-for="group in POI_GROUPS" :key="group.id"><input v-model="groups" :value="group.id" :aria-label="group.label" type="checkbox"><span aria-hidden="true" :style="{color:group.color}">{{group.icon}}</span> {{group.label}}</label><label><input v-model="showRadius" type="checkbox"> Vùng tìm tiện ích</label></div>
          <div v-if="!preview" class="explorer-radius"><label>Bán kính tìm kiếm <select v-model.number="radius" aria-label="Bán kính tìm tiện ích"><option v-for="r in RADII" :key="r" :value="r">{{distanceLabel(r)}}</option></select></label><small>Vòng tròn tìm kiếm, không phải ranh giới hay sai số vị trí.</small></div>
        </div>
        <footer class="explorer-credits"><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a><span> · </span><a href="https://www.geoapify.com/" target="_blank" rel="noopener noreferrer">Powered by Geoapify</a><span v-if="!preview"> · Khoảng cách đường chim bay, không phải quãng đường di chuyển.</span></footer>
      </div>
    </section>
  </Teleport>
</template>
<style scoped>
.property-explorer{display:grid;grid-template-columns:340px minmax(0,1fr);background:#fff;color:#202944;border:1px solid #e5e2ef;border-radius:20px;overflow:hidden;min-height:720px;box-shadow:0 8px 35px #29245908;font-family:inherit}.property-explorer.is-expanded{position:fixed;inset:12px;z-index:10000;border-radius:16px;height:calc(100dvh - 24px);min-height:0;outline:none}.explorer-sidebar{padding:22px;max-height:800px;overflow-y:auto;background:linear-gradient(135deg,#fcfbff,#fff);border-right:1px solid #e9e5f1}.is-expanded .explorer-sidebar{max-height:none}.explorer-back{display:inline-block;background:#f0edfb;color:#363268;border-radius:8px;padding:8px 11px;font-size:12px;margin-bottom:17px}.explorer-picker{margin-bottom:16px}.explorer-picker label{display:block;font-size:11px;color:#6e7290;margin-bottom:5px}.explorer-picker select{width:100%;border:1px solid #dedbe9;border-radius:8px;padding:9px;font-size:12px;background:white}.explorer-sidebar h2{font-size:21px;line-height:1.5;font-weight:750;margin:0 0 10px;overflow-wrap:anywhere}.explorer-price{font-size:29px;font-weight:800;color:#5734d8;line-height:1.35}.explorer-exact{font-size:11px;color:#6c6683;margin:6px 0 14px}.explorer-exact summary{cursor:pointer}.explorer-photo{height:175px;border-radius:12px;overflow:hidden;background:#eceaf0}.explorer-photo :deep(img){height:100%;width:100%;object-fit:cover}.explorer-facts{display:flex;gap:7px;background:#f6f3fe;padding:12px 8px;border-radius:10px;margin:13px 0 22px}.explorer-facts>div{flex:1;text-align:center;display:flex;flex-direction:column;gap:5px}.explorer-facts strong{font-size:13px}.explorer-facts span{font-size:11px;color:#716a89}.explorer-sidebar h3{font-size:14px;font-weight:750;margin-bottom:10px}.explorer-address{font-size:12px;line-height:1.7}.explorer-location-note,.explorer-source{font-size:11px;line-height:1.7;color:#77778e;margin:9px 0}.explorer-notice{font-size:12px;line-height:1.7;color:#77778e;padding:10px 0}.explorer-warning{font-size:12px;line-height:1.7;color:#945620;background:#fff4e9;padding:12px;border-radius:9px;margin-block:12px}.explorer-warning button{text-decoration:underline;font-weight:700}.explorer-pois{margin:10px 0 0;padding:0;list-style:none;max-height:310px;overflow:auto}.explorer-pois li button{display:flex;align-items:center;gap:9px;padding:10px 4px;width:100%;text-align:left;border-bottom:1px solid #efedf6}.explorer-pois li button:hover,.explorer-pois li button.active{background:#f0edfd;border-radius:7px}.poi-dot{width:25px;height:25px;color:white;border-radius:50%;display:grid;place-items:center;flex-shrink:0;font-size:13px}.explorer-pois li button>span:nth-child(2){flex:1;min-width:0}.explorer-pois strong{display:block;font-size:12px;font-weight:550;overflow-wrap:anywhere}.explorer-pois small{display:block;font-size:10px;color:#8b879c}.explorer-pois b{font-size:11px;font-weight:550;white-space:nowrap}.explorer-detail{display:block;text-align:center;border:1px solid #d6cff8;color:#5734d8;border-radius:9px;padding:10px;font-size:12px;margin-top:16px}.explorer-map-column{min-width:0;display:flex;flex-direction:column}.explorer-map-toolbar{display:flex;justify-content:space-between;gap:12px;align-items:center;background:#fff;padding:13px 16px;min-height:55px}.explorer-map-toolbar>div{display:flex;align-items:center;gap:8px}.explorer-map-toolbar strong{font-size:14px}.gis-dot{width:7px;height:7px;background:#6851df;border-radius:50%}.explorer-subtitle{font-size:11px;color:#85829a}.explorer-map-toolbar button{font-size:12px;font-weight:650;border:1px solid #ddd7f4;border-radius:8px;padding:8px 11px;color:#5734d8;white-space:nowrap}.explorer-map-content{position:relative;flex:1;min-height:620px}.explorer-map-content>:deep(.leaflet-explorer-shell){position:absolute;inset:0}.explorer-layers{position:absolute;left:16px;bottom:40px;z-index:500;background:#ffffffed;border:1px solid #e7e1f6;border-radius:12px;padding:12px 14px;box-shadow:0 4px 18px #22234418;max-width:215px}.explorer-layers h3{font-size:12px;font-weight:750;margin:0 0 7px}.explorer-layers label{display:flex;align-items:center;gap:7px;font-size:11px;line-height:1.6;padding:3px 0;cursor:pointer}.explorer-layers input{accent-color:#6542db}.explorer-radius{position:absolute;right:16px;bottom:40px;z-index:500;background:#fffffff0;box-shadow:0 4px 18px #22234418;border:1px solid #e7e1f6;border-radius:12px;padding:12px;max-width:225px}.explorer-radius label{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:12px;font-weight:650}.explorer-radius select{border:1px solid #e4dff1;border-radius:7px;padding:6px;background:white;color:#5734d8;font-weight:700}.explorer-radius small{font-size:10px;line-height:1.6;color:#817990;display:block;margin-top:7px}.explorer-credits{font-size:10px;line-height:1.7;color:#807891;padding:9px 16px;border-top:1px solid #eeeaf4}.explorer-credits a{color:#605395;text-decoration:underline}.property-explorer :focus-visible{outline:3px solid #a695ef;outline-offset:2px}.is-compact{grid-template-columns:280px minmax(0,1fr)}.is-compact .explorer-subtitle{display:none}.is-compact .explorer-map-content{min-height:650px}.is-compact .explorer-radius{right:10px;max-width:170px}.is-compact .explorer-layers{left:10px;padding:10px}.is-compact .explorer-sidebar{padding:16px}.is-compact .explorer-sidebar h2{font-size:17px}@media(max-width:1100px){.property-explorer{grid-template-columns:290px minmax(0,1fr)}.explorer-subtitle{display:none}}@media(max-width:760px){.property-explorer,.is-compact{grid-template-columns:minmax(0,1fr);min-height:0}.explorer-sidebar{max-height:400px;border-right:0;border-bottom:1px solid #e9e5f1}.explorer-photo{display:none}.explorer-sidebar h2{font-size:18px}.explorer-facts{margin-bottom:13px}.explorer-pois{max-height:170px}.explorer-map-content,.is-compact .explorer-map-content{min-height:620px}.is-expanded{display:flex!important;flex-direction:column}.is-expanded .explorer-sidebar{max-height:28dvh;flex:none}.is-expanded .explorer-map-column{flex:1;min-height:0}.is-expanded .explorer-map-content{min-height:0}.explorer-layers{left:10px;bottom:33px;padding:10px;max-width:180px}.explorer-layers label{font-size:10px}.explorer-radius{right:10px;bottom:33px;max-width:145px;padding:9px}.explorer-radius label{flex-wrap:wrap;font-size:11px}.explorer-map-toolbar{padding:10px 12px}.explorer-credits{padding:7px 10px}.property-explorer.is-expanded{inset:0;height:100dvh;border-radius:0}.explorer-price{font-size:26px}}

.property-explorer{--gis-accent:#147d80;border:1px solid #dce5e7;border-radius:24px;box-shadow:0 15px 50px #15364d0d;color:#173147}
.explorer-sidebar{background:linear-gradient(155deg,#fff 30%,#f0f6f5);padding:24px;border-color:#e1e9e8}
.explorer-sidebar h2{font-size:22px;font-weight:720;letter-spacing:-.025em;line-height:1.45}
.explorer-price{color:#137477;font-size:32px;letter-spacing:-.04em;margin-top:12px}
.explorer-photo{border-radius:16px;margin-top:16px}.explorer-facts{background:#eaf3ef;border:1px solid #dfece6;border-radius:14px;padding-block:14px}
.explorer-back{background:#edf3f3;color:#3f6068}.explorer-picker label{color:#627d80;text-transform:uppercase;letter-spacing:.08em;font-size:10px}
.explorer-picker select{border-color:#d5e2df;border-radius:10px;padding:11px;color:#254651}
.explorer-map-toolbar{background:linear-gradient(110deg,#142b4f,#21495d);color:#fff;min-height:72px;padding:16px 22px}
.explorer-map-toolbar>div{flex-wrap:wrap;column-gap:10px;row-gap:3px}
.explorer-map-toolbar strong{font-size:17px;font-weight:650;letter-spacing:-.02em}
.explorer-subtitle{color:#c3d9dc}.gis-dot{background:#6ad5b1;box-shadow:0 0 0 4px #6ad5b118}
.explorer-map-toolbar button,.explorer-launch{border:1px solid #ffffff35;background:#ffffff12;color:#fff;border-radius:11px;padding:10px 14px;font-size:12px;white-space:nowrap}
.explorer-launch{background:#e7c98f;color:#172c40;border-color:#e7c98f;font-weight:700;text-decoration:none}
.explorer-layers,.explorer-radius{border:1px solid #e0e9e5;border-radius:16px;backdrop-filter:blur(14px);box-shadow:0 6px 30px #1a34451a;padding:15px}
.explorer-layers h3{font-size:12px;color:#244950;padding-bottom:9px;border-bottom:1px solid #e5ece9}
.explorer-layers label{padding-block:4px;font-size:12px}.explorer-layers input{accent-color:#147d80}
.explorer-radius select{border-color:#c9dfda;color:#137477;padding:8px 10px;border-radius:10px}
.explorer-pois li button{border-color:#e0eae7;padding:12px 3px;border-radius:10px}
.explorer-pois li button:hover,.explorer-pois li button.active{background:#e3f1eb}
.explorer-pois strong{font-size:13px}.poi-dot{width:30px;height:30px;font-size:15px}
.explorer-detail{color:#147477;border-color:#bddbd3;border-radius:11px;font-weight:650;background:#fff}
.explorer-credits{background:#f8fbfa;border-color:#e3ece8;color:#6e8588}.explorer-credits a{color:#567678}
.is-preview{grid-template-columns:310px minmax(0,1fr);min-height:590px}
.is-preview .explorer-sidebar{max-height:650px;padding:22px}
.is-preview .explorer-sidebar h2{font-size:18px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.is-preview .explorer-photo{height:120px;margin-top:12px}
.is-preview .explorer-price{font-size:28px;margin-top:5px}
.is-preview .explorer-facts{margin:12px 0 18px;padding:10px 5px}
.is-preview .explorer-map-content{min-height:540px}.is-preview .explorer-pois{max-height:155px}
.is-preview .explorer-map-toolbar{gap:12px}.is-preview .explorer-subtitle{display:none}
.is-expanded .explorer-map-column,.is-expanded .explorer-map-content{min-height:0}
.property-explorer :focus-visible{outline-color:#2ba990}
@media(max-width:900px){.explorer-map-toolbar{padding:14px}.explorer-map-toolbar strong{font-size:15px}.explorer-subtitle{display:none}.is-preview{grid-template-columns:260px minmax(0,1fr)}.is-preview .explorer-sidebar{padding:17px}.explorer-launch{padding:10px;font-size:11px}}
@media(max-width:760px){.property-explorer{border-radius:18px}.is-preview{display:flex;flex-direction:column}.is-preview .explorer-map-column{order:-1}.is-preview .explorer-map-content{min-height:420px}.is-preview .explorer-sidebar{max-height:380px}.explorer-map-toolbar{padding:13px 12px;min-height:64px}.explorer-map-toolbar strong{font-size:14px}.explorer-layers,.explorer-radius{padding:10px;border-radius:12px}.explorer-layers label{font-size:10px}.explorer-layers h3{padding-bottom:6px}.explorer-sidebar h2{font-size:19px}}
</style>
