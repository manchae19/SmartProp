<script setup>
import { computed, ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { chatPresentation } from '../services/chatPresentation.js'
import { amenityIntent, loadAmenityMap, amenitySummary } from '../services/chatAmenities.js'
import ChatAmenityMap from './ChatAmenityMap.vue'
import AppIcon from './AppIcon.vue'
const props = defineProps({ result: { type: Object, required: true }, messageId: { type: Number, required: true }, question: { type: String, default: '' } })
const emit = defineEmits(['reading', 'resized'])
const expanded = ref(false)
const view = computed(() => chatPresentation(props.result))
const intent = computed(() => amenityIntent(props.question, props.result))
const mapData = ref(null), mapStatus = ref('idle')
const summary = computed(() => intent.value.requested && mapData.value ? amenitySummary(mapData.value) : view.value.summary)
let disposed = false
async function loadMap() {
  if (!intent.value.enabled || mapStatus.value === 'loading') return
  mapStatus.value = 'loading'
  try { const data = await loadAmenityMap(intent.value); if (!disposed) { mapData.value = data; mapStatus.value = 'ready' } }
  catch { if (!disposed) mapStatus.value = 'error' }
  if (!disposed) { await nextTick(); emit('resized') }
}
onMounted(loadMap)
onBeforeUnmount(() => { disposed = true })
const visibleCards = computed(() => expanded.value ? view.value.cards : view.value.cards.slice(0, 3))
function expand() { emit('reading'); expanded.value = !expanded.value }
function reading(event) { if (event.target.open) emit('reading') }
</script>

<template>
  <div class="chat-answer" data-chat-answer :data-generation-mode="result.generationMode">
    <div class="ai-bubble" :data-chat-empty="!view.cards.length && !view.clarification && result.evidence.criteria?.budgetVnd ? '' : undefined">
      <p class="ai-summary" data-chat-summary>{{ summary }}</p>
      <p v-if="view.clarification" class="clarification-note" role="status" data-chat-clarification>{{ view.clarification }}</p>
      <p v-if="view.fallback" class="fallback-note" role="status" data-chat-fallback>AI chưa sẵn sàng. Kết quả này được tổng hợp trực tiếp từ bằng chứng công khai.</p>
      <p v-if="view.noMatches" class="empty-followup">Hãy nhắc lại ngân sách, loại BĐS và địa bàn trong câu hỏi tiếp theo. <RouterLink to="/advisor">Mở bộ lọc</RouterLink></p>
      <p class="answer-basis">{{ view.clarification ? 'Cần bạn xác nhận trước khi tra cứu' : view.noMatches ? 'Kết quả tra cứu dữ liệu công khai' : 'Tổng hợp từ nguồn công khai · mở Nguồn để đối chiếu' }}</p>
    </div>

    <ChatAmenityMap v-if="intent.enabled || intent.requested" :data="mapData" :status="mapStatus" :message="intent.message" @retry="loadMap" @reading="emit('reading')" />

    <section v-if="view.cards.length" class="chat-properties" :aria-label="'Bất động sản đề xuất trong phản hồi ' + messageId" data-chat-properties>
      <article v-for="(card, index) in visibleCards" :key="card.id" class="chat-property" :data-chat-property="card.id">
        <div class="card-heading"><span class="card-rank">{{ String(index + 1).padStart(2, '0') }}</span><p class="card-location"><AppIcon name="gis" />{{ card.location }}</p></div>
        <h3>{{ card.title }}</h3>
        <div class="card-facts"><p class="card-price" :title="card.price.exact">{{ card.price.text }}</p><span aria-hidden="true">·</span><p>{{ card.area }} m²</p></div>
        <p v-if="card.reason" class="card-reason" :title="card.reason">{{ card.reason }}</p>
        <div class="card-footer"><span class="card-score"><strong>{{ card.score }}</strong>/100 <span>phù hợp</span></span>
          <RouterLink v-if="card.href && card.platform" :to="card.href" class="card-link">Xem chi tiết <AppIcon name="arrow" /></RouterLink>
          <a v-else-if="card.href" :href="card.href" target="_blank" rel="noopener noreferrer" class="card-link">Xem chi tiết <AppIcon name="arrow" /></a>
          <span v-else class="no-link">Chưa có đường dẫn nguồn</span>
        </div>
        <p v-if="card.warnings.length" class="quality-note">Thông tin nguồn cần được đối chiếu trước khi quyết định.</p>
      </article>
      <button v-if="view.cards.length > 3" type="button" class="expand-properties" :aria-expanded="expanded" @click="expand" data-chat-expand>{{ expanded ? 'Thu gọn danh sách' : 'Xem tất cả ' + view.cards.length + ' bất động sản' }}<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true" :class="{ rotated: expanded }"><path d="m6 9 6 6 6-6" /></svg></button>
    </section>

    <details v-if="view.citations.length" class="citation-panel" data-chat-sources @toggle="reading">
      <summary><AppIcon name="report" /><span>Nguồn ({{ view.citations.length }})</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true" class="source-chevron"><path d="m6 9 6 6 6-6" /></svg></summary>
      <ol class="source-list"><li v-for="source in view.citations" :key="source.sourceId">
        <span class="source-number">{{ source.number }}</span><div class="source-body"><a :href="source.href" target="_blank" rel="noopener noreferrer" data-chat-citation>{{ source.label }}</a><p>{{ source.basis }}</p>
          <details class="technical-source" @toggle="reading"><summary>Thông tin đối chiếu</summary><dl><dt>Nguồn</dt><dd>{{ source.sourceId }}</dd><dt>Phiên bản</dt><dd>{{ source.version }}</dd><dt>SHA-256</dt><dd>{{ source.contentHash }}</dd></dl></details>
        </div>
      </li></ol>
      <details class="original-evidence" @toggle="reading"><summary>{{ view.generated ? 'Xem phản hồi Qwen nguyên văn đã kiểm tra' : 'Xem bản tổng hợp nguyên văn' }}</summary><p class="original-answer" data-chat-original>{{ view.originalAnswer }}</p></details>
      <details v-if="result.recommendedProperties.length" class="original-evidence" @toggle="reading"><summary>Chi tiết giá và thông tin nguồn</summary><div v-for="property in result.recommendedProperties" :key="property.id" class="property-audit"><strong>{{ property.title }}</strong><p>{{ view.cards.find(c => c.id === property.id).price.exact }} · Nguồn {{ property.source.name }}</p><p v-for="line in property.explanations" :key="line">{{ line }}</p><p v-for="warning in property.warnings" :key="warning">{{ warning }}</p><code>{{ property.id }}</code></div></details>
      <details class="original-evidence" @toggle="reading"><summary>Giới hạn dữ liệu</summary><ul><li v-for="item in view.limitations" :key="item">{{ item }}</li></ul></details>
    </details>
    <p v-if="view.citations.length" class="answer-caution">Giá rao và điểm phù hợp để tham khảo. Bằng chứng khu vực không chứng minh khoảng cách từ căn nhà.</p>
  </div>
</template>

<style scoped>
.chat-answer{min-width:0;max-width:620px;overflow-wrap:anywhere}.ai-bubble{max-width:560px;background:#edf0f4;border-radius:6px 21px 21px 21px;padding:14px 18px;color:var(--color-brand-navy)}.ai-summary{font-size:.94rem;line-height:1.75}.answer-basis{font-size:.65rem;line-height:1.6;color:var(--color-brand-muted);margin-top:9px}.fallback-note{border-top:1px solid #d8dfe7;margin-top:10px;padding-top:9px;font-size:.78rem;line-height:1.7;color:#74501d}.clarification-note{border-left:3px solid var(--color-brand-accent);margin-top:10px;padding:2px 0 2px 11px;font-size:.86rem;line-height:1.75}.empty-followup{font-size:.8rem;line-height:1.75;color:var(--color-brand-muted);margin-top:8px}.empty-followup a{display:inline-block;min-height:32px;align-content:center;font-weight:650;color:var(--color-brand-accent);text-decoration:underline;text-underline-offset:3px}.chat-properties{display:grid;gap:10px;margin-top:12px;max-width:560px}.chat-property{min-width:0;background:white;border:1px solid #dce2e9;border-radius:17px;padding:14px 16px;box-shadow:0 2px 8px #10233f04}.card-heading{display:flex;align-items:center;gap:8px;margin-bottom:6px}.card-rank{font-size:.62rem;color:var(--color-brand-accent);font-weight:750;letter-spacing:.06em;background:#f4ede1;padding:2px 5px;border-radius:5px}.card-location{display:flex;align-items:center;gap:5px;color:var(--color-brand-muted);font-size:.72rem;line-height:1.5}.card-location svg{width:13px;height:13px;flex-shrink:0}.chat-property h3{font-size:.85rem;font-weight:650;line-height:1.65;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.card-facts{display:flex;align-items:baseline;gap:9px;margin-top:8px;font-size:.8rem;color:var(--color-brand-muted);flex-wrap:wrap}.card-price{font-size:1.15rem;line-height:1.4;font-weight:750;color:var(--color-brand-navy);letter-spacing:-.02em;font-variant-numeric:tabular-nums}.card-reason{font-size:.74rem;line-height:1.7;color:var(--color-brand-muted);margin-top:5px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.card-footer{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:7px}.card-score{font-size:.68rem;color:var(--color-brand-muted);white-space:nowrap}.card-score strong{color:#214e43;font-size:.9rem}.card-score>span{margin-left:3px}.card-link{display:inline-flex;align-items:center;gap:5px;min-height:36px;font-size:.75rem;font-weight:650;color:var(--color-brand-navy)}.card-link svg{width:14px;height:14px}.card-link:hover{text-decoration:underline;text-underline-offset:3px}.quality-note{font-size:.64rem;color:#74501d;line-height:1.6;margin-top:2px}.no-link{font-size:.67rem;color:var(--color-brand-muted)}.expand-properties{display:flex;align-items:center;justify-content:center;gap:7px;border:1px solid #cbd6e3;border-radius:14px;min-height:44px;background:#f7f9fc;color:var(--color-brand-navy);font-size:.78rem;font-weight:650}.expand-properties:hover{background:#eaf0f7}.expand-properties svg{width:17px;height:17px}.rotated{transform:rotate(180deg)}.citation-panel{max-width:560px;margin-top:10px;font-size:.77rem;border:1px solid #e0e5eb;border-radius:14px;background:white;padding:0 12px}.citation-panel>summary{display:flex;align-items:center;gap:7px;min-height:46px;cursor:pointer;color:var(--color-brand-muted);font-weight:600;list-style:none}.citation-panel>summary::-webkit-details-marker{display:none}.citation-panel>summary svg{width:16px;height:16px}.source-chevron{margin-left:auto;width:16px;height:16px}.citation-panel[open]>summary{color:var(--color-brand-navy)}.source-list{list-style:none;padding:0;border-top:1px solid var(--color-brand-line)}.source-list>li{display:flex;gap:9px;padding:11px 0;border-bottom:1px solid #e8edf2}.source-number{display:grid;place-items:center;flex-shrink:0;width:22px;height:22px;background:#edf0f4;color:var(--color-brand-muted);border-radius:7px;font-size:.68rem;margin-top:5px}.source-body{min-width:0}.source-body>a{display:inline-block;align-content:center;min-height:34px;font-weight:650;text-decoration:underline;text-underline-offset:3px}.source-body>p{font-size:.67rem;line-height:1.7;color:var(--color-brand-muted)}.technical-source>summary,.original-evidence>summary{min-height:38px;align-content:center;cursor:pointer;font-size:.7rem;color:var(--color-brand-muted);line-height:1.65}.technical-source dl{font-size:.65rem;line-height:1.8}.technical-source dt{font-weight:700}.technical-source dd{font-family:monospace;margin-bottom:4px}.original-evidence{border-bottom:1px solid #e8edf2;padding:3px 0}.original-evidence:last-child{border-bottom:0}.original-answer{white-space:pre-wrap;font-size:.74rem;line-height:1.9;padding:8px 0;color:var(--color-brand-muted)}.property-audit{padding:10px 0;font-size:.7rem;line-height:1.8;border-top:1px solid var(--color-brand-line)}.property-audit p{margin-top:5px}.original-evidence ul{padding:6px 0 10px 16px;list-style:disc;font-size:.7rem;line-height:1.8;color:var(--color-brand-muted)}.answer-caution{max-width:520px;font-size:.63rem;line-height:1.7;color:var(--color-brand-muted);margin:8px 6px 0}:focus-visible{outline:3px solid var(--color-brand-accent);outline-offset:3px}@media(max-width:600px){.ai-bubble{padding:12px 14px}.ai-summary{font-size:.9rem}.chat-property{padding:12px}.card-facts{gap:7px}.card-price{font-size:1.08rem}.card-link{min-height:44px}.card-score>span{display:none}}
</style>
