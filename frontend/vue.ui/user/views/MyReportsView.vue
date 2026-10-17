
<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// SMARTPROP MY REPORTS 2.0
// Dữ liệu và hình ảnh minh họa - chưa kết nối backend.

const activeFilter = ref('all')
const searchText = ref('')
const selectedReport = ref(null)

const reports = ref([
  {
    id: 1,
    title: 'Villa sân vườn Điện Ngọc, sổ hồng riêng',
    location: 'Ngũ Hành Sơn, Đà Nẵng',
    reason: 'NGHI NGỜ ẢNH GIẢ MẠO',
    sentAt: 'Gửi lúc 09:10, 17/09/2026',
    status: 'processing',
    statusLabel: 'Đang xử lý',
    update: 'Cập nhật gần nhất: hôm nay',
    result: '',
    image:
      'https://images.unsplash.com/photo-1613977257363-707ba9348227?auto=format&fit=crop&w=900&q=85'
  },
  {
    id: 2,
    title: 'Nhà mặt tiền Nguyễn Văn Linh',
    location: 'Thanh Khê, Đà Nẵng',
    reason: 'GIÁ CAO HƠN THAM CHIẾU',
    sentAt: 'Gửi lúc 20:44, 15/09/2026',
    status: 'processing',
    statusLabel: 'Đang xử lý',
    update: 'Cập nhật gần nhất: hôm qua',
    result: '',
    image:
      'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=900&q=85'
  },
  {
    id: 3,
    title: 'Nhà 3 tầng hẻm xe hơi, gần cầu Rồng',
    location: 'Hải Châu, Đà Nẵng',
    reason: 'ẢNH TRÙNG 94%',
    sentAt: 'Gửi lúc 14:02, 10/09/2026',
    status: 'resolved',
    statusLabel: 'Đã xử lý',
    update: '12/09/2026',
    result: 'Đã xử lý — tin đăng đã bị gỡ do vi phạm.',
    image:
      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=900&q=85'
  },
  {
    id: 4,
    title: 'Đất thổ cư Hòa Xuân, pháp lý đầy đủ',
    location: 'Cẩm Lệ, Đà Nẵng',
    reason: 'SAI LỆCH GIÁ BÁN',
    sentAt: 'Gửi lúc 08:30, 05/09/2026',
    status: 'resolved',
    statusLabel: 'Không vi phạm',
    update: '07/09/2026',
    result: 'Đã xem xét — không phát hiện vi phạm rõ ràng.',
    image:
      'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=900&q=85'
  },
  {
    id: 5,
    title: 'Căn hộ Studio gần Đại học Duy Tân',
    location: 'Hải Châu, Đà Nẵng',
    reason: 'TIN ĐĂNG TRÙNG LẶP',
    sentAt: 'Gửi lúc 19:15, 28/08/2026',
    status: 'rejected',
    statusLabel: 'Từ chối',
    update: '30/08/2026',
    result: 'Báo cáo bị từ chối — thiếu minh chứng cụ thể.',
    image:
      'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=900&q=85'
  }
])

const processingCount = computed(() =>
  reports.value.filter(r => r.status === 'processing').length
)

const resolvedCount = computed(() =>
  reports.value.filter(r => r.status === 'resolved').length
)

const rejectedCount = computed(() =>
  reports.value.filter(r => r.status === 'rejected').length
)

const filters = computed(() => [
  { key: 'all', label: 'Tất cả', count: reports.value.length },
  { key: 'processing', label: 'Đang xử lý', count: processingCount.value },
  { key: 'resolved', label: 'Đã xử lý', count: resolvedCount.value },
  { key: 'rejected', label: 'Từ chối', count: rejectedCount.value }
])

const filteredReports = computed(() => {
  const keyword = searchText.value.trim().toLocaleLowerCase('vi-VN')

  return reports.value.filter(report => {
    const matchesStatus =
      activeFilter.value === 'all' ||
      report.status === activeFilter.value

    const searchableText = [
      report.title,
      report.location,
      report.reason,
      report.statusLabel,
      report.result
    ].join(' ').toLocaleLowerCase('vi-VN')

    return matchesStatus && (!keyword || searchableText.includes(keyword))
  })
})

function statusClass(status) {
  if (status === 'processing') {
    return 'bg-[#FFF1D9] text-[#A36A19]'
  }

  if (status === 'resolved') {
    return 'bg-[#E5F4EB] text-[#287B56]'
  }

  return 'bg-[#FCE8E3] text-[#BD5D48]'
}

function statusDot(status) {
  if (status === 'processing') return 'bg-[#D69C44]'
  if (status === 'resolved') return 'bg-[#4DAD80]'
  return 'bg-[#D17760]'
}

