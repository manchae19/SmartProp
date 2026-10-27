<script setup>
import { ref, computed, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useComparison } from '../services/useComparison.js'
import { api } from '../services/api.js'
import { isPublicProperty } from '../services/usePublicListings.js'
import { price, compactPrice, types } from '../services/property.js'
const route = useRoute(), compare = useComparison(), dialog = ref(null), busy = ref(false), error = ref('')
const visible = computed(() => ['/home', '/listings', '/map'].includes(route.path))
const mixed = computed(() => new Set(compare.items.value.map(p => `${p.transactionType}:${p.priceUnit}`)).size > 1)
let sequence = 0
async function open() {
  const run = ++sequence; busy.value = true; error.value = ''
  const originals = [...compare.items.value]
  const result = await Promise.allSettled(originals.map(p => api('/properties/' + encodeURIComponent(p.id), { authenticated: false })))
  if (run !== sequence) return
  busy.value = false
  if (compare.items.value.map(p => p.id).join('|') !== originals.map(p => p.id).join('|')) { error.value = 'Lựa chọn đã thay đổi trong lúc kiểm tra. Hãy bấm so sánh lại.'; return }
  if (result.some(r => r.status === 'rejected' && r.reason?.status !== 404)) { error.value = 'Chưa xác minh được trạng thái mới nhất của các tin. Hãy thử lại.'; return }
  const current = result.flatMap(r => r.status === 'fulfilled' && isPublicProperty(r.value) ? [r.value] : [])
  compare.replace(current)
  if (current.length !== originals.length) { error.value = 'Đã bỏ tin không còn công khai. Hãy chọn ít nhất 2 tin hợp lệ.'; return }
  if (current.length < 2) return
  dialog.value.showModal()
}
function close() { dialog.value?.close() }
watch(() => route.fullPath, () => { sequence++; busy.value = false; close() })
onBeforeUnmount(() => { sequence++; close() })
function perSqm(p) {
  if (p.transactionType !== 'SALE' || p.priceUnit !== 'TOTAL' || !(Number(p.areaSqm) > 0)) return '—'
  return Math.round(Number(p.priceExact ?? p.price) / Number(p.areaSqm)).toLocaleString('vi-VN') + ' VND/m²'
}
</script>
<template>
  <aside v-if="visible && compare.items.value.length" class="comparison-tray" aria-label="Các tin đã chọn để so sánh">
    <div class="tray-items"><strong>So sánh {{ compare.items.value.length }}/3</strong><span v-for="item in compare.items.value" :key="item.id" class="tray-chip"><span :title="item.title">{{ item.title }}</span><button type="button" :disabled="busy" :aria-label="'Bỏ so sánh ' + item.title" @click="compare.toggle(item)">×</button></span></div>
    <div class="tray-actions"><button type="button" :disabled="busy" @click="compare.clear">Xóa</button><button type="button" class="primary" :disabled="busy || compare.items.value.length < 2" @click="open">{{ busy ? 'Đang kiểm tra…' : 'So sánh ngay' }}</button></div>
    <p v-if="compare.notice.value || error" role="status">{{ error || compare.notice.value }}</p>
  </aside>
  <dialog ref="dialog" class="comparison-dialog" aria-labelledby="compare-heading" @click="event => { if (event.target === dialog) close() }">
    <div class="dialog-header"><h2 id="compare-heading">So sánh bất động sản</h2><button type="button" aria-label="Đóng so sánh" @click="close">×</button></div>
    <p class="compare-note">Giá chào và thông tin do người đăng cung cấp. Pháp lý chưa được xác nhận bởi bảng so sánh.</p>
    <p v-if="mixed" class="mixed-note">Các tin khác hình thức giao dịch hoặc đơn vị giá. Không so sánh trực tiếp giá bán với giá thuê.</p>
    <div class="table-scroll" tabindex="0" role="region" aria-label="Bảng so sánh, cuộn ngang để xem thêm"><table><thead><tr><th scope="col">Tiêu chí</th><th v-for="p in compare.items.value" :key="p.id" scope="col"><RouterLink :to="'/listing/' + p.id" @click="close">{{ p.title }} ↗</RouterLink></th></tr></thead><tbody>
      <tr><th scope="row">Giá chào</th><td v-for="p in compare.items.value" :key="p.id"><strong>{{ compactPrice(p) }}</strong><small>{{ price(p) }}</small></td></tr>
      <tr><th scope="row">Hình thức / Loại</th><td v-for="p in compare.items.value" :key="p.id">{{ p.transactionType === 'RENT' ? 'Cho thuê' : 'Bán' }} · {{ types[p.propertyType] }}</td></tr>
      <tr><th scope="row">Diện tích</th><td v-for="p in compare.items.value" :key="p.id">{{ p.areaSqm }} m²</td></tr>
      <tr><th scope="row">Giá bán / m²</th><td v-for="p in compare.items.value" :key="p.id">{{ perSqm(p) }}</td></tr>
      <tr><th scope="row">Khu vực</th><td v-for="p in compare.items.value" :key="p.id">{{ [p.district, p.city].filter(Boolean).join(', ') }}</td></tr>
      <tr><th scope="row">Phòng ngủ / Phòng tắm</th><td v-for="p in compare.items.value" :key="p.id">{{ p.bedrooms ?? '—' }} / {{ p.bathrooms ?? '—' }}</td></tr>
      <tr><th scope="row">Pháp lý</th><td v-for="p in compare.items.value" :key="p.id">Xem hồ sơ công khai trong chi tiết tin, nếu có.</td></tr>
    </tbody></table></div>
  </dialog>
