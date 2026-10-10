<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const searchText = ref('Hải Châu, Đà Nẵng')
const showFilters = ref(false)

const minPrice = ref('1,5 tỷ')
const maxPrice = ref('15 tỷ')

const selectedType = ref('Nhà phố')
const bedrooms = ref(3)

const minArea = ref(50)
const maxArea = ref(150)

const propertyTypes = [
  'Nhà phố',
  'Căn hộ',
  'Đất nền',
  'Biệt thự'
]

const toggleFilters = () => {
  showFilters.value = !showFilters.value
}

const increaseBedroom = () => {
  bedrooms.value++
}

const decreaseBedroom = () => {
  if (bedrooms.value > 1) {
    bedrooms.value--
  }
}

const resetFilters = () => {
  minPrice.value = '1,5 tỷ'
  maxPrice.value = '15 tỷ'
  selectedType.value = 'Nhà phố'
  bedrooms.value = 3
  minArea.value = 50
  maxArea.value = 150
}

const applyFilters = () => {
  showFilters.value = false

  console.log({
    minPrice: minPrice.value,
    maxPrice: maxPrice.value,
    propertyType: selectedType.value,
    bedrooms: bedrooms.value,
    minArea: minArea.value,
    maxArea: maxArea.value
  })
}

const listings = [
  {
    id: 1,
    title: 'Nhà 3 tầng hẻm xe hơi, gần cầu Rồng',
    location: 'Hải Châu, Đà Nẵng',
    price: '4,85 tỷ',
    detail: '92 m² · 3 PN · 2 WC',
    status: 'Ảnh trùng 94%',
    statusType: 'warning',
  },
  {
    id: 2,
    title: 'Căn hộ 2PN view sông Hàn',
    location: 'Hải Châu, Đà Nẵng',
    price: '3,20 tỷ',
    detail: '68 m² · 2 PN · 2 WC',
    status: 'Giá hợp lý',
    statusType: 'good',
  },
  {
    id: 3,
    title: 'Nhà mặt tiền Nguyễn Văn Linh',
    location: 'Thanh Khê, Đà Nẵng',
    price: '12,5 tỷ',
    detail: '140 m² · 4 PN · 3 WC',
    status: 'Giá cao hơn tham chiếu',
    statusType: 'high',
  },
  {
    id: 4,
    title: 'Đất nền Hoà Xuân, sổ đỏ riêng',
    location: 'Cẩm Lệ, Đà Nẵng',
    price: '2,95 tỷ',
    detail: '100 m² · Đất nền',
    status: 'Giá hợp lý',
    statusType: 'good',
  },
  {
    id: 5,
    title: 'Căn hộ Studio gần Đại học Duy Tân',
    location: 'Hải Châu, Đà Nẵng',
    price: '1,45 tỷ',
    detail: '32 m² · Studio · 1 WC',
    status: 'Giá hợp lý',
    statusType: 'good',
  },
]

const filters = [
  'Loại hình',
  'Mức giá',
  'Phòng ngủ',
  'Diện tích',
]

const statusClass = (type) => {
  if (type === 'good') {
    return 'bg-[#e2f3e8] text-[#43936c]'
  }

  if (type === 'warning') {
    return 'bg-[#f9e8dd] text-[#c66a43]'
  }

  if (type === 'high') {
    return 'bg-[#fae7dc] text-[#c56a45]'
  }

  return 'bg-gray-100 text-gray-500'
}

const goHome = () => {
  router.push('/home')
}

const goPost = () => {
  router.push('/post')
}

const goAccount = () => {
  router.push('/account')
}

const search = () => {
  console.log('Tìm:', searchText.value)
}
</script>

