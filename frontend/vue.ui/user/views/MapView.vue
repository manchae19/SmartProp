
<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

/* =========================================
   SMARTPROP GIS EXPLORER 2.1
   Vietnamese Typography Fix
   Vue 3 + Tailwind CSS
========================================= */

const searchText = ref('')
const appliedSearch = ref('')
const showFilters = ref(false)
const selectedId = ref(1)
const showDetails = ref(false)
const mapMode = ref('light')
const mapZoom = ref(1)
const sortBy = ref('default')

const minPrice = ref('')
const maxPrice = ref('')
const selectedType = ref('Tất cả')
const bedrooms = ref(0)
const minArea = ref('')
const maxArea = ref('')

const appliedFilters = ref({
  minPrice: '',
  maxPrice: '',
  type: 'Tất cả',
  bedrooms: 0,
  minArea: '',
  maxArea: ''
})

const propertyTypes = [
  'Tất cả',
  'Nhà phố',
  'Căn hộ',
  'Đất nền',
  'Biệt thự'
]

const listings = [
  {
    id: 1,
    title: 'Nhà 3 tầng hẻm xe hơi, gần cầu Rồng',
    location: 'Hải Châu, Đà Nẵng',
    district: 'Hải Châu',
    type: 'Nhà phố',
    price: 4.85,
    area: 92,
    beds: 3,
    baths: 2,
    status: 'Ảnh trùng 94%',
    statusType: 'warning',
    image:
      'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=800&q=85',
    x: 37,
    y: 33
  },
  {
    id: 2,
    title: 'Căn hộ 2PN view sông Hàn',
    location: 'Hải Châu, Đà Nẵng',
    district: 'Hải Châu',
    type: 'Căn hộ',
    price: 3.2,
    area: 68,
    beds: 2,
    baths: 2,
    status: 'Giá hợp lý',
    statusType: 'good',
    image:
      'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=800&q=85',
    x: 58,
    y: 25
  },
  {
    id: 3,
    title: 'Nhà mặt tiền Nguyễn Văn Linh',
    location: 'Thanh Khê, Đà Nẵng',
    district: 'Thanh Khê',
    type: 'Nhà phố',
    price: 12.5,
    area: 140,
    beds: 4,
    baths: 3,
    status: 'Giá cao hơn tham chiếu',
    statusType: 'high',
    image:
      'https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?auto=format&fit=crop&w=800&q=85',
    x: 29,
    y: 55
  },
  {
    id: 4,
    title: 'Đất nền Hòa Xuân, sổ đỏ riêng',
    location: 'Cẩm Lệ, Đà Nẵng',
    district: 'Cẩm Lệ',
    type: 'Đất nền',
    price: 2.95,
    area: 100,
    beds: 0,
    baths: 0,
    status: 'Giá hợp lý',
    statusType: 'good',
    image:
      'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=800&q=85',
    x: 48,
    y: 72
  },
  {
    id: 5,
    title: 'Căn hộ Studio gần Đại học Duy Tân',
    location: 'Hải Châu, Đà Nẵng',
    district: 'Hải Châu',
    type: 'Căn hộ',
    price: 1.45,
    area: 32,
    beds: 1,
    baths: 1,
    status: 'Giá hợp lý',
    statusType: 'good',
    image:
      'https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=800&q=85',
    x: 69,
    y: 49
  }
]

const filteredListings = computed(() => {
  const keyword = appliedSearch.value.trim().toLowerCase()
  const f = appliedFilters.value

  const result = listings.filter((item) => {
    const matchSearch =
      !keyword ||
      item.title.toLowerCase().includes(keyword) ||
      item.location.toLowerCase().includes(keyword) ||
      item.type.toLowerCase().includes(keyword)

    const matchType =
      f.type === 'Tất cả' || item.type === f.type

    const matchMinPrice =
      f.minPrice === '' || item.price >= Number(f.minPrice)

    const matchMaxPrice =
      f.maxPrice === '' || item.price <= Number(f.maxPrice)

    const matchBeds =
      f.bedrooms === 0 || item.beds >= f.bedrooms

    const matchMinArea =
      f.minArea === '' || item.area >= Number(f.minArea)

    const matchMaxArea =
      f.maxArea === '' || item.area <= Number(f.maxArea)

    return (
      matchSearch &&
      matchType &&
      matchMinPrice &&
      matchMaxPrice &&
      matchBeds &&
      matchMinArea &&
      matchMaxArea
    )
  })

  if (sortBy.value === 'priceAsc') {
    result.sort((a, b) => a.price - b.price)
  } else if (sortBy.value === 'priceDesc') {
    result.sort((a, b) => b.price - a.price)
  } else if (sortBy.value === 'areaDesc') {
    result.sort((a, b) => b.area - a.area)
  }

  return result
})

