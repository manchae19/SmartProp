<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const isFavorite = ref(false)

// ==================== IMAGE GALLERY ====================

const showGallery = ref(false)
const currentImageIndex = ref(0)

const images = [
  '/images/image0.png',
  '/images/image1.png',
  '/images/image2.png',
  '/images/image3.png'
]

const openGallery = (index = 0) => {
  currentImageIndex.value = index
  showGallery.value = true
  document.body.style.overflow = 'hidden'
}

const closeGallery = () => {
  showGallery.value = false
  document.body.style.overflow = ''
}

const nextImage = () => {
  currentImageIndex.value =
    (currentImageIndex.value + 1) % images.length
}

const prevImage = () => {
  currentImageIndex.value =
    (currentImageIndex.value - 1 + images.length) % images.length
}

const selectImage = (index) => {
  currentImageIndex.value = index
}

// ==================== LISTING DATA ====================

const listings = {
  1: {
    title: 'Nhà 3 tầng hẻm xe hơi, gần cầu Rồng',
    location: 'Hải Châu, Đà Nẵng',
    price: '4,85 tỷ đ',
    priceShort: '4,85 tỷ',
    type: 'Nhà phố',
    area: '92 m²',
    bedrooms: '3',
    bathrooms: '2',
    direction: 'Đông Nam',
    status: 'Ảnh trùng 94%',
    hasWarning: true,
    pricePerM2: '≈ 52,7 triệu/m²',
    valuation: '4,60 – 4,90 tỷ',
    description1:
      'Nhà 3 tầng nằm trong khu dân cư yên tĩnh tại Hải Châu, đường trước nhà rộng, ô tô có thể di chuyển thuận tiện. Vị trí gần cầu Rồng, trung tâm thành phố và nhiều tiện ích xung quanh.',
    description2:
      'Nhà gồm phòng khách, bếp, 3 phòng ngủ, 2 phòng tắm và khu vực ban công thoáng mát. Phù hợp để ở lâu dài hoặc đầu tư cho thuê.',
  },

  2: {
    title: 'Căn hộ 2PN view sông Hàn',
    location: 'Hải Châu, Đà Nẵng',
    price: '3,20 tỷ đ',
    priceShort: '3,20 tỷ',
    type: 'Căn hộ',
    area: '68 m²',
    bedrooms: '2',
    bathrooms: '2',
    direction: 'Đông',
    status: 'Không cảnh báo',
    hasWarning: false,
    pricePerM2: '≈ 47,1 triệu/m²',
    valuation: '3,00 – 3,35 tỷ',
    description1:
      'Căn hộ nằm tại khu vực Hải Châu, Đà Nẵng, có vị trí thuận tiện và tầm nhìn hướng về sông Hàn.',
    description2:
      'Căn hộ gồm 2 phòng ngủ, 2 phòng tắm và không gian sinh hoạt thoáng. Phù hợp để ở hoặc đầu tư cho thuê.',
  },

  3: {
    title: 'Đất nền Hoà Xuân, sổ đỏ riêng',
    location: 'Cẩm Lệ, Đà Nẵng',
    price: '2,95 tỷ đ',
    priceShort: '2,95 tỷ',
    type: 'Đất nền',
    area: '100 m²',
    bedrooms: '—',
    bathrooms: '—',
    direction: '—',
    status: 'Không cảnh báo',
    hasWarning: false,
    pricePerM2: '≈ 29,5 triệu/m²',
    valuation: '2,80 – 3,10 tỷ',
    description1:
      'Đất nền tại khu vực Hoà Xuân, Cẩm Lệ, Đà Nẵng. Khu vực dân cư phát triển, giao thông thuận tiện.',
    description2:
      'Diện tích 100 m², sổ đỏ riêng. Phù hợp xây nhà ở lâu dài hoặc đầu tư.',
  },
}

const listing = computed(() => {
  return listings[route.params.id] || listings[1]
})

const listingId = computed(() => route.params.id || '1')

const toggleFavorite = () => {
  isFavorite.value = !isFavorite.value
}

const goHome = () => router.push('/home')
const goMap = () => router.push('/map')
const goAccount = () => router.push('/account')
</script>

