<script setup>
import { ref, computed } from 'vue'

const activeFilter = ref('Tất cả')
const sortType = ref('Mới lưu')

const filters = ['Tất cả', 'Nhà phố', 'Căn hộ', 'Đất nền']

const listings = ref([
  {
    id: 1,
    type: 'Nhà phố',
    badge: 'Ảnh trùng 94%',
    badgeColor: 'orange',
    title: 'Nhà 3 tầng hẻm xe hơi, gần cầu Rồng',
    location: 'Hải Châu, Đà Nẵng',
    price: '4,85 tỷ đ',
    info: '92 m² · 3 PN · 2 WC',
    saved: 'Lưu 2 ngày trước',
  },
  {
    id: 2,
    type: 'Căn hộ',
    badge: 'Giá hợp lý',
    badgeColor: 'green',
    title: 'Căn hộ 2PN view sông Hàn',
    location: 'Hải Châu, Đà Nẵng',
    price: '3,20 tỷ đ',
    info: '68 m² · 2 PN · 2 WC',
    saved: 'Lưu 3 ngày trước',
  },
  {
    id: 3,
    type: 'Nhà phố',
    badge: 'Giá cao hơn tham chiếu',
    badgeColor: 'orange',
    title: 'Nhà mặt tiền Nguyễn Văn Linh',
    location: 'Thanh Khê, Đà Nẵng',
    price: '12,5 tỷ đ',
    info: '140 m² · 4 PN · 3 WC',
    saved: 'Lưu 5 ngày trước',
  },
  {
    id: 4,
    type: 'Đất nền',
    badge: 'Giá hợp lý',
    badgeColor: 'green',
    title: 'Đất nền Hoà Xuân, sổ đỏ riêng',
    location: 'Cẩm Lệ, Đà Nẵng',
    price: '2,95 tỷ đ',
    info: '100 m² · Đất nền',
    saved: 'Lưu 1 tuần trước',
  },
  {
    id: 5,
    type: 'Căn hộ',
    badge: 'Giá hợp lý',
    badgeColor: 'green',
    title: 'Căn hộ Studio gần Đại học Duy Tân',
    location: 'Hải Châu, Đà Nẵng',
    price: '1,45 tỷ đ',
    info: '32 m² · Studio · 1 WC',
    saved: 'Lưu 1 tuần trước',
  },
  {
    id: 6,
    type: 'Đất nền',
    badge: 'Giá hợp lý',
    badgeColor: 'green',
    title: 'Đất nền mặt tiền đường Nguyễn Tất Thành',
    location: 'Thanh Khê, Đà Nẵng',
    price: '6,30 tỷ đ',
    info: '150 m² · Đất nền',
    saved: 'Lưu 2 tuần trước',
  },
  {
    id: 7,
    type: 'Nhà phố',
    badge: 'Giá hợp lý',
    badgeColor: 'green',
    title: 'Villa sân vườn Điện Ngọc, sổ hồng riêng',
    location: 'Ngũ Hành Sơn, Đà Nẵng',
    price: '9,80 tỷ đ',
    info: '220 m² · 5 PN · 4 WC',
    saved: 'Lưu 3 tuần trước',
  },
])

const filteredListings = computed(() => {
  if (activeFilter.value === 'Tất cả') {
    return listings.value
  }

  return listings.value.filter(
    (item) => item.type === activeFilter.value
  )
})

function removeFavorite(id) {
  listings.value = listings.value.filter((item) => item.id !== id)
}
</script>

