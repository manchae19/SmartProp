<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { buildValuationPayload, createValuationClient, featureLabels, formatPrice, locationLabel, warningLabel } from '../services/valuation.js'

const props = defineProps({ initialInput: { type: Object, default: () => ({}) }, demo: Boolean })
const client = createValuationClient()
const options = ref(null)
const optionsLoading = ref(false)
const optionsError = ref('')
const predicting = ref(false)
const predictionError = ref('')
const result = ref(null)
const form = reactive({})
let optionsController
let predictionController
let generation = 0

const locations = computed(() => options.value?.categories.find((item) => item.category === form.category)?.locations ?? [])
const legacyLocations = computed(() => locations.value.filter((value) => !value.startsWith('new_unit:')))
const expandedLocations = computed(() => locations.value.filter((value) => value.startsWith('new_unit:')))
const displayLocation = (value) => locationLabel(value, options.value?.location_labels)
const isHouse = computed(() => form.category === 'Nhà ở')
const isApartment = computed(() => form.category === 'Căn hộ chung cư')
const hasRooms = computed(() => form.category !== 'Đất nền')
const missingLabels = computed(() => result.value?.missing_features.map((key) => featureLabels[key] ?? 'Thông tin bổ sung') ?? [])
const usedFeatures = computed(() => {
  if (!result.value) return []
  return Object.entries(result.value.features_used).filter(([, value]) => value !== null).map(([key, value]) => {
    if (key === 'area_sqm') value = `${value} m²`
    if (key === 'location_feature') value = displayLocation(value)
    if (key === 'ward_source') value = String(form.ward ?? '').trim() || value
    if (key === 'access_type') value = options.value.access_types[value]
    if (key === 'house_subtype') value = options.value.house_subtypes[value]
    return { label: featureLabels[key], value }
  })
})

function invalidate() {
  generation++
  predictionController?.abort()
  result.value = null
  predictionError.value = ''
  predicting.value = false
}

watch(form, invalidate, { deep: true, flush: 'sync' })
watch(() => props.initialInput, (input) => {
  invalidate()
  Object.assign(form, { category: 'Nhà ở', area_sqm: '', location_feature: '', ward: '', rooms: '', floors: '', access_type: '', house_subtype: '' }, input)
}, { immediate: true })
watch(() => form.category, () => {
  if (!hasRooms.value) form.rooms = ''
  if (!isHouse.value) { form.floors = ''; form.house_subtype = '' }
  if (isApartment.value) form.access_type = ''
  if (options.value && !locations.value.includes(form.location_feature)) form.location_feature = ''
})

async function loadOptions() {
  invalidate()
  optionsController?.abort()
  const controller = new AbortController()
  optionsController = controller
  optionsLoading.value = true
  optionsError.value = ''
  try {
    const data = await client.getOptions({ signal: controller.signal })
    if (controller.signal.aborted) return
    options.value = data
    if (!locations.value.includes(form.location_feature)) form.location_feature = ''
  } catch (error) {
    if (!controller.signal.aborted) optionsError.value = error.message
  } finally {
    if (optionsController === controller) optionsLoading.value = false
  }
}

async function estimate() {
  invalidate()
  if (!options.value) return
  let payload
  try { payload = buildValuationPayload(form, options.value) }
  catch (error) { predictionError.value = error.message; return }
  const current = generation
  const controller = new AbortController()
  predictionController = controller
  predicting.value = true
  try {
    const prediction = await client.predict(payload, { signal: controller.signal })
    if (current === generation && !controller.signal.aborted) result.value = prediction
  } catch (error) {
    if (current === generation && !controller.signal.aborted) predictionError.value = error.message
  } finally {
    if (current === generation) predicting.value = false
  }
}

onMounted(loadOptions)
onBeforeUnmount(() => { generation++; optionsController?.abort(); predictionController?.abort() })
</script>

