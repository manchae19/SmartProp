<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const activeFilter = ref('all')

const filters = [
  { id: 'all', label: 'Tất cả', count: 6 },
  { id: 'showing', label: 'Đang hiển thị', count: 3 },
  { id: 'pending', label: 'Chờ duyệt', count: 2 },
  { id: 'rejected', label: 'Bị từ chối', count: 1 },
  { id: 'expired', label: 'Hết hạn', count: 0 },
]

const listings = [
  {
    id: 1,
    image: '/div12.png',
    title: 'Nhà 3 tầng hẻm xe hơi, gần cầu Rồng',
    location: 'Hải Châu, Đà Nẵng',
    info: '92 m² · 3 PN · 2 WC · Bán',
    status: 'showing',
    statusText: 'Đang hiển thị',
    views: '1.240',
    saves: '6',
    price: '4,85 tỷ',
  },
  {
    id: 2,
    image: '/div18.png',
    title: 'Căn hộ Studio gần Đại học Duy Tân',
    location: 'Hải Châu, Đà Nẵng',
    info: '32 m² · Studio · 1 WC · Cho thuê',
    status: 'showing',
    statusText: 'Đang hiển thị',
    views: '582',
    saves: '3',
    price: '6,5 tr/th',
  },
  {
    id: 3,
    image: '/div24.png',
    title: 'Đất nền Hoà Xuân, sổ đỏ riêng',
    location: 'Cẩm Lệ, Đà Nẵng',
    info: '100 m² · Đất nền · Bán',
    status: 'showing',
    statusText: 'Đang hiển thị',
    views: '310',
    saves: '2',
    price: '2,95 tỷ',
  },
  {
    id: 4,
    image: '/div30.png',
    title: 'Đất nền mặt tiền đường Nguyễn Tất Thành',
    location: 'Thanh Khê, Đà Nẵng',
    info: '150 m² · Đất nền · Bán',
    status: 'pending',
    statusText: 'Chờ duyệt',
    statusSub: 'gửi 2 giờ trước',
    views: null,
    saves: null,
    price: '6,3 tỷ',
  },
  {
    id: 5,
    image: '/div37.png',
    title: 'Nhà phố 2 mặt tiền gần chợ Cồn',
    location: 'Hải Châu, Đà Nẵng',
    info: '130 m² · 4 PN · 3 WC · Bán',
    status: 'pending',
    statusText: 'Chờ duyệt',
    statusSub: 'gửi hôm qua',
    views: null,
    saves: null,
    price: '8,1 tỷ',
  },
  {
    id: 6,
    image: '/div44.png',
    title: 'Villa sân vườn Điện Ngọc, sổ hồng riêng',
    location: 'Ngũ Hành Sơn, Đà Nẵng',
    info: '220 m² · 5 PN · 4 WC · Bán',
    status: 'rejected',
    statusText: 'Bị từ chối',
    statusSub: 'nghi ngờ ảnh giả mạo',
    views: null,
    saves: null,
    price: '9,8 tỷ',
  },
]

const filteredListings = computed(() => {
  if (activeFilter.value === 'all') return listings

  return listings.filter(
    (listing) => listing.status === activeFilter.value
  )
})

const statusClass = (status) => {
  if (status === 'showing') {
    return 'bg-[#e8f5ee] text-[#2f8f62]'
  }

  if (status === 'pending') {
    return 'bg-[#fff4dc] text-[#b7791f]'
  }

  if (status === 'rejected') {
    return 'bg-[#fde9e5] text-[#c65d45]'
  }

  return 'bg-gray-100 text-gray-500'
}

const goHome = () => {
  router.push('/home')
}

const goAccount = () => {
  router.push('/account')
}

const createPost = () => {
  router.push('/post')
}
</script>

