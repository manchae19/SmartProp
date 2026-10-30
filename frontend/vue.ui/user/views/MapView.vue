<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../src/services/api.js'
import { usePublicListings, isPublicProperty } from '../../src/services/usePublicListings.js'
import { useListingFilters } from '../../src/services/useListingFilters.js'
import HomeGIS from '../../src/components/HomeGIS.vue'
import ListingFilters from '../../src/components/ListingFilters.vue'
import { LegacyState, LegacyPager } from '../../src/services/legacy.js'
const route = useRoute(), router = useRouter(), search = useListingFilters()
const state = usePublicListings(() => search.filters.value, { endpoint: '/properties/map' })
const selectedId = ref(null), requested = ref(null), selectionError = ref('')
let sequence = 0
const mapItems = computed(() => requested.value && !state.items.some(p => p.id === requested.value.id) ? [...state.items, requested.value] : state.items)
async function loadRequested(id) {
  const run = ++sequence; selectionError.value = ''; requested.value = null; selectedId.value = id ? String(id) : null
  if (!id) { selectedId.value = state.items[0]?.id || null; return }
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(id))) { selectionError.value = 'Mã tin trên bản đồ không hợp lệ.'; return }
  try { const p = await api('/properties/' + encodeURIComponent(id), { authenticated: false }); if (run !== sequence) return; if (!isPublicProperty(p)) throw Error(); requested.value = p }
  catch { if (run === sequence) selectionError.value = 'Không tìm thấy tin công khai đang chọn; không thay bằng vị trí của tin khác.' }
}
watch(() => route.query.propertyId, loadRequested, { immediate: true })
watch(() => state.items, items => { if (!route.query.propertyId && !items.some(p => p.id === selectedId.value)) selectedId.value = items[0]?.id || null })
function select(id) { router.replace({ query: { ...route.query, propertyId: id } }) }
onBeforeUnmount(() => sequence++)
</script>
<template>
  <div class="map-v3"><div class="map-page-width"><div class="map-heading"><p>GIS EXPLORER</p><h1>Bản đồ bất động sản</h1><span>Tin công khai và tiện ích từ Backend. Đồng bộ bộ lọc với trang chủ và danh sách.</span></div><ListingFilters :model-value="search.filters.value" @update:model-value="search.set" /><LegacyState :state="state" /><p v-if="selectionError" role="alert" class="selection-error">{{ selectionError }}</p><p v-if="requested && !state.items.some(p => p.id === requested.id)" class="selection-info">Đang hiển thị thêm tin được mở trực tiếp theo UUID; tin này có thể nằm ngoài bộ lọc hoặc trang hiện tại.</p><HomeGIS :selected-id="selectedId" :items="mapItems" :total="state.totalElements" :busy="state.busy" :error="state.error" @update:selected-id="select" @retry="state.reload" /><LegacyPager :state="state" /></div></div>
</template>
<style scoped>
.map-v3{min-height:100vh;background:#f7f5f0;color:#142b4f}.map-page-width{width:min(1400px,calc(100% - 64px));margin:auto}header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e7e1d7;padding-block:22px;gap:20px}header>div{display:flex;align-items:center;gap:20px;font-size:12px}.brand{font-size:24px;font-weight:700}.brand>span{color:#b3915f}.map-heading{padding-block:32px}.map-heading>p{font-size:13px;letter-spacing:.2em;color:#78572f}.map-heading h1{font-size:36px;font-weight:550;letter-spacing:-.03em;margin:10px 0}.map-heading>span{font-size:13px;line-height:1.8;color:#536178}main>:deep(.listing-filters){margin-bottom:25px}.map-v3 :deep(.gis-map-pane){height:580px}.map-v3 :deep(.gis-list){max-height:580px}.selection-error,.selection-info{font-size:13px;line-height:1.8;padding:16px;border-radius:12px;margin-bottom:20px;background:#fff1e1;color:#894b20}.selection-info{background:#e9eff5;color:#52647c}footer{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;padding-block:35px 150px;font-size:12px;color:#536178}:focus-visible{outline:3px solid #b3915f;outline-offset:3px}@media(max-width:900px){.map-v3 :deep(.gis-map-pane){height:450px}.map-v3 :deep(.gis-list){max-height:340px}}@media(max-width:540px){.map-page-width{width:calc(100% - 32px)}.map-heading h1{font-size:29px}.map-v3 :deep(.gis-map-pane){height:390px}header>div{gap:10px}}
</style>
