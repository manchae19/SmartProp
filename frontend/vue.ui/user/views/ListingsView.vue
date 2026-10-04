<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const searchText = ref('')
const selectedType = ref('Tất cả')
const selectedPrice = ref('Tất cả')
const selectedDistrict = ref('Tất cả')

const propertyTypes = [
  'Tất cả',
  'Nhà phố',
  'Căn hộ',
  'Đất nền'
]

const priceRanges = [
  'Tất cả',
  'Dưới 3 tỷ',
  '3 - 5 tỷ',
  'Trên 5 tỷ'
]

const districts = [
  'Tất cả',
  'Hải Châu',
  'Cẩm Lệ',
  'Ngũ Hành Sơn',
  'Thanh Khê'
]

const listings = ref([
  {
    id: 1,
    title: 'Nhà 3 tầng hẻm xe hơi, gần cầu Rồng',
    location: 'Hải Châu, Đà Nẵng',
    district: 'Hải Châu',
    price: 4.85,
    priceText: '4,85 tỷ đ',
    type: 'Nhà phố',
    area: '92 m²',
    bedrooms: 3,
    status: 'Ảnh trùng 94%',
    statusType: 'warning'
  },

  {
    id: 2,
    title: 'Căn hộ 2PN view sông Hàn',
    location: 'Hải Châu, Đà Nẵng',
    district: 'Hải Châu',
    price: 3.2,
    priceText: '3,20 tỷ đ',
    type: 'Căn hộ',
    area: '78 m²',
    bedrooms: 2,
    status: 'Không cảnh báo',
    statusType: 'safe'
  },

  {
    id: 3,
    title: 'Đất nền Hoà Xuân, sổ đỏ riêng',
    location: 'Cẩm Lệ, Đà Nẵng',
    district: 'Cẩm Lệ',
    price: 2.95,
    priceText: '2,95 tỷ đ',
    type: 'Đất nền',
    area: '100 m²',
    bedrooms: null,
    status: 'Giá hợp lý',
    statusType: 'safe'
  }
])

const filteredListings = computed(() => {
  return listings.value.filter((item) => {
    const keyword = searchText.value
      .trim()
      .toLowerCase()

    const matchesSearch =
      !keyword ||
      item.title.toLowerCase().includes(keyword) ||
      item.location.toLowerCase().includes(keyword)

    const matchesType =
      selectedType.value === 'Tất cả' ||
      item.type === selectedType.value

    const matchesDistrict =
      selectedDistrict.value === 'Tất cả' ||
      item.district === selectedDistrict.value

    let matchesPrice = true

    if (selectedPrice.value === 'Dưới 3 tỷ') {
      matchesPrice = item.price < 3
    }

    if (selectedPrice.value === '3 - 5 tỷ') {
      matchesPrice =
        item.price >= 3 &&
        item.price <= 5
    }

    if (selectedPrice.value === 'Trên 5 tỷ') {
      matchesPrice = item.price > 5
    }

    return (
      matchesSearch &&
      matchesType &&
      matchesDistrict &&
      matchesPrice
    )
  })
})

const resetFilters = () => {
  searchText.value = ''
  selectedType.value = 'Tất cả'
  selectedPrice.value = 'Tất cả'
  selectedDistrict.value = 'Tất cả'
}

const openListing = (id) => {
  router.push(`/listing/${id}`)
}

const goHome = () => {
  router.push('/home')
}

const goMap = () => {
  router.push('/map')
}

const goAccount = () => {
  router.push('/account')
}

const goPost = () => {
  router.push('/post')
}
</script>

