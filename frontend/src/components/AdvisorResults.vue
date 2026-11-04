<script setup>
import { computed, nextTick, ref } from 'vue'
import BrowseTileMap from '../features/map/BrowseTileMap.vue'
import AmenityEvidence from './AmenityEvidence.vue'
import { advisorListingUrl, advisorWarning } from '../features/prediction/advisor.js'
const props = defineProps({ result: { type: Object, required: true }, points: { type: Array, default: () => [] }, selectedId: String, mapBusy: Boolean, mapFailures: Number })
const emit = defineEmits(['select', 'area', 'adjust', 'retry-map'])
const cards = new Map(), mapHost = ref(null)
const located = computed(() => new Set(props.points.map(p => p.id)))
const pointById = computed(() => new Map(props.points.map(p => [p.id, p])))
const isResearch = computed(() => props.result.mode === 'INTERNAL_DEMO')
const isV11 = computed(() => props.result.method === 'HEURISTIC_V1_1')
const breakdownLabels = { budgetFit: 'Ngân sách', areaFit: 'Diện tích', propertyTypeFit: 'Loại BĐS', amenityFit: 'Tiện ích khu vực' }
const typeLabel = type => ({ HOUSE:'Nhà ở', APARTMENT:'Căn hộ', LAND:'Đất', VILLA:'Biệt thự/nhà liền kề' }[type] || type)
const money = value => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(value)
const score = value => new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 }).format(value)
const scrollBehavior = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'
async function selectFromMap(id) {
  emit('select', id); await nextTick()
  cards.get(id)?.scrollIntoView({ behavior: scrollBehavior(), block: 'center' })
  cards.get(id)?.focus({ preventScroll: true })
}
async function selectFromCard(id) {
  emit('select', id); await nextTick()
  mapHost.value?.scrollIntoView({ behavior: scrollBehavior(), block: 'center' })
  mapHost.value?.querySelector('[role="region"]')?.focus({ preventScroll: true })
}
</script>
<template>
  <div class="advisor-output">
    <div class="section-heading"><div><p class="eyebrow">TOP KHU VỰC</p><h2>Khu vực phù hợp với nhu cầu</h2></div><p>Tối đa 5 khu vực · {{ result.eligibleCandidateCount }} ứng viên đủ điều kiện</p></div>
    <div v-if="result.topAreas.length" class="area-grid">
      <article v-for="(area, i) in result.topAreas" :key="area.district + ':' + area.ward" class="area-card" data-advisor-area>
        <div class="area-top"><span class="rank">{{ String(i + 1).padStart(2, '0') }}</span><span class="area-score">{{ score(area.score) }}/100</span></div>
        <h3>{{ area.district }}<span v-if="area.ward"> · {{ area.ward }}</span></h3>
        <p>{{ area.candidateCount }} tin đủ điều kiện · Giá rao bình quân <strong>{{ money(area.averageAskingPriceVnd) }}</strong></p>
        <p v-if="area.amenityScore != null" class="area-amenity" data-area-amenity>Tiện ích khu vực <strong>{{ score(area.amenityScore) }}/100</strong><span v-if="area.amenityConfidence != null"> · tin cậy {{ Math.round(area.amenityConfidence * 100) }}%</span><span class="area-amenity-basis">{{ area.amenityEvidenceBasis === 'DIRECT_WARD_EVIDENCE' ? 'cấp phường/xã' : 'cấp quận/huyện' }}</span></p>
        <p v-else-if="isV11" class="area-amenity muted" data-area-amenity-missing>Chưa có hồ sơ tiện ích cho khu vực này.</p>
        <ul v-if="area.poiEvidence?.length" class="area-pois"><li v-for="poi in area.poiEvidence" :key="poi.name + poi.category">{{ poi.name }} <span>{{ poi.category }}</span></li></ul>
        <ul><li v-for="reason in area.explanations" :key="reason">{{ reason }}</li></ul>
        <p class="source">Nguồn: {{ area.sources.join(', ') }}</p>
        <p v-for="warning in area.warnings" :key="warning" class="quality-note">{{ advisorWarning(warning) }}</p>
        <button type="button" class="text-action" @click="emit('area', area)">Tìm trong khu vực này <span aria-hidden="true">→</span></button>
      </article>
    </div>
    <p v-else-if="result.topProperties.length" class="muted">Chưa đủ thông tin để xếp hạng khu vực. Bạn vẫn có thể xem các tin phù hợp bên dưới.</p>
    <div v-if="!result.topProperties.length" class="advisor-empty" role="status" data-advisor-empty>
      <span class="empty-icon" aria-hidden="true">⌕</span><h3>{{ isResearch ? 'Chưa có bản ghi nghiên cứu phù hợp' : 'Chưa có gợi ý công khai phù hợp' }}</h3>
      <p>Có thể chưa có tin khớp bộ lọc hoặc nguồn chưa đủ điều kiện công khai. Thử tăng ngân sách, giảm diện tích tối thiểu hoặc bỏ lọc khu vực.</p>
      <p>Tin chưa xác minh không được đưa vào kết quả để lấp đầy danh sách.</p>
      <button type="button" class="sp-button sp-button-secondary" @click="emit('adjust')">Điều chỉnh bộ lọc</button>
    </div>
    <div class="result-grid">
      <section aria-labelledby="property-title"><div class="section-heading"><div><p class="eyebrow">TOP BẤT ĐỘNG SẢN</p><h2 id="property-title">{{ result.topProperties.length }} tin được đề xuất</h2></div></div>
        <p v-if="!result.topProperties.length" class="muted">Kết quả sẽ xuất hiện tại đây khi có tin phù hợp.</p>
        <article v-for="property in result.topProperties" :key="property.id" :ref="el => el ? cards.set(property.id, el) : cards.delete(property.id)" tabindex="-1" class="property-card" :class="{ selected: selectedId === property.id }" :data-advisor-property="property.id">
          <div class="property-top"><span class="source-badge">{{ property.source.kind === 'TINIX_AI' ? 'Dữ liệu nghiên cứu TiniX AI — chưa xác minh' : property.source.kind === 'PROPERTY' ? 'Tin công khai SmartProp' : 'Nguồn đã xác minh' }}</span><span class="fit-score">{{ score(property.score) }}<small>/100</small></span></div>
          <p v-if="property.source.kind === 'TINIX_AI'" class="source">ID nội bộ: {{ property.source.recordKey }} · {{ typeLabel(property.propertyType) }} · Lịch sử, chưa biết còn bán</p>
          <p class="score-label">Điểm phù hợp theo nhu cầu</p><div class="score-track" role="meter" :aria-label="'Điểm phù hợp: ' + property.title" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="property.score"><span :style="{ width: property.score + '%' }" /></div>
          <ul v-if="isV11 && property.scoreBreakdown" class="breakdown" data-score-breakdown>
            <li v-for="(value, key) in property.scoreBreakdown" :key="key" v-show="breakdownLabels[key]"><span>{{ breakdownLabels[key] }}</span><strong>{{ score(value) }}</strong></li>
          </ul>
          <h3><a v-if="advisorListingUrl(property)" :href="advisorListingUrl(property)" :target="property.source.kind === 'EXTERNAL' ? '_blank' : undefined" rel="noopener noreferrer">{{ property.title }}<span v-if="property.source.kind === 'EXTERNAL'" class="sr-only"> (mở nguồn trong thẻ mới)</span></a><span v-else>{{ property.title }}</span></h3>
          <p class="price">{{ money(property.priceVnd) }} <span>· {{ property.areaSqm.toLocaleString('vi-VN') }} m²</span></p>
          <p class="location">{{ property.district || 'Chưa có địa bàn' }}<span v-if="property.ward"> · {{ property.ward }}</span></p>
          <p v-if="pointById.get(property.id)?.locationLabel" class="source">{{ pointById.get(property.id).locationLabel }}</p>
          <AmenityEvidence v-if="isV11 && property.amenityEvidence" :evidence="property.amenityEvidence" compact />
          <h4>Vì sao phù hợp?</h4><ul><li v-for="reason in property.explanations" :key="reason">{{ reason }}</li></ul>
          <p v-for="warning in property.warnings" :key="warning" class="quality-note">{{ advisorWarning(warning) }}</p>
          <div class="property-footer"><span>Nguồn: <strong>{{ property.source.name }}</strong></span><button v-if="located.has(property.id)" type="button" class="text-action" :aria-pressed="selectedId === property.id" @click="selectFromCard(property.id)">{{ selectedId === property.id ? 'Đang chọn trên bản đồ' : 'Xem trên bản đồ' }}</button><span v-else>{{ mapBusy ? 'Đang tải vị trí…' : 'Chưa có tọa độ công khai' }}</span></div>
        </article>
      </section>
      <aside ref="mapHost" class="gis" aria-labelledby="advisor-map-title">
        <p class="eyebrow">BẢN ĐỒ GIS</p><h2 id="advisor-map-title">Danh sách và vị trí cùng một nơi</h2>
        <p role="status">{{ mapBusy ? 'Đang tải vị trí công khai…' : points.length + '/' + result.topProperties.length + ' tin có tọa độ công khai hợp lệ.' }}</p>
        <div class="advisor-map" :aria-busy="mapBusy"><BrowseTileMap :points="points" :selected-id="selectedId" @select="selectFromMap" /></div>
        <p v-if="mapFailures" class="map-warning" role="status">Chưa tải được một số vị trí. Danh sách gợi ý vẫn dùng được. <button type="button" class="text-action" :disabled="mapBusy" @click="emit('retry-map')">Tải lại vị trí</button></p>
        <p class="map-note">Chọn ghim để tìm thẻ tin tương ứng; chọn “Xem trên bản đồ” để định vị tin. Chỉ đặt ghim từ tọa độ công khai của chính bất động sản; không dùng tâm khu vực thay thế.</p>
      </aside>
    </div>
    <details class="result-notes"><summary>Cách hiểu kết quả và giới hạn dữ liệu</summary><p v-for="warning in result.warnings" :key="warning">{{ advisorWarning(warning) }}</p><p>Điểm phù hợp không phải độ chính xác định giá. Giá hiển thị là tổng giá rao bán; hãy kiểm tra nguồn và tình trạng bất động sản trước khi quyết định.</p></details>
  </div>
