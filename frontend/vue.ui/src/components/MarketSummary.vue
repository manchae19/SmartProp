<script setup>
import { ref, watch } from 'vue'
import { api } from '../services/api.js'
import { types } from '../services/property.js'

const props = defineProps({ district: String })
const summary = ref(null)
const busy = ref(false)
const error = ref('')
const type = ref('')
let sequence = 0

async function load() {
  const run = ++sequence
  busy.value = true
  error.value = ''
  summary.value = null
  try {
    const query = new URLSearchParams({ transactionType: 'SALE', priceUnit: 'TOTAL' })
    if (props.district) query.set('district', props.district)
    if (type.value) query.set('propertyType', type.value)
    const result = await api('/properties/market-summary?' + query, { authenticated: false })
    if (run === sequence) summary.value = result
  } catch {
    if (run === sequence) error.value = 'Chưa tải được giá chào hiện tại. Vui lòng thử lại.'
  } finally {
    if (run === sequence) busy.value = false
  }
}

watch(() => [props.district, type.value], load, { immediate: true })
const price = value => value == null ? '—' : Number(value).toLocaleString('vi-VN', { maximumFractionDigits: 0 })
</script>

<template>
  <section id="market-current" aria-labelledby="market-current-heading" class="bg-[#F1EEE8] pb-14 text-[#142B4F] md:pb-20">
    <div class="mx-auto max-w-7xl px-5 lg:px-8">
      <div class="rounded-3xl border border-[#E7E1D7] bg-white p-5 md:p-7" :aria-busy="busy">
        <div class="flex flex-wrap items-start justify-between gap-5">
          <div class="max-w-2xl">
            <p class="text-xs font-bold uppercase tracking-[0.2em] text-[#8B683A]">Dữ liệu từ SmartProp</p>
            <h2 id="market-current-heading" class="mt-2 text-xl font-semibold md:text-2xl">Giá chào hiện tại trên SmartProp</h2>
            <p class="mt-2 text-sm leading-6 text-[#536178]">
              Tin bán được duyệt còn hiệu lực<span v-if="district"> tại {{ district }}</span> · VND / tổng giá.
              Đây là giá chào, chưa có dữ liệu lịch sử hoặc giá giao dịch.
            </p>
          </div>
          <label class="flex w-full flex-col gap-2 text-sm font-medium sm:w-auto">
            Loại bất động sản
            <select v-model="type" class="min-h-11 rounded-xl border border-[#DCD5CA] bg-white px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B3915F]">
              <option value="">Tất cả</option>
              <option v-for="(label, key) in types" :key="key" :value="key">{{ label }}</option>
            </select>
          </label>
        </div>

        <p v-if="busy" role="status" class="mt-6 text-sm text-[#536178]">Đang tải thống kê…</p>
        <p v-if="error" role="alert" class="mt-6 rounded-xl bg-rose-50 p-4 text-sm text-rose-800">
          {{ error }}
          <button type="button" @click="load" class="ml-2 cursor-pointer rounded font-semibold underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2">Thử lại</button>
        </p>

        <div v-if="summary" class="mt-6 grid gap-4 md:grid-cols-3">
          <div class="min-w-0 rounded-2xl bg-[#F7F5F0] p-5">
            <p class="text-sm text-[#536178]">Tin phù hợp</p>
            <strong class="mt-2 block text-3xl font-bold">{{ summary.overall.count }}</strong>
          </div>
          <div class="min-w-0 rounded-2xl bg-[#F7F5F0] p-5">
            <p class="text-sm text-[#536178]">Giá chào trung bình</p>
            <strong class="mt-2 block text-xl font-semibold wrap-anywhere">{{ price(summary.overall.averageAskingPrice) }} <span class="text-sm font-medium">VND</span></strong>
          </div>
          <div class="min-w-0 rounded-2xl bg-[#F7F5F0] p-5">
            <p class="text-sm text-[#536178]">Giá chào theo tổng diện tích</p>
            <strong class="mt-2 block text-xl font-semibold wrap-anywhere">{{ price(summary.overall.weightedAskingPricePerSqm) }} <span class="text-sm font-medium">VND/m²</span></strong>
          </div>
        </div>
        <p v-if="summary?.overall.count === 0" class="mt-5 text-sm text-[#536178]">Chưa có tin đủ điều kiện để thống kê.</p>
        <ul v-if="summary?.byDistrict?.length" class="mt-5 grid gap-3 md:grid-cols-3">
          <li v-for="group in summary.byDistrict" :key="group.key" class="rounded-xl border border-[#E7E1D7] p-4 text-sm leading-6 text-[#536178]">
            <strong class="block font-semibold text-[#142B4F]">{{ group.key || 'Chưa xác định khu vực' }}</strong>
            {{ group.amounts.count }} tin · {{ price(group.amounts.weightedAskingPricePerSqm) }} VND/m²
          </li>
        </ul>
        <p v-if="summary?.districtsTruncated" class="mt-4 text-sm text-[#536178]">Danh sách thống kê khu vực đã được giới hạn bởi server.</p>
      </div>
    </div>
  </section>
</template>