<template>
  <div class="min-h-screen bg-[#f5f3ed] text-[#1E325A]">

    <!-- HEADER -->
    <header class="bg-[#f5f3ed]">
      <div
        class="max-w-[1400px] mx-auto px-6 md:px-10"
      >
        <div
          class="h-[76px] flex items-center justify-between border-b border-[#1E325A]/30"
        >
          <!-- LEFT -->
          <div class="flex items-center gap-8">
            <button
              @click="goHome"
              class="flex items-center gap-3"
            >
              <div
                class="w-8 h-8 rounded-lg bg-[#1E325A] text-white flex items-center justify-center font-bold"
              >
                S
              </div>

              <span class="font-semibold">
                SmartProp
              </span>
            </button>

            <button
              @click="goHome"
              class="hidden md:block text-xs text-gray-500 hover:text-[#1E325A]"
            >
              ‹ Trang chủ
            </button>
          </div>

          <!-- RIGHT -->
          <div class="flex items-center gap-3">
            <button
              @click="goMap"
              class="hidden sm:block px-5 py-2.5 rounded-full border border-gray-300 bg-white text-xs hover:bg-gray-50"
            >
              Xem bản đồ
            </button>

            <button
              @click="goPost"
              class="hidden sm:block px-5 py-2.5 rounded-full bg-white text-xs border border-gray-200"
            >
              Đăng tin
            </button>

            <button
              @click="goAccount"
              class="px-5 py-2.5 rounded-full bg-[#1E325A] text-white text-xs"
            >
              Tài khoản
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- MAIN -->
    <main
      class="max-w-[1200px] mx-auto px-6 md:px-8 py-10"
    >

      <!-- TITLE -->
      <section
        class="flex flex-col md:flex-row md:items-end md:justify-between gap-5"
      >
        <div>
          <p
            class="text-[11px] font-semibold tracking-[0.18em] text-gray-400 uppercase"
          >
            Bất động sản Đà Nẵng
          </p>

          <h1
            class="text-3xl md:text-4xl font-bold text-[#101a2c] mt-2"
          >
            Tìm tin phù hợp với bạn
          </h1>

          <p
            class="text-sm text-gray-500 mt-3"
          >
            Tìm kiếm, lọc và xem chi tiết các tin đăng bất động sản.
          </p>
        </div>

        <button
          @click="goMap"
          class="self-start md:self-auto px-6 py-3 bg-[#1E325A] text-white rounded-full text-xs hover:bg-[#294470] transition"
        >
          Xem trên bản đồ
        </button>
      </section>

      <!-- SEARCH + FILTER -->
      <section
        class="mt-8 bg-white rounded-[24px] p-5 md:p-6 shadow-sm"
      >
        <!-- SEARCH -->
        <div class="relative">
          <span
            class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400"
          >
            ⌕
          </span>

          <input
            v-model="searchText"
            type="text"
            placeholder="Tìm theo tên tin đăng hoặc khu vực..."
            class="w-full h-12 rounded-xl border border-gray-200 pl-11 pr-4 text-sm outline-none focus:border-[#1E325A]"
          />
        </div>

        <!-- FILTERS -->
        <div
          class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4"
        >
          <!-- TYPE -->
          <div>
            <label
              class="block text-[10px] text-gray-400 mb-1.5"
            >
              Loại bất động sản
            </label>

            <select
              v-model="selectedType"
              class="w-full h-11 px-3 rounded-xl border border-gray-200 bg-white text-xs outline-none"
            >
              <option
                v-for="type in propertyTypes"
                :key="type"
              >
                {{ type }}
              </option>
            </select>
          </div>

          <!-- PRICE -->
          <div>
            <label
              class="block text-[10px] text-gray-400 mb-1.5"
            >
              Mức giá
            </label>

            <select
              v-model="selectedPrice"
              class="w-full h-11 px-3 rounded-xl border border-gray-200 bg-white text-xs outline-none"
            >
              <option
                v-for="price in priceRanges"
                :key="price"
              >
                {{ price }}
              </option>
            </select>
          </div>

          <!-- DISTRICT -->
          <div>
            <label
              class="block text-[10px] text-gray-400 mb-1.5"
            >
              Khu vực
            </label>

            <select
              v-model="selectedDistrict"
              class="w-full h-11 px-3 rounded-xl border border-gray-200 bg-white text-xs outline-none"
            >
              <option
                v-for="district in districts"
                :key="district"
              >
                {{ district }}
              </option>
            </select>
          </div>

          <!-- RESET -->
          <div class="flex items-end">
            <button
              @click="resetFilters"
              class="w-full h-11 rounded-xl border border-[#1E325A]/20 text-xs text-[#1E325A] hover:bg-[#1E325A]/5 transition"
            >
              Xóa bộ lọc
            </button>
          </div>
        </div>
      </section>

      <!-- RESULT HEADER -->
      <section
        class="mt-8 flex items-center justify-between"
      >
        <div>
          <h2
            class="text-xl font-bold text-[#101a2c]"
          >
            Tin đăng
          </h2>

          <p
            class="text-xs text-gray-400 mt-1"
          >
            Tìm thấy {{ filteredListings.length }} kết quả
          </p>
        </div>

        <button
          @click="goMap"
          class="text-xs font-semibold hover:underline"
        >
          Xem bản đồ ›
        </button>
      </section>

      <!-- LISTINGS -->
      <section
        v-if="filteredListings.length"
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-5"
      >
        <article
          v-for="listing in filteredListings"
          :key="listing.id"
          @click="openListing(listing.id)"
          class="bg-white rounded-[22px] overflow-hidden shadow-md border border-gray-100 cursor-pointer transition-all duration-200 hover:-translate-y-1 hover:shadow-xl"
        >
          <!-- IMAGE PLACEHOLDER -->
          <div
            class="h-[210px] bg-[#f1f2f4] relative flex items-center justify-center border-b border-gray-200"
          >
            <!-- STATUS -->
            <span
              class="absolute top-4 left-4 px-3 py-1.5 rounded-lg text-[10px] font-semibold text-white shadow-sm"
              :class="
                listing.statusType === 'warning'
                  ? 'bg-amber-500'
                  : 'bg-emerald-600'
              "
            >
              {{ listing.status }}
            </span>

            <span
              class="text-xs text-gray-400"
            >
              Hình ảnh {{ listing.type.toLowerCase() }}
            </span>
          </div>

          <!-- CONTENT -->
          <div class="p-5">
            <div
              class="flex items-start justify-between gap-3"
            >
              <div class="min-w-0">
                <p
                  class="text-[10px] text-gray-400"
                >
                  {{ listing.type }}
                </p>

                <h3
                  class="font-bold text-[#101a2c] text-sm mt-1 leading-5"
                >
                  {{ listing.title }}
                </h3>

                <p
                  class="text-xs text-gray-400 mt-1"
                >
                  {{ listing.location }}
                </p>
              </div>
            </div>

            <!-- INFO -->
            <div
              class="flex items-center gap-4 mt-5 pt-4 border-t border-gray-100 text-[10px] text-gray-500"
            >
              <span>
                {{ listing.area }}
              </span>

              <span
                v-if="listing.bedrooms"
              >
                {{ listing.bedrooms }} phòng ngủ
              </span>
            </div>

            <!-- PRICE -->
            <div
              class="flex items-center justify-between mt-4"
            >
              <span
                class="text-lg font-bold text-[#101a2c]"
              >
                {{ listing.priceText }}
              </span>

              <span
                class="text-xs text-[#1E325A]"
              >
                Xem chi tiết →
              </span>
            </div>
          </div>
        </article>
      </section>

      <!-- EMPTY -->
      <section
        v-else
        class="mt-5 bg-white rounded-[24px] py-20 text-center shadow-sm"
      >
        <div
          class="w-12 h-12 mx-auto rounded-full bg-[#1E325A]/10 flex items-center justify-center"
        >
          ⌕
        </div>

        <h3
          class="font-semibold text-sm mt-4"
        >
          Không tìm thấy tin đăng
        </h3>

        <p
          class="text-xs text-gray-400 mt-2"
        >
          Hãy thử thay đổi từ khóa hoặc bộ lọc.
        </p>

        <button
          @click="resetFilters"
          class="mt-5 px-5 py-2.5 rounded-full bg-[#1E325A] text-white text-xs"
        >
          Xóa bộ lọc
        </button>
      </section>

    </main>
  </div>
</template>