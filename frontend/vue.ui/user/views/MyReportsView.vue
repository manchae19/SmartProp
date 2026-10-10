<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// ==================== FILTER ====================

const activeFilter = ref('all')

const filters = [
  {
    key: 'all',
    label: 'Tất cả',
  },
  {
    key: 'processing',
    label: 'Đang xử lý',
  },
  {
    key: 'resolved',
    label: 'Đã xử lý',
  },
  {
    key: 'rejected',
    label: 'Từ chối',
  },
]

// ==================== REPORT DATA ====================

const reports = ref([
  {
    id: 1,

    title:
      'Villa sân vườn Điện Ngọc, sổ hồng riêng',

    location:
      'Ngũ Hành Sơn, Đà Nẵng',

    reason:
      'NGHI NGỜ ẢNH GIẢ MẠO',

    sentAt:
      'Gửi lúc 09:10, 17/09/2026',

    status:
      'processing',

    statusLabel:
      'Đang xử lý',

    update:
      'Cập nhật gần nhất: hôm nay',

    result:
      '',

    image:
      '/images/report1.png',
  },

  {
    id: 2,

    title:
      'Nhà mặt tiền Nguyễn Văn Linh',

    location:
      'Thanh Khê, Đà Nẵng',

    reason:
      'GIÁ CAO HƠN THAM CHIẾU',

    sentAt:
      'Gửi lúc 20:44, 15/09/2026',

    status:
      'processing',

    statusLabel:
      'Đang xử lý',

    update:
      'Cập nhật gần nhất: hôm qua',

    result:
      '',

    image:
      '/images/report2.png',
  },

  {
    id: 3,

    title:
      'Nhà 3 tầng hẻm xe hơi, gần cầu Rồng',

    location:
      'Hải Châu, Đà Nẵng',

    reason:
      'ẢNH TRÙNG 94%',

    sentAt:
      'Gửi lúc 14:02, 10/09/2026',

    status:
      'resolved',

    statusLabel:
      'Đã xử lý',

    update:
      '12/09/2026',

    result:
      '✓ Đã xử lý — tin đăng đã bị gỡ do vi phạm.',

    image:
      '/images/report3.png',
  },

  {
    id: 4,

    title:
      'Đất thổ cư Hòa Xuân, pháp lý đầy đủ',

    location:
      'Cẩm Lệ, Đà Nẵng',

    reason:
      'SAI LỆCH GIÁ BÁN',

    sentAt:
      'Gửi lúc 08:30, 05/09/2026',

    status:
      'resolved',

    statusLabel:
      'Không vi phạm',

    update:
      '07/09/2026',

    result:
      'Đã xem xét — không phát hiện vi phạm rõ ràng.',

    image:
      '/images/report4.png',
  },

  {
    id: 5,

    title:
      'Căn hộ Studio gần Đại học Duy Tân',

    location:
      'Hải Châu, Đà Nẵng',

    reason:
      'TIN ĐĂNG TRÙNG LẶP',

    sentAt:
      'Gửi lúc 19:15, 28/08/2026',

    status:
      'rejected',

    statusLabel:
      'Từ chối',

    update:
      '30/08/2026',

    result:
      'Báo cáo bị từ chối — thiếu minh chứng cụ thể.',

    image:
      '/images/report5.png',
  },
])

// ==================== COUNTS ====================

const processingCount = computed(() => {
  return reports.value.filter(
    report => report.status === 'processing'
  ).length
})

const resolvedCount = computed(() => {
  return reports.value.filter(
    report => report.status === 'resolved'
  ).length
})

const rejectedCount = computed(() => {
  return reports.value.filter(
    report => report.status === 'rejected'
  ).length
})

// ==================== FILTERED REPORTS ====================

const filteredReports = computed(() => {
  if (activeFilter.value === 'all') {
    return reports.value
  }

  return reports.value.filter(
    report => report.status === activeFilter.value
  )
})

// ==================== FUNCTIONS ====================

const getFilterCount = (key) => {
  if (key === 'all') {
    return reports.value.length
  }

  if (key === 'processing') {
    return processingCount.value
  }

  if (key === 'resolved') {
    return resolvedCount.value
  }

  if (key === 'rejected') {
    return rejectedCount.value
  }

  return 0
}