const selectedListing = computed(() =>
  filteredListings.value.find(
    (item) => item.id === selectedId.value
  ) || null
)

const activeFilterCount = computed(() => {
  const f = appliedFilters.value

  return [
    f.type !== 'Tất cả',
    f.minPrice !== '',
    f.maxPrice !== '',
    f.bedrooms > 0,
    f.minArea !== '',
    f.maxArea !== ''
  ].filter(Boolean).length
})

function priceLabel(price) {
  return `${price.toLocaleString('vi-VN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })} tỷ`
}

function statusClass(type) {
  if (type === 'good') {
    return 'bg-[#E4F3EC] text-[#348567]'
  }

  if (type === 'warning') {
    return 'bg-[#F9E8DB] text-[#B76C42]'
  }

  return 'bg-[#FBE8DF] text-[#B65A43]'
}

function selectListing(id) {
  selectedId.value = id
  showDetails.value = true
}

function ensureSelectedVisible() {
  if (
    !filteredListings.value.some(
      (item) => item.id === selectedId.value
    )
  ) {
    selectedId.value = filteredListings.value[0]?.id ?? null
    showDetails.value = false
  }
}

function search() {
  appliedSearch.value = searchText.value
  ensureSelectedVisible()
}

function applyFilters() {
  const minimumPrice =
    minPrice.value === ''
      ? ''
      : Math.max(0, Number(minPrice.value))

  const maximumPrice =
    maxPrice.value === ''
      ? ''
      : Math.max(0, Number(maxPrice.value))

  const minimumArea =
    minArea.value === ''
      ? ''
      : Math.max(0, Number(minArea.value))

  const maximumArea =
    maxArea.value === ''
      ? ''
      : Math.max(0, Number(maxArea.value))

  if (
    (maximumPrice !== '' &&
      minimumPrice !== '' &&
      minimumPrice > maximumPrice) ||
    (maximumArea !== '' &&
      minimumArea !== '' &&
      minimumArea > maximumArea)
  ) {
    alert('Giá trị tối thiểu không được lớn hơn tối đa.')
    return
  }

  appliedFilters.value = {
    minPrice: minimumPrice,
    maxPrice: maximumPrice,
    type: selectedType.value,
    bedrooms: bedrooms.value,
    minArea: minimumArea,
    maxArea: maximumArea
  }

  showFilters.value = false
  ensureSelectedVisible()
}

function resetFilters() {
  minPrice.value = ''
  maxPrice.value = ''
  selectedType.value = 'Tất cả'
  bedrooms.value = 0
  minArea.value = ''
  maxArea.value = ''
  searchText.value = ''
  appliedSearch.value = ''
  sortBy.value = 'default'

  appliedFilters.value = {
    minPrice: '',
    maxPrice: '',
    type: 'Tất cả',
    bedrooms: 0,
    minArea: '',
    maxArea: ''
  }

  selectedId.value = 1
  showDetails.value = false
  showFilters.value = false
}

function zoomIn() {
  mapZoom.value = Math.min(1.6, mapZoom.value + 0.15)
}

function zoomOut() {
  mapZoom.value = Math.max(0.8, mapZoom.value - 0.15)
}

function openListing(id) {
  router.push(`/listing/${id}`)
}
</script>

