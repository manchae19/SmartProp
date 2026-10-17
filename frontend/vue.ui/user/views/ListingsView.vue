
<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

/*
  SMARTPROP PROPERTY COLLECTION 2.0
  Vue 3 + Tailwind CSS
  Dữ liệu minh họa, chưa kết nối backend
*/

const searchText = ref('')
const selectedType = ref('Tất cả')
const selectedPrice = ref('Tất cả')
const selectedDistrict = ref('Tất cả')
const sortBy = ref('default')
const viewMode = ref('grid')

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

const listings = [
  {
    id: 1,
    title: 'Nhà 3 tầng hẻm xe hơi, gần cầu Rồng',
    location: 'Hải Châu, Đà Nẵng',
    district: 'Hải Châu',
    price: 4.85,
    type: 'Nhà phố',
    area: 92,
    bedrooms: 3,
    bathrooms: 2,
    status: 'Ảnh trùng 94%',
    statusType: 'warning',
    image:
      'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=1200&q=85',
    label: 'Urban Residence',
    number: '01'
  },
  {
    id: 2,
    title: 'Căn hộ 2PN view sông Hàn',
    location: 'Hải Châu, Đà Nẵng',
    district: 'Hải Châu',
    price: 3.2,
    type: 'Căn hộ',
    area: 78,
    bedrooms: 2,
    bathrooms: 2,
    status: 'Không cảnh báo',
    statusType: 'safe',
    image:
      'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=1200&q=85',
    label: 'Riverfront Living',
    number: '02'
  },
  {
    id: 3,
    title: 'Đất nền Hoà Xuân, sổ đỏ riêng',
    location: 'Cẩm Lệ, Đà Nẵng',
    district: 'Cẩm Lệ',
    price: 2.95,
    type: 'Đất nền',
    area: 100,
    bedrooms: null,
    bathrooms: null,
    status: 'Giá hợp lý',
    statusType: 'safe',
    image:
      'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1200&q=85',
    label: 'Land Opportunity',
    number: '03'
  }
]