</template>
<style scoped>
.comparison-tray{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);z-index:45;width:min(1000px,calc(100% - 28px));border:1px solid #d7c4a2;background:#fffffff7;backdrop-filter:blur(15px);border-radius:18px;padding:14px 18px;box-shadow:0 8px 45px #142b4f33;display:flex;align-items:center;gap:14px;flex-wrap:wrap;color:#142b4f}.tray-items{display:flex;align-items:center;gap:10px;min-width:0;flex:1;flex-wrap:wrap;font-size:12px}.tray-chip{display:flex;align-items:center;background:#f1eee8;border-radius:9px;padding:6px 8px;gap:7px;max-width:190px}.tray-chip>span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.tray-chip button{font-size:20px;padding:0 4px}.tray-actions{display:flex;gap:10px;align-items:center}.tray-actions button{padding:11px 15px;border-radius:24px;font-size:12px}.tray-actions .primary{background:#142b4f;color:white}.comparison-tray p{width:100%;font-size:12px;color:#a23e23}button{cursor:pointer}button:disabled{opacity:.45;cursor:default}.comparison-dialog{width:min(1050px,calc(100vw - 28px));max-height:85dvh;border:0;border-radius:22px;padding:28px;color:#142b4f;background:white;margin:auto;overflow:auto}.comparison-dialog::backdrop{background:#07162bbd;backdrop-filter:blur(4px)}.dialog-header{display:flex;justify-content:space-between;align-items:start;gap:20px}.dialog-header h2{font-size:26px;font-weight:650}.dialog-header button{font-size:28px;min-width:40px;border-radius:50%;background:#f1eee8}.compare-note,.mixed-note{font-size:12px;line-height:1.8;margin:15px 0;color:#637083}.mixed-note{background:#fff3da;padding:12px;border-radius:10px;color:#805c24}.table-scroll{overflow:auto}table{border-collapse:collapse;min-width:620px;width:100%;table-layout:fixed;font-size:13px;line-height:1.7}th,td{text-align:left;vertical-align:top;padding:18px 14px;border-bottom:1px solid #e7e1d7;overflow-wrap:anywhere}thead th{background:#f7f5f0}th:first-child{width:140px}td strong{font-size:18px;color:#b13724}td small{display:block;color:#637083;margin-top:5px}:focus-visible{outline:3px solid #b3915f;outline-offset:2px}@media(max-width:540px){.comparison-tray{bottom:10px;padding:12px}.tray-items{gap:6px}.tray-chip{max-width:110px}.tray-items>strong{width:100%}.tray-actions{width:100%;justify-content:flex-end}.comparison-dialog{padding:18px}}
</style>