<template>
  <div class="min-h-screen bg-[#e9e7df] text-[#1E325A]">

    <!-- ================= HEADER ================= -->
    <header class="max-w-[1450px] mx-auto px-7 md:px-10 pt-6">
      <div
        class="flex items-center justify-between border-b border-[#1E325A]/70 pb-5"
      >
        <!-- LOGO -->
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

        <!-- SEARCH -->
        <div
          class="hidden md:flex items-center bg-white rounded-full border border-gray-200 p-1 w-[430px] shadow-sm"
        >
          <input
            v-model="searchText"
            type="text"
            placeholder="Tìm khu vực..."
            class="flex-1 bg-transparent outline-none px-4 text-xs text-[#1E325A]"
            @keyup.enter="search"
          />

          <button
            @click="search"
            class="bg-[#1E325A] text-white rounded-full px-5 py-2 text-xs hover:opacity-90 transition"
          >
            Tìm
          </button>
        </div>

        <!-- RIGHT -->
        <div class="flex items-center gap-2">
          <button
            @click="goPost"
            class="bg-white border border-gray-200 rounded-full px-5 py-2 text-xs text-gray-500 hover:text-[#1E325A] transition"
          >
            Đăng tin
          </button>

          <button
            @click="goAccount"
            class="bg-[#1E325A] text-white rounded-full px-5 py-2 text-xs hover:opacity-90 transition"
          >
            Tài khoản
          </button>
        </div>
      </div>

      <!-- MOBILE SEARCH -->
      <div class="md:hidden mt-4">
        <div
          class="flex items-center bg-white rounded-full border border-gray-200 p-1"
        >
          <input
            v-model="searchText"
            type="text"
            class="flex-1 outline-none bg-transparent px-4 py-2 text-xs"
          />

          <button
            @click="search"
            class="bg-[#1E325A] text-white px-5 py-2 rounded-full text-xs"
          >
            Tìm
          </button>
        </div>
      </div>
    </header>


    <!-- ================= FILTER BAR ================= -->
    <section
      class="max-w-[1450px] mx-auto px-7 md:px-10 py-4 border-b border-[#1E325A]/40"
    >
      <div class="flex flex-wrap items-center gap-3">

        <!-- LOẠI HÌNH -->
<button
  @click="toggleFilters"
  :class="[
    'border rounded-full px-4 py-2 text-[11px] transition',
    showFilters
      ? 'bg-white text-gray-500 border-gray-200'
      : 'bg-white text-gray-500 border-gray-200'
  ]"
>
  Loại hình⌄
</button>

<!-- MỨC GIÁ -->
<button
  @click="toggleFilters"
  :class="[
    'border rounded-full px-4 py-2 text-[11px] transition',
    showFilters
      ? 'bg-[#1E325A] text-white border-[#1E325A]'
      : 'bg-white text-gray-500 border-gray-200'
  ]"
>
  Mức giá⌄
</button>

<!-- PHÒNG NGỦ -->
<button
  @click="toggleFilters"
  class="bg-white border border-gray-200 rounded-full px-4 py-2 text-[11px] text-gray-500 hover:border-[#1E325A] transition"
>
  Phòng ngủ⌄
</button>

<!-- DIỆN TÍCH -->
<button
  @click="toggleFilters"
  class="bg-white border border-gray-200 rounded-full px-4 py-2 text-[11px] text-gray-500 hover:border-[#1E325A] transition"
>
  Diện tích⌄
</button>

        <button
          class="bg-[#deddd8] rounded-full px-4 py-2 text-[11px] text-gray-400 hover:text-[#1E325A] transition"
        >
          Xoá bộ lọc
        </button>

      </div>
    </section>
    <!-- ================= ADVANCED FILTER ================= -->
<section
  v-if="showFilters"
  class="border-b border-[#1E325A]/50"
