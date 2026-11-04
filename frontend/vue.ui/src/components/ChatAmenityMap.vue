<script setup>
import { computed, ref, nextTick } from 'vue'
import BrowseTileMap from './BrowseTileMap.vue'
import PoiIcon from './PoiIcon.vue'
import { amenityCategories } from '../services/chatAmenities.js'
import { poiColor } from '../services/nearbyPlaces.js'
const props = defineProps({ data: Object, status: String, message: String })
const emit = defineEmits(['retry', 'reading'])
const selected = ref(null), expanded = ref(false), host = ref(null)
const items = computed(() => props.data?.items || [])
const points = computed(() => items.value.map(p => ({ ...p, categoryLabel: amenityCategories[p.category] })))
const cards = computed(() => expanded.value ? items.value : items.value.slice(0, 6))
const categories = computed(() => [...new Set(items.value.map(p => p.category))])
function select(id) {
  selected.value = id; emit('reading')
  // In a conversation the map may be partly above the reading viewport. Bring
  // the actual map (not just a focused pin) into view so its popup stays readable.
  if (id) nextTick(() => host.value?.querySelector('.browse-map')?.scrollIntoView({ block: 'center', inline: 'nearest' }))
}
</script>
<template>
  <section ref="host" class="chat-amenity" data-chat-amenities aria-label="Tiện ích trên bản đồ">
    <p v-if="status === 'loading'" class="map-state" role="status" data-amenity-loading>Đang tìm tiện ích trên bản đồ…</p>
    <p v-else-if="status === 'error'" class="map-state map-error" role="status" data-amenity-error>Chưa tải được bản đồ tiện ích. Câu trả lời phía trên vẫn được giữ. <button type="button" @click="emit('retry')">Thử lại bản đồ</button></p>
    <template v-else-if="items.length || data?.boundary">
      <div class="amenity-map-card" data-chat-map>
        <div class="map-heading"><h3>Tiện ích · {{ data.district }}</h3><span>{{ items.length ? items.length + ' địa điểm' : 'Ranh giới khu vực' }}</span></div>
        <BrowseTileMap class="chat-poi-map" :poi-items="points" :boundary="data.boundary?.geometry" :selected-poi-id="selected" map-label="Bản đồ tiện ích: kéo để di chuyển, phím mũi tên và cộng trừ để điều khiển" @select-poi="select" />
        <p v-if="!items.length" class="map-note" data-amenity-area-only>Chỉ có ranh giới khu vực lịch sử. Chưa có tọa độ tiện ích đủ điều kiện cho yêu cầu này; không đặt ghim ước lượng.</p>
        <div class="map-legend" aria-label="Loại tiện ích"><span v-for="cat in categories" :key="cat"><i :style="{ background: poiColor(cat) }" aria-hidden="true"></i>{{ amenityCategories[cat] }}</span></div>
        <p class="map-note">Điểm theo dữ liệu OpenStreetMap, chưa xác minh thực địa. Ghim vùng đại diện cho đối tượng bản đồ, không phải cổng vào. Không xác định khoảng cách tới căn nhà.</p>
        <p v-if="data.truncated" class="map-note">Đang hiển thị một phần địa điểm, tối đa 8 mỗi loại khi xem nhiều loại tiện ích.</p>
      </div>
      <div class="amenity-cards" data-amenity-cards>
        <article v-for="p in cards" :key="p.id" :data-amenity-card="p.id" :class="{ active: selected === p.id }">
          <button type="button" class="amenity-select" @click="select(p.id)"><span class="amenity-icon" :style="{ color: poiColor(p.category) }"><PoiIcon :category="p.category" /></span><span><strong>{{ p.name }}</strong><small>{{ amenityCategories[p.category] }} · {{ p.district }}</small></span></button>
          <div class="amenity-source"><span>{{ p.coordinateBasis === 'OSM_NODE' ? 'Điểm ghi trong OSM' : 'Điểm đại diện đối tượng OSM' }}</span><a :href="p.sourceUrl" target="_blank" rel="noopener noreferrer">Nguồn OSM ↗</a></div>
        </article>
      </div>
      <button v-if="items.length > 6" type="button" class="more-amenities" :aria-expanded="expanded" @click="expanded = !expanded; emit('reading')">{{ expanded ? 'Thu gọn tiện ích' : 'Xem tất cả ' + items.length + ' tiện ích' }}</button>
      <details class="map-provenance" @toggle="event => event.target.open && emit('reading')"><summary>Nguồn bản đồ ({{ items.length || 1 }})</summary><p v-if="items.length">{{ items[0].attribution }} · {{ items[0].sourceLicense }}</p><p v-if="data.boundary"><a :href="data.boundary.sourceUrl" target="_blank" rel="noopener noreferrer">Ranh giới lịch sử · {{ data.boundary.attribution }} · {{ data.boundary.license }}</a></p><p v-for="line in data.dataLimitations" :key="line">{{ line }}</p></details>
    </template>
    <p v-else class="map-state" data-amenity-empty>{{ message || 'Chưa có tọa độ tiện ích đủ điều kiện hiển thị; không đặt ghim ước lượng trên bản đồ.' }}</p>
  </section>