function openReport(report) {
  selectedReport.value = report
}

function closeReport() {
  selectedReport.value = null
}

function resetFilters() {
  activeFilter.value = 'all'
  searchText.value = ''
}

function goHome() {
  router.push('/home')
}

function goAccount() {
  router.push('/account')
}

function goPost() {
  router.push('/post')
}

function goMap() {
  router.push('/map')
}
</script>

<template>
  <div class="sp-my-reports min-h-screen bg-[#F7F5F0] text-[#142B4F]">

    <!-- HEADER -->
    <header class="border-b border-[#E7E2D8] bg-[#F7F5F0]">
      <div class="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-4 px-5 py-5 md:px-10">
        <div class="flex items-center gap-5">
          <button
            type="button"
            @click="goHome"
            class="flex items-center gap-3"
          >
            <span class="flex h-10 w-10 items-center justify-center rounded-full bg-[#142B4F] font-bold text-white">
              S
            </span>

            <span class="text-xl font-bold">
              SmartProp<span class="text-[#C6A77A]">.</span>
            </span>
          </button>

          <button
            type="button"
            @click="goHome"
            class="hidden text-xs text-[#8290A0] hover:text-[#142B4F] sm:block"
          >
            ← Trang chủ
          </button>
        </div>

        <div class="flex items-center gap-2">
          <button
            type="button"
            @click="goPost"
            class="hidden rounded-full border border-[#E4DED3] bg-white px-5 py-3 text-xs font-semibold hover:border-[#C6A77A] sm:block"
          >
            Đăng tin ↗
          </button>

          <button
            type="button"
            @click="goAccount"
            class="rounded-full bg-[#142B4F] px-5 py-3 text-xs font-semibold text-white hover:bg-[#25466B]"
          >
            Tài khoản
          </button>
        </div>
      </div>
    </header>

    <!-- INTRO -->
    <section class="relative overflow-hidden border-b border-[#E7E2D8]">
      <div class="pointer-events-none absolute -right-28 -top-32 h-[420px] w-[420px] rounded-full border border-[#C6A77A]/20"></div>
      <div class="pointer-events-none absolute -right-10 -top-12 h-[280px] w-[280px] rounded-full border border-[#C6A77A]/20"></div>

      <div class="relative mx-auto max-w-[1440px] px-5 py-12 md:px-10 md:py-16">
        <div class="flex flex-wrap items-end justify-between gap-8">
          <div>
            <div class="flex items-center gap-3">
              <span class="h-px w-9 bg-[#B49362]"></span>
              <p class="text-[10px] font-bold uppercase tracking-[0.22em] text-[#B49362]">
                SMARTPROP / TRUST & TRANSPARENCY
              </p>
            </div>

            <h1 class="mt-6 text-[39px] font-medium leading-tight tracking-tight sm:text-[56px]">
              Theo dõi
              <span class="block italic text-[#B49362]">báo cáo của bạn.</span>
            </h1>

            <p class="mt-5 max-w-2xl text-sm leading-7 text-[#7B8798]">
              Quản lý các báo cáo đã gửi, theo dõi tiến độ xem xét
              và xem kết quả xử lý trong một không gian trực quan,
              minh bạch và dễ sử dụng.
            </p>

            <span class="mt-5 inline-flex rounded-full border border-[#E2D8C8] bg-[#EEE7DB] px-4 py-2 text-[10px] font-bold uppercase tracking-widest text-[#94774F]">
              Dữ liệu minh họa
            </span>
          </div>

          <button
            type="button"
            @click="goMap"
            class="rounded-full border border-[#DCD4C7] bg-white px-7 py-4 text-xs font-bold transition hover:border-[#C6A77A]"
          >
            Khám phá GIS Explorer ↗
          </button>
        </div>
      </div>
    </section>

    <!-- STATISTICS -->
    <section class="mx-auto max-w-[1440px] px-5 pt-10 md:px-10">
      <div class="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-5">

        <div class="rounded-[20px] border border-[#E8E3DA] bg-white p-5 sm:p-7">
          <p class="text-[10px] font-bold uppercase tracking-widest text-[#8D99A8]">
            Tổng báo cáo
          </p>

          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ reports.length }}</span>
            <span class="text-xl text-[#C6A77A]">▤</span>
          </div>

          <p class="mt-3 text-[11px] text-[#8D99A8]">
            Báo cáo đã gửi
          </p>
        </div>

        <div class="rounded-[20px] bg-[#142B4F] p-5 text-white sm:p-7">
          <p class="text-[10px] font-bold uppercase tracking-widest text-white/60">
            Đang xử lý
          </p>

          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ processingCount }}</span>
            <span class="h-3 w-3 rounded-full bg-[#E5B76A]"></span>
          </div>

          <p class="mt-3 text-[11px] text-white/55">
            Đang chờ kết quả
          </p>
        </div>

        <div class="rounded-[20px] border border-[#E8E3DA] bg-white p-5 sm:p-7">
          <p class="text-[10px] font-bold uppercase tracking-widest text-[#8D99A8]">
            Đã xử lý
          </p>

          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ resolvedCount }}</span>
            <span class="text-xl text-[#3A9A70]">✓</span>
          </div>

          <p class="mt-3 text-[11px] text-[#8D99A8]">
            Đã có kết quả xem xét
          </p>
        </div>

        <div class="rounded-[20px] border border-[#E8E3DA] bg-white p-5 sm:p-7">
          <p class="text-[10px] font-bold uppercase tracking-widest text-[#8D99A8]">
            Bị từ chối
          </p>

          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ rejectedCount }}</span>
            <span class="text-xl text-[#C56E56]">!</span>
          </div>

          <p class="mt-3 text-[11px] text-[#8D99A8]">
            Báo cáo không được chấp nhận
          </p>
        </div>
      </div>
    </section>

    <!-- REPORTS -->
    <main class="mx-auto max-w-[1440px] px-5 pb-20 pt-12 md:px-10">

      <div class="flex flex-wrap items-end justify-between gap-5">
        <div>
          <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-[#B49362]">
            REPORT CENTER / 01
          </p>

          <h2 class="mt-3 text-3xl font-medium tracking-tight sm:text-4xl">
            Lịch sử <span class="italic text-[#B49362]">báo cáo.</span>
          </h2>

          <p class="mt-3 text-xs text-[#87919F]">
            Theo dõi tiến độ và kết quả xử lý của từng báo cáo.
          </p>
        </div>

        <div class="flex w-full items-center gap-3 rounded-xl border border-[#E4DED3] bg-white px-4 sm:w-[320px]">
          <span class="text-xl text-[#B49362]">⌕</span>

          <input
            v-model="searchText"
            type="search"
            aria-label="Tìm kiếm báo cáo"
            placeholder="Tìm báo cáo, lý do hoặc khu vực..."
            class="h-12 min-w-0 w-full bg-transparent text-xs outline-none"
          />
        </div>
      </div>

      <!-- FILTERS -->
      <div class="mt-8 flex flex-wrap gap-2">
        <button
          v-for="filter in filters"
          :key="filter.key"
          type="button"
          @click="activeFilter = filter.key"
          class="rounded-full border px-4 py-2.5 text-[11px] font-semibold transition sm:px-5"
          :class="
            activeFilter === filter.key
              ? 'border-[#142B4F] bg-[#142B4F] text-white'
              : 'border-[#E4DED3] bg-white text-[#64748B] hover:border-[#C6A77A]'
          "
        >
          {{ filter.label }}
          <span class="ml-1 opacity-65">{{ filter.count }}</span>
        </button>
      </div>

      <div class="mb-5 mt-7 flex items-center justify-between gap-4">
        <p class="text-xs text-[#87919F]">
          Hiển thị
          <strong class="text-[#142B4F]">{{ filteredReports.length }}</strong>
          báo cáo
        </p>

        <span class="text-[10px] uppercase tracking-widest text-[#B49362]">
          REPORT HISTORY
        </span>
      </div>

      <!-- REPORT CARDS -->
      <div v-if="filteredReports.length" class="space-y-5">
        <article
          v-for="report in filteredReports"
          :key="report.id"
          class="group grid min-w-0 overflow-hidden rounded-[22px] border border-[#E8E3DA] bg-white transition duration-300 hover:border-[#C6A77A] hover:shadow-[0_16px_45px_rgba(20,43,79,0.08)] lg:grid-cols-[245px_minmax(0,1fr)_225px]"
        >
          <!-- IMAGE -->
          <div class="relative h-[225px] overflow-hidden bg-[#E7E2D8] lg:h-full lg:min-h-[230px]">
            <img
              :src="report.image"
              :alt="`Ảnh minh họa: ${report.title}`"
              loading="lazy"
              class="h-full w-full object-cover transition duration-700 group-hover:scale-105"
            />

            <div class="absolute inset-0 bg-gradient-to-t from-[#142B4F]/55 to-transparent"></div>

            <span class="absolute bottom-4 left-4 text-[10px] font-bold uppercase tracking-[0.12em] text-white">
              {{ report.location }}
            </span>
          </div>

          <!-- INFO -->
          <div class="flex min-w-0 flex-col justify-center p-5 sm:p-7">
            <div class="flex flex-wrap items-center gap-3">
              <span
                class="inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[10px] font-bold"
                :class="statusClass(report.status)"
              >
                <span
                  class="h-1.5 w-1.5 rounded-full"
                  :class="statusDot(report.status)"
                ></span>
                {{ report.statusLabel }}
              </span>

              <span class="text-[10px] font-semibold text-[#B49362]">
                REPORT #{{ String(report.id).padStart(3, '0') }}
              </span>
            </div>

            <h3 class="mt-4 text-lg font-semibold leading-7 sm:text-xl">
              {{ report.title }}
            </h3>

            <p class="mt-2 text-xs text-[#87919F]">
              ⌖ {{ report.location }}
            </p>

            <div class="mt-4">
              <span class="inline-flex max-w-full rounded-full bg-[#F4EFE7] px-3 py-2 text-[10px] font-bold tracking-wide text-[#9B7952]">
                {{ report.reason }}
              </span>
            </div>

            <p class="mt-4 text-[11px] text-[#87919F]">
              {{ report.sentAt }}
            </p>

            <p
              v-if="report.result"
              class="mt-4 border-l-2 border-[#C6A77A] pl-3 text-xs leading-6 text-[#64748B]"
            >
              {{ report.result }}
            </p>
          </div>

          <!-- STATUS / ACTION -->
          <div class="flex flex-col justify-between gap-6 border-t border-[#EEEAE3] p-5 sm:p-7 lg:border-l lg:border-t-0">
            <div class="lg:text-right">
              <p class="text-[10px] uppercase tracking-widest text-[#9AA4B1]">
                Trạng thái hiện tại
              </p>

              <p class="mt-3 text-base font-semibold">
                {{ report.statusLabel }}
              </p>

              <p class="mt-2 text-[11px] leading-5 text-[#87919F]">
                {{ report.update }}
              </p>
            </div>

            <button
              type="button"
              @click="openReport(report)"
              class="self-start rounded-full border border-[#E4DED3] bg-white px-5 py-3 text-[11px] font-semibold transition hover:border-[#142B4F] hover:bg-[#142B4F] hover:text-white lg:self-end"
            >
              Xem báo cáo ↗
            </button>
          </div>
        </article>
      </div>

      <!-- EMPTY -->
      <div
        v-else
        class="rounded-[24px] border border-[#E8E3DA] bg-white px-6 py-20 text-center"
      >
        <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[#F7F5F0] text-3xl text-[#B49362]">
          ⚑
        </div>

        <h3 class="mt-6 text-xl font-semibold">
          Không tìm thấy báo cáo
        </h3>

        <p class="mt-3 text-sm text-[#87919F]">
          Hãy thử thay đổi trạng thái hoặc từ khóa tìm kiếm.
        </p>

        <button
          type="button"
          @click="resetFilters"
          class="mt-6 rounded-full bg-[#142B4F] px-6 py-3 text-xs font-semibold text-white"
        >
          Xem tất cả báo cáo
        </button>
      </div>

      <!-- NOTICE -->
      <section class="mt-10 rounded-[22px] border border-[#E8E3DA] bg-white px-6 py-6 sm:px-8">
        <div class="flex items-start gap-4">
          <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#EEE7DB] text-lg font-semibold text-[#9B7952]">
            i
          </div>

          <div>
            <h3 class="text-sm font-semibold">
              Thông tin về quá trình xử lý
            </h3>

            <p class="mt-2 max-w-3xl text-xs leading-6 text-[#87919F]">
              Theo quy trình minh họa của SmartProp, báo cáo thường được
              xem xét trong khoảng 24–48 giờ. Trạng thái và kết quả trên
              trang hiện là dữ liệu mẫu, chưa được cập nhật tự động từ hệ thống.
            </p>
          </div>
        </div>
      </section>

      <!-- CTA -->
      <section class="relative mt-12 overflow-hidden rounded-[25px] bg-[#142B4F] px-7 py-10 text-white sm:px-10">
        <div class="pointer-events-none absolute -right-12 -top-24 h-72 w-72 rounded-full border border-[#C6A77A]/20"></div>

        <div class="relative flex flex-wrap items-center justify-between gap-7">
          <div>
            <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-[#7BD4E5]">
              SMARTPROP / TRUST & SAFETY
            </p>

            <h2 class="mt-4 text-3xl font-medium">
              Minh bạch hơn.
              <span class="italic text-[#C6A77A]"> An tâm hơn.</span>
            </h2>

            <p class="mt-4 max-w-xl text-sm leading-7 text-white/60">
              Khám phá bất động sản và các thông tin tham khảo
              trên nền tảng SmartProp.
            </p>
          </div>

          <button
            type="button"
            @click="goMap"
            class="rounded-full bg-[#C6A77A] px-7 py-4 text-xs font-bold text-[#142B4F] transition hover:bg-[#E1C394]"
          >
            Khám phá bản đồ GIS ↗
          </button>
        </div>
      </section>

      <p class="mt-7 text-center text-[11px] leading-6 text-[#87919F]">
        Báo cáo, kết quả xử lý và hình ảnh trên trang này đều là dữ liệu minh họa.
      </p>
    </main>

    <!-- REPORT DETAIL MODAL -->
    <div
      v-if="selectedReport"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[#08172B]/70 p-4"
      @click.self="closeReport"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-dialog-title"
        class="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-[24px] bg-white shadow-2xl"
      >
        <div class="relative h-[210px]">
          <img
            :src="selectedReport.image"
            :alt="selectedReport.title"
            class="h-full w-full object-cover"
          />

          <button
            type="button"
            @click="closeReport"
            aria-label="Đóng chi tiết báo cáo"
            class="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full bg-white text-[#142B4F]"
          >
            ✕
          </button>
        </div>

        <div class="p-6 sm:p-8">
          <div class="flex flex-wrap items-center gap-3">
            <span
              class="rounded-full px-3 py-1.5 text-[10px] font-semibold"
              :class="statusClass(selectedReport.status)"
            >
              {{ selectedReport.statusLabel }}
            </span>

            <span class="text-[11px] text-[#B49362]">
              REPORT #{{ String(selectedReport.id).padStart(3, '0') }}
            </span>
          </div>

          <h2 id="report-dialog-title" class="mt-5 text-2xl font-semibold">
            {{ selectedReport.title }}
          </h2>

          <p class="mt-3 text-sm text-[#87919F]">
            {{ selectedReport.location }}
          </p>

          <div class="mt-6 space-y-4 border-y border-[#EEEAE3] py-5">
            <div>
              <p class="text-[10px] uppercase tracking-widest text-[#9AA4B1]">
                Lý do báo cáo
              </p>
              <p class="mt-2 text-sm font-semibold">
                {{ selectedReport.reason }}
              </p>
            </div>

            <div>
              <p class="text-[10px] uppercase tracking-widest text-[#9AA4B1]">
                Thời gian gửi
              </p>
              <p class="mt-2 text-sm">
                {{ selectedReport.sentAt }}
              </p>
            </div>

            <div>
              <p class="text-[10px] uppercase tracking-widest text-[#9AA4B1]">
                Cập nhật
              </p>
              <p class="mt-2 text-sm">
                {{ selectedReport.update }}
              </p>
            </div>

            <div>
              <p class="text-[10px] uppercase tracking-widest text-[#9AA4B1]">
                Kết quả
              </p>
              <p class="mt-2 text-sm leading-6 text-[#64748B]">
                {{ selectedReport.result || 'Báo cáo đang được xử lý, chưa có kết quả.' }}
              </p>
            </div>
          </div>

          <button
            type="button"
            @click="closeReport"
            class="mt-6 rounded-full bg-[#142B4F] px-7 py-3 text-xs font-semibold text-white"
          >
            Đóng chi tiết
          </button>
        </div>
      </div>
    </div>

    <!-- FOOTER -->
    <footer class="border-t border-[#E7E2D8]">
      <div class="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-4 px-5 py-7 md:px-10">
        <button @click="goHome" class="text-lg font-bold">
          SmartProp<span class="text-[#C6A77A]">.</span>
        </button>

        <p class="text-[11px] text-[#87919F]">
          © 2026 SmartProp · My Reports 2.0
        </p>

        <button @click="goHome" class="text-xs text-[#64748B]">
          Về trang chủ ↗
        </button>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.sp-my-reports {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
  font-family: Arial, "Segoe UI", sans-serif;
  font-synthesis: none;
}

.sp-my-reports h1,
.sp-my-reports h2,
.sp-my-reports h3 {
  font-family: Arial, "Segoe UI", sans-serif;
  font-variant-ligatures: none;
  word-spacing: normal;
}

.sp-my-reports button,
.sp-my-reports input {
  font-family: inherit;
}

.sp-my-reports img {
  display: block;
}

@media (prefers-reduced-motion: reduce) {
  .sp-my-reports *,
  .sp-my-reports *::before,
  .sp-my-reports *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}
</style>
