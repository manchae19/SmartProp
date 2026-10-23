
<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// SMARTPROP MY LISTINGS 2.0
// Dữ liệu minh họa, chưa kết nối backend.

const activeFilter = ref('all')
const searchText = ref('')
const selectedListing = ref(null)
const showEditNotice = ref(false)

const listings = [
  {
    id: 1,
    image: 'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=900&q=85',
    title: 'Nhà 3 tầng hẻm xe hơi, gần cầu Rồng',
    location: 'Hải Châu, Đà Nẵng',
    info: '92 m² · 3 PN · 2 WC · Bán',
    status: 'showing',
    statusText: 'Đang hiển thị',
    views: '1.240',
    saves: '6',
    price: '4,85 tỷ',
    priceUnit: 'VNĐ'
  },
  {
    id: 2,
    image: 'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=900&q=85',
    title: 'Căn hộ Studio gần Đại học Duy Tân',
    location: 'Hải Châu, Đà Nẵng',
    info: '32 m² · Studio · 1 WC · Cho thuê',
    status: 'showing',
    statusText: 'Đang hiển thị',
    views: '582',
    saves: '3',
    price: '6,5 tr/th',
    priceUnit: 'VNĐ'
  },
  {
    id: 3,
    image: 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=900&q=85',
    title: 'Đất nền Hoà Xuân, sổ đỏ riêng',
    location: 'Cẩm Lệ, Đà Nẵng',
    info: '100 m² · Đất nền · Bán',
    status: 'showing',
    statusText: 'Đang hiển thị',
    views: '310',
    saves: '2',
    price: '2,95 tỷ',
    priceUnit: 'VNĐ'
  },
  {
    id: 4,
    image: 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=900&q=85',
    title: 'Đất nền mặt tiền đường Nguyễn Tất Thành',
    location: 'Thanh Khê, Đà Nẵng',
    info: '150 m² · Đất nền · Bán',
    status: 'pending',
    statusText: 'Chờ duyệt',
    statusSub: 'Gửi 2 giờ trước',
    views: null,
    saves: null,
    price: '6,3 tỷ',
    priceUnit: 'VNĐ'
  },
  {
    id: 5,
    image: 'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=900&q=85',
    title: 'Nhà phố 2 mặt tiền gần chợ Cồn',
    location: 'Hải Châu, Đà Nẵng',
    info: '130 m² · 4 PN · 3 WC · Bán',
    status: 'pending',
    statusText: 'Chờ duyệt',
    statusSub: 'Gửi hôm qua',
    views: null,
    saves: null,
    price: '8,1 tỷ',
    priceUnit: 'VNĐ'
  },
  {
    id: 6,
    image: 'https://images.unsplash.com/photo-1613977257363-707ba9348227?auto=format&fit=crop&w=900&q=85',
    title: 'Villa sân vườn Điện Ngọc, sổ hồng riêng',
    location: 'Ngũ Hành Sơn, Đà Nẵng',
    info: '220 m² · 5 PN · 4 WC · Bán',
    status: 'rejected',
    statusText: 'Bị từ chối',
    statusSub: 'Nghi ngờ ảnh giả mạo',
    views: null,
    saves: null,
    price: '9,8 tỷ',
    priceUnit: 'VNĐ'
  }
]

const filters = computed(() => [
  { id: 'all', label: 'Tất cả', count: listings.length },
  {
    id: 'showing',
    label: 'Đang hiển thị',
    count: listings.filter(x => x.status === 'showing').length
  },
  {
    id: 'pending',
    label: 'Chờ duyệt',
    count: listings.filter(x => x.status === 'pending').length
  },
  {
    id: 'rejected',
    label: 'Bị từ chối',
    count: listings.filter(x => x.status === 'rejected').length
  },
  {
    id: 'expired',
    label: 'Hết hạn',
    count: listings.filter(x => x.status === 'expired').length
  }
])

