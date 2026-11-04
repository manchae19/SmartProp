<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { api, session } from '../../src/services/api.js'
import { createResearchAdvisorClient } from '../../src/services/tinixAdvisor.js'
import { advisorRequest, parseAdvisorBudget, formatAdvisorBudget, createAdvisorClient, advisorMapData, advisorError } from '../../src/services/advisor.js'
import { districts } from '../../src/services/districts.js'
import AdvisorResults from '../../src/components/AdvisorResults.vue'
const defaults = () => ({ budgetVnd: '2.000.000.000', purpose: 'LIVING', propertyType: 'ALL', minAreaSqm: '', district: '', ward: '', limit: 10 })
const form = reactive(defaults())
const busy = ref(false), mapBusy = ref(false), error = ref(''), result = ref(null), points = ref([]), selected = ref(''), mapFailures = ref(0)
const submitted = ref(null), resultsHeading = ref(null), budgetInput = ref(null)
const recommend = createAdvisorClient(api)
const researchRecommend = createResearchAdvisorClient(api)
const research = ref(false), researchAvailable = ref(false)
let sequence = 0, mapSequence = 0
watch(() => [session.user?.role, session.status], async ([role, status]) => {
  researchAvailable.value = false; research.value = false; reset()
  if (role === 'ADMIN' && status === 'AUTHENTICATED') {
    try { const config = await api('/recommendations/research/config'); researchAvailable.value = session.user?.role === 'ADMIN' && config.enabled === true } catch { /* Public Advisor remains available. */ }
  }
}, { immediate: true })
function setResearch(value) { if (value && !researchAvailable.value) return; reset(); research.value = value }
const money = value => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(value)
const budgetHint = computed(() => { try { return formatAdvisorBudget(form.budgetVnd) + ' VNĐ' } catch { return 'Nhập tổng số tiền VNĐ, ví dụ 2.350.000.000' } })
const districtSuggestions = computed(() => [...new Set([...districts.filter(d => d !== 'Tất cả'), ...(result.value?.topAreas || []).map(a => a.district)])])
const changed = computed(() => { if (!result.value) return false; try { return JSON.stringify(advisorRequest(form)) !== JSON.stringify(submitted.value) } catch { return true } })
const submittedSummary = computed(() => submitted.value ? [money(submitted.value.budgetVnd), { LIVING: 'Mua để ở', INVESTMENT: 'Đầu tư', RENTAL: 'Mua để cho thuê' }[submitted.value.purpose], submitted.value.district || 'Tất cả khu vực', submitted.value.ward, submitted.value.minAreaSqm ? 'Từ ' + submitted.value.minAreaSqm + ' m²' : ''].filter(Boolean).join(' · ') : '')
function formatBudget() { try { form.budgetVnd = formatAdvisorBudget(form.budgetVnd) } catch { /* Keep invalid text for an explicit validation error. */ } }
function budgetEquals(value) { try { return parseAdvisorBudget(form.budgetVnd) === value } catch { return false } }
async function loadMap() {
  if (!result.value) return
  const current = sequence, mapCurrent = ++mapSequence, properties = result.value.topProperties
  mapBusy.value = true; mapFailures.value = 0
  try {
    const mapped = await advisorMapData(properties, path => api(path, { authenticated: false }))
    if (current === sequence && mapCurrent === mapSequence) { points.value = mapped.points; mapFailures.value = mapped.failedCount }
  } finally { if (current === sequence && mapCurrent === mapSequence) mapBusy.value = false }
}
async function submit() {
  const current = ++sequence
  mapSequence++; busy.value = true; mapBusy.value = false; error.value = ''; result.value = null; points.value = []; selected.value = ''; mapFailures.value = 0
  const input = { ...form }
  try {
    const request = advisorRequest(input), response = await (research.value ? researchRecommend : recommend)(input)
    if (current !== sequence) return
    submitted.value = request; result.value = response
    await nextTick(); resultsHeading.value?.focus({ preventScroll: true })
    void loadMap()
  } catch (failure) { if (current === sequence) error.value = research.value && [401, 403].includes(failure.status) ? 'Cần phiên ADMIN hợp lệ và máy chủ demo nội bộ được bật. Không thể mở dữ liệu nghiên cứu bằng liên kết hoặc tham số URL.' : advisorError(failure) }
  finally { if (current === sequence) busy.value = false }
}
function reset() {
  sequence++; mapSequence++; Object.assign(form, defaults())
  busy.value = false; mapBusy.value = false; error.value = ''; result.value = null; submitted.value = null; points.value = []; selected.value = ''; mapFailures.value = 0
  nextTick(() => budgetInput.value?.focus())
}
function adjust() { document.getElementById('advisor-form')?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' }); budgetInput.value?.focus({ preventScroll: true }) }
function areaSelected(area) { form.district = area.district; form.ward = area.ward || ''; submit() }
onBeforeUnmount(() => { sequence++; mapSequence++ })
</script>
<template>
  <section class="sp-container advisor-page" aria-labelledby="advisor-title">
    <div class="advisor-intro"><p class="eyebrow">SMARTPROP · TƯ VẤN BĐS</p><h1 id="advisor-title">Tìm không gian phù hợp với bạn</h1><p>Chọn theo ngân sách và mục đích. So sánh khu vực, xem lý do đề xuất và đối chiếu vị trí trên bản đồ.</p></div>
    <p class="mb-5"><RouterLink to="/advisor/chat" class="sp-button sp-button-secondary" data-chat-entry>Trao đổi với AI Advisor ↗</RouterLink></p>
    <div class="safe-note" :class="{ 'research-note': research }"><span aria-hidden="true">{{ research ? '!' : '✓' }}</span><div><strong>{{ research ? 'Internal Demo — chỉ ADMIN' : 'Chế độ an toàn' }}</strong><p>{{ research ? 'Dữ liệu nghiên cứu TiniX AI — chưa xác minh. Lịch sử, chưa biết còn bán; chỉ nghiên cứu phi thương mại (CC BY-NC 4.0).' : 'Chỉ hiển thị tin đủ điều kiện công khai. Không cần đăng nhập để tìm gợi ý.' }}</p></div></div>
    <div v-if="researchAvailable" class="research-controls"><button type="button" class="sp-button sp-button-secondary" :aria-pressed="research" @click="setResearch(!research)">{{ research ? 'Quay lại chế độ an toàn' : 'Mở Internal Demo TiniX AI' }}</button><p>Không thay đổi danh sách công khai. Quyền truy cập được kiểm tra tại Backend.</p></div>
    <form id="advisor-form" class="advisor-form" :aria-busy="busy" @submit.prevent="submit">
      <div class="form-heading"><div><h2>Nhu cầu của bạn</h2><p>Nhập tổng ngân sách mua bất động sản bằng VNĐ. Bạn có thể nhập số tiền bất kỳ.</p></div><span class="required-note">* Thông tin bắt buộc</span></div>
      <fieldset :disabled="busy"><legend class="sr-only">Bộ lọc gợi ý bất động sản</legend>
        <div class="form-grid">
          <label class="budget-field">Ngân sách tối đa (VNĐ) *<input ref="budgetInput" v-model="form.budgetVnd" @blur="formatBudget" name="budget" type="text" inputmode="numeric" maxlength="32" required aria-describedby="budget-hint" autocomplete="off" /><small id="budget-hint">{{ budgetHint }}</small><span class="budget-presets"><button v-for="value in [1, 2, 3, 5, 10]" :key="value" type="button" :aria-pressed="budgetEquals(value * 1000000000)" @click="form.budgetVnd = formatAdvisorBudget(String(value * 1000000000))">{{ value }} tỷ</button></span></label>
          <label>Mục đích *<select v-model="form.purpose" name="purpose"><option value="LIVING">Mua để ở</option><option value="INVESTMENT">Đầu tư</option><option value="RENTAL">Mua để cho thuê</option></select><small>{{ form.purpose === 'RENTAL' ? 'Ngân sách mua nhà, không phải tiền thuê hàng tháng.' : form.purpose === 'INVESTMENT' ? 'Điểm tham khảo, không dự báo lợi nhuận đầu tư.' : 'Ưu tiên mức phù hợp với nhu cầu đã nhập.' }}</small></label>
          <label>Loại bất động sản *<select v-model="form.propertyType" name="propertyType"><option value="ALL">Tất cả loại</option><option value="HOUSE">Nhà ở</option><option value="APARTMENT">Căn hộ</option><option value="LAND">Đất nền</option><option value="VILLA">Biệt thự</option><option value="ROOM">Phòng</option><option value="COMMERCIAL">Bất động sản thương mại</option></select></label>
          <label>Diện tích tối thiểu (m²)<input v-model="form.minAreaSqm" name="minAreaSqm" type="number" min="0.1" max="1000000" step="any" placeholder="Không giới hạn" /><small>Để trống nếu chưa có yêu cầu.</small></label>
          <label>Địa bàn<input v-model="form.district" name="district" list="advisor-districts" maxlength="100" placeholder="Tất cả khu vực" autocomplete="off" /><small>Chọn gợi ý hoặc nhập địa bàn theo nguồn tin.</small></label>
          <label>Phường/xã<input v-model="form.ward" name="ward" maxlength="100" placeholder="Không bắt buộc" /><small>Nguồn chưa có phường/xã sẽ không khớp bộ lọc này.</small></label>
          <label>Số gợi ý<select v-model.number="form.limit" name="limit"><option :value="10">Tối đa 10 tin</option><option :value="5">Tối đa 5 tin</option></select></label>
        </div>
        <datalist id="advisor-districts"><option v-for="district in districtSuggestions" :key="district" :value="district" /></datalist>
        <div class="form-footer"><p>Điểm phù hợp được tính theo quy tắc tham khảo; không thay thế kiểm tra pháp lý, hiện trạng hoặc định giá độc lập.</p><div class="form-actions"><button class="sp-button sp-button-secondary" type="button" @click="reset">Đặt lại</button><button class="sp-button sp-button-primary" type="submit">{{ busy ? 'Đang tìm gợi ý…' : 'Tìm gợi ý phù hợp' }}</button></div></div>
      </fieldset>
    </form>
    <div v-if="error" role="alert" class="advisor-error"><div><strong>Chưa thể tải gợi ý</strong><p>{{ error }}</p></div><button type="button" class="sp-button sp-button-secondary" @click="submit">Thử lại</button></div>
    <div v-if="busy" role="status" class="loading-panel"><span class="loading-spinner" aria-hidden="true"/><div><strong>Đang tìm gợi ý phù hợp…</strong><p>Đối chiếu ngân sách, khu vực và điều kiện công khai.</p></div></div>
    <template v-if="result">
      <div class="submitted-heading"><h2 ref="resultsHeading" tabindex="-1">Kết quả tư vấn</h2><p>{{ submittedSummary }}</p></div>
      <div v-if="changed" role="status" class="changed-note">Bạn đã thay đổi bộ lọc. Kết quả bên dưới vẫn theo nhu cầu đã gửi; bấm “Tìm gợi ý phù hợp” để cập nhật.</div>
      <AdvisorResults :result="result" :points="points" :selected-id="selected" :map-busy="mapBusy" :map-failures="mapFailures" @select="selected = $event" @area="areaSelected" @adjust="adjust" @retry-map="loadMap" />
    </template>
    <div v-else-if="!busy && !error" class="start-note"><strong>Bắt đầu từ nhu cầu, kiểm tra bằng dữ liệu</strong><p>Sau khi tìm, bạn có thể xem tối đa 5 khu vực và 10 bất động sản cùng điểm phù hợp, lý do và nguồn. Số kết quả phụ thuộc dữ liệu đủ điều kiện; hệ thống không thêm tin chưa xác minh.</p></div>
  </section>
</template>
<style scoped>
.research-note{background:#fff6e6;border-color:#d9b779;color:#74521e}.research-controls{margin-bottom:1.2rem}.research-controls p{font-size:.78rem;line-height:1.7;color:#59677a;margin-top:.5rem}
.advisor-page{padding-top:2.5rem;padding-bottom:4rem;color:#142b4f}.advisor-intro{max-width:790px;margin-bottom:1.4rem}.eyebrow{font-size:.72rem;letter-spacing:.18em;color:#85683e;font-weight:700;margin-bottom:.65rem}h1{font-size:clamp(1.85rem,4vw,2.9rem);font-weight:650;line-height:1.2;letter-spacing:-.025em;margin-bottom:1rem}.advisor-intro>p:last-child{font-size:.95rem;line-height:1.8;color:#59677a}.safe-note{display:flex;align-items:center;gap:.85rem;background:#eaf0e9;border:1px solid #d4e0d3;border-radius:.9rem;padding:.9rem 1.1rem;margin-bottom:1.2rem;color:#355b40}.safe-note>span{width:28px;height:28px;display:grid;place-items:center;border:1px solid #a2baa4;border-radius:50%}.safe-note strong{font-size:.85rem}.safe-note p{font-size:.8rem;line-height:1.65;margin-top:.1rem}.advisor-form{background:white;border:1px solid #ddd8cf;border-radius:1.2rem;padding:1.5rem;scroll-margin-top:110px}.form-heading{display:flex;justify-content:space-between;align-items:start;gap:1rem;margin-bottom:1.2rem}.form-heading h2,.submitted-heading h2{font-size:1.35rem;font-weight:650}.form-heading p,.required-note{font-size:.78rem;line-height:1.65;color:#59677a;margin-top:.35rem}.required-note{white-space:nowrap}fieldset{min-width:0}fieldset:disabled{opacity:.7}.form-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1.1rem}.form-grid label{display:flex;flex-direction:column;gap:.5rem;min-width:0;font-size:.82rem;font-weight:600}.form-grid input,.form-grid select{width:100%;min-width:0;min-height:46px;padding:.7rem .8rem;border:1px solid #cdd3dc;border-radius:.6rem;background:white;color:#142b4f;font:inherit}.form-grid small{font-size:.72rem;font-weight:400;color:#59677a;line-height:1.65}.budget-presets{display:flex;flex-wrap:wrap;gap:.4rem}.budget-presets button{padding:.3rem .7rem;min-height:36px;border:1px solid #ded8cc;border-radius:2rem;font-size:.73rem;cursor:pointer}.budget-presets button[aria-pressed=true]{background:#142b4f;color:white;border-color:#142b4f}.form-footer{display:flex;justify-content:space-between;align-items:center;gap:1.5rem;border-top:1px solid #ebe6dd;padding-top:1.1rem;margin-top:1.3rem}.form-footer>p{font-size:.78rem;line-height:1.7;color:#59677a;max-width:560px}.form-actions{display:flex;gap:.65rem;flex-shrink:0}.form-actions button{cursor:pointer;white-space:nowrap}.advisor-error{display:flex;align-items:center;justify-content:space-between;gap:1rem;background:#fff0ed;border:1px solid #edc4bc;padding:1.1rem;border-radius:.9rem;margin-top:1.3rem;color:#8b3021}.advisor-error strong{font-size:.9rem}.advisor-error p{font-size:.82rem;line-height:1.65;margin-top:.3rem}.loading-panel{display:flex;align-items:center;gap:1rem;background:#fff;border:1px solid #ddd8cf;border-radius:1rem;padding:1.5rem;margin-top:1.5rem}.loading-panel strong{font-size:.9rem}.loading-panel p{font-size:.8rem;color:#59677a;margin-top:.35rem}.loading-spinner{width:24px;height:24px;flex-shrink:0;border:3px solid #e6dfd3;border-top-color:#967242;border-radius:50%;animation:spin 1s linear infinite}.submitted-heading{margin-top:2.3rem;margin-bottom:1.5rem}.submitted-heading p{font-size:.85rem;line-height:1.7;color:#59677a;margin-top:.5rem}.submitted-heading h2:focus{outline:none}.changed-note{padding:.9rem 1rem;border:1px solid #e2cfab;background:#fbf5e9;border-radius:.8rem;font-size:.8rem;line-height:1.75;margin-bottom:1.3rem}.start-note{padding:1.5rem;background:#f0ece4;border-radius:1rem;margin-top:1.5rem}.start-note strong{font-size:.9rem}.start-note p{font-size:.84rem;line-height:1.8;color:#59677a;margin-top:.6rem;max-width:780px}:focus-visible{outline:3px solid #a88c5e;outline-offset:3px}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:1100px){.form-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.form-footer{align-items:start;flex-direction:column;gap:1rem}.form-actions{align-self:flex-end}}@media(max-width:560px){.advisor-page{padding-top:1.5rem}.advisor-form{padding:1rem}.form-heading{flex-direction:column;gap:.25rem}.form-grid{grid-template-columns:1fr}.form-actions{align-self:stretch;flex-wrap:wrap}.form-actions button{flex:1;min-width:100px}.advisor-error{align-items:stretch;flex-direction:column}.safe-note{align-items:start}.safe-note>span{flex-shrink:0}.start-note{padding:1.1rem}.submitted-heading{margin-top:1.8rem}}@media(prefers-reduced-motion:reduce){.loading-spinner{animation:none}}
</style>