>
  <div class="max-w-[1450px] mx-auto px-7 md:px-10 py-5">

    <div
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-[1.2fr_1.2fr_1fr_1.2fr] gap-8 items-end"
    >

      <!-- KHOẢNG GIÁ -->
      <div>
        <p class="text-[10px] text-gray-400 mb-2">
          Khoảng giá
        </p>

        <div class="flex items-center gap-3">
          <input
            v-model="minPrice"
            type="text"
            class="w-full bg-white border border-gray-200 rounded-xl px-4 py-2.5 text-xs outline-none focus:border-[#1E325A]"
          />

          <span class="text-gray-300">—</span>

          <input
            v-model="maxPrice"
            type="text"
            class="w-full bg-white border border-gray-200 rounded-xl px-4 py-2.5 text-xs outline-none focus:border-[#1E325A]"
          />
        </div>
      </div>

      <!-- LOẠI HÌNH -->
      <div>
        <p class="text-[10px] text-gray-400 mb-2">
          Loại hình
        </p>

        <div class="flex flex-wrap gap-2">
          <button
            v-for="type in propertyTypes"
            :key="type"
            @click="selectedType = type"
            :class="[
              'px-4 py-2 rounded-full text-[10px] border transition',
              selectedType === type
                ? 'bg-[#1E325A] text-white border-[#1E325A]'
                : 'bg-white text-gray-500 border-gray-200'
            ]"
          >
            {{ type }}
          </button>
        </div>
      </div>

      <!-- PHÒNG NGỦ -->
      <div>
        <p class="text-[10px] text-gray-400 mb-2">
          Phòng ngủ
        </p>

        <div class="flex items-center gap-4">

          <button
            @click="decreaseBedroom"
            class="w-7 h-7 rounded-full bg-white border border-gray-200 flex items-center justify-center text-gray-500"
          >
            −
          </button>

          <span class="text-sm font-medium">
            {{ bedrooms }}
          </span>

          <button
            @click="increaseBedroom"
            class="w-7 h-7 rounded-full bg-white border border-gray-200 flex items-center justify-center text-gray-500"
          >
            +
          </button>

        </div>
      </div>

      <!-- DIỆN TÍCH -->
      <div>
        <p class="text-[10px] text-gray-400 mb-2">
          Diện tích (m²)
        </p>

        <div class="flex items-center gap-3">

          <input
            v-model="minArea"
            type="number"
            class="w-full bg-white border border-gray-200 rounded-xl px-4 py-2.5 text-xs outline-none focus:border-[#1E325A]"
          />

          <span class="text-gray-300">—</span>

          <input
            v-model="maxArea"
            type="number"
            class="w-full bg-white border border-gray-200 rounded-xl px-4 py-2.5 text-xs outline-none focus:border-[#1E325A]"
          />

        </div>
      </div>

    </div>

    <!-- NÚT ĐẶT LẠI + ÁP DỤNG -->
    <div class="flex justify-end gap-3 mt-5">

      <button
        @click="resetFilters"
        class="px-5 py-2 rounded-full bg-[#deddd8] text-gray-500 text-[11px] hover:bg-gray-300 transition"
      >
        Đặt lại
      </button>

      <button
        @click="applyFilters"
        class="px-6 py-2 rounded-full bg-[#c86435] text-white text-[11px] hover:opacity-90 transition"
      >
        Áp dụng bộ lọc
      </button>

    </div>

  </div>