const filteredListings = computed(() => {
  const keyword = searchText.value
    .trim()
    .toLocaleLowerCase('vi-VN')

  const result = listings.filter((item) => {
    const searchContent = [
      item.title,
      item.location,
      item.district,
      item.type
    ]
      .join(' ')
      .toLocaleLowerCase('vi-VN')

    const matchesSearch =
      !keyword || searchContent.includes(keyword)

    const matchesType =
      selectedType.value === 'Tất cả' ||
      item.type === selectedType.value

    const matchesDistrict =
      selectedDistrict.value === 'Tất cả' ||
      item.district === selectedDistrict.value

    let matchesPrice = true

    if (selectedPrice.value === 'Dưới 3 tỷ') {
      matchesPrice = item.price < 3
    } else if (selectedPrice.value === '3 - 5 tỷ') {
      matchesPrice = item.price >= 3 && item.price <= 5
    } else if (selectedPrice.value === 'Trên 5 tỷ') {
      matchesPrice = item.price > 5
    }

    return (
      matchesSearch &&
      matchesType &&
      matchesDistrict &&
      matchesPrice
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

const activeFilterCount = computed(() => {
  return [
    searchText.value.trim() !== '',
    selectedType.value !== 'Tất cả',
    selectedPrice.value !== 'Tất cả',
    selectedDistrict.value !== 'Tất cả'
  ].filter(Boolean).length
})

const averagePrice = computed(() => {
  if (!filteredListings.value.length) return '—'

  const total = filteredListings.value.reduce(
    (sum, item) => sum + item.price,
    0
  )

  return formatPrice(total / filteredListings.value.length)
})

function formatPrice(price) {
  return price.toLocaleString('vi-VN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

function resetFilters() {
  searchText.value = ''
  selectedType.value = 'Tất cả'
  selectedPrice.value = 'Tất cả'
  selectedDistrict.value = 'Tất cả'
  sortBy.value = 'default'
}

function statusClass(type) {
  return type === 'warning'
    ? 'bg-[#F9E8DB] text-[#A95E3C]'
    : 'bg-[#E4F3EC] text-[#2F8061]'
}

function openListing(id) {
  router.push(`/listing/${id}`)
}

function goHome() {
  router.push('/home')
}

function goMap() {
  router.push('/map')
}

function goAccount() {
  router.push('/account')
}

function goPost() {
  router.push('/post')
}
</script>

<template>
  <div
    class="sp-collection min-h-screen w-full overflow-x-hidden bg-[#F7F5F0] text-[#142B4F]"
  >
    <!-- HEADER -->
    <header
      class="relative z-30 border-b border-[#E7E2D8] bg-[#F7F5F0]/95"
    >
      <div
        class="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-4 px-5 py-5 md:px-8 lg:px-12"
      >
        <div class="flex items-center gap-6">
          <button
            type="button"
            @click="goHome"
            class="flex items-center gap-3"
          >
            <span
              class="flex h-10 w-10 items-center justify-center rounded-full bg-[#142B4F] font-bold text-white"
            >
              S
            </span>

            <span class="text-xl font-bold tracking-tight">
              SmartProp<span class="text-[#C6A77A]">.</span>
            </span>
          </button>

          <button
            type="button"
            @click="goHome"
            class="hidden text-xs text-[#87919F] transition hover:text-[#142B4F] md:block"
          >
            ← Trang chủ
          </button>
        </div>

        <div
          class="hidden items-center gap-2 rounded-full border border-[#E4DED3] bg-white px-4 py-2 lg:flex"
        >
          <span
            class="h-2 w-2 rounded-full bg-[#5CB9D3]"
          ></span>

          <span
            class="text-[10px] font-bold uppercase tracking-[0.15em] text-[#64748B]"
          >
            SmartProp / Property Collection
          </span>
        </div>

        <div class="flex items-center gap-2 sm:gap-3">
          <button
            type="button"
            @click="goMap"
            class="hidden rounded-full border border-[#DED8CE] bg-white px-5 py-3 text-xs font-semibold transition hover:border-[#C6A77A] sm:block"
          >
            GIS Explorer ↗
          </button>

          <button
            type="button"
            @click="goPost"
            class="rounded-full border border-[#DED8CE] bg-white px-4 py-3 text-xs font-semibold transition hover:border-[#C6A77A] sm:px-5"
          >
            Đăng tin ↗
          </button>

          <button
            type="button"
            @click="goAccount"
            class="rounded-full bg-[#142B4F] px-4 py-3 text-xs font-semibold text-white transition hover:bg-[#25466B] sm:px-5"
          >
            Tài khoản
          </button>
        </div>
      </div>
    </header>

    <!-- INTRO -->
    <section class="relative overflow-hidden border-b border-[#E7E2D8]">
      <div
        class="pointer-events-none absolute -right-24 -top-36 h-[430px] w-[430px] rounded-full border border-[#C6A77A]/20"
      ></div>

      <div
        class="pointer-events-none absolute -right-10 -top-16 h-[290px] w-[290px] rounded-full border border-[#C6A77A]/20"
      ></div>

      <div
        class="relative mx-auto max-w-[1440px] px-5 pb-12 pt-12 md:px-8 md:pb-16 md:pt-16 lg:px-12"
      >
        <div
          class="grid min-w-0 gap-9 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)] lg:items-end"
        >
          <div class="min-w-0">
            <div class="flex items-center gap-3">
              <span
                class="h-px w-9 bg-[#B49362]"
              ></span>

              <p
                class="text-[10px] font-bold uppercase tracking-[0.24em] text-[#B49362]"
              >
                SMARTPROP / CURATED REAL ESTATE
              </p>
            </div>

            <h1
              class="mt-6 max-w-[780px] text-[40px] font-medium leading-[1.18] tracking-[-0.035em] sm:text-[55px] lg:text-[65px]"
            >
              Không gian sống
              <span
                class="block italic text-[#B49362]"
              >
                dành riêng cho bạn.
              </span>
            </h1>

            <p
              class="mt-6 max-w-[630px] text-sm leading-8 text-[#748194] sm:text-[15px]"
            >
              Khám phá những lựa chọn bất động sản tại Đà Nẵng.
              Tìm kiếm theo nhu cầu, so sánh mức giá và kết nối
              mỗi tin đăng với góc nhìn không gian trên bản đồ.
            </p>

            <div class="mt-7 flex flex-wrap items-center gap-3">
              <span
                class="rounded-full border border-[#E2D8C8] bg-[#EEE7DB] px-4 py-2 text-[10px] font-bold uppercase tracking-[0.12em] text-[#94774F]"
              >
                Dữ liệu minh họa
              </span>

              <span
                class="flex items-center gap-2 text-[11px] text-[#748194]"
              >
                <span
                  class="h-2 w-2 rounded-full bg-[#5CB9D3]"
                ></span>
                Data Driven · GIS · Property Insights
              </span>
            </div>
          </div>

          <!-- EDITORIAL FEATURE -->
          <div
            class="relative min-w-0 overflow-hidden rounded-[24px] bg-[#142B4F] p-6 text-white sm:p-8"
          >
            <div
              class="pointer-events-none absolute -right-12 -top-12 h-48 w-48 rounded-full border border-white/10"
            ></div>

            <div
              class="pointer-events-none absolute -right-2 top-8 h-32 w-32 rounded-full border border-[#C6A77A]/25"
            ></div>

            <div class="relative">
              <div class="flex items-center justify-between gap-3">
                <span
                  class="text-[10px] font-bold uppercase tracking-[0.18em] text-[#7BD4E5]"
                >
                  Collection Overview
                </span>

                <span
                  class="rounded-full border border-white/20 px-3 py-1 text-[10px] text-white/70"
                >
                  2026
                </span>
              </div>

              <div class="mt-10 grid grid-cols-2 gap-5">
                <div>
                  <p
                    class="text-[10px] uppercase tracking-[0.15em] text-white/50"
                  >
                    Kết quả hiển thị
                  </p>

                  <p class="mt-3 text-4xl font-semibold">
                    {{ filteredListings.length }}
                    <span
                      class="text-lg text-[#C6A77A]"
                    >
                      / {{ listings.length }}
                    </span>
                  </p>
                </div>

                <div>
                  <p
                    class="text-[10px] uppercase tracking-[0.15em] text-white/50"
                  >
                    Giá trung bình
                  </p>

                  <p class="mt-3 text-3xl font-semibold">
                    {{ averagePrice }}
                    <span
                      v-if="filteredListings.length"
                      class="text-base text-[#C6A77A]"
                    >
                      tỷ
                    </span>
                  </p>
                </div>
              </div>

              <div class="mt-8 h-px bg-white/15"></div>

              <div class="mt-6 flex items-center justify-between gap-4">
                <div>
                  <p
                    class="text-xs font-semibold"
                  >
                    Khám phá bằng bản đồ
                  </p>

                  <p
                    class="mt-1 text-[11px] leading-5 text-white/55"
                  >
                    Xem vị trí và các tin đăng trên GIS Explorer.
                  </p>
                </div>

                <button
                  type="button"
                  @click="goMap"
                  aria-label="Mở GIS Explorer"
                  class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#C6A77A] text-lg text-[#142B4F] transition hover:scale-105"
                >
                  ↗
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- SEARCH & FILTER -->
    <section
      class="border-b border-[#E7E2D8] bg-white"
    >
      <div
        class="mx-auto max-w-[1440px] px-5 py-8 md:px-8 lg:px-12"
      >
        <div
          class="flex flex-wrap items-center justify-between gap-3"
        >
          <div>
            <p
              class="text-[10px] font-bold uppercase tracking-[0.2em] text-[#B49362]"
            >
              FIND YOUR PROPERTY
            </p>

            <h2
              class="mt-2 text-2xl font-semibold tracking-tight"
            >
              Tìm kiếm theo nhu cầu
            </h2>
          </div>

          <span
            class="text-xs text-[#87919F]"
          >
            {{ activeFilterCount }} bộ lọc đang sử dụng
          </span>
        </div>

        <div
          class="mt-6 grid min-w-0 gap-3 lg:grid-cols-[minmax(0,1fr)_190px_190px_190px]"
        >
          <div
            class="flex min-w-0 items-center gap-3 rounded-xl border border-[#E4DED3] bg-[#F9F8F5] px-5"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#B49362"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="shrink-0"
            >
              <circle cx="11" cy="11" r="7"></circle>
              <path d="m20 20-4-4"></path>
            </svg>

            <input
              v-model="searchText"
              type="search"
              aria-label="Tìm kiếm bất động sản"
              placeholder="Tìm theo tên tin đăng, loại hình hoặc khu vực..."
              class="h-[54px] min-w-0 w-full bg-transparent text-sm text-[#142B4F] outline-none placeholder:text-[#9AA4B1]"
            />
          </div>

          <div class="min-w-0">
            <label
              for="sp-type"
              class="sr-only"
            >
              Loại bất động sản
            </label>

            <select
              id="sp-type"
              v-model="selectedType"
              class="h-[54px] w-full rounded-xl border border-[#E4DED3] bg-[#F9F8F5] px-4 text-xs text-[#142B4F] outline-none focus:border-[#C6A77A]"
            >
              <option
                v-for="type in propertyTypes"
                :key="type"
                :value="type"
              >
                {{ type === 'Tất cả' ? 'Mọi loại hình' : type }}
              </option>
            </select>
          </div>

          <div class="min-w-0">
            <label
              for="sp-price"
              class="sr-only"
            >
              Khoảng giá
            </label>

            <select
              id="sp-price"
              v-model="selectedPrice"
              class="h-[54px] w-full rounded-xl border border-[#E4DED3] bg-[#F9F8F5] px-4 text-xs text-[#142B4F] outline-none focus:border-[#C6A77A]"
            >
              <option
                v-for="price in priceRanges"
                :key="price"
                :value="price"
              >
                {{ price === 'Tất cả' ? 'Mọi mức giá' : price }}
              </option>
            </select>
          </div>

          <div class="min-w-0">
            <label
              for="sp-district"
              class="sr-only"
            >
              Khu vực
            </label>

            <select
              id="sp-district"
              v-model="selectedDistrict"
              class="h-[54px] w-full rounded-xl border border-[#E4DED3] bg-[#F9F8F5] px-4 text-xs text-[#142B4F] outline-none focus:border-[#C6A77A]"
            >
              <option
                v-for="district in districts"
                :key="district"
                :value="district"
              >
                {{ district === 'Tất cả' ? 'Mọi khu vực' : district }}
              </option>
            </select>
          </div>
        </div>

        <div
          class="mt-5 flex flex-wrap items-center justify-between gap-4"
        >
          <div
            class="flex flex-wrap items-center gap-2"
          >
            <span
              class="mr-2 text-[11px] font-semibold text-[#87919F]"
            >
              Khám phá nhanh:
            </span>

            <button
              v-for="type in propertyTypes"
              :key="type"
              type="button"
              @click="selectedType = type"
              class="rounded-full border px-4 py-2 text-[11px] font-semibold transition"
              :class="
                selectedType === type
                  ? 'border-[#142B4F] bg-[#142B4F] text-white'
                  : 'border-[#E4DED3] bg-white text-[#64748B] hover:border-[#C6A77A]'
              "
            >
              {{ type }}
            </button>
          </div>

          <button
            type="button"
            @click="resetFilters"
            class="text-[11px] font-semibold text-[#9B7952] underline underline-offset-4 transition hover:text-[#142B4F]"
          >
            Xóa bộ lọc
          </button>
        </div>
      </div>
    </section>

    <!-- COLLECTION -->
    <main
      class="mx-auto max-w-[1440px] px-5 pb-20 pt-12 md:px-8 lg:px-12"
    >
      <div
        class="flex flex-wrap items-end justify-between gap-5"
      >
        <div>
          <p
            class="text-[10px] font-bold uppercase tracking-[0.2em] text-[#B49362]"
          >
            PROPERTY COLLECTION / 01
          </p>

          <h2
            class="mt-3 text-3xl font-medium tracking-tight sm:text-4xl"
          >
            Bất động sản
            <span class="italic text-[#B49362]">
              nổi bật.
            </span>
          </h2>

          <p
            class="mt-3 text-sm text-[#87919F]"
          >
            {{ filteredListings.length }} kết quả phù hợp với bộ lọc của bạn.
          </p>
        </div>

        <div
          class="flex flex-wrap items-center gap-3"
        >
          <label
            for="sp-sort"
            class="sr-only"
          >
            Sắp xếp
          </label>

          <select
            id="sp-sort"
            v-model="sortBy"
            class="h-11 rounded-xl border border-[#E4DED3] bg-white px-4 text-xs outline-none"
          >
            <option value="default">Sắp xếp mặc định</option>
            <option value="priceAsc">Giá thấp đến cao</option>
            <option value="priceDesc">Giá cao đến thấp</option>
            <option value="areaDesc">Diện tích lớn nhất</option>
          </select>

          <div
            class="flex overflow-hidden rounded-xl border border-[#E4DED3] bg-white"
          >
            <button
              type="button"
              aria-label="Xem dạng lưới"
              :aria-pressed="viewMode === 'grid'"
              @click="viewMode = 'grid'"
              class="flex h-11 w-11 items-center justify-center text-lg transition"
              :class="
                viewMode === 'grid'
                  ? 'bg-[#142B4F] text-white'
                  : 'text-[#87919F] hover:bg-[#F7F5F0]'
              "
            >
              ▦
            </button>

            <button
              type="button"
              aria-label="Xem dạng danh sách"
              :aria-pressed="viewMode === 'list'"
              @click="viewMode = 'list'"
              class="flex h-11 w-11 items-center justify-center text-lg transition"
              :class="
                viewMode === 'list'
                  ? 'bg-[#142B4F] text-white'
                  : 'text-[#87919F] hover:bg-[#F7F5F0]'
              "
            >
              ☷
            </button>
          </div>
        </div>
      </div>

      <!-- RESULTS -->
      <div
        v-if="filteredListings.length"
        class="mt-8 grid min-w-0 gap-6"
        :class="
          viewMode === 'grid'
            ? 'grid-cols-1 md:grid-cols-2 xl:grid-cols-3'
            : 'grid-cols-1'
        "
      >
        <article
          v-for="listing in filteredListings"
          :key="listing.id"
          class="group min-w-0 overflow-hidden rounded-[22px] border border-[#E8E3DA] bg-white transition duration-300 hover:-translate-y-1 hover:border-[#C6A77A] hover:shadow-[0_18px_50px_rgba(20,43,79,.10)]"
          :class="
            viewMode === 'list'
              ? 'flex flex-col md:flex-row'
              : ''
          "
        >
          <!-- IMAGE -->
          <button
            type="button"
            @click="openListing(listing.id)"
            class="relative block w-full shrink-0 overflow-hidden text-left"
            :class="
              viewMode === 'list'
                ? 'h-[250px] md:h-auto md:w-[38%]'
                : 'h-[260px] sm:h-[300px]'
            "
          >
            <img
              :src="listing.image"
              :alt="`Ảnh minh họa: ${listing.title}`"
              loading="lazy"
              class="h-full w-full object-cover transition duration-700 group-hover:scale-105"
            />

            <div
              class="absolute inset-0 bg-gradient-to-t from-[#071728]/50 via-transparent to-transparent"
            ></div>

            <span
              class="absolute left-5 top-5 rounded-full px-4 py-2 text-[10px] font-bold shadow-sm"
              :class="statusClass(listing.statusType)"
            >
              {{ listing.status }}
            </span>

            <span
              class="absolute bottom-5 left-5 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/90"
            >
              {{ listing.label }}
            </span>

            <span
              class="absolute bottom-5 right-5 text-3xl font-light text-white/80"
            >
              {{ listing.number }}
            </span>
          </button>

          <!-- CONTENT -->
          <div
            class="flex min-w-0 flex-1 flex-col p-6 sm:p-7"
          >
            <div
              class="flex items-center justify-between gap-3"
            >
              <span
                class="text-[10px] font-bold uppercase tracking-[0.15em] text-[#B49362]"
              >
                {{ listing.type }}
              </span>

              <span
                class="text-[10px] text-[#9AA4B1]"
              >
                Đà Nẵng
              </span>
            </div>

            <h3
              class="mt-4 text-xl font-semibold leading-7 tracking-tight sm:text-[22px]"
            >
              {{ listing.title }}
            </h3>

            <p
              class="mt-3 flex items-center gap-2 text-xs text-[#87919F]"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#B49362"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="shrink-0"
              >
                <path
                  d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"
                ></path>
                <circle cx="12" cy="10" r="2.5"></circle>
              </svg>

              {{ listing.location }}
            </p>

            <div
              class="mt-6 flex flex-wrap items-center gap-x-5 gap-y-3 border-y border-[#EEEAE3] py-4 text-xs text-[#64748B]"
            >
              <span
                class="flex items-center gap-2"
              >
                <span class="text-[#B49362]">▧</span>
                {{ listing.area }} m²
              </span>

              <span
                v-if="listing.bedrooms"
                class="flex items-center gap-2"
              >
                <span class="text-[#B49362]">⌂</span>
                {{ listing.bedrooms }} phòng ngủ
              </span>

              <span
                v-if="listing.bathrooms"
                class="flex items-center gap-2"
              >
                <span class="text-[#B49362]">◈</span>
                {{ listing.bathrooms }} WC
              </span>
            </div>

            <div
              class="mt-auto flex flex-wrap items-end justify-between gap-4 pt-6"
            >
              <div>
                <p
                  class="text-[10px] uppercase tracking-[0.12em] text-[#9AA4B1]"
                >
                  Giá tham khảo
                </p>

                <p
                  class="mt-2 text-[27px] font-semibold tracking-tight text-[#142B4F]"
                >
                  {{ formatPrice(listing.price) }}
                  <span class="text-base text-[#B49362]">
                    tỷ
                  </span>
                </p>
              </div>

              <button
                type="button"
                @click="openListing(listing.id)"
                class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-[#E4DED3] text-lg transition group-hover:border-[#142B4F] group-hover:bg-[#142B4F] group-hover:text-white"
                :aria-label="`Xem chi tiết ${listing.title}`"
              >
                ↗
              </button>
            </div>
          </div>
        </article>
      </div>

      <!-- EMPTY STATE -->
      <div
        v-else
        class="mt-8 rounded-[24px] border border-[#E8E3DA] bg-white px-6 py-20 text-center"
      >
        <div
          class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[#F7F5F0] text-2xl text-[#B49362]"
        >
          ⌕
        </div>

        <h3
          class="mt-6 text-2xl font-semibold"
        >
          Chưa tìm thấy bất động sản phù hợp
        </h3>

        <p
          class="mx-auto mt-3 max-w-md text-sm leading-7 text-[#87919F]"
        >
          Hãy thử thay đổi từ khóa, khu vực hoặc mức giá
          để khám phá thêm các lựa chọn.
        </p>

        <button
          type="button"
          @click="resetFilters"
          class="mt-7 rounded-full bg-[#142B4F] px-7 py-3 text-xs font-semibold text-white transition hover:bg-[#25466B]"
        >
          Xem tất cả bất động sản ↗
        </button>
      </div>

      <!-- GIS PROMOTION -->
      <section
        class="relative mt-16 overflow-hidden rounded-[26px] bg-[#142B4F] px-7 py-10 text-white sm:px-10 md:py-12"
      >
        <div
          class="pointer-events-none absolute -right-16 -top-24 h-80 w-80 rounded-full border border-[#C6A77A]/20"
        ></div>

        <div
          class="pointer-events-none absolute -right-5 top-5 h-52 w-52 rounded-full border border-[#C6A77A]/20"
        ></div>

        <div
          class="relative flex flex-wrap items-center justify-between gap-8"
        >
          <div class="max-w-[680px]">
            <p
              class="text-[10px] font-bold uppercase tracking-[0.2em] text-[#7BD4E5]"
            >
              SMARTPROP / GIS EXPLORER
            </p>

            <h2
              class="mt-4 text-3xl font-medium leading-tight sm:text-4xl"
            >
              Một vị trí tốt.
              <span
                class="block italic text-[#C6A77A]"
              >
                Một góc nhìn khác biệt.
              </span>
            </h2>

            <p
              class="mt-4 max-w-xl text-sm leading-7 text-white/65"
            >
              Khám phá các tin đăng qua góc nhìn không gian,
              so sánh vị trí và tiếp cận thông tin bất động sản
              theo cách trực quan hơn.
            </p>
          </div>

          <button
            type="button"
            @click="goMap"
            class="shrink-0 rounded-full bg-[#C6A77A] px-7 py-4 text-xs font-bold text-[#142B4F] transition hover:bg-[#E1C394]"
          >
            Khám phá GIS Explorer ↗
          </button>
        </div>
      </section>

      <p
        class="mt-7 text-center text-[11px] leading-6 text-[#87919F]"
      >
        Lưu ý: Tin đăng, hình ảnh, giá, số liệu và trạng thái
        đánh giá trên trang này đều là dữ liệu minh họa.
        Các ảnh chỉ mang tính đại diện, không phải ảnh của bất động sản thực tế.
      </p>
    </main>

    <!-- FOOTER -->
    <footer
      class="border-t border-[#E7E2D8] bg-[#F7F5F0]"
    >
      <div
        class="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-4 px-5 py-7 md:px-8 lg:px-12"
      >
        <button
          type="button"
          @click="goHome"
          class="text-lg font-bold tracking-tight"
        >
          SmartProp<span class="text-[#C6A77A]">.</span>
        </button>

        <p class="text-[11px] text-[#87919F]">
          © 2026 SmartProp · Property Collection 2.0
        </p>

        <div class="flex flex-wrap gap-5">
          <button
            type="button"
            @click="goHome"
            class="text-xs text-[#64748B] hover:text-[#142B4F]"
          >
            Trang chủ
          </button>

          <button
            type="button"
            @click="goMap"
            class="text-xs text-[#64748B] hover:text-[#142B4F]"
          >
            Bản đồ GIS
          </button>

          <button
            type="button"
            @click="goPost"
            class="text-xs text-[#64748B] hover:text-[#142B4F]"
          >
            Đăng tin
          </button>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/*
  Chỉ áp dụng cho trang /listings.
  Dùng font hệ thống để tránh lỗi dấu tiếng Việt.
*/

.sp-collection {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
  font-family: Arial, "Segoe UI", sans-serif;
  font-synthesis: none;
}

.sp-collection h1,
.sp-collection h2,
.sp-collection h3 {
  font-family: Arial, "Segoe UI", sans-serif;
  font-kerning: normal;
  font-variant-ligatures: none;
  letter-spacing: -0.025em;
  word-spacing: normal;
}

.sp-collection input,
.sp-collection select,
.sp-collection button {
  font-family: inherit;
}

.sp-collection img {
  display: block;
}

@media (prefers-reduced-motion: reduce) {
  .sp-collection *,
  .sp-collection *::before,
  .sp-collection *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