<template>
  <section class="valuation-panel bg-[#1E325A] text-white rounded-[24px] p-6 md:p-8 shadow-sm" aria-labelledby="valuation-heading">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p class="text-xs text-white/60 uppercase tracking-widest">Định giá tham chiếu · XGBoost v6</p>
        <h2 id="valuation-heading" class="text-2xl font-semibold mt-2">Ước tính giá rao</h2>
      </div>
      <span v-if="demo" class="rounded-full bg-white/10 px-3 py-1 text-xs text-white/80">Tin minh họa</span>
    </div>
    <p class="text-sm text-white/70 mt-3 leading-6">Nhập thông tin hiện có. Các trường chưa rõ có thể để trống; kết quả được tính từ thông tin trong form này.</p>

    <p v-if="optionsLoading" role="status" class="mt-5 text-sm text-white/80">Đang tải địa bàn được hỗ trợ…</p>
    <div v-else-if="optionsError" role="alert" class="mt-5 rounded-xl bg-white/10 p-4">
      <p>{{ optionsError }}</p>
      <button type="button" class="mt-3 underline underline-offset-4" @click="loadOptions">Thử kết nối lại</button>
    </div>

    <form v-else-if="options" class="mt-6" novalidate @submit.prevent="estimate">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <label class="block text-sm">Loại bất động sản <span aria-hidden="true">*</span>
          <select v-model="form.category" required class="valuation-input mt-2">
            <option v-for="item in options.categories" :key="item.category" :value="item.category">{{ item.category }}</option>
          </select>
        </label>
        <label class="block text-sm">Địa bàn <span aria-hidden="true">*</span>
          <select v-model="form.location_feature" required class="valuation-input mt-2">
            <option disabled value="">Chọn địa bàn</option>
            <optgroup v-if="legacyLocations.length" label="Quận/huyện cũ">
              <option v-for="location in legacyLocations" :key="location" :value="location">{{ displayLocation(location) }}</option>
            </optgroup>
            <optgroup v-if="expandedLocations.length" label="Địa bàn mở rộng trong dữ liệu">
              <option v-for="location in expandedLocations" :key="location" :value="location">{{ displayLocation(location) }}</option>
            </optgroup>
          </select>
        </label>
        <label class="block text-sm">Diện tích (m²) <span aria-hidden="true">*</span>
          <input v-model="form.area_sqm" type="number" min="20" max="1000" step="any" inputmode="decimal" required class="valuation-input mt-2" placeholder="Ví dụ: 80" />
          <span class="block mt-1 text-xs text-white/60">Từ 20 đến 1.000 m²</span>
        </label>
        <label class="block text-sm">Phường/xã theo tin <span class="text-white/50">· tùy chọn</span>
          <input v-model="form.ward" maxlength="100" class="valuation-input mt-2" placeholder="Để trống nếu chưa rõ" />
          <span class="block mt-1 text-xs text-white/60">Bổ sung nếu địa chỉ tin nêu rõ; có thể để trống.</span>
        </label>
        <label v-if="hasRooms" class="block text-sm">Phòng ngủ <span class="text-white/50">· tùy chọn</span>
          <input v-model="form.rooms" type="number" min="1" max="30" step="1" inputmode="numeric" class="valuation-input mt-2" placeholder="Chưa rõ" />
        </label>
        <label v-if="isHouse" class="block text-sm">Số tầng nhà <span class="text-white/50">· tùy chọn</span>
          <input v-model="form.floors" type="number" min="1" max="20" step="any" inputmode="decimal" class="valuation-input mt-2" placeholder="Chưa rõ" />
        </label>
        <label v-if="!isApartment" class="block text-sm">Lối vào <span class="text-white/50">· tùy chọn</span>
          <select v-model="form.access_type" class="valuation-input mt-2">
            <option value="">Chưa rõ</option>
            <option v-for="(label, value) in options.access_types" :key="value" :value="value">{{ label }}</option>
          </select>
        </label>
        <label v-if="isHouse" class="block text-sm">Loại nhà chi tiết <span class="text-white/50">· tùy chọn</span>
          <select v-model="form.house_subtype" class="valuation-input mt-2">
            <option value="">Chưa rõ</option>
            <option v-for="(label, value) in options.house_subtypes" :key="value" :value="value">{{ label }}</option>
          </select>
        </label>
      </div>
      <button type="submit" :disabled="predicting" class="mt-6 rounded-full bg-white px-6 py-3 text-sm font-semibold text-[#1E325A] hover:bg-[#f4f3ec] disabled:opacity-60 disabled:cursor-wait transition">
        {{ predicting ? 'Đang ước tính…' : 'Ước tính giá rao' }}
      </button>
    </form>

    <div aria-live="polite" aria-atomic="true" class="mt-5">
      <p v-if="predicting" role="status" class="text-sm text-white/80">Mô hình đang tính giá từ thông tin đã nhập…</p>
      <p v-if="predictionError" role="alert" class="rounded-xl bg-[#f7e9df] p-4 text-sm text-[#713b24]">{{ predictionError }}</p>
      <div v-if="result" class="border-t border-white/20 pt-6" data-testid="valuation-result">
        <p class="text-sm text-white/70">Giá rao ước tính</p>
        <p class="text-3xl sm:text-4xl font-semibold mt-2" data-testid="estimated-price">{{ formatPrice(result.predicted_asking_price_vnd) }}</p>
        <p class="text-sm text-white/70 mt-2">{{ new Intl.NumberFormat('vi-VN').format(result.predicted_asking_price_vnd) }} đồng · Tổng giá bất động sản</p>
        <h3 class="font-medium text-sm mt-6">Thông tin đã dùng</h3>
        <dl class="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-3">
          <div v-for="feature in usedFeatures" :key="feature.label" class="rounded-xl bg-white/10 p-3">
            <dt class="text-xs text-white/60">{{ feature.label }}</dt><dd class="text-sm mt-1">{{ feature.value }}</dd>
          </div>
        </dl>
        <p v-if="missingLabels.length" class="text-sm text-white/80 mt-4">Thông tin còn thiếu: {{ missingLabels.join(', ') }}.</p>
        <ul v-if="result.warnings.length" class="list-disc pl-5 mt-3 space-y-2 text-sm text-[#ffdfb8]">
          <li v-for="warning in result.warnings" :key="warning">{{ warningLabel(warning) }}</li>
        </ul>
      </div>
    </div>
    <p class="mt-6 text-xs text-white/60 leading-5">Giá rao ước tính để tham khảo. Mô hình chưa sử dụng tọa độ tài sản và khoảng cách tới tiện ích; kết quả chưa được xác minh bằng giá giao dịch.</p>
  </section>
</template>

<style scoped>
.valuation-input { display: block; width: 100%; min-height: 44px; border: 1px solid #ffffff45; border-radius: 12px; padding: 11px 12px; background: #fff; color: #1e325a; font-size: 14px; }
.valuation-input:focus-visible { outline: 3px solid #9bd7bf; outline-offset: 2px; }
.valuation-input::placeholder { color: #6b7280; }
</style>