const filteredListings = computed(() => {
  const keyword = searchText.value.trim().toLocaleLowerCase('vi-VN')

  return listings.filter(item => {
    const matchesStatus =
      activeFilter.value === 'all' ||
      item.status === activeFilter.value

    const matchesSearch =
      !keyword ||
      `${item.title} ${item.location} ${item.info}`
        .toLocaleLowerCase('vi-VN')
        .includes(keyword)

    return matchesStatus && matchesSearch
  })
})

const totalViews = computed(() =>
  listings.reduce((total, item) => {
    return total + Number((item.views || '0').replace(/\./g, ''))
  }, 0).toLocaleString('vi-VN')
)

const totalSaves = computed(() =>
  listings.reduce((total, item) => total + Number(item.saves || 0), 0)
)

function statusClass(status) {
  if (status === 'showing') {
    return 'bg-[#E5F4EB] text-[#287B56]'
  }
  if (status === 'pending') {
    return 'bg-[#FFF1D9] text-[#A36A19]'
  }
  if (status === 'rejected') {
    return 'bg-[#FCE8E3] text-[#BD5D48]'
  }
  return 'bg-[#EDF0F3] text-[#64748B]'
}

function openListing(item) {
  selectedListing.value = item
}

function closeListing() {
  selectedListing.value = null
}

function goToDetail(item) {
  // Chỉ các ID 1, 2, 3 có route chi tiết đã biết.
  if ([1, 2, 3].includes(item.id)) {
    router.push(`/listing/${item.id}`)
  }
}

function editListing(item) {
  selectedListing.value = item
  showEditNotice.value = true
}

function closeEditNotice() {
  showEditNotice.value = false
  selectedListing.value = null
}

function goHome() {
  router.push('/home')
}

function goMap() {
  router.push('/map')
}

function goPost() {
  router.push('/post')
}

function goAccount() {
  router.push('/account')
}
</script>