<template>
  <div class="min-h-screen bg-[#ebe9e2] text-[#1E325A]">

    <!-- ==================== HEADER ==================== -->

    <header class="max-w-[1400px] mx-auto px-6 md:px-10 pt-5">
      <div
        class="flex items-center justify-between border-b border-[#1E325A]/50 pb-4"
      >
        <button
          @click="goHome"
          class="flex items-center gap-2.5"
        >
          <div
            class="w-7 h-7 rounded-lg bg-[#1E325A] text-white flex items-center justify-center text-xs font-bold"
          >
            S
          </div>

          <span class="font-semibold text-sm">
            SmartProp
          </span>
        </button>

        <div class="flex items-center gap-2">
          <button
            @click="goMap"
            class="px-5 py-2 rounded-full bg-white border border-gray-200 text-xs text-gray-500 hover:text-[#1E325A] transition"
          >
            Xem bản đồ
          </button>

          <button
            @click="goAccount"
            class="px-5 py-2 rounded-full bg-[#1E325A] text-white text-xs hover:opacity-90 transition"
          >
            Tài khoản
          </button>
        </div>
      </div>
    </header>

    <!-- ==================== MAIN ==================== -->

    <main class="max-w-[1400px] mx-auto px-6 md:px-10 pt-6 pb-20">

      <!-- BACK -->

      <button
        @click="router.back()"
        class="text-xs text-gray-500 hover:text-[#1E325A] mb-5"
      >
        ← Quay lại
      </button>

      <!-- ==================== IMAGES ==================== -->

      <section
        class="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-3 h-auto lg:h-[430px]"
      >

        <!-- BIG IMAGE -->

        <div
          @click="openGallery(0)"
          class="relative min-h-[300px] lg:min-h-0 rounded-[24px] overflow-hidden bg-[#d9d6ce] cursor-pointer group"
        >
          <img
            :src="images[0]"
            :alt="listing.title"
            class="absolute inset-0 w-full h-full object-cover transition duration-300 group-hover:scale-[1.02]"
          />

          <!-- FAVORITE -->

          <button
            @click.stop="toggleFavorite"
            class="absolute top-4 right-4 w-10 h-10 rounded-full bg-white shadow flex items-center justify-center text-xl transition z-20"
            :class="isFavorite ? 'text-red-500' : 'text-[#1E325A]'"
          >
            {{ isFavorite ? '♥' : '♡' }}
          </button>
        </div>

        <!-- RIGHT IMAGES -->

        <div class="grid grid-cols-2 lg:grid-cols-1 gap-3">

          <!-- IMAGE 2 -->

          <div
            @click="openGallery(1)"
            class="relative min-h-[150px] rounded-[20px] bg-[#d9d6ce] overflow-hidden cursor-pointer group"
          >
            <img
              :src="images[1]"
              alt="Ảnh bất động sản"
              class="absolute inset-0 w-full h-full object-cover transition duration-300 group-hover:scale-105"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">

            <!-- IMAGE 3 -->

            <div
              @click="openGallery(2)"
              class="relative min-h-[150px] rounded-[20px] bg-[#d9d6ce] overflow-hidden cursor-pointer group"
            >
              <img
                :src="images[2]"
                alt="Ảnh bất động sản"
                class="absolute inset-0 w-full h-full object-cover transition duration-300 group-hover:scale-105"
              />
            </div>

            <!-- IMAGE 4 / VIEW ALL -->

            <div
              @click="openGallery(3)"
              class="relative min-h-[150px] rounded-[20px] bg-[#1E325A] overflow-hidden cursor-pointer group"
            >
              <img
                :src="images[3]"
                alt="Ảnh bất động sản"
                class="absolute inset-0 w-full h-full object-cover opacity-55 transition duration-300 group-hover:scale-105"
              />

              <div
                class="absolute inset-0 flex items-center justify-center bg-[#1E325A]/40"
              >
                <span class="text-white text-lg font-semibold">
                  +12 ảnh
                </span>
              </div>
            </div>

          </div>
        </div>
      </section>

      <!-- ==================== CONTENT ==================== -->

      <div
        class="grid grid-cols-1 lg:grid-cols-[1fr_330px] gap-6 mt-6 items-start"
      >

        <!-- LEFT -->

        <div class="space-y-5">

          <!-- MAIN INFO -->

          <section
            class="bg-white rounded-[24px] p-6 md:p-8 shadow-sm"
          >
            <div
              class="flex flex-col md:flex-row md:items-start justify-between gap-5"
            >
              <div>

                <div
                  class="inline-flex px-3 py-1 rounded-full bg-[#e5f3ea] text-[#438665] text-[11px] mb-3"
                >
                  {{ listing.type }}
                </div>

                <h1
                  class="text-2xl md:text-3xl font-semibold tracking-tight text-[#1E325A]"
                >
                  {{ listing.title }}
                </h1>

                <p class="text-xs text-gray-400 mt-2">
                  {{ listing.location }}
                </p>
              </div>

              <div class="md:text-right">

                <p
                  class="text-2xl md:text-3xl font-semibold text-[#1E325A]"
                >
                  {{ listing.price }}
                </p>

                <p class="text-[11px] text-gray-400 mt-1">
                  {{ listing.pricePerM2 }}
                </p>

              </div>
            </div>

            <!-- SPECS -->

            <div
              class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-7 pt-6 border-t border-gray-100"
            >
              <div>
                <p class="text-[11px] text-gray-400">
                  Diện tích
                </p>

                <p class="text-sm font-semibold mt-1">
                  {{ listing.area }}
                </p>
              </div>

              <div>
                <p class="text-[11px] text-gray-400">
                  Phòng ngủ
                </p>

                <p class="text-sm font-semibold mt-1">
                  {{ listing.bedrooms }}
                  <span v-if="listing.bedrooms !== '—'">
                    PN
                  </span>
                </p>
              </div>

              <div>
                <p class="text-[11px] text-gray-400">
                  Phòng tắm
                </p>

                <p class="text-sm font-semibold mt-1">
                  {{ listing.bathrooms }}
                  <span v-if="listing.bathrooms !== '—'">
                    WC
                  </span>
                </p>
              </div>

              <div>
                <p class="text-[11px] text-gray-400">
                  Hướng
                </p>

                <p class="text-sm font-semibold mt-1">
                  {{ listing.direction }}
                </p>
              </div>
            </div>
          </section>

          <!-- ==================== DESCRIPTION ==================== -->

          <section
            class="bg-white rounded-[24px] p-6 md:p-8 shadow-sm"
          >
            <h2 class="text-base font-semibold mb-4">
              Mô tả
            </h2>

            <p class="text-xs text-gray-500 leading-6">
              {{ listing.description1 }}
            </p>

            <p class="text-xs text-gray-500 leading-6 mt-3">
              {{ listing.description2 }}
            </p>
          </section>

          <!-- ==================== AI WARNING ==================== -->

          <section
            v-if="listing.hasWarning"
            class="rounded-[24px] p-6 md:p-8 bg-[#f7e9df] border border-[#e6c9b6]"
          >
            <div
              class="flex flex-col md:flex-row md:items-center justify-between gap-5"
            >
              <div>

                <div class="flex items-center gap-2 mb-2">

                  <div
                    class="w-8 h-8 rounded-lg bg-[#c9683c] text-white flex items-center justify-center"
                  >
                    !
                  </div>

                  <h2 class="font-semibold text-[#9c4e2e]">
                    Đối chiếu hình ảnh bằng AI
                  </h2>
                </div>

                <p
                  class="text-xs text-[#a26b53] max-w-2xl leading-5"
                >
                  Hệ thống phát hiện hình ảnh trong tin đăng có mức độ
                  tương đồng cao với một số hình ảnh khác.
                  Bạn nên kiểm tra kỹ trước khi giao dịch.
                </p>
              </div>

              <div
                class="px-4 py-2 rounded-full bg-[#c9683c] text-white text-xs whitespace-nowrap"
              >
                {{ listing.status }}
              </div>
            </div>
          </section>

          <!-- ==================== NO WARNING ==================== -->

          <section
            v-else
            class="rounded-[24px] p-6 md:p-8 bg-[#e5f3ea] border border-[#c9e5d5]"
          >
            <div class="flex items-center justify-between gap-5">

              <div>
                <h2 class="font-semibold text-[#438665]">
                  Kiểm tra hình ảnh
                </h2>

                <p class="text-xs text-[#438665]/80 mt-2">
                  Hệ thống chưa phát hiện cảnh báo bất thường đối với
                  hình ảnh của tin đăng này.
                </p>
              </div>

              <div
                class="px-4 py-2 rounded-full bg-[#438665] text-white text-xs"
              >
                {{ listing.status }}
              </div>
            </div>
          </section>

          <!-- ==================== AMENITIES ==================== -->

          <section
            class="bg-white rounded-[24px] p-6 md:p-8 shadow-sm"
          >
            <h2 class="text-base font-semibold mb-5">
              Tiện ích xung quanh
            </h2>

            <div
              class="grid grid-cols-2 md:grid-cols-4 gap-3"
            >
              <div class="bg-[#f5f4ef] rounded-2xl p-4">
                <div class="text-lg mb-2">🏫</div>
                <p class="text-xs font-medium">Trường học</p>
                <p class="text-[11px] text-gray-400 mt-1">450 m</p>
              </div>

              <div class="bg-[#f5f4ef] rounded-2xl p-4">
                <div class="text-lg mb-2">🏥</div>
                <p class="text-xs font-medium">Bệnh viện</p>
                <p class="text-[11px] text-gray-400 mt-1">1,2 km</p>
              </div>

              <div class="bg-[#f5f4ef] rounded-2xl p-4">
                <div class="text-lg mb-2">🛒</div>
                <p class="text-xs font-medium">Siêu thị</p>
                <p class="text-[11px] text-gray-400 mt-1">600 m</p>
              </div>

              <div class="bg-[#f5f4ef] rounded-2xl p-4">
                <div class="text-lg mb-2">🌳</div>
                <p class="text-xs font-medium">Công viên</p>
                <p class="text-[11px] text-gray-400 mt-1">850 m</p>
              </div>
            </div>
          </section>

          <!-- ==================== LOCATION ==================== -->

          <section
            class="bg-white rounded-[24px] p-6 md:p-8 shadow-sm"
          >
            <div class="flex items-center justify-between mb-4">

              <div>
                <h2 class="text-base font-semibold">
                  Vị trí
                </h2>

                <p class="text-[11px] text-gray-400 mt-1">
                  {{ listing.location }}
                </p>
              </div>

              <button
                @click="goMap"
                class="px-4 py-2 rounded-full bg-[#1E325A] text-white text-[11px]"
              >
                Xem trên bản đồ
              </button>
            </div>

            <div
              class="relative h-[250px] rounded-[20px] overflow-hidden bg-[#dedbd2]"
            >
              <div class="absolute inset-0 map-pattern"></div>

              <div
                class="absolute inset-0 flex items-center justify-center"
              >
                <div
                  class="bg-[#1E325A] text-white px-4 py-2 rounded-full text-xs shadow-lg"
                >
                  {{ listing.price }}
                </div>
              </div>
            </div>
          </section>

          <!-- ==================== AI VALUATION ==================== -->

          <section
            class="bg-[#1E325A] text-white rounded-[24px] p-6 md:p-8 shadow-sm"
          >
            <div
              class="flex flex-col md:flex-row md:items-center justify-between gap-6"
            >
              <div>
                <p
                  class="text-[11px] text-white/50 uppercase tracking-widest"
                >
                  Định giá tham chiếu
                </p>

                <h2 class="text-2xl font-semibold mt-2">
                  {{ listing.valuation }}
                </h2>

                <p class="text-[11px] text-white/60 mt-2">
                  Ước tính bằng mô hình XGBoost từ dữ liệu khu vực.
                </p>
              </div>

              <div class="bg-white/10 rounded-2xl px-5 py-4">

                <p class="text-[11px] text-white/60">
                  Giá tin đăng
                </p>

                <p class="text-lg font-semibold mt-1">
                  {{ listing.price }}
                </p>

                <p class="text-[11px] text-emerald-300 mt-1">
                  Nằm trong khoảng hợp lý
                </p>
              </div>
            </div>

            <div class="mt-7 border-t border-white/10 pt-5">

              <p class="text-xs font-medium mb-4">
                Các yếu tố ảnh hưởng đến giá
              </p>

              <div class="space-y-3">

                <div>
                  <div
                    class="flex justify-between text-[11px] text-white/60 mb-1"
                  >
                    <span>Vị trí trung tâm</span>
                    <span>+12%</span>
                  </div>

                  <div class="h-1.5 bg-white/10 rounded-full">
                    <div
                      class="h-full w-[80%] bg-white/70 rounded-full"
                    ></div>
                  </div>
                </div>

                <div>
                  <div
                    class="flex justify-between text-[11px] text-white/60 mb-1"
                  >
                    <span>Diện tích</span>
                    <span>+8%</span>
                  </div>

                  <div class="h-1.5 bg-white/10 rounded-full">
                    <div
                      class="h-full w-[65%] bg-white/70 rounded-full"
                    ></div>
                  </div>
                </div>

                <div>
                  <div
                    class="flex justify-between text-[11px] text-white/60 mb-1"
                  >
                    <span>Khoảng cách tiện ích</span>
                    <span>+5%</span>
                  </div>

                  <div class="h-1.5 bg-white/10 rounded-full">
                    <div
                      class="h-full w-[45%] bg-white/70 rounded-full"
                    ></div>
                  </div>
                </div>

              </div>
            </div>
          </section>

        </div>

        <!-- ==================== RIGHT SIDEBAR ==================== -->

        <aside class="space-y-4 lg:sticky lg:top-5">

          <!-- CONTACT -->

          <section
            class="bg-white rounded-[24px] p-6 shadow-sm"
          >
            <p class="text-[11px] text-gray-400 mb-4">
              Người đăng
            </p>

            <div class="flex items-center gap-3">

              <div
                class="w-11 h-11 rounded-full bg-[#1E325A] text-white flex items-center justify-center text-xs font-semibold"
              >
                NT
              </div>

              <div>
                <p class="text-sm font-semibold">
                  Nguyễn Thành
                </p>

                <p class="text-[11px] text-gray-400 mt-1">
                  Môi giới xác thực
                </p>
              </div>

            </div>

            <div class="mt-5 space-y-2">

              <button
                class="w-full py-3 rounded-full bg-[#1E325A] text-white text-xs hover:opacity-90 transition"
              >
                Nhắn tin
              </button>

              <button
                class="w-full py-3 rounded-full bg-white border border-[#1E325A] text-[#1E325A] text-xs hover:bg-[#1E325A]/5 transition"
              >
                Gọi 090 *** 789
              </button>

            </div>

            <p
              class="text-[10px] text-gray-400 text-center mt-4 leading-4"
            >
              Không chuyển tiền hoặc đặt cọc trước khi xác minh
              thông tin bất động sản.
            </p>
          </section>

          <!-- QUICK INFO -->

          <section
            class="bg-white rounded-[24px] p-6 shadow-sm"
          >
            <h3 class="text-sm font-semibold mb-4">
              Thông tin tin đăng
            </h3>

            <div class="space-y-3 text-[11px]">

              <div class="flex justify-between">
                <span class="text-gray-400">
                  Mã tin
                </span>

                <span>
                  #SP{{ listingId }}
                </span>
              </div>

              <div class="flex justify-between">
                <span class="text-gray-400">
                  Ngày đăng
                </span>

                <span>
                  01/10/2026
                </span>
              </div>

              <div class="flex justify-between">
                <span class="text-gray-400">
                  Lượt xem
                </span>

                <span>
                  1.240
                </span>
              </div>

              <div class="flex justify-between">
                <span class="text-gray-400">
                  Lượt lưu
                </span>

                <span>
                  6
                </span>
              </div>

            </div>
          </section>

          <!-- REPORT -->

          <section
            class="bg-white rounded-[24px] p-5 shadow-sm"
          >
            <p class="text-[11px] text-gray-400 leading-5">
              Bạn thấy thông tin hoặc hình ảnh của tin đăng này
              có vấn đề?
            </p>

            <button
  @click="router.push(`/listing/${route.params.id}/report`)"
  class="mt-3 text-[12px] text-[#b65c3c] hover:underline cursor-pointer"
