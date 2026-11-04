<script setup>
import { computed } from 'vue'
const props = defineProps({
  evidence: { type: Object, default: null },
  compact: { type: Boolean, default: false },
  area: { type: Boolean, default: false },
})
const num = value => Number.isFinite(value) ? new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 }).format(value) : null
const categories = computed(() => {
  const scores = props.evidence?.categoryScores
  if (!scores) return []
  return [
    { key: 'essentials', icon: '🛒', label: 'Chợ & siêu thị', score: scores.essentials },
    { key: 'education', icon: '🎓', label: 'Trường học', score: scores.education },
    { key: 'healthcare', icon: '🏥', label: 'Y tế', score: scores.healthcare },
    { key: 'transit', icon: '🚌', label: 'Giao thông công cộng', score: scores.transit },
    { key: 'recreation', icon: '🌳', label: 'Công viên & biển', score: scores.recreation },
  ].filter(c => Number.isFinite(c.score))
})
const basisLabel = computed(() => ({
  DIRECT_WARD_EVIDENCE: 'Theo đúng phường/xã của bất động sản',
  DISTRICT_SHARED_AMENITY: 'Theo quận/huyện (tiện ích dùng chung)',
  NO_AREA_MATCH: 'Chưa xác định được địa bàn',
}[props.evidence?.evidenceBasis] || 'Chưa xác định'))
const hasProfile = computed(() => props.evidence != null && props.evidence.areaAmenityScore != null)
const visibleEvidence = computed(() => (props.evidence?.poiEvidence || []).slice(0, props.compact ? 4 : 8))
</script>
<template>
  <section class="amenity-evidence" :class="{ compact, 'area-mode': area }" data-amenity-evidence>
    <header class="ae-head">
      <div>
        <p class="ae-eyebrow">{{ area ? 'TIỆN ÍCH KHU VỰC' : 'TIỆN ÍCH KHU VỰC SINH SỐNG' }}</p>
        <h4 v-if="hasProfile">{{ num(evidence.areaAmenityScore) }}<small>/100</small> <span class="ae-name">{{ evidence.areaName }}</span></h4>
        <h4 v-else class="ae-na">Chưa có điểm tiện ích</h4>
      </div>
      <span v-if="hasProfile && Number.isFinite(evidence.confidence)" class="ae-confidence" :title="basisLabel">Tin cậy {{ Math.round(evidence.confidence * 100) }}%</span>
    </header>
    <p class="ae-basis">{{ basisLabel }} · {{ evidence.areaLevel === 'WARD' ? 'cấp phường/xã' : evidence.areaLevel === 'DISTRICT' ? 'cấp quận/huyện' : 'không xác định' }}</p>
    <ul v-if="categories.length" class="ae-bars">
      <li v-for="c in categories" :key="c.key">
        <span class="ae-label"><span aria-hidden="true">{{ c.icon }}</span> {{ c.label }}</span>
        <span class="ae-track" role="meter" :aria-label="c.label" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="c.score"><span :style="{ width: c.score + '%' }" /></span>
        <span class="ae-value">{{ num(c.score) }}</span>
      </li>
    </ul>
    <div v-if="visibleEvidence.length" class="ae-pois">
      <p class="ae-pois-title">Tiện ích đã số hóa trong khu vực</p>
      <ul><li v-for="poi in visibleEvidence" :key="poi.name + poi.category"><span class="ae-poi-name">{{ poi.name }}</span><span class="ae-poi-cat">{{ poi.category }}</span></li></ul>
    </div>
    <p v-else-if="hasProfile" class="ae-note">Hồ sơ khu vực không kèm tên tiện ích cụ thể.</p>
    <p v-for="limitation in (evidence?.dataLimitations || []).slice(0, compact ? 1 : 3)" :key="limitation" class="ae-note">{{ limitation }}</p>
    <p v-if="hasProfile" class="ae-note ae-note-strong">{{ evidence.note }}</p>
  </section>
</template>
<style scoped>
.amenity-evidence{border:1px solid #e2dccf;background:#faf8f3;border-radius:.85rem;padding:1rem;margin-top:.9rem;min-width:0}
.amenity-evidence.compact{padding:.8rem;margin-top:.75rem}
.ae-head{display:flex;align-items:start;justify-content:space-between;gap:.75rem}
.ae-eyebrow{font-size:.62rem;letter-spacing:.13em;font-weight:700;color:#85683e;margin-bottom:.3rem}
.ae-head h4{font-size:1.15rem;font-weight:650;line-height:1.35;color:#142b4f}
.ae-head h4 small{font-size:.72rem;font-weight:400;color:#59677a}
.ae-head h4.ae-na{font-size:.9rem;color:#74521e}
.ae-name{display:block;font-size:.78rem;font-weight:500;color:#59677a;margin-top:.15rem}
.ae-confidence{flex-shrink:0;font-size:.7rem;font-weight:650;padding:.22rem .5rem;background:#e8f0e9;color:#355b40;border-radius:2rem;white-space:nowrap}
.ae-basis{font-size:.72rem;color:#59677a;line-height:1.6;margin-top:.35rem}
.ae-bars{list-style:none;display:flex;flex-direction:column;gap:.4rem;margin-top:.7rem;padding:0}
.ae-bars li{display:grid;grid-template-columns:9.5rem minmax(0,1fr) 2.2rem;align-items:center;gap:.5rem;font-size:.74rem;color:#3d4d63}
.ae-label{display:flex;gap:.35rem;align-items:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ae-track{height:6px;border-radius:6px;background:#e9e4da;overflow:hidden}
.ae-track>span{display:block;height:100%;background:linear-gradient(90deg,#b68a4c,#6d8f74);border-radius:6px}
.ae-value{font-variant-numeric:tabular-nums;text-align:right;font-weight:650;color:#142b4f}
.ae-pois{margin-top:.75rem}
.ae-pois-title{font-size:.7rem;font-weight:650;color:#3d4d63;margin-bottom:.35rem}
.ae-pois ul{list-style:none;display:flex;flex-wrap:wrap;gap:.35rem;padding:0}
.ae-pois li{display:flex;align-items:center;gap:.3rem;background:white;border:1px solid #e5dfd3;border-radius:2rem;padding:.2rem .55rem;font-size:.7rem;color:#3d4d63}
.ae-poi-name{overflow-wrap:anywhere}
.ae-poi-cat{font-size:.58rem;letter-spacing:.04em;color:#85683e;border-left:1px solid #e5dfd3;padding-left:.35rem}
.ae-note{font-size:.7rem;line-height:1.65;color:#59677a;margin-top:.5rem}
.ae-note-strong{color:#74521e}
@media(max-width:420px){.ae-bars li{grid-template-columns:7.5rem minmax(0,1fr) 2rem;font-size:.7rem}}
</style>