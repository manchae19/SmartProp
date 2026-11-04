<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { session, errorText } from '../auth/api.js'
import { createHistoryClient } from './history.js'
import { formatPrice, locationLabel } from './valuation.js'

const props = defineProps({ refreshKey: Number })
const client = createHistoryClient()
const items = ref([]), busy = ref(false), error = ref(''), page = ref(0), pages = ref(0)
const removing = ref(''), labels = ref({})
let revision = 0

async function load() {
  const current = ++revision
  items.value = []; error.value = ''; busy.value = false
  if (!session.token) return
  busy.value = true
  try {
    const result = await client.list(page.value)
    if (current !== revision) return
    items.value = result.items; pages.value = result.totalPages
  } catch (failure) { if (current === revision) error.value = failure.code==='HISTORY_UNAVAILABLE'?'Lịch sử định giá hiện chưa khả dụng. Bạn vẫn có thể thực hiện ước tính mới.':errorText(failure) }
  finally { if (current === revision) busy.value = false }
}
async function remove(id) {
  if (removing.value) return
  const current = revision
  removing.value = id; error.value = ''
  try {
    await client.remove(id)
    if (current !== revision) return
    page.value = 0
    await load()
  } catch (failure) { if (current === revision) error.value = errorText(failure) }
  finally { removing.value = '' }
}

function setLabels(value) { labels.value = value }
defineExpose({ setLabels })
watch(() => session.token, () => { page.value = 0; load() }, { immediate: true })
watch(() => props.refreshKey, () => { page.value = 0; load() })
onBeforeUnmount(() => { revision++ })
</script>

<template>
  <section class="mt-8 rounded-3xl border border-[#1E325A]/20 bg-white p-6 sm:p-8" aria-labelledby="history-heading">
    <div class="flex flex-wrap justify-between gap-3">
      <h2 id="history-heading" class="text-xl font-semibold sm:text-2xl">Lịch sử định giá</h2><RouterLink to="/valuation" class="text-sm underline">Ước tính giá rao mới ↗</RouterLink>

    </div>
    <p v-if="!session.token" class="mt-3 text-sm leading-6">
      <RouterLink to="/login?next=/valuation" class="underline">Đăng nhập</RouterLink> để lưu và xem lại kết quả của bạn.
    </p>
    <template v-else>
      <p class="mt-2 text-sm text-[#58657c]">Kết quả đã lưu của {{ session.user?.fullName || 'tài khoản hiện tại' }}. Giá được giữ theo thời điểm ước tính.</p>
      <p v-if="busy" role="status" class="mt-4">Đang tải lịch sử…</p>
      <div v-if="error" role="alert" class="mt-4 rounded-xl bg-[#f7e9df] p-3 text-sm">
        {{ error }} <button class="underline ml-2" @click="load">Tải lại lịch sử</button>
      </div>
      <div v-if="!busy && !error && !items.length" class="mt-5 rounded-2xl border border-dashed border-brand-line bg-brand-cream p-6 text-center"><h3 class="text-base font-semibold">Chưa có phân tích đã lưu</h3><p class="mx-auto mt-2 max-w-md text-sm leading-7 text-brand-muted">Khi bạn lưu một kết quả ước tính, kết quả đó sẽ xuất hiện tại đây.</p><RouterLink to="/valuation" class="sp-button sp-button-secondary mt-4">Thực hiện đánh giá mới ↗</RouterLink></div>
      <ol class="mt-4 space-y-3">
        <li v-for="item in items" :key="item.id" class="rounded-xl bg-[#ebe9e2]/60 p-4" data-testid="history-item">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p class="font-semibold">{{ formatPrice(item.prediction.predicted_asking_price_vnd) }}</p>
              <p class="text-sm mt-1">{{ item.input.category }} · {{ item.input.area_sqm }} m² · {{ locationLabel(item.input.location_feature, labels) }}</p>
              <p class="text-xs mt-2 text-[#58657c]">{{ new Intl.DateTimeFormat('vi-VN', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(item.createdAt)) }} · Giá rao tham khảo</p>
            </div>
            <button type="button" :disabled="!!removing" class="text-sm underline disabled:opacity-50" :aria-label="`Xóa kết quả ${formatPrice(item.prediction.predicted_asking_price_vnd)}`" @click="remove(item.id)">
              {{ removing === item.id ? 'Đang xóa…' : 'Xóa' }}
            </button>
          </div>
        </li>
      </ol>
      <nav v-if="pages > 1" class="mt-4 flex items-center gap-4 text-sm" aria-label="Trang lịch sử">
        <button :disabled="busy || page === 0" class="underline disabled:opacity-40" @click="page--; load()">Trang trước</button>
        <span>{{ page + 1 }} / {{ pages }}</span>
        <button :disabled="busy || page + 1 >= pages" class="underline disabled:opacity-40" @click="page++; load()">Trang sau</button>
      </nav>
    </template>
  </section>
</template>