>
  ⚑ Báo cáo tin đăng
</button>
          </section>

        </aside>
      </div>
    </main>

    <!-- ====================================================== -->
    <!-- FULL SCREEN IMAGE GALLERY -->
    <!-- ====================================================== -->

    <Teleport to="body">
      <div
        v-if="showGallery"
        class="fixed inset-0 z-[9999] bg-black/80 flex items-center justify-center p-2 md:p-5"
        @click.self="closeGallery"
      >
        <div
          class="relative w-full max-w-[1500px] h-[95vh] bg-[#11182a] rounded-[28px] overflow-hidden flex flex-col shadow-2xl"
        >

          <!-- GALLERY HEADER -->

          <div
            class="flex items-center justify-between gap-4 px-5 md:px-8 py-4 text-white"
          >

            <!-- PROPERTY INFO -->

            <div class="flex items-center gap-4 min-w-0">

              <div class="min-w-0">

                <h2
                  class="text-xs md:text-sm font-medium truncate"
                >
                  {{ listing.title }}
                </h2>

                <p
                  class="text-[10px] md:text-[11px] text-white/40 mt-1 truncate"
                >
                  {{ listing.location }}
                </p>

              </div>

              <!-- IMAGE NUMBER -->

              <div
                class="hidden sm:block px-3 py-1 rounded-full bg-white/10 text-[11px] text-white/70 whitespace-nowrap"
              >
                {{ currentImageIndex + 1 }} / {{ images.length }} ảnh
              </div>

            </div>

            <!-- HEADER ACTIONS -->

            <div class="flex items-center gap-2 shrink-0">

              <button
                class="hidden sm:block px-4 py-2 rounded-full border border-white/10 bg-white/5 text-[11px] text-white/70 hover:bg-white/10 transition"
              >
                Tải ảnh
              </button>

              <button
                class="hidden md:block px-4 py-2 rounded-full border border-white/10 bg-white/5 text-[11px] text-white/70 hover:bg-white/10 transition"
              >
                Báo cáo ảnh sai
              </button>

              <!-- CLOSE -->

              <button
                @click="closeGallery"
                class="w-9 h-9 rounded-full border border-white/10 bg-white/5 flex items-center justify-center text-white/70 hover:bg-white/10 hover:text-white transition"
              >
                ✕
              </button>

            </div>
          </div>

          <!-- ==================== MAIN PHOTO ==================== -->

          <div
            class="relative flex-1 min-h-0 flex items-center justify-center px-5 md:px-16"
          >

            <img
              :src="images[currentImageIndex]"
              :alt="`Ảnh ${currentImageIndex + 1} của ${listing.title}`"
              class="w-full h-full object-contain rounded-[18px]"
            />

            <!-- PREVIOUS -->

            <button
              @click="prevImage"
              class="absolute left-3 md:left-5 top-1/2 -translate-y-1/2 w-11 h-11 md:w-12 md:h-12 rounded-full bg-white/10 border border-white/10 text-white text-3xl flex items-center justify-center hover:bg-white/20 transition"
              aria-label="Ảnh trước"
            >
              ‹
            </button>

            <!-- NEXT -->

            <button
              @click="nextImage"
              class="absolute right-3 md:right-5 top-1/2 -translate-y-1/2 w-11 h-11 md:w-12 md:h-12 rounded-full bg-white/10 border border-white/10 text-white text-3xl flex items-center justify-center hover:bg-white/20 transition"
              aria-label="Ảnh tiếp theo"
            >
              ›
            </button>

            <!-- MOBILE IMAGE COUNT -->

            <div
              class="sm:hidden absolute bottom-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-black/50 text-white text-[11px]"
            >
              {{ currentImageIndex + 1 }} / {{ images.length }}
            </div>

          </div>

          <!-- ==================== THUMBNAILS ==================== -->

          <div class="px-5 md:px-8 py-4">

            <div
              class="flex gap-2 overflow-x-auto pb-1 gallery-scroll"
            >

              <button
                v-for="(image, index) in images"
                :key="index"
                @click="selectImage(index)"
                class="relative shrink-0 w-[105px] md:w-[130px] h-[65px] md:h-[78px] rounded-xl overflow-hidden border-2 transition"
                :class="
                  currentImageIndex === index
                    ? 'border-white opacity-100'
                    : 'border-transparent opacity-50 hover:opacity-100'
                "
              >
                <img
                  :src="image"
                  :alt="`Ảnh thu nhỏ ${index + 1}`"
                  class="w-full h-full object-cover"
                />

                <div
                  class="absolute bottom-1 left-1 px-1.5 py-0.5 rounded-full bg-black/60 text-white text-[9px]"
                >
                  {{ index + 1 }}
                </div>

              </button>

            </div>
          </div>

        </div>
      </div>
    </Teleport>

  </div>
</template>

<style scoped>
.map-pattern {
  background-color: #dedbd2;

  background-image: repeating-linear-gradient(
    120deg,
    rgba(255, 255, 255, 0.45) 0,
    rgba(255, 255, 255, 0.45) 12px,
    rgba(205, 202, 194, 0.35) 12px,
    rgba(205, 202, 194, 0.35) 24px
  );
}

/* Gallery thumbnail scrollbar */
.gallery-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.25) transparent;
}

.gallery-scroll::-webkit-scrollbar {
  height: 5px;
}

.gallery-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.gallery-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.25);
  border-radius: 999px;
}
</style>