<template>
  <div class="sp-gis min-h-screen w-full overflow-x-hidden bg-[#F7F5F0] text-[#142B4F]">

    <!-- HEADER -->
    <header class="relative z-30 border-b border-[#E7E2D8] bg-[#F7F5F0]/95">
      <div class="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-5 px-5 py-5 md:px-8 lg:px-10">

        <button
          type="button"
          @click="router.push('/home')"
          class="flex items-center gap-3"
        >
          <span class="flex h-10 w-10 items-center justify-center rounded-full bg-[#142B4F] font-serif text-lg text-white">
            S
          </span>

          <span class="text-xl font-semibold tracking-tight">
            SmartProp<span class="text-[#C6A77A]">.</span>
          </span>
        </button>

        <div class="hidden items-center gap-2 rounded-full border border-[#E4DED3] bg-white px-4 py-2 text-[11px] font-semibold uppercase tracking-[.16em] text-[#64748B] lg:flex">
          <span class="h-2 w-2 rounded-full bg-[#5CB9D3]"></span>
          Spatial Intelligence / GIS Explorer
        </div>

        <div class="flex items-center gap-3">
          <button
            type="button"
            @click="router.push('/post')"
            class="rounded-full border border-[#DCD5C8] px-5 py-3 text-xs font-semibold transition hover:border-[#142B4F]"
          >
            Đăng tin ↗
          </button>

          <button
            type="button"
            @click="router.push('/account')"
            class="rounded-full bg-[#142B4F] px-5 py-3 text-xs font-semibold text-white transition hover:bg-[#25466B]"
          >
            Tài khoản
          </button>
        </div>
      </div>
    </header>

    <!-- INTRO -->
    <section class="border-b border-[#E7E2D8]">
      <div class="mx-auto max-w-[1500px] px-5 pb-7 pt-9 md:px-8 lg:px-10">

        <div class="flex flex-wrap items-end justify-between gap-5">
          <div>
            <p class="text-[11px] font-bold uppercase tracking-[.25em] text-[#B49362]">
              SMARTPROP / LOCATION INTELLIGENCE
            </p>

            <h1 class="mt-3 font-serif text-4xl leading-tight sm:text-5xl">
              Khám phá bất động sản
              <span class="italic text-[#B49362]">theo vị trí.</span>
            </h1>

            <p class="mt-3 max-w-2xl text-sm leading-7 text-[#748194]">
              Kết nối danh sách bất động sản với góc nhìn không gian.
              Chọn một tin đăng để khám phá vị trí và thông tin liên quan.
            </p>
          </div>

          <span class="rounded-full border border-[#E2D8C8] bg-[#EEE7DB] px-4 py-2 text-[11px] font-bold uppercase tracking-[.12em] text-[#94774F]">
            Dữ liệu minh họa
          </span>
        </div>

        <!-- SEARCH -->
        <form
          @submit.prevent="search"
          class="mt-7 flex flex-col gap-3 sm:flex-row"
        >
          <div class="flex min-w-0 flex-1 items-center gap-3 rounded-xl border border-[#E4DED3] bg-white px-5 py-4">
            <span class="text-lg text-[#B49362]">⌕</span>

            <input
              v-model="searchText"
              type="search"
              placeholder="Tìm khu vực, loại hình hoặc tên bất động sản..."
              class="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-[#9AA4B1]"
            />
          </div>

          <button
            type="submit"
            class="rounded-xl bg-[#142B4F] px-8 py-4 text-xs font-semibold text-white transition hover:bg-[#25466B]"
          >
            Tìm kiếm ↗
          </button>

          <button
            type="button"
            @click="showFilters = !showFilters"
            class="rounded-xl border border-[#DCD5C8] bg-white px-6 py-4 text-xs font-semibold transition hover:border-[#142B4F]"
          >
            Bộ lọc
            <span v-if="activeFilterCount" class="ml-1 text-[#B49362]">
              ({{ activeFilterCount }})
            </span>
            ⌄
          </button>
        </form>

        <!-- FILTER SHORTCUTS -->
        <div class="mt-5 flex flex-wrap items-center gap-2">
          <button
            v-for="type in propertyTypes"
            :key="type"
            type="button"
            @click="selectedType = type; applyFilters()"
            class="rounded-full border px-4 py-2.5 text-[12px] font-semibold transition"
            :class="
              appliedFilters.type === type
                ? 'border-[#142B4F] bg-[#142B4F] text-white'
                : 'border-[#E4DED3] bg-white text-[#64748B] hover:border-[#C6A77A]'
            "
          >
            {{ type }}
          </button>

          <button
            type="button"
            @click="resetFilters"
            class="ml-auto text-[12px] font-semibold text-[#9B7952] underline underline-offset-4"
          >
            Xóa bộ lọc
          </button>
        </div>

        <!-- ADVANCED FILTER -->
        <div
          v-if="showFilters"
          class="mt-6 rounded-2xl border border-[#E4DED3] bg-white p-5 shadow-lg sm:p-7"
        >
          <div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">

            <div>
              <label class="mb-3 block text-xs font-semibold">
                Khoảng giá (tỷ VNĐ)
              </label>

              <div class="flex items-center gap-2">
                <input
                  v-model="minPrice"
                  type="number"
                  min="0"
                  step="0.1"
                  placeholder="Từ"
                  class="sp-gis-input min-w-0"
                />

                <span class="text-[#94A3B8]">—</span>

                <input
                  v-model="maxPrice"
                  type="number"
                  min="0"
                  step="0.1"
                  placeholder="Đến"
                  class="sp-gis-input min-w-0"
                />
              </div>
            </div>

            <div>
              <label class="mb-3 block text-xs font-semibold">
                Loại hình
              </label>

              <select v-model="selectedType" class="sp-gis-input">
                <option
                  v-for="type in propertyTypes"
                  :key="type"
                >
                  {{ type }}
                </option>
              </select>
            </div>

            <div>
              <label class="mb-3 block text-xs font-semibold">
                Số phòng ngủ tối thiểu
              </label>

              <div class="flex items-center gap-4">
                <button
                  type="button"
                  @click="bedrooms = Math.max(0, bedrooms - 1)"
                  class="flex h-10 w-10 items-center justify-center rounded-full border border-[#DDD8CF] text-lg"
                >
                  −
                </button>

                <span class="min-w-10 text-center text-sm font-semibold">
                  {{ bedrooms === 0 ? 'Bất kỳ' : bedrooms }}
                </span>

                <button
                  type="button"
                  @click="bedrooms = Math.min(10, bedrooms + 1)"
                  class="flex h-10 w-10 items-center justify-center rounded-full border border-[#DDD8CF] text-lg"
                >
                  +
                </button>
              </div>
            </div>

            <div>
              <label class="mb-3 block text-xs font-semibold">
                Diện tích (m²)
              </label>

              <div class="flex items-center gap-2">
                <input
                  v-model="minArea"
                  type="number"
                  min="0"
                  placeholder="Từ"
                  class="sp-gis-input min-w-0"
                />

                <span class="text-[#94A3B8]">—</span>

                <input
                  v-model="maxArea"
                  type="number"
                  min="0"
                  placeholder="Đến"
                  class="sp-gis-input min-w-0"
                />
              </div>
            </div>
          </div>

          <div class="mt-6 flex flex-wrap justify-end gap-3 border-t border-[#ECE7DE] pt-5">
            <button
              type="button"
              @click="resetFilters"
              class="rounded-full border border-[#DDD8CF] px-6 py-3 text-xs font-semibold"
            >
              Đặt lại
            </button>

            <button
              type="button"
              @click="applyFilters"
              class="rounded-full bg-[#142B4F] px-7 py-3 text-xs font-semibold text-white"
            >
              Áp dụng bộ lọc ↗
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- MAIN CONTENT -->
    <main class="mx-auto max-w-[1500px] px-5 pb-12 pt-7 md:px-8 lg:px-10">

      <div class="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,430px)_minmax(0,1fr)]">

        <!-- LISTINGS -->
        <section class="min-w-0">

          <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p class="text-[11px] font-bold uppercase tracking-[.2em] text-[#B49362]">
                PROPERTY COLLECTION
              </p>

              <h2 class="mt-2 font-serif text-2xl">
                {{ filteredListings.length }} bất động sản
              </h2>
            </div>

            <select
              v-model="sortBy"
              aria-label="Sắp xếp bất động sản"
              class="max-w-full rounded-lg border border-[#E2DDD3] bg-white px-3 py-3 text-[12px] outline-none"
            >
              <option value="default">Mặc định</option>
              <option value="priceAsc">Giá thấp đến cao</option>
              <option value="priceDesc">Giá cao đến thấp</option>
              <option value="areaDesc">Diện tích lớn nhất</option>
            </select>
          </div>

          <div class="space-y-4">

            <article
              v-for="listing in filteredListings"
              :key="listing.id"
              tabindex="0"
              role="button"
              :aria-pressed="selectedId === listing.id"
              @click="selectListing(listing.id)"
              @keydown.enter.prevent="selectListing(listing.id)"
              @keydown.space.prevent="selectListing(listing.id)"
              class="group cursor-pointer overflow-hidden rounded-2xl border bg-white transition duration-300 hover:-translate-y-1 hover:shadow-xl"
              :class="
                selectedId === listing.id
                  ? 'border-[#C6A77A] shadow-[0_10px_35px_rgba(20,43,79,.09)]'
                  : 'border-[#E8E3DA]'
              "
            >
              <div class="flex min-w-0 flex-col sm:flex-row lg:flex-row">

                <div class="relative h-48 shrink-0 overflow-hidden sm:h-auto sm:w-[145px] lg:w-[145px]">
                  <img
                    :src="listing.image"
                    :alt="listing.title"
                    loading="lazy"
                    class="h-full w-full object-cover transition duration-500 group-hover:scale-105"
                  />

                  <span
                    v-if="selectedId === listing.id"
                    class="absolute left-3 top-3 rounded-full bg-[#142B4F] px-3 py-1.5 text-[10px] font-semibold text-white"
                  >
                    Đang chọn
                  </span>
                </div>

                <div class="min-w-0 flex-1 p-4">

                  <span
                    class="inline-block max-w-full rounded-full px-3 py-1 text-[10px] font-semibold"
                    :class="statusClass(listing.statusType)"
                  >
                    {{ listing.status }}
                  </span>

                  <h3 class="mt-3 text-[14px] font-bold leading-6 text-[#142B4F]">
                    {{ listing.title }}
                  </h3>

                  <p class="mt-2 text-[12px] text-[#8190A0]">
                    ⌖ {{ listing.location }}
                  </p>

                  <p class="mt-3 font-serif text-2xl">
                    {{ priceLabel(listing.price) }}
                  </p>

                  <div class="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-[11px] text-[#778394]">
                    <span>{{ listing.area }} m²</span>
                    <span>{{ listing.type }}</span>
                    <span v-if="listing.beds">
                      {{ listing.beds }} PN
                    </span>
                  </div>
                </div>
              </div>
            </article>

            <div
              v-if="!filteredListings.length"
              class="rounded-2xl border border-[#E8E3DA] bg-white px-6 py-12 text-center"
            >
              <p class="font-serif text-2xl">
                Không tìm thấy bất động sản.
              </p>

              <p class="mt-3 text-sm text-[#778394]">
                Hãy thử thay đổi khu vực hoặc bộ lọc.
              </p>

              <button
                type="button"
                @click="resetFilters"
                class="mt-6 rounded-full bg-[#142B4F] px-6 py-3 text-xs font-semibold text-white"
              >
                Xem tất cả
              </button>
            </div>
          </div>

          <p class="mt-5 text-[12px] leading-6 text-[#87919F]">
            Tin đăng, hình ảnh, giá và trạng thái đánh giá
            đều là dữ liệu minh họa.
          </p>
        </section>

        <!-- MAP PANEL -->
        <section
          class="relative min-w-0 overflow-hidden rounded-[26px] border border-[#D9DED9] shadow-[0_18px_60px_rgba(20,43,79,.08)] lg:sticky lg:top-5 lg:h-[790px]"
          :class="
            mapMode === 'dark'
              ? 'bg-[#102B3D] text-white'
              : 'bg-[#E7EDE7] text-[#142B4F]'
          "
        >
          <div class="relative h-[520px] overflow-hidden sm:h-[650px] lg:h-full">

            <!-- SCHEMATIC MAP -->
            <div
              class="absolute inset-0 origin-center transition-transform duration-500"
              :style="{ transform: `scale(${mapZoom})` }"
            >
              <div
                class="sp-gis-grid absolute inset-0"
                :class="mapMode === 'dark' ? 'sp-gis-grid-dark' : ''"
              ></div>

              <svg
                viewBox="0 0 800 800"
                preserveAspectRatio="xMidYMid slice"
                class="absolute inset-0 h-full w-full"
                aria-hidden="true"
              >
                <g
                  :fill="mapMode === 'dark' ? '#244458' : '#D5DED5'"
                  opacity=".85"
                >
                  <rect x="45" y="60" width="155" height="100" rx="15" transform="rotate(-12 45 60)" />
                  <rect x="260" y="55" width="150" height="120" rx="15" transform="rotate(12 260 55)" />
                  <rect x="70" y="310" width="145" height="130" rx="15" transform="rotate(-10 70 310)" />
                  <rect x="270" y="430" width="160" height="120" rx="15" transform="rotate(10 270 430)" />
                  <rect x="55" y="620" width="190" height="120" rx="15" transform="rotate(-8 55 620)" />
                  <rect x="500" y="600" width="130" height="130" rx="15" />
                </g>

                <path
                  d="M600 -70 C480 80 620 170 520 280 C400 420 610 520 500 680 C450 750 520 820 520 850"
                  fill="none"
                  :stroke="mapMode === 'dark' ? '#276E86' : '#9FD4DE'"
                  stroke-width="110"
                  opacity=".85"
                />

                <path
                  d="M600 -70 C480 80 620 170 520 280 C400 420 610 520 500 680 C450 750 520 820 520 850"
                  fill="none"
                  :stroke="mapMode === 'dark' ? '#52B5CB' : '#C9EFF3'"
                  stroke-width="65"
                  opacity=".65"
                />

                <g
                  fill="none"
                  :stroke="mapMode === 'dark' ? '#527181' : '#FFFFFF'"
                  stroke-width="18"
                  opacity=".9"
                >
                  <path d="M-30 180 L850 400" />
                  <path d="M-30 510 L850 200" />
                  <path d="M220 -30 L370 850" />
                  <path d="M-20 700 L850 590" />
                </g>

                <g
                  fill="none"
                  :stroke="mapMode === 'dark' ? '#38596C' : '#D1D8D1'"
                  stroke-width="2"
                  stroke-dasharray="8 10"
                >
                  <path d="M-30 180 L850 400" />
                  <path d="M-30 510 L850 200" />
                  <path d="M220 -30 L370 850" />
                  <path d="M-20 700 L850 590" />
                </g>
              </svg>

              <!-- DISTRICT LABELS -->
              <span class="pointer-events-none absolute left-[13%] top-[18%] text-[12px] font-bold uppercase tracking-[.2em] opacity-40">
                Thanh Khê
              </span>

              <span class="pointer-events-none absolute left-[43%] top-[43%] text-[12px] font-bold uppercase tracking-[.2em] opacity-40">
                Hải Châu
              </span>

              <span class="pointer-events-none absolute right-[7%] top-[16%] text-[12px] font-bold uppercase tracking-[.2em] opacity-40">
                Sơn Trà
              </span>

              <span class="pointer-events-none absolute left-[30%] bottom-[12%] text-[12px] font-bold uppercase tracking-[.2em] opacity-40">
                Cẩm Lệ
              </span>

              <!-- PRICE MARKERS -->
              <button
                v-for="listing in filteredListings"
                :key="listing.id"
                type="button"
                @click="selectListing(listing.id)"
                class="absolute z-10 -translate-x-1/2 -translate-y-1/2 whitespace-nowrap rounded-full border px-3 py-2 text-[12px] font-bold shadow-lg transition duration-300 hover:scale-110"
                :class="
                  selectedId === listing.id
                    ? 'border-[#E8CAA0] bg-[#C6A77A] text-[#142B4F] ring-4 ring-[#C6A77A]/25'
                    : listing.statusType === 'high'
                      ? 'border-[#D97E60] bg-[#C86646] text-white'
                      : 'border-white/20 bg-[#142B4F] text-white'
                "
                :style="{
                  left: `${listing.x}%`,
                  top: `${listing.y}%`
                }"
              >
                {{ priceLabel(listing.price) }}
              </button>
            </div>

            <!-- MAP TOP BAR -->
            <div class="pointer-events-none absolute left-4 right-4 top-4 z-20 flex flex-wrap items-start justify-between gap-3">

              <div class="pointer-events-auto rounded-xl border border-white/20 bg-[#142B4F]/95 px-5 py-4 text-white shadow-xl backdrop-blur-xl">
                <p class="text-[11px] font-bold uppercase tracking-[.2em] text-[#6DD5E7]">
                  GIS EXPLORER
                </p>

                <p class="mt-2 text-sm font-semibold">
                  Đà Nẵng · Spatial View
                </p>

                <p class="mt-1 text-[11px] text-white/55">
                  Sơ đồ vị trí minh họa
                </p>
              </div>

              <span class="pointer-events-auto rounded-full border border-white/30 bg-white/95 px-4 py-2 text-[11px] font-semibold text-[#142B4F] shadow-lg">
                {{ filteredListings.length }} điểm hiển thị
              </span>
            </div>

            <!-- MAP CONTROLS -->
            <div class="absolute right-4 top-36 z-20 flex flex-col gap-2">
              <button
                type="button"
                aria-label="Phóng to sơ đồ"
                @click="zoomIn"
                class="sp-gis-map-control"
              >
                +
              </button>

              <button
                type="button"
                aria-label="Thu nhỏ sơ đồ"
                @click="zoomOut"
                class="sp-gis-map-control"
              >
                −
              </button>

              <button
                type="button"
                aria-label="Đặt lại tỷ lệ sơ đồ"
                @click="mapZoom = 1"
                class="sp-gis-map-control text-xs"
              >
                1:1
              </button>

              <button
                type="button"
                :aria-label="mapMode === 'light' ? 'Chế độ tối' : 'Chế độ sáng'"
                @click="mapMode = mapMode === 'light' ? 'dark' : 'light'"
                class="sp-gis-map-control text-sm"
              >
                {{ mapMode === 'light' ? '☾' : '☀' }}
              </button>
            </div>

            <!-- SELECTED PROPERTY PANEL -->
            <div
              v-if="showDetails && selectedListing"
              class="absolute bottom-16 left-4 right-4 z-20 overflow-hidden rounded-2xl border border-white/25 bg-white/95 text-[#142B4F] shadow-2xl backdrop-blur-xl sm:left-5 sm:right-auto sm:w-[370px]"
            >
              <div class="flex items-start gap-4 p-4">

                <img
                  :src="selectedListing.image"
                  :alt="selectedListing.title"
                  class="h-24 w-24 shrink-0 rounded-xl object-cover"
                />

                <div class="min-w-0 flex-1">
                  <p class="text-[11px] font-bold uppercase tracking-[.15em] text-[#B49362]">
                    PROPERTY INSIGHT
                  </p>

                  <h3 class="mt-2 text-xs font-bold leading-5">
                    {{ selectedListing.title }}
                  </h3>

                  <p class="mt-2 font-serif text-xl">
                    {{ priceLabel(selectedListing.price) }}
                  </p>

                  <p class="mt-1 text-[11px] text-[#778394]">
                    {{ selectedListing.area }} m² ·
                    {{ selectedListing.location }}
                  </p>
                </div>

                <button
                  type="button"
                  aria-label="Đóng thông tin bất động sản"
                  @click="showDetails = false"
                  class="text-xl text-[#64748B]"
                >
                  ×
                </button>
              </div>

              <div class="flex items-center justify-between border-t border-[#E7E2D8] px-4 py-3">
                <span class="text-[11px] text-[#87919F]">
                  Tin đăng minh họa
                </span>

                <button
                  type="button"
                  @click="openListing(selectedListing.id)"
                  class="text-xs font-bold text-[#142B4F] underline underline-offset-4"
                >
                  Xem chi tiết ↗
                </button>
              </div>
            </div>

            <!-- MAP FOOTER -->
            <div class="absolute bottom-0 left-0 right-0 z-10 flex flex-wrap items-center justify-between gap-2 bg-[#142B4F]/95 px-5 py-4 text-[11px] text-white/70 backdrop-blur-xl">
              <span class="flex items-center gap-2">
                <span class="h-2 w-2 rounded-full bg-[#6DD5E7]"></span>
                Spatial Intelligence Demo
              </span>

              <span>
                Không phải bản đồ GIS địa lý thực
              </span>
            </div>
          </div>
        </section>
      </div>
    </main>

    <!-- FOOTER -->
    <footer class="border-t border-[#E7E2D8] bg-[#F7F5F0]">
      <div class="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-3 px-5 py-6 text-[12px] text-[#87919F] md:px-8 lg:px-10">
        <span>© 2026 SmartProp · GIS Explorer 2.1</span>

        <button
          type="button"
          @click="router.push('/home')"
          class="font-semibold text-[#142B4F]"
        >
          Quay về trang chủ ↗
        </button>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* SmartProp GIS: chỉ thay font trong trang bản đồ */