</template>
<style scoped>
.chat-amenity .chat-poi-map{position:relative;inset:auto;overflow:clip}.chat-poi-map :deep(.poi-map-popup){left:10px!important;right:10px;top:auto!important;bottom:30px;transform:none!important;max-height:210px;overflow:auto;animation:none}.chat-poi-map :deep(.poi-popup-card){max-width:none;min-width:0}.chat-poi-map :deep(.poi-popup-arrow){display:none}.chat-poi-map :deep(.poi-popup-source){display:block;font-size:12px;line-height:1.7;min-height:30px;align-content:center;color:#23466c;text-decoration:underline}.chat-poi-map :deep(.poi-popup-close){min-width:36px;min-height:36px}.chat-poi-map :deep(.map-controls button){min-width:40px;min-height:40px}.chat-poi-map :deep(.poi-pin){width:34px;height:34px}
.chat-amenity{max-width:560px;min-width:0;margin:12px 0}.amenity-map-card{border:1px solid #dce2e9;border-radius:17px;overflow:hidden;background:#fff}.map-heading{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:12px 14px}.map-heading h3{font-size:.83rem;font-weight:700}.map-heading>span{font-size:.65rem;color:var(--color-brand-muted);white-space:nowrap}.chat-poi-map{height:300px;min-height:240px;width:100%;border-radius:0}.map-legend{display:flex;flex-wrap:wrap;gap:7px 12px;padding:10px 12px 0;font-size:.65rem;color:#46566a}.map-legend span{display:inline-flex;align-items:center;gap:5px}.map-legend i{width:8px;height:8px;border-radius:50%}.map-note{font-size:.65rem;line-height:1.75;color:#5b6879;padding:8px 12px 10px}.map-note+.map-note{padding-top:0}.map-state{font-size:.78rem;line-height:1.75;background:#f3f5f8;padding:12px 14px;border-radius:14px;color:#53627a}.map-error{background:#fff5e7;color:#79571c}.map-state button{display:block;min-height:44px;font-weight:650;text-decoration:underline}.amenity-cards{display:grid;gap:8px;margin-top:10px}.amenity-cards article{background:#fff;border:1px solid #dfe5ec;border-radius:14px;padding:5px 11px}.amenity-cards article.active{border-color:#7999bf;box-shadow:0 0 0 2px #e6edf7}.amenity-select{display:flex;align-items:center;gap:10px;min-height:49px;width:100%;text-align:left}.amenity-icon{width:30px;height:30px;display:grid;place-items:center;flex-shrink:0;background:#f2f5f9;border-radius:10px}.amenity-icon svg{width:18px;height:18px}.amenity-select strong{display:block;font-size:.79rem;font-weight:650;line-height:1.65}.amenity-select small{display:block;font-size:.65rem;color:#65738a;line-height:1.7}.amenity-source{display:flex;align-items:center;justify-content:space-between;gap:10px;font-size:.61rem;color:#66758b;padding-left:40px;flex-wrap:wrap}.amenity-source a{display:inline-block;align-content:center;min-height:34px;text-decoration:underline;color:#233e61}.more-amenities{width:100%;min-height:44px;font-size:.75rem;color:#233e61;border:1px solid #dce3ee;border-radius:13px;margin-top:8px;background:#f5f8fc}.map-provenance{font-size:.65rem;color:#66758b;margin:6px}.map-provenance summary{min-height:40px;align-content:center;cursor:pointer}.map-provenance p{line-height:1.8;margin:5px 0}:focus-visible{outline:3px solid #ae8148;outline-offset:3px}@media(max-width:600px){.chat-poi-map{height:270px}.map-heading{padding:11px}.map-heading h3{font-size:.77rem}.map-heading>span{font-size:.61rem}.amenity-source{padding-left:0}.amenity-source a{min-height:44px}}
</style>