<template>
  <div class="sp-my-listings min-h-screen bg-[#F7F5F0] text-[#142B4F]">

    <!-- HEADER -->
    <header class="border-b border-[#E7E2D8] bg-[#F7F5F0]">
      <div class="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-4 px-5 py-5 md:px-10">
        <div class="flex items-center gap-5">
          <button @click="goHome" class="flex items-center gap-3">
            <span class="flex h-10 w-10 items-center justify-center rounded-full bg-[#142B4F] font-bold text-white">
              S
            </span>
            <span class="text-xl font-bold">
              SmartProp<span class="text-[#C6A77A]">.</span>
            </span>
          </button>

          <button @click="goHome" class="hidden text-xs text-[#8290A0] hover:text-[#142B4F] sm:block">
            ← Trang chủ
          </button>
        </div>

        <div class="flex items-center gap-2">
          <button @click="goMap" class="hidden rounded-full border border-[#E4DED3] bg-white px-5 py-3 text-xs font-semibold hover:border-[#C6A77A] sm:block">
            GIS Explorer ↗
          </button>

          <button @click="goAccount" class="rounded-full bg-[#142B4F] px-5 py-3 text-xs font-semibold text-white hover:bg-[#25466B]">
            Tài khoản
          </button>
        </div>
      </div>
    </header>

    <!-- PAGE INTRO -->
    <section class="relative overflow-hidden border-b border-[#E7E2D8]">
      <div class="pointer-events-none absolute -right-28 -top-32 h-[420px] w-[420px] rounded-full border border-[#C6A77A]/20"></div>
      <div class="pointer-events-none absolute -right-10 -top-12 h-[280px] w-[280px] rounded-full border border-[#C6A77A]/20"></div>

      <div class="relative mx-auto max-w-[1440px] px-5 py-12 md:px-10 md:py-16">
        <div class="flex flex-wrap items-end justify-between gap-8">
          <div>
            <div class="flex items-center gap-3">
              <span class="h-px w-9 bg-[#B49362]"></span>
              <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-[#B49362]">
                SMARTPROP / PROPERTY MANAGEMENT
              </p>
            </div>

            <h1 class="mt-6 text-[41px] font-medium leading-tight tracking-tight sm:text-[58px]">
              Quản lý
              <span class="block italic text-[#B49362]">bất động sản của bạn.</span>
            </h1>

            <p class="mt-5 max-w-xl text-sm leading-7 text-[#7B8798]">
              Theo dõi trạng thái tin đăng, lượt quan tâm và quản lý danh mục
              bất động sản của bạn trong một không gian trực quan.
            </p>

            <span class="mt-5 inline-flex rounded-full border border-[#E2D8C8] bg-[#EEE7DB] px-4 py-2 text-[11px] font-bold uppercase tracking-widest text-[#94774F]">
              Dữ liệu minh họa
            </span>
          </div>

          <button
            @click="goPost"
            class="rounded-full bg-[#142B4F] px-7 py-4 text-xs font-bold text-white shadow-lg transition hover:-translate-y-0.5 hover:bg-[#25466B]"
          >
            + Đăng bất động sản mới ↗
          </button>
        </div>
      </div>
    </section>

    <!-- STATS -->
    <section class="mx-auto max-w-[1440px] px-5 pt-10 md:px-10">
      <div class="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-5">
        <div class="rounded-[20px] border border-[#E8E3DA] bg-white p-5 sm:p-7">
          <p class="text-[11px] font-bold uppercase tracking-widest text-[#8D99A8]">
            Tổng tin đăng
          </p>
          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ listings.length }}</span>
            <span class="text-xl text-[#C6A77A]">⌂</span>
          </div>
          <p class="mt-3 text-[12px] text-[#8D99A8]">Danh mục của bạn</p>
        </div>

        <div class="rounded-[20px] bg-[#142B4F] p-5 text-white sm:p-7">
          <p class="text-[11px] font-bold uppercase tracking-widest text-white/60">
            Đang hiển thị
          </p>
          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">
              {{ listings.filter(x => x.status === 'showing').length }}
            </span>
            <span class="h-3 w-3 rounded-full bg-[#7BD4B0]"></span>
          </div>
          <p class="mt-3 text-[12px] text-white/55">Tin đang hoạt động</p>
        </div>

        <div class="rounded-[20px] border border-[#E8E3DA] bg-white p-5 sm:p-7">
          <p class="text-[11px] font-bold uppercase tracking-widest text-[#8D99A8]">
            Tổng lượt xem
          </p>
          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ totalViews }}</span>
            <span class="text-xl text-[#C6A77A]">↗</span>
          </div>
          <p class="mt-3 text-[12px] text-[#8D99A8]">Tương tác minh họa</p>
        </div>

        <div class="rounded-[20px] border border-[#E8E3DA] bg-white p-5 sm:p-7">
          <p class="text-[11px] font-bold uppercase tracking-widest text-[#8D99A8]">
            Lượt lưu tin
          </p>
          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ totalSaves }}</span>
            <span class="text-xl text-[#C6A77A]">♡</span>
          </div>
          <p class="mt-3 text-[12px] text-[#8D99A8]">Người dùng quan tâm</p>
        </div>
      </div>
    </section>

    <!-- MANAGEMENT -->
    <main class="mx-auto max-w-[1440px] px-5 pb-20 pt-12 md:px-10">

      <div class="flex flex-wrap items-end justify-between gap-5">
        <div>
          <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[#B49362]">
            YOUR COLLECTION / 01
          </p>
          <h2 class="mt-3 text-3xl font-medium tracking-tight sm:text-4xl">
            Danh sách <span class="italic text-[#B49362]">tin đăng.</span>
          </h2>
          <p class="mt-3 text-xs text-[#87919F]">
            Quản lý và theo dõi các bất động sản đã đăng.
          </p>
        </div>

        <div class="flex w-full items-center gap-3 rounded-xl border border-[#E4DED3] bg-white px-4 sm:w-[300px]">
          <span class="text-[#B49362]">⌕</span>
          <input
            v-model="searchText"
            type="search"
            placeholder="Tìm tin đăng hoặc khu vực..."
            aria-label="Tìm tin đăng"
            class="h-12 min-w-0 w-full bg-transparent text-xs outline-none"
          />
        </div>
      </div>

      <!-- FILTERS -->
      <div class="mt-8 flex flex-wrap gap-2">
        <button
          v-for="filter in filters"
          :key="filter.id"
          @click="activeFilter = filter.id"
          class="rounded-full border px-4 py-2.5 text-[12px] font-semibold transition sm:px-5"
          :class="activeFilter === filter.id
            ? 'border-[#142B4F] bg-[#142B4F] text-white'
            : 'border-[#E4DED3] bg-white text-[#64748B] hover:border-[#C6A77A]'"
        >
          {{ filter.label }}
          <span class="ml-1 opacity-65">{{ filter.count }}</span>
        </button>
      </div>

      <div class="mb-5 mt-7 flex items-center justify-between gap-4">
        <p class="text-xs text-[#87919F]">
          Hiển thị <strong class="text-[#142B4F]">{{ filteredListings.length }}</strong> tin đăng
        </p>
        <span class="text-[11px] uppercase tracking-widest text-[#B49362]">
          PROPERTY PORTFOLIO
        </span>
      </div>

      <!-- LISTINGS -->
      <div v-if="filteredListings.length" class="space-y-5">
        <article
          v-for="listing in filteredListings"
          :key="listing.id"
          class="group grid min-w-0 overflow-hidden rounded-[22px] border border-[#E8E3DA] bg-white transition duration-300 hover:border-[#C6A77A] hover:shadow-[0_16px_45px_rgba(20,43,79,0.08)] lg:grid-cols-[245px_minmax(0,1fr)_230px]"
        >
          <!-- IMAGE -->
          <div class="relative h-[230px] overflow-hidden bg-[#E7E2D8] lg:h-full lg:min-h-[220px]">
            <img
              :src="listing.image"
              :alt="`Ảnh minh họa: ${listing.title}`"
              loading="lazy"
              class="h-full w-full object-cover transition duration-700 group-hover:scale-105"
            />

            <div class="absolute inset-0 bg-gradient-to-t from-[#142B4F]/45 to-transparent"></div>

            <span class="absolute bottom-4 left-4 text-[11px] font-bold uppercase tracking-[0.15em] text-white">
              {{ listing.location }}
            </span>
          </div>

          <!-- INFORMATION -->
          <div class="flex min-w-0 flex-col justify-center p-5 sm:p-7">
            <div class="flex flex-wrap items-center gap-3">
              <span
                class="rounded-full px-3 py-1.5 text-[11px] font-bold"
                :class="statusClass(listing.status)"
              >
                {{ listing.statusText }}
              </span>

              <span v-if="listing.statusSub" class="text-[11px] text-[#9AA4B1]">
                {{ listing.statusSub }}
              </span>
            </div>

            <h3 class="mt-4 text-lg font-semibold leading-7 sm:text-xl">
              {{ listing.title }}
            </h3>

            <p class="mt-2 text-xs text-[#87919F]">
              ⌖ {{ listing.location }}
            </p>

            <p class="mt-3 text-xs leading-6 text-[#64748B]">
              {{ listing.info }}
            </p>

            <div class="mt-5 flex flex-wrap gap-5 border-t border-[#EEEAE3] pt-4">
              <template v-if="listing.views !== null">
                <span class="text-xs text-[#87919F]">
                  <strong class="mr-1 text-sm text-[#142B4F]">{{ listing.views }}</strong>
                  lượt xem
                </span>

                <span class="text-xs text-[#87919F]">
                  <strong class="mr-1 text-sm text-[#142B4F]">{{ listing.saves }}</strong>
                  lượt lưu
                </span>
              </template>

              <span v-else class="text-[12px] text-[#9AA4B1]">
                Chưa có thống kê tương tác
              </span>
            </div>
          </div>

          <!-- ACTIONS -->
          <div class="flex flex-col justify-between gap-6 border-t border-[#EEEAE3] p-5 sm:p-7 lg:border-l lg:border-t-0">
            <div class="lg:text-right">
              <p class="text-[11px] uppercase tracking-widest text-[#9AA4B1]">
                Giá đăng
              </p>
              <p class="mt-2 text-[27px] font-semibold tracking-tight">
                {{ listing.price }}
              </p>
              <p class="mt-1 text-[11px] text-[#B49362]">
                {{ listing.priceUnit }}
              </p>
            </div>

            <div class="flex flex-wrap gap-2 lg:justify-end">
              <button
                @click="openListing(listing)"
                class="rounded-full border border-[#E4DED3] bg-white px-5 py-3 text-[12px] font-semibold transition hover:border-[#C6A77A]"
              >
                Xem
              </button>

              <button
                @click="editListing(listing)"
                class="rounded-full px-5 py-3 text-[12px] font-semibold text-white transition hover:opacity-90"
                :class="listing.status === 'rejected'
                  ? 'bg-[#BD6A4C]'
                  : 'bg-[#142B4F]'"
              >
                {{ listing.status === 'rejected' ? 'Sửa & gửi lại' : 'Sửa tin' }}
              </button>
            </div>
          </div>
        </article>
      </div>

      <!-- EMPTY -->
      <div v-else class="rounded-[24px] border border-[#E8E3DA] bg-white px-6 py-20 text-center">
        <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[#F7F5F0] text-3xl text-[#B49362]">
          ⌕
        </div>

        <h3 class="mt-6 text-xl font-semibold">
          Không tìm thấy tin đăng
        </h3>

        <p class="mt-3 text-sm text-[#87919F]">
          Thử thay đổi trạng thái hoặc từ khóa tìm kiếm.
        </p>

        <button
          @click="activeFilter = 'all'; searchText = ''"
          class="mt-6 rounded-full bg-[#142B4F] px-6 py-3 text-xs font-semibold text-white"
        >
          Xem tất cả tin đăng
        </button>
      </div>

      <!-- CTA -->
      <section class="relative mt-14 overflow-hidden rounded-[25px] bg-[#142B4F] px-7 py-10 text-white sm:px-10">
        <div class="pointer-events-none absolute -right-12 -top-24 h-72 w-72 rounded-full border border-[#C6A77A]/20"></div>

        <div class="relative flex flex-wrap items-center justify-between gap-7">
          <div>
            <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[#7BD4E5]">
              SMARTPROP / YOUR NEXT LISTING
            </p>

            <h2 class="mt-4 text-3xl font-medium">
              Sẵn sàng cho <span class="italic text-[#C6A77A]">tin đăng tiếp theo?</span>
            </h2>

            <p class="mt-4 max-w-xl text-sm leading-7 text-white/60">
              Đăng tải bất động sản và tiếp tục xây dựng danh mục của bạn trên SmartProp.
            </p>
          </div>

          <button
            @click="goPost"
            class="rounded-full bg-[#C6A77A] px-7 py-4 text-xs font-bold text-[#142B4F] transition hover:bg-[#E1C394]"
          >
            + Tạo tin đăng mới ↗
          </button>
        </div>
      </section>

      <p class="mt-7 text-center text-[12px] leading-6 text-[#87919F]">
        Dữ liệu, hình ảnh và thống kê trong trang quản lý này chỉ mang tính minh họa.
      </p>
    </main>

    <!-- DETAIL MODAL -->
    <div
      v-if="selectedListing && !showEditNotice"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[#08172B]/70 p-4"
      @click.self="closeListing"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="listing-dialog-title"
        class="w-full max-w-xl overflow-hidden rounded-[24px] bg-white shadow-2xl"
      >
        <div class="relative h-[220px]">
          <img
            :src="selectedListing.image"
            :alt="selectedListing.title"
            class="h-full w-full object-cover"
          />

          <button
            @click="closeListing"
            aria-label="Đóng"
            class="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full bg-white text-[#142B4F]"
          >
            ✕
          </button>
        </div>

        <div class="p-6 sm:p-8">
          <span
            class="rounded-full px-3 py-1.5 text-[11px] font-semibold"
            :class="statusClass(selectedListing.status)"
          >
            {{ selectedListing.statusText }}
          </span>

          <h2 id="listing-dialog-title" class="mt-5 text-2xl font-semibold">
            {{ selectedListing.title }}
          </h2>

          <p class="mt-3 text-sm text-[#87919F]">
            {{ selectedListing.location }}
          </p>

          <p class="mt-3 text-sm text-[#64748B]">
            {{ selectedListing.info }}
          </p>

          <p class="mt-6 text-2xl font-semibold">
            {{ selectedListing.price }}
          </p>

          <div class="mt-7 flex flex-wrap gap-3">
            <button
              v-if="[1, 2, 3].includes(selectedListing.id)"
              @click="goToDetail(selectedListing)"
              class="rounded-full bg-[#142B4F] px-6 py-3 text-xs font-semibold text-white"
            >
              Mở trang chi tiết ↗
            </button>

            <button
              @click="closeListing"
              class="rounded-full border border-[#E4DED3] px-6 py-3 text-xs font-semibold"
            >
              Đóng
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- EDIT NOTICE -->
    <div
      v-if="showEditNotice && selectedListing"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[#08172B]/70 p-4"
      @click.self="closeEditNotice"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-dialog-title"
        class="w-full max-w-md rounded-[24px] bg-white p-7 text-center shadow-2xl sm:p-9"
      >
        <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[#EEE7DB] text-2xl text-[#B49362]">
          ✎
        </div>

        <h2 id="edit-dialog-title" class="mt-5 text-2xl font-semibold">
          Chỉnh sửa tin đăng
        </h2>

        <p class="mt-4 text-sm leading-7 text-[#64748B]">
          Tin <strong>{{ selectedListing.title }}</strong> chưa có
          trang chỉnh sửa được kết nối. Chức năng này cần được
          xây dựng ở bước tiếp theo.
        </p>

        <button
          @click="closeEditNotice"
          class="mt-7 rounded-full bg-[#142B4F] px-8 py-3 text-xs font-semibold text-white"
        >
          Đã hiểu
        </button>
      </div>
    </div>

    <!-- FOOTER -->
    <footer class="border-t border-[#E7E2D8]">
      <div class="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-4 px-5 py-7 md:px-10">
        <button @click="goHome" class="text-lg font-bold">
          SmartProp<span class="text-[#C6A77A]">.</span>
        </button>

        <p class="text-[12px] text-[#87919F]">
          © 2026 SmartProp · My Listings 2.0
        </p>

        <button @click="goHome" class="text-xs text-[#64748B]">
          Về trang chủ ↗
        </button>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.sp-my-listings {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
  font-family: var(--font-sans);
  font-synthesis: none;
}

.sp-my-listings h1,
.sp-my-listings h2,
.sp-my-listings h3 {
  font-family: var(--font-sans);
  font-variant-ligatures: none;
  word-spacing: normal;
}

.sp-my-listings button,
.sp-my-listings input {
  font-family: inherit;
}

.sp-my-listings img {
  display: block;
}

@media (prefers-reduced-motion: reduce) {
  .sp-my-listings *,
  .sp-my-listings *::before,
  .sp-my-listings *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}
</style>