</section>


    <!-- ================= MAIN ================= -->
    <main
      class="max-w-[1450px] mx-auto px-7 md:px-10 pt-5 pb-8"
    >

      <div
        class="grid grid-cols-1 lg:grid-cols-[460px_1fr] gap-8"
      >

        <!-- ================= LEFT LIST ================= -->
        <section>

          <!-- RESULT HEADER -->
          <div
            class="flex items-center justify-between mb-4 px-1"
          >
            <span class="text-[11px] text-gray-400">
              2.417 tin đăng phù hợp
            </span>

            <button
              class="text-[10px] text-gray-400 hover:text-[#1E325A]"
            >
              Sắp xếp: Mới nhất⌄
            </button>
          </div>


          <!-- LISTINGS -->
          <div class="space-y-3">

            <article
              v-for="listing in listings"
              :key="listing.id"
              class="bg-white rounded-[20px] px-5 py-4 min-h-[118px]
                     cursor-pointer border border-transparent
                     hover:border-[#1E325A]/20 hover:shadow-md
                     transition"
            >

              <div class="flex gap-4">

                <!-- STATUS -->
                <div class="w-[105px] shrink-0">
                  <span
                    class="inline-block rounded-full px-3 py-1 text-[9px] whitespace-nowrap"
                    :class="statusClass(listing.statusType)"
                  >
                    {{ listing.status }}
                  </span>
                </div>


                <!-- INFORMATION -->
                <div class="flex-1 min-w-0">

                  <h2
                    class="text-[13px] font-medium text-[#1E325A] truncate"
                  >
                    {{ listing.title }}
                  </h2>

                  <p
                    class="text-[10px] text-gray-400 mt-1"
                  >
                    {{ listing.location }}
                  </p>

                  <p
                    class="text-[15px] font-semibold text-[#1E325A] mt-1"
                  >
                    {{ listing.price }}
                  </p>

                  <p
                    class="text-[10px] text-gray-400 mt-1"
                  >
                    {{ listing.detail }}
                  </p>

                </div>

              </div>

            </article>

          </div>
        </section>


        <!-- ================= MAP ================= -->
        <section
          class="relative min-h-[650px] lg:min-h-[720px]
                 rounded-[32px] overflow-hidden
                 bg-[#e5e2da]"
        >

          <!--
            Hiện tại đây là bản đồ mô phỏng theo Figma.
            Sau này có thể thay bằng Mapbox/Leaflet thật.
          -->

          <!-- STRIPED MAP BACKGROUND -->
          <div class="absolute inset-0 map-pattern"></div>


          <!-- MAP LABEL -->
          <div
            class="absolute top-5 left-5 bg-white/90 backdrop-blur
                   px-4 py-2 rounded-full
                   text-[10px] text-gray-500 shadow-sm"
          >
            mapbox gl js → cụm 2.417 điểm
          </div>


          <!-- ================= PRICE MARKERS ================= -->

          <!-- 4.85 -->
          <button
            class="absolute left-[32%] top-[22%]
                   bg-[#1E325A] text-white
                   px-3 py-1.5 rounded-full
                   text-[10px] shadow-lg
                   hover:scale-110 transition"
          >
            4,85 tỷ
          </button>


          <!-- 3.20 -->
          <button
            class="absolute left-[55%] top-[14%]
                   bg-[#1E325A] text-white
                   px-3 py-1.5 rounded-full
                   text-[10px] shadow-lg
                   hover:scale-110 transition"
          >
            3,20 tỷ
          </button>


          <!-- 12.5 -->
          <button
            class="absolute left-[69%] top-[43%]
                   bg-[#c9673f] text-white
                   px-3 py-1.5 rounded-full
                   text-[10px] shadow-lg
                   hover:scale-110 transition"
          >
            12,5 tỷ
          </button>


          <!-- 1.45 -->
          <button
            class="absolute left-[20%] top-[47%]
                   bg-[#1E325A] text-white
                   px-3 py-1.5 rounded-full
                   text-[10px] shadow-lg
                   hover:scale-110 transition"
          >
            1,45 tỷ
          </button>


          <!-- 2.95 -->
          <button
            class="absolute left-[40%] top-[58%]
                   bg-[#1E325A] text-white
                   px-3 py-1.5 rounded-full
                   text-[10px] shadow-lg
                   hover:scale-110 transition"
          >
            2,95 tỷ
          </button>

        </section>

      </div>
    </main>

  </div>
</template>


<style scoped>
.map-pattern {
  background-color: #e5e2da;

  background-image: repeating-linear-gradient(
    115deg,
    rgba(255, 255, 255, 0.38) 0px,
    rgba(255, 255, 255, 0.38) 12px,
    rgba(215, 212, 204, 0.35) 12px,
    rgba(215, 212, 204, 0.35) 24px
  );
}
</style>