<template>
  <div class="min-h-screen bg-[#f3f1e9] text-[#1E325A]">

    <!-- HEADER -->
    <header class="border-b border-[#1E325A]/40">
      <div
        class="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between"
      >
        <!-- Logo -->
        <div class="flex items-center gap-4">
          <RouterLink to="/home" class="flex items-center gap-2">
            <div
              class="w-7 h-7 rounded-lg bg-[#1E325A] text-white
                     flex items-center justify-center text-xs font-bold"
            >
              S
            </div>

            <span class="font-semibold text-sm">
              SmartProp
            </span>
          </RouterLink>

          <span class="text-gray-300">|</span>

          <RouterLink
            to="/home"
            class="text-xs text-gray-400 hover:text-[#1E325A]"
          >
            ‹ Trang chủ
          </RouterLink>
        </div>

        <!-- Header buttons -->
        <div class="flex items-center gap-3">
          <RouterLink
            to="/post"
            class="px-5 py-2 rounded-full bg-white border border-gray-200
                   text-xs hover:bg-gray-50 transition"
          >
            Đăng tin
          </RouterLink>

          <RouterLink
            to="/account"
            class="px-5 py-2 rounded-full bg-[#1E325A] text-white
                   text-xs hover:opacity-90 transition"
          >
            Tài khoản
          </RouterLink>
        </div>
      </div>
    </header>

    <!-- CONTENT -->
    <main class="max-w-7xl mx-auto px-6 py-7">

      <!-- TITLE -->
      <div class="flex justify-between items-start mb-5">
        <div>
          <h1 class="text-2xl font-medium mb-1">
            Tin đăng yêu thích
          </h1>

          <p class="text-xs text-gray-400">
            {{ listings.length }} tin đăng đã lưu
          </p>
        </div>

        <!-- SORT -->
        <div class="flex items-center gap-1 text-xs text-gray-400">
          <span>Sắp xếp:</span>

          <select
            v-model="sortType"
            class="bg-transparent text-[#1E325A] outline-none cursor-pointer"
          >
            <option>Mới lưu</option>
            <option>Cũ nhất</option>
            <option>Giá thấp</option>
            <option>Giá cao</option>
          </select>
        </div>
      </div>

      <!-- FILTER -->
      <div class="flex gap-2 mb-6">
        <button
          v-for="filter in filters"
          :key="filter"
          @click="activeFilter = filter"
          :class="[
            'px-4 py-2 rounded-full text-xs border transition',
            activeFilter === filter
              ? 'bg-[#1E325A] text-white border-[#1E325A]'
              : 'bg-white text-gray-500 border-gray-200 hover:border-[#1E325A]'
          ]"
        >
          {{ filter }}

          <span class="ml-1">
            ·
            {{
              filter === 'Tất cả'
                ? listings.length
                : listings.filter(item => item.type === filter).length
            }}
          </span>
        </button>
      </div>

      <!-- CARDS -->
      <div
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
      >
        <article
          v-for="item in filteredListings"
          :key="item.id"
          class="bg-white rounded-2xl overflow-hidden
                 border border-gray-100 shadow-sm"
        >

          <!-- IMAGE PLACEHOLDER -->
          <div
            class="relative h-44 bg-[#e4e1d8]
                   overflow-hidden"
          >
            <!-- pattern -->
            <div
              class="absolute inset-0 opacity-40"
              style="
                background-image:
                  repeating-linear-gradient(
                    120deg,
                    transparent,
                    transparent 8px,
                    rgba(255,255,255,.8) 8px,
                    rgba(255,255,255,.8) 13px
                  );
              "
            ></div>

            <!-- Badge -->
            <span
              :class="[
                'absolute top-3 left-3 px-3 py-1 rounded-full text-[10px] text-white',
                item.badgeColor === 'green'
                  ? 'bg-emerald-500'
                  : 'bg-orange-500'
              ]"
            >
              {{ item.badge }}
            </span>

            <!-- Heart -->
            <button
              @click="removeFavorite(item.id)"
              class="absolute top-3 right-3 w-8 h-8
                     rounded-full bg-[#1E325A]
                     text-white flex items-center justify-center
                     hover:scale-105 transition"
              title="Bỏ yêu thích"
            >
              ♥
            </button>
          </div>

          <!-- CARD CONTENT -->
          <div class="p-4">
            <h2
              class="text-sm font-medium text-[#1E325A] mb-1
                     line-clamp-1"
            >
              {{ item.title }}
            </h2>

            <p class="text-[11px] text-gray-400 mb-2">
              {{ item.location }}
            </p>

            <p class="text-base font-semibold mb-1">
              {{ item.price }}
            </p>

            <p class="text-[11px] text-gray-400">
              {{ item.info }}
            </p>

            <div
              class="flex items-center justify-between
                     mt-4 pt-3 border-t border-gray-100"
            >
              <span class="text-[10px] text-gray-400">
                {{ item.saved }}
              </span>

              <button
                class="text-[11px] text-[#1E325A]
                       hover:underline"
              >
                Xem chi tiết ›
              </button>
            </div>
          </div>
        </article>
      </div>

      <!-- EMPTY -->
      <div
        v-if="filteredListings.length === 0"
        class="py-20 text-center"
      >
        <div class="text-4xl mb-4">♡</div>

        <p class="font-medium">
          Chưa có tin đăng trong mục này
        </p>
      </div>

    </main>
  </div>
</template>