const goHome = () => {
  router.push('/home')
}

const goAccount = () => {
  router.push('/account')
}

const goPost = () => {
  router.push('/post')
}
</script>

<template>
  <div
    class="min-h-screen bg-[#e9e7e1] text-[#1E325A]"
  >

    <!-- ========================================== -->
    <!-- HEADER -->
    <!-- ========================================== -->

    <header
      class="max-w-[1400px] mx-auto px-6 md:px-8 pt-5"
    >
      <div
        class="h-[70px] border-b border-[#1E325A]
               flex items-center justify-between"
      >

        <!-- LEFT -->

        <div
          class="flex items-center gap-5 md:gap-8"
        >
          <button
            @click="goHome"
            class="flex items-center gap-3"
          >
            <div
              class="w-8 h-8 rounded-lg
                     bg-[#1E325A] text-white
                     flex items-center justify-center
                     font-bold text-sm"
            >
              S
            </div>

            <span
              class="font-semibold"
            >
              SmartProp
            </span>
          </button>

          <span
            class="hidden sm:block text-gray-300"
          >
            •
          </span>

          <button
            @click="goHome"
            class="hidden sm:block
                   text-xs text-gray-500
                   hover:text-[#1E325A]
                   transition"
          >
            ‹ Trang chủ
          </button>
        </div>

        <!-- RIGHT -->

        <div
          class="flex items-center gap-3"
        >
          <button
            @click="goPost"
            class="hidden sm:block
                   px-5 py-2
                   bg-white
                   border border-gray-200
                   rounded-full
                   text-xs text-gray-500
                   hover:bg-gray-50
                   transition"
          >
            Đăng tin
          </button>

          <button
            @click="goAccount"
            class="px-5 py-2
                   bg-[#1E325A]
                   text-white
                   rounded-full
                   text-xs
                   hover:bg-[#263f70]
                   transition"
          >
            Tài khoản
          </button>
        </div>

      </div>
    </header>

    <!-- ========================================== -->
    <!-- PAGE -->
    <!-- ========================================== -->

    <main
      class="max-w-[1180px] mx-auto
             px-6 md:px-8
             pt-10 pb-20"
    >

      <!-- TITLE -->

      <section>
        <h1
          class="text-3xl md:text-[34px]
                 font-medium tracking-tight"
        >
          Báo cáo của tôi
        </h1>

        <p
          class="text-xs text-gray-400 mt-2"
        >
          {{ reports.length }} báo cáo đã gửi ·
          {{ processingCount }} đang xử lý
        </p>
      </section>

      <!-- ========================================== -->
      <!-- FILTER -->
      <!-- ========================================== -->

      <section
        class="mt-7 flex flex-wrap gap-2"
      >
        <button
          v-for="filter in filters"
          :key="filter.key"
          type="button"
          @click="activeFilter = filter.key"
          class="px-5 py-2.5
                 rounded-full
                 border
                 text-[11px]
                 transition-all duration-200"
          :class="
            activeFilter === filter.key
              ? 'bg-[#1E325A] border-[#1E325A] text-white shadow-sm'
              : 'bg-white/70 border-gray-200 text-gray-500 hover:border-[#1E325A]/30 hover:text-[#1E325A]'
          "
        >
          {{ filter.label }} ·
          {{ getFilterCount(filter.key) }}
        </button>
      </section>

      <!-- ========================================== -->
      <!-- REPORT LIST -->
      <!-- ========================================== -->

      <section
        class="mt-6 bg-white/70
               rounded-[24px]
               shadow-sm
               overflow-hidden"
      >

        <!-- REPORT ITEM -->

        <article
          v-for="(report, index) in filteredReports"
          :key="report.id"
          class="relative
                 flex flex-col md:flex-row
                 md:items-center
                 gap-4 md:gap-5
                 p-5 md:p-6"
          :class="
            index !== filteredReports.length - 1
              ? 'border-b border-[#1E325A]/15'
              : ''
          "
        >

          <!-- IMAGE -->

          <div
            class="w-full md:w-[115px]
                   h-[150px] md:h-[82px]
                   shrink-0
                   rounded-[14px]
                   overflow-hidden
                   bg-[#d8d6cf]"
          >
            <img
              :src="report.image"
              :alt="report.title"
              class="w-full h-full object-cover"
            />
          </div>

          <!-- ====================================== -->
          <!-- INFORMATION -->
          <!-- ====================================== -->

          <div
            class="flex-1 min-w-0"
          >
            <h2
              class="text-[13px]
                     font-semibold
                     text-[#1E325A]
                     truncate"
            >
              {{ report.title }}
            </h2>

            <p
              class="text-[10px]
                     text-gray-400
                     mt-1"
            >
              {{ report.location }}
            </p>

            <!-- REASON -->

            <div
              class="mt-2.5"
            >
              <span
                class="inline-flex
                       px-2.5 py-1
                       rounded-full
                       text-[8px]
                       font-semibold
                       tracking-wide"
                :class="[
                  report.status === 'processing'
                    ? 'bg-[#f2dfd3] text-[#b6603d]'
                    : '',

                  report.status === 'resolved'
                    ? 'bg-[#e5f3ea] text-[#438665]'
                    : '',

                  report.status === 'rejected'
                    ? 'bg-[#eeeeec] text-gray-500'
                    : ''
                ]"
              >
                {{ report.reason }}
              </span>
            </div>

            <!-- SENT -->

            <p
              class="text-[9px]
                     text-gray-400
                     mt-2"
            >
              {{ report.sentAt }}
            </p>

            <!-- RESULT -->

            <p
              v-if="report.result"
              class="text-[10px]
                     mt-2
                     leading-5"
              :class="
                report.status === 'resolved'
                  ? 'text-[#438665]'
                  : 'text-gray-500'
              "
            >
              {{ report.result }}
            </p>
          </div>

          <!-- ====================================== -->
          <!-- STATUS -->
          <!-- ====================================== -->

          <div
            class="md:w-[180px]
                   shrink-0
                   flex md:flex-col
                   items-start md:items-end
                   justify-between md:justify-center
                   gap-2"
          >

            <!-- STATUS BADGE -->

            <span
              class="inline-flex
                     px-3.5 py-1.5
                     rounded-full
                     text-[9px]
                     font-medium"
              :class="[
                report.status === 'processing'
                  ? 'bg-[#f2dfd3] text-[#b6603d]'
                  : '',

                report.status === 'resolved'
                  ? 'bg-[#e5f3ea] text-[#438665]'
                  : '',

                report.status === 'rejected'
                  ? 'bg-[#ececea] text-gray-500'
                  : ''
              ]"
            >
              {{ report.statusLabel }}
            </span>

            <!-- UPDATE -->

            <p
              class="text-[9px]
                     text-gray-400
                     md:text-right"
            >
              {{ report.update }}
            </p>
          </div>

        </article>

        <!-- ====================================== -->
        <!-- EMPTY -->
        <!-- ====================================== -->

        <div
          v-if="filteredReports.length === 0"
          class="py-20 text-center"
        >
          <div
            class="w-12 h-12
                   rounded-full
                   bg-[#1E325A]/10
                   flex items-center
                   justify-center
                   mx-auto"
          >
            ⚑
          </div>

          <h3
            class="text-sm font-medium mt-4"
          >
            Không có báo cáo
          </h3>

          <p
            class="text-[10px]
                   text-gray-400
                   mt-2"
          >
            Không có báo cáo nào thuộc trạng thái này.
          </p>
        </div>

      </section>

      <!-- ========================================== -->
      <!-- FOOT NOTE -->
      <!-- ========================================== -->

      <section
        class="mt-5
               flex items-start gap-3
               bg-white/40
               rounded-[18px]
               px-5 py-4"
      >
        <div
          class="w-7 h-7
                 rounded-full
                 bg-[#1E325A]/10
                 flex items-center
                 justify-center
                 text-xs
                 shrink-0"
        >
          i
        </div>

        <p
          class="text-[10px]
                 text-gray-500
                 leading-5"
        >
          Báo cáo thường được xem xét trong vòng 24–48 giờ.
          Bạn sẽ nhận được thông báo khi trạng thái báo cáo
          thay đổi.
        </p>
      </section>

    </main>
  </div>
</template>