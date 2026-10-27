<script setup>
import { ref, watch, nextTick, useId } from 'vue'
import { districts } from '../services/districts.js'
import { propertyTypes, normalizeFilters, filterError, sortOptions } from '../services/listingFilters.js'
const props = defineProps({ modelValue: { type: Object, required: true } })
const emit = defineEmits(['update:modelValue', 'search'])
const draft = ref({}), expanded = ref(false), error = ref(''), errorNode = ref(null), panelId = useId()
watch(() => props.modelValue, value => { draft.value = { ...value }; error.value = '' }, { immediate: true, deep: true })
async function apply() {
  error.value = filterError(draft.value)
  if (error.value) { expanded.value = true; await nextTick(); errorNode.value?.focus(); return }
  emit('update:modelValue', normalizeFilters(draft.value)); emit('search')
}
function transaction(value) { draft.value.transactionType = value; apply() }
function reset() { draft.value = {}; apply() }
defineExpose({ expand: () => { expanded.value = true } })
</script>
<template>
  <form class="listing-filters rounded-panel border border-brand-line bg-white p-4 shadow-sm sm:p-6" aria-label="Tìm kiếm bất động sản" @submit.prevent="apply">
    <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
      <div class="filter-tabs inline-flex flex-wrap gap-1 rounded-full bg-brand-surface p-1" role="group" aria-label="Hình thức giao dịch"><button v-for="(label, key) in { '': 'Tất cả', SALE: 'Bán', RENT: 'Cho thuê' }" :key="key" type="button" :aria-pressed="(draft.transactionType || '') === key" class="min-h-11 rounded-full px-4 py-2 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-gold sm:px-6" :class="(draft.transactionType || '') === key ? 'bg-brand-navy text-white shadow-sm' : 'text-brand-muted hover:bg-white'" @click="transaction(key)">{{ label }}</button><slot name="tabs" /></div>
      <button type="button" class="advanced-toggle sp-button sp-button-secondary" :aria-expanded="expanded" :aria-controls="panelId" @click="expanded = !expanded">{{ expanded ? 'Thu gọn bộ lọc' : 'Bộ lọc nâng cao' }}<svg class="size-4 transition-transform motion-reduce:transition-none" :class="{ 'rotate-180': expanded }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg></button>
    </div>
    <div class="quick-fields grid items-end gap-3 min-[360px]:grid-cols-2 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
      <label class="keyword sp-field min-[360px]:col-span-2 lg:col-span-1">Từ khóa<input v-model="draft.keyword" name="keyword" class="sp-input" maxlength="200" placeholder="Tên tin, địa chỉ, khu vực…" type="search" /></label>
      <label class="sp-field">Khu vực<select v-model="draft.district" name="district" class="sp-input"><option :value="undefined">Tất cả khu vực</option><option v-for="district in districts.filter(d => d !== 'Tất cả')" :key="district">{{ district }}</option></select></label>
      <label class="sp-field">Loại bất động sản<select v-model="draft.propertyType" name="propertyType" class="sp-input"><option :value="undefined">Tất cả loại hình</option><option v-for="(label, key) in propertyTypes" :key="key" :value="key">{{ label }}</option></select></label>
      <button class="search-button sp-button sp-button-primary min-[360px]:col-span-2 lg:col-span-1" type="submit"><svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></svg>Tìm kiếm</button>
    </div>
    <div v-show="expanded" :id="panelId" class="advanced-fields mt-6 grid gap-4 border-t border-brand-line pt-5 sm:grid-cols-2 lg:grid-cols-3">
      <p class="filter-help text-xs leading-6 text-brand-muted sm:col-span-2 lg:col-span-3">Giá nhập bằng VND, theo đơn vị giá niêm yết của từng tin: tổng giá / tháng / năm / ngày. Bộ lọc áp dụng trên toàn bộ danh sách.</p>
      <label class="sp-field">Giá tối thiểu (VND)<input v-model="draft.minPrice" name="minPrice" class="sp-input" type="text" inputmode="decimal" placeholder="Ví dụ: 2000000000" /></label>
      <label class="sp-field">Giá tối đa (VND)<input v-model="draft.maxPrice" name="maxPrice" class="sp-input" type="text" inputmode="decimal" placeholder="Không giới hạn" /></label>
      <label class="sp-field">Diện tích tối thiểu (m²)<input v-model="draft.minArea" name="minArea" class="sp-input" type="number" min="0" step="0.01" /></label>
      <label class="sp-field">Diện tích tối đa (m²)<input v-model="draft.maxArea" name="maxArea" class="sp-input" type="number" min="0" step="0.01" /></label>
      <label class="sp-field">Phòng ngủ tối thiểu<select v-model="draft.bedrooms" name="bedrooms" class="sp-input"><option :value="undefined">Không giới hạn</option><option v-for="n in 5" :key="n" :value="String(n)">{{ n }}+</option></select></label>
      <label class="sp-field">Sắp xếp<select v-model="draft.sort" name="sort" class="sp-input"><option v-for="(label, key) in sortOptions" :key="key" :value="key">{{ label }}</option></select></label>
      <label v-if="draft.city" class="sp-field">Thành phố<input v-model="draft.city" class="sp-input" name="city" maxlength="100" /></label>
      <label v-if="draft.ward" class="sp-field">Phường / xã<input v-model="draft.ward" class="sp-input" name="ward" maxlength="100" /></label>
      <div class="advanced-actions flex flex-wrap justify-end gap-3 sm:col-span-2 lg:col-span-3"><button type="submit" class="sp-button sp-button-primary">Áp dụng bộ lọc</button></div>
    </div>
    <div class="mt-4 flex flex-wrap items-center justify-between gap-3"><p class="text-[11px] leading-6 text-brand-muted">Có thể kết hợp hình thức, khu vực và loại hình.</p><button type="button" class="reset-filters min-h-11 rounded-control px-2 text-xs font-semibold text-brand-accent underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-brand-gold" @click="reset">Xóa bộ lọc</button></div>
    <p v-if="error" ref="errorNode" role="alert" tabindex="-1" class="filter-error mt-4 rounded-control bg-red-50 p-4 text-sm leading-6 text-red-800 focus-visible:outline-2 focus-visible:outline-red-700">{{ error }}</p>
  </form>
</template>