</template>
<style scoped>
.breakdown{list-style:none;display:flex;flex-wrap:wrap;gap:.35rem;margin:.1rem 0 .7rem;padding:0}
.breakdown li{display:flex;gap:.3rem;align-items:baseline;background:#f3efe7;border:1px solid #e4ddd0;border-radius:2rem;padding:.15rem .55rem;font-size:.68rem;color:#3d4d63}
.breakdown strong{color:#142b4f;font-variant-numeric:tabular-nums}
.area-amenity{font-size:.78rem;color:#3d4d63}
.area-amenity strong{color:#142b4f}
.area-amenity-basis{display:block;font-size:.7rem;color:#59677a;margin-top:.1rem}
.area-pois{list-style:none!important;display:flex;flex-wrap:wrap;gap:.3rem;padding:0!important;margin-top:.15rem}
.area-pois li{background:#faf8f3;border:1px solid #e4ddd0;border-radius:2rem;padding:.15rem .5rem;font-size:.68rem;color:#3d4d63}
.area-pois li span{font-size:.58rem;color:#85683e;margin-left:.2rem}
h2{font-size:1.35rem;font-weight:650;line-height:1.4}h3{font-size:1.05rem;font-weight:650;line-height:1.55}h4{font-size:.84rem;font-weight:650;margin-top:1rem}.eyebrow{font-size:.68rem;letter-spacing:.15em;color:#85683e;font-weight:700;margin-bottom:.4rem}.section-heading{display:flex;justify-content:space-between;align-items:end;gap:1rem;margin-bottom:1.1rem}.section-heading>p,.muted,.source,.location{font-size:.82rem;line-height:1.7;color:#59677a}.area-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,210px),1fr));gap:1rem;margin-bottom:2rem}.area-card{background:white;border:1px solid #ddd8cf;border-radius:1rem;padding:1.2rem;display:flex;flex-direction:column;gap:.65rem;min-width:0;overflow-wrap:anywhere}.area-top{display:flex;align-items:center;justify-content:space-between}.rank{font-size:1.7rem;font-weight:650;color:#a08252}.area-score{font-size:.85rem;font-weight:650;padding:.25rem .5rem;background:#f2eee5;border-radius:2rem}.area-card p,.area-card li{font-size:.8rem;line-height:1.7}.area-card .text-action{margin-top:auto;text-align:left}.area-card ul,.property-card ul{list-style:disc;padding-left:1.1rem;font-size:.82rem;line-height:1.75;color:#59677a}.text-action{color:#142b4f;font-size:.8rem;font-weight:650;text-decoration:underline;text-underline-offset:3px;cursor:pointer;min-height:44px}.text-action:disabled{opacity:.6;cursor:wait}.advisor-empty{padding:2rem;border:1px dashed #beb3a1;background:#f5f1e8;border-radius:1rem;margin:1.5rem 0 2rem;max-width:100%}.empty-icon{font-size:2rem;color:#957344}.advisor-empty h3{font-size:1.25rem;margin:.35rem 0 .65rem}.advisor-empty p{font-size:.88rem;line-height:1.7;color:#59677a;max-width:760px;margin-bottom:.7rem}.advisor-empty button{margin-top:.4rem}.result-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:1.5rem}.result-grid>section{min-width:0}.property-card{background:white;border:1px solid #ddd8cf;border-radius:1rem;padding:1.3rem;margin-bottom:1rem;scroll-margin-top:110px;overflow-wrap:anywhere}.property-card.selected{outline:3px solid #aa8956;outline-offset:2px}.property-top{display:flex;align-items:center;justify-content:space-between;gap:.8rem}.source-badge{font-size:.7rem;line-height:1.6;padding:.25rem .5rem;background:#e8f0e9;border-radius:2rem;color:#355b40}.fit-score{font-size:1.6rem;font-weight:650;white-space:nowrap}.fit-score small{font-size:.8rem;font-weight:400;color:#59677a}.score-label{font-size:.7rem;color:#59677a;text-align:right;margin:.1rem 0 .35rem}.score-track{height:4px;border-radius:4px;background:#eeeae3;overflow:hidden;margin-bottom:1rem}.score-track span{display:block;height:100%;background:#ac8a56}.property-card h3 a:hover{text-decoration:underline}.price{font-size:1.2rem;font-weight:650;margin:.7rem 0 .3rem}.price span{font-size:.85rem;font-weight:400;color:#59677a}.quality-note{padding:.65rem .8rem;background:#fff6e6;border-left:3px solid #b68a4c;color:#74521e;font-size:.78rem;line-height:1.7;margin-top:.65rem}.property-footer{display:flex;justify-content:space-between;align-items:center;gap:.75rem;flex-wrap:wrap;border-top:1px solid #e7e2d8;padding-top:.6rem;margin-top:1rem;font-size:.76rem;color:#59677a}.gis{position:sticky;top:100px;align-self:start;min-width:0;scroll-margin-top:110px}.gis>p:not(.eyebrow){font-size:.8rem;line-height:1.7;color:#59677a;margin:.7rem 0}.advisor-map{position:relative;height:430px;border:1px solid #ddd8cf;border-radius:1rem;overflow:hidden}.map-warning{padding:.7rem;background:#fff6e6;border-radius:.7rem}.result-notes{padding:1.1rem 1.2rem;border:1px solid #e1dacd;background:#f3efe7;border-radius:.9rem;font-size:.82rem;margin-top:2rem}.result-notes summary{font-weight:650;cursor:pointer}.result-notes p{margin-top:.75rem;line-height:1.8;color:#59677a}:focus-visible{outline:3px solid #a88c5e;outline-offset:3px}@media(max-width:1000px){.result-grid{grid-template-columns:1fr}.gis{position:static}.advisor-map{height:380px}}@media(max-width:560px){.section-heading{align-items:start;flex-direction:column;gap:.5rem}.advisor-empty{padding:1.2rem}.property-card{padding:1rem}.advisor-map{height:330px}.area-grid{grid-template-columns:1fr}.advisor-empty button{width:100%}.gis h2{font-size:1.2rem}}
</style>