.sp-gis {
  width: 100%;
  max-width: 100%;
  overflow-x: clip;
  font-family: var(--font-sans);
  font-synthesis: none;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

.sp-gis :deep(.font-serif) {
  font-family: var(--font-serif);
  font-synthesis: none;
  font-kerning: normal;
  letter-spacing: normal;
}

.sp-gis h1,
.sp-gis h2,
.sp-gis h3 {
  word-spacing: normal;
  font-kerning: normal;
  overflow-wrap: break-word;
}

.sp-gis button,
.sp-gis input,
.sp-gis select,
.sp-gis textarea {
  font-family: var(--font-sans);
}

.sp-gis main,
.sp-gis section,
.sp-gis article {
  min-width: 0;
}

/* =====================================
   INPUTS
===================================== */

.sp-gis-input {
  width: 100%;
  min-width: 0;
  border: 1px solid #e4ded3;
  border-radius: 10px;
  background: #faf9f6;
  padding: 12px;
  color: #142b4f;
  font-size: var(--text-xs);
  outline: none;
}

.sp-gis-input:focus {
  border-color: #5cb9d3;
  box-shadow: 0 0 0 3px rgba(92, 185, 211, 0.12);
}

/* =====================================
   MAP
===================================== */

.sp-gis-grid {
  background-color: #e7ede7;
  background-image:
    linear-gradient(
      rgba(72, 110, 116, 0.08) 1px,
      transparent 1px
    ),
    linear-gradient(
      90deg,
      rgba(72, 110, 116, 0.08) 1px,
      transparent 1px
    );
  background-size: 42px 42px;
}

.sp-gis-grid-dark {
  background-color: #102b3d;
  background-image:
    linear-gradient(
      rgba(109, 213, 231, 0.08) 1px,
      transparent 1px
    ),
    linear-gradient(
      90deg,
      rgba(109, 213, 231, 0.08) 1px,
      transparent 1px
    );
}

.sp-gis-map-control {
  display: flex;
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(20, 43, 79, 0.08);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.96);
  color: #142b4f;
  font-size: var(--text-xl);
  font-weight: 700;
  box-shadow: 0 5px 20px rgba(20, 43, 79, 0.12);
  transition:
    transform 0.2s ease,
    background 0.2s ease;
}

.sp-gis-map-control:hover {
  transform: translateY(-2px);
  background: #f2e8d9;
}

@media (prefers-reduced-motion: reduce) {
  .sp-gis *,
  .sp-gis *::before,
  .sp-gis *::after {
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}
</style>