<template>
  <div class="min-h-screen bg-[#ebe9e2] text-[#1E325A]">

    <!-- ================= HEADER ================= -->
    <header
      class="max-w-[1400px] mx-auto px-6 md:px-10 pt-5"
    >
      <div
        class="flex items-center justify-between border-b border-[#1E325A]/50 pb-4"
      >
        <!-- LEFT -->
        <div class="flex items-center gap-5">
          <!-- Logo -->
          <button
            @click="goHome"
            class="flex items-center gap-2.5"
          >
            <div
              class="w-7 h-7 rounded-lg bg-[#1E325A] text-white flex items-center justify-center text-xs font-bold"
            >
              S
            </div>

            <span class="font-semibold text-sm text-[#1E325A]">
              SmartProp
            </span>
          </button>

          <span class="text-gray-300">•</span>

          <button
            @click="goHome"
            class="text-xs text-gray-500 hover:text-[#1E325A] transition"
          >
            ‹ Trang chủ
          </button>
        </div>

        <!-- RIGHT -->
        <button
          @click="goAccount"
          class="px-5 py-2 rounded-full bg-[#1E325A] text-white text-xs font-medium hover:opacity-90 transition"
        >
          Tài khoản
        </button>
      </div>
    </header>


    <!-- ================= MAIN ================= -->
    <main
      class="max-w-[1400px] mx-auto px-6 md:px-10 pt-8 pb-16"
    >

      <!-- TITLE -->
      <section
        class="flex flex-col sm:flex-row sm:items-center justify-between gap-5"
      >
        <div>
          <h1
            class="text-2xl md:text-3xl font-medium tracking-tight text-[#1E325A]"
          >
            Tin đăng của tôi
          </h1>

          <p class="text-xs text-gray-400 mt-1.5">
            6 tin đăng · 2 đang chờ duyệt
          </p>
        </div>

        <button
          @click="createPost"
          class="bg-[#1E325A] text-white px-5 py-2.5 rounded-full text-xs font-medium hover:opacity-90 transition shadow-sm"
        >
          + Đăng tin mới
        </button>
      </section>


      <!-- ================= FILTER ================= -->
      <section
        class="flex flex-wrap gap-2 mt-7 mb-6"
      >
        <button
          v-for="filter in filters"
          :key="filter.id"
          @click="activeFilter = filter.id"
          class="px-4 py-2 rounded-full border text-xs transition"
          :class="
            activeFilter === filter.id
              ? 'bg-[#1E325A] border-[#1E325A] text-white'
              : 'bg-white border-gray-200 text-gray-500 hover:border-[#1E325A] hover:text-[#1E325A]'
          "
        >
          {{ filter.label }} · {{ filter.count }}
        </button>
      </section>


      <!-- ================= LIST ================= -->
      <section class="space-y-3">

        <article
          v-for="listing in filteredListings"
          :key="listing.id"
          class="bg-white rounded-[20px] px-4 py-4 md:px-5 md:py-4 shadow-sm border border-black/[0.03]"
        >

          <div
            class="grid grid-cols-1 md:grid-cols-[180px_1fr_180px_120px_160px] gap-5 md:items-center"
          >

            <!-- IMAGE -->
            <div
              class="relative w-full h-[130px] rounded-[14px] overflow-hidden bg-[#e6e3da]"
            >
              <img
                :src="listing.image"
                :alt="listing.title"
                class="w-full h-full object-cover"
              />

              <!-- Mobile status -->
              <div
                class="absolute top-2 left-2 md:hidden px-3 py-1 rounded-full text-[10px] font-medium"
                :class="statusClass(listing.status)"
              >
                {{ listing.statusText }}
              </div>
            </div>


            <!-- INFO -->
            <div class="min-w-0">
              <h2
                class="text-[15px] font-semibold text-[#1E325A] mb-2"
              >
                {{ listing.title }}
              </h2>

              <p class="text-[11px] text-gray-400 mb-1.5">
                {{ listing.location }}
              </p>

              <p class="text-[11px] text-gray-500">
                {{ listing.info }}
              </p>
            </div>


            <!-- STATUS -->
            <div class="hidden md:block">
              <div
                class="inline-flex flex-col items-start px-3 py-1.5 rounded-full text-[10px]"
                :class="statusClass(listing.status)"
              >
                <span class="font-medium">
                  {{ listing.statusText }}
                </span>

                <span
                  v-if="listing.statusSub"
                  class="text-[9px] opacity-70 mt-0.5"
                >
                  {{ listing.statusSub }}
                </span>
              </div>
            </div>


            <!-- VIEWS -->
            <div>
              <template v-if="listing.views">
                <div
                  class="flex md:flex-col gap-5 md:gap-1"
                >
                  <div class="text-[11px] text-gray-400">
                    <span
                      class="font-semibold text-[#1E325A] text-sm mr-1"
                    >
                      {{ listing.views }}
                    </span>

                    lượt xem
                  </div>

                  <div class="text-[11px] text-gray-400">
                    <span
                      class="font-semibold text-[#1E325A] text-sm mr-1"
                    >
                      {{ listing.saves }}
                    </span>

                    lượt lưu
                  </div>
                </div>
              </template>

              <template v-else>
                <span class="text-gray-300 text-lg">
                  —
                </span>
              </template>
            </div>


            <!-- PRICE + ACTION -->
            <div
              class="md:text-right flex md:flex-col items-center md:items-end justify-between gap-3"
            >
              <div
                class="text-lg font-semibold text-[#1E325A]"
              >
                {{ listing.price }}
              </div>

              <div
                class="flex items-center justify-end gap-2"
              >
                <!-- VIEW -->
                <button
                  class="px-4 py-2 rounded-full border border-gray-200 bg-white text-[11px] text-[#1E325A] hover:bg-gray-50 transition"
                >
                  Xem
                </button>

                <!-- EDIT -->
                <button
                  v-if="listing.status !== 'rejected'"
                  class="px-4 py-2 rounded-full bg-[#1E325A] text-white text-[11px] hover:opacity-90 transition"
                >
                  Sửa
                </button>

                <!-- REJECTED -->
                <button
                  v-else
                  class="px-4 py-2 rounded-full bg-[#c9653d] text-white text-[11px] whitespace-nowrap hover:opacity-90 transition"
                >
                  Sửa & gửi lại
                </button>
              </div>
            </div>

          </div>
        </article>


        <!-- EMPTY -->
        <div
          v-if="filteredListings.length === 0"
          class="bg-white rounded-[20px] py-16 text-center border border-gray-100"
        >
          <div
            class="w-12 h-12 mx-auto rounded-full bg-[#1E325A]/10 flex items-center justify-center mb-3 text-[#1E325A]"
          >
            ⌂
          </div>

          <p class="font-medium text-[#1E325A]">
            Chưa có tin đăng
          </p>

          <p class="text-xs text-gray-400 mt-1">
            Hiện chưa có tin đăng thuộc trạng thái này.
          </p>
        </div>

      </section>
    </main>
  </div>
</template>