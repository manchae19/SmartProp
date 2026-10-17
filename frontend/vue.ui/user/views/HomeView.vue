<script setup>

import { ref, computed, onMounted, onUnmounted } from 'vue'

 

const menuOpen = ref(false)

const searchOpen = ref(false)

const compareOpen = ref(false)

const viewingOpen = ref(false)

const viewingSuccess = ref(false)

const selectedProject = ref(null)

const amenityDistrict = ref('Hải Châu')

const amenityType = ref('Tất cả')

const activeArea = ref('Tất cả')

const showAllProperties = ref(false)

 

const projects = [

  {

    id: 1,

    name: 'Sun Ponte Residence',

    location: 'Trần Hưng Đạo, An Hải, Đà Nẵng',

    type: 'Khu phức hợp ven sông',

    developer: 'Sun Property',

    description:

      'Không gian sống ven sông Hàn với định hướng phát triển đa dạng loại hình bất động sản.',

    image:

      'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=1200&q=85',

    website:

      'https://sunpropertygroup.vn/cac-du-an/sun-ponte-residence-9554',

  },

  {

    id: 2,

    name: 'The Filmore Da Nang',

    location: 'Bạch Đằng, Hải Châu, Đà Nẵng',

    type: 'Căn hộ cao cấp',

    developer: 'Filmore Development',

    description:

      'Dự án căn hộ cao cấp tại khu vực ven sông Hàn, trung tâm Đà Nẵng.',

    image:

      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=85',

    website:

      'https://filmore.com.vn/chinh-thuc-khai-truong-khu-can-ho-the-filmore-da-nang/',

  },

  {

    id: 3,

    name: 'FPT Plaza 3',

    location: 'Hoàng Minh Thắng, khu đô thị FPT, Đà Nẵng',

    type: 'Chung cư',

    developer: 'FPT City',

    description:

      'Dự án căn hộ thuộc khu đô thị FPT với hệ thống tiện ích phục vụ cư dân.',

    image:

      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=1200&q=85',

    website: 'https://fptplaza3.fptcity.vn/gioi-thieu/',

  },

]

 

const areas = [

  {

    name: 'Hải Châu',

    description: 'Nhịp sống trung tâm',

    image:

      'https://images.unsplash.com/photo-1480714378408-67cf0d13bc1b?w=1200&q=85',

  },

  {

    name: 'Sơn Trà',

    description: 'Không gian sống ven biển',

    image:

      'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1200&q=85',

  },

  {

    name: 'Ngũ Hành Sơn',

    description: 'Kết nối du lịch và đô thị',

    image:

      'https://images.unsplash.com/photo-1511818966892-d7d671e672a2?w=1200&q=85',

  },

  {

    name: 'Cẩm Lệ',

    description: 'Không gian đô thị đang phát triển',

    image:

      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1200&q=85',

  },

  {

    name: 'Liên Chiểu',

    description: 'Khu vực phía tây bắc thành phố',

    image:

      'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=1200&q=85',

  },

  { name: 'Thanh Khê', description: 'Khu vực đô thị phía tây trung tâm', image: 'https://images.unsplash.com/photo-1480714378408-67cf0d13bc1b?w=1200&q=85' },

  { name: 'Hòa Vang', description: 'Không gian xanh và phát triển đô thị', image: 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=1200&q=85' },

  { name: 'Hội An', description: 'Di sản và du lịch ven biển', image: 'https://images.unsplash.com/photo-1528127269322-539801943592?w=1200&q=85' },

  { name: 'Điện Bàn', description: 'Kết nối Đà Nẵng và Hội An', image: 'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=1200&q=85' },

  { name: 'Tam Kỳ', description: 'Trung tâm đô thị phía nam', image: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=85' },

  { name: 'Núi Thành', description: 'Khu vực công nghiệp và ven biển', image: 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1200&q=85' },

 

]

 

const properties = [

  {

    id: 1,

    name: 'The Riverside Residence',

    district: 'Hải Châu',

    address: 'Hải Châu, Đà Nẵng',

    type: 'Nhà phố',

    price: 4.85,

    area: 86,

    bedrooms: 3,

    bathrooms: 3,

    legal: 'Sổ hồng',

    image:

      'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1200&q=85',

  },

  {

    id: 2,

    name: 'Ocean View Apartment',

    district: 'Sơn Trà',

    address: 'Sơn Trà, Đà Nẵng',

    type: 'Căn hộ',

    price: 3.2,

    area: 72,

    bedrooms: 2,

    bathrooms: 2,

    legal: 'Sổ hồng',

    image:

      'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=1200&q=85',

  },

  {

    id: 3,

    name: 'Hòa Xuân Garden',

    district: 'Cẩm Lệ',

    address: 'Cẩm Lệ, Đà Nẵng',

    type: 'Đất nền',

    price: 2.95,

    area: 100,

    bedrooms: 0,

    bathrooms: 0,

    legal: 'Sổ đỏ',

    image:

      'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=1200&q=85',

  },

]

 

const filters = ref({

  keyword: '',

  district: 'Tất cả',

  type: 'Tất cả',

  minPrice: '',

  maxPrice: '',

  minArea: '',

  bedrooms: 'Tất cả',

  legal: 'Tất cả',

})

 

const filteredProperties = computed(() => {

  return properties.filter((p) => {

    const f = filters.value

    const keyword = f.keyword.trim().toLowerCase()

 

    return (

      (!keyword ||

        `${p.name} ${p.address} ${p.type}`

          .toLowerCase()

          .includes(keyword)) &&

      (f.district === 'Tất cả' || p.district === f.district) &&

      (activeArea.value === 'Tất cả' ||

        p.district === activeArea.value) &&

      (f.type === 'Tất cả' || p.type === f.type) &&

      (!f.minPrice || p.price >= Number(f.minPrice)) &&

      (!f.maxPrice || p.price <= Number(f.maxPrice)) &&

      (!f.minArea || p.area >= Number(f.minArea)) &&

      (f.bedrooms === 'Tất cả' ||

        p.bedrooms >= Number(f.bedrooms)) &&

      (f.legal === 'Tất cả' || p.legal === f.legal)

    )

  })

})

 

const displayedProperties = computed(() =>

  showAllProperties.value

    ? filteredProperties.value

    : filteredProperties.value.slice(0, 3)

)

 

function resetFilters() {

  filters.value = {

    keyword: '',

    district: 'Tất cả',

    type: 'Tất cả',

    minPrice: '',

    maxPrice: '',

    minArea: '',

    bedrooms: 'Tất cả',

    legal: 'Tất cả',

  }

  activeArea.value = 'Tất cả'

}

 

function scrollToSection(id) {

  menuOpen.value = false

  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })

}

 

function goToProperties() {

  searchOpen.value = false

  menuOpen.value = false

  document

    .getElementById('properties')

    ?.scrollIntoView({ behavior: 'smooth' })

}

 

function selectArea(name) {

  activeArea.value = name

  filters.value.district = 'Tất cả'

  goToProperties()

}

 

const compareIds = ref([])

 

const comparedProperties = computed(() =>

  properties.filter((p) => compareIds.value.includes(p.id))

)

 

function toggleCompare(id) {

  if (compareIds.value.includes(id)) {

    compareIds.value = compareIds.value.filter((x) => x !== id)

    return

  }

 

  if (compareIds.value.length >= 3) {

    alert('Bạn chỉ có thể so sánh tối đa 3 bất động sản.')

    return

  }

 

  compareIds.value = [...compareIds.value, id]

}

 

function formatPrice(value) {

  return `${Number(value).toLocaleString('vi-VN')} tỷ`

}

 

function pricePerSquareMeter(property) {

  return Math.round((property.price * 1000) / property.area)

}

 

const viewing = ref({

  propertyId: 1,

  name: '',

  phone: '',

  date: '',

  time: '',

  note: '',

})

 

const minDate = new Date().toLocaleDateString('en-CA')

 

const selectedViewingProperty = computed(() =>

  properties.find((p) => p.id === Number(viewing.value.propertyId))

)

 

function openViewing(id) {

  viewing.value.propertyId = id

  viewingSuccess.value = false

  viewingOpen.value = true

}

 

function submitViewing() {

  if (

    !viewing.value.name.trim() ||

    !viewing.value.phone.trim() ||

    !viewing.value.date ||

    !viewing.value.time

  ) {

    return

  }

 

  viewingSuccess.value = true

}

 

const amenities = [

  { name: 'Trường học', icon: '🎓' },

  { name: 'Bệnh viện', icon: '✚' },

  { name: 'Siêu thị', icon: '🛍' },

  { name: 'Công viên', icon: '🌳' },

  { name: 'Giao thông', icon: '🚉' },

]

 

const visibleAmenities = computed(() =>

  amenityType.value === 'Tất cả'

    ? amenities

    : amenities.filter((a) => a.name === amenityType.value)

)

 

const valuation = ref({

  area: 80,

  unitPrice: 45,

  adjustment: 0,

})

 

const estimatedValue = computed(

  () =>

    (Number(valuation.value.area || 0) *

      Number(valuation.value.unitPrice || 0) *

      (1 + Number(valuation.value.adjustment || 0) / 100)) /

    1000

)

 

const loan = ref({

  propertyPrice: 4,

  downPayment: 30,

  years: 20,

  interest: 9,

})

 

const loanPrincipal = computed(() =>

  Math.max(

    0,

    Number(loan.value.propertyPrice || 0) *

      1_000_000_000 *

      (1 - Number(loan.value.downPayment || 0) / 100)

  )

)

 

const monthlyPayment = computed(() => {

  const principal = loanPrincipal.value

  const months = Math.max(1, Number(loan.value.years || 1) * 12)

  const rate = Number(loan.value.interest || 0) / 1200

 

  if (rate === 0) return principal / months

 

  const factor = Math.pow(1 + rate, months)

  return (principal * rate * factor) / (factor - 1)

})

 

function moneyVnd(value) {

  return Math.round(value).toLocaleString('vi-VN') + ' ₫'

}

 

function handleEscape(event) {

  if (event.key === 'Escape') {

    searchOpen.value = false

    compareOpen.value = false

    viewingOpen.value = false

    selectedProject.value = null

    menuOpen.value = false

  }

}

 

onMounted(() => {

  window.addEventListener('keydown', handleEscape)

})

 

onUnmounted(() => {

  window.removeEventListener('keydown', handleEscape)

})

</script>

 

<template>

  <div class="min-h-screen bg-[#F7F5F0] text-[#142B4F]">

    <main>

    <!-- ================= HERO ================= -->

 

    <section

      id="home"

      class="relative flex min-h-[760px] flex-col overflow-hidden bg-[#091728] text-white lg:min-h-[820px]"

    >

      <video

        autoplay

        muted

        loop

        playsinline

        class="absolute inset-0 h-full w-full object-cover"

      >

        <source src="/background.mp4" type="video/mp4" />

      </video>

 

      <div class="absolute inset-0 bg-gradient-to-r from-[#071525]/90 via-[#071525]/55 to-[#071525]/20"></div>

      <div class="absolute inset-0 bg-gradient-to-t from-[#071525]/80 via-transparent to-[#071525]/30"></div>

 

      <!-- Decorative tech grid -->

      <div class="sp-tech-grid pointer-events-none absolute inset-0 opacity-20"></div>

 

      <!-- Light accent -->

      <div class="pointer-events-none absolute -right-32 top-20 h-[480px] w-[480px] rounded-full bg-[#5CB9D3]/10 blur-[110px]"></div>

 

      <!-- NAV -->

      <header class="relative z-30 mx-auto flex w-full max-w-[1360px] items-center justify-between px-6 py-7 md:px-10">

 

        <button

          type="button"

          @click="scrollToSection('home')"

          class="flex items-center gap-3"

        >

          <span class="flex h-10 w-10 items-center justify-center rounded-full border border-white/60 font-serif text-lg">

            S

          </span>

 

          <span class="text-xl font-semibold tracking-tight">

            SmartProp<span class="text-[#D8B887]">.</span>

          </span>

        </button>

 

        <nav class="hidden items-center gap-7 text-xs font-medium text-white/80 lg:flex">

          <button @click="scrollToSection('projects')" class="transition hover:text-[#D8B887]">Dự án</button>

          <button @click="scrollToSection('properties')" class="transition hover:text-[#D8B887]">Bất động sản</button>

          <button @click="scrollToSection('gis')" class="transition hover:text-[#D8B887]">GIS Explorer</button>

          <button @click="scrollToSection('valuation')" class="transition hover:text-[#D8B887]">Định giá</button>

          <button @click="scrollToSection('investment')" class="transition hover:text-[#D8B887]">Tài chính</button>

        </nav>

 

        <div class="hidden items-center gap-3 lg:flex">

          <RouterLink to="/listings" class="hidden text-xs font-semibold hover:text-[#D8B887] xl:inline">Danh sách</RouterLink>

          <RouterLink to="/map" class="hidden text-xs font-semibold hover:text-[#D8B887] xl:inline">Bản đồ</RouterLink>

          <RouterLink to="/account" class="text-xs font-semibold hover:text-[#D8B887]">

            Tài khoản

          </RouterLink>

 

          <RouterLink

            to="/post"

            class="rounded-full border border-white/50 px-6 py-3 text-xs font-semibold transition hover:bg-white hover:text-[#142B4F]"

          >

            Đăng tin ↗

          </RouterLink>

        </div>

 

        <button

          type="button"

          aria-label="Mở menu"

          @click="menuOpen = !menuOpen"

          class="flex h-10 w-10 items-center justify-center rounded-full border border-white/50 lg:hidden"

        >

          ☰

        </button>

      </header>

 

      <!-- MOBILE MENU -->

      <div

        v-if="menuOpen"

        class="relative z-40 mx-5 grid gap-4 rounded-2xl border border-white/20 bg-[#142B4F]/95 p-6 text-sm lg:hidden"

      >

        <button @click="scrollToSection('projects')" class="text-left">Dự án</button>

        <button @click="scrollToSection('properties')" class="text-left">Bất động sản</button>

        <button @click="scrollToSection('gis')" class="text-left">GIS Explorer</button>

        <button @click="scrollToSection('valuation')" class="text-left">Định giá</button>

        <button @click="scrollToSection('investment')" class="text-left">Tài chính</button>

        <RouterLink to="/map">Bản đồ GIS</RouterLink>

        <RouterLink to="/listings">Danh sách bất động sản</RouterLink>

        <RouterLink to="/account">Tài khoản</RouterLink>

        <RouterLink to="/post">Đăng tin</RouterLink>

      </div>

 

      <!-- HERO CONTENT -->

      <div class="relative z-10 mx-auto flex w-full max-w-[1360px] flex-1 items-center px-6 pb-32 pt-14 md:px-10">

 

        <div class="max-w-[900px]">

 

          <div class="mb-7 flex flex-wrap items-center gap-3">

            <span class="h-px w-10 bg-[#D8B887]"></span>

 

            <span class="text-[10px] font-semibold uppercase tracking-[.24em] text-[#E4C89E]">

              Real Estate × Intelligence

            </span>

 

            <span class="sp-pulse ml-1 h-1.5 w-1.5 rounded-full bg-[#6DD5E7]"></span>

 

            <span class="text-[10px] text-[#BCE6ED]">

              SmartProp Experience

            </span>

          </div>

 

          <h1 class="font-serif text-[clamp(3.5rem,7.5vw,7.8rem)] font-normal leading-[1.03] tracking-[-.045em]">

            Nhà không chỉ

            <br>

            là một

            <span class="italic text-[#D8B887]">mức giá.</span>

          </h1>

 

          <p class="mt-8 max-w-xl text-sm leading-8 text-white/75 sm:text-base">

            Khám phá bất động sản Đà Nẵng từ góc nhìn mới.

            Nơi dữ liệu thị trường, bản đồ GIS và công nghệ

            phân tích giúp bạn hiểu sâu hơn về giá trị của một ngôi nhà.

          </p>

 

          <div class="mt-10 flex flex-wrap gap-3">

            <button

              type="button"

              @click="searchOpen = true"

              class="group rounded-full bg-[#D8B887] px-8 py-4 text-xs font-bold text-[#142B4F] transition duration-300 hover:-translate-y-1 hover:bg-[#E8CAA0]"

            >

              Khám phá bất động sản

              <span class="ml-2 inline-block transition group-hover:translate-x-1">↗</span>

            </button>

 

            <RouterLink

              to="/map"

              class="rounded-full border border-white/50 px-8 py-4 text-xs font-semibold backdrop-blur-sm transition hover:border-[#6DD5E7] hover:bg-white/10"

            >

              Khám phá GIS

            </RouterLink>

          </div>

 

          <!-- TECHNOLOGY HINT -->

          <div class="mt-10 flex flex-wrap gap-5 text-[10px] uppercase tracking-[.16em] text-white/55">

            <span class="flex items-center gap-2">

              <span class="h-1.5 w-1.5 rounded-full bg-[#6DD5E7]"></span>

              Market Intelligence

            </span>

 

            <span class="flex items-center gap-2">

              <span class="h-1.5 w-1.5 rounded-full bg-[#6DD5E7]"></span>

              GIS Technology

            </span>

 

            <span class="flex items-center gap-2">

              <span class="h-1.5 w-1.5 rounded-full bg-[#6DD5E7]"></span>

              Explainable AI

            </span>

          </div>

        </div>

      </div>

 

      <!-- HERO BOTTOM -->

      <div class="absolute bottom-8 left-6 right-6 z-10 mx-auto flex max-w-[1280px] items-end justify-between border-t border-white/20 pt-5 md:left-10 md:right-10">

 

        <div class="flex flex-wrap gap-8 sm:gap-14">

          <div>

            <p class="text-[10px] uppercase tracking-[.18em] text-white/50">Location</p>

            <p class="mt-2 text-xs font-semibold">Đà Nẵng, Việt Nam</p>

          </div>

 

          <div>

            <p class="text-[10px] uppercase tracking-[.18em] text-white/50">Experience</p>

            <p class="mt-2 text-xs font-semibold">Luxury × Technology</p>

          </div>

        </div>

 

        <button

          type="button"

          @click="scrollToSection('projects')"

          aria-label="Cuộn đến thị trường"

          class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-white/50 text-xl transition hover:bg-white hover:text-[#142B4F]"

        >

          ↓

        </button>

      </div>

    </section>

 

      <!-- QUICK SEARCH -->

      <section class="relative z-10 mx-auto -mt-4 max-w-6xl px-5">

        <div

          class="rounded-3xl border border-[#E7E1D7] bg-white p-5 shadow-2xl shadow-[#142B4F]/10 md:p-7"

        >

          <div class="mb-5 flex flex-wrap items-center justify-between gap-3">

            <h2 class="text-xl font-bold">Tìm bất động sản phù hợp</h2>

            <button

              @click="searchOpen = true"

              class="text-sm font-bold text-[#A27E4A] hover:underline"

            >

              Bộ lọc nâng cao ↗

            </button>

          </div>

 

          <div class="grid gap-3 md:grid-cols-4">

            <input

              v-model="filters.keyword"

              placeholder="Tên hoặc địa điểm..."

              class="rounded-xl border border-[#E5E0D7] px-4 py-3 outline-none focus:border-[#B3915F]"

            />

 

            <select

              v-model="filters.district"

              class="rounded-xl border border-[#E5E0D7] px-4 py-3 outline-none focus:border-[#B3915F]"

            >

              <option>Tất cả</option>

              <option v-for="area in areas" :key="area.name" :value="area.name">{{ area.name }}</option>

            </select>

 

            <select

              v-model="filters.type"

              class="rounded-xl border border-[#E5E0D7] px-4 py-3 outline-none focus:border-[#B3915F]"

            >

              <option>Tất cả</option>

              <option>Nhà phố</option>

              <option>Căn hộ</option>

              <option>Đất nền</option>

            </select>

 

            <button

              @click="activeArea = 'Tất cả'; goToProperties()"

              class="rounded-xl bg-[#142B4F] px-5 py-3 font-bold text-white hover:bg-[#24456D]"

            >

              Tìm kiếm ↗

            </button>

          </div>

        </div>

      </section>

 

      <!-- FEATURED PROJECTS -->

      <section id="projects" class="mx-auto max-w-7xl px-5 py-24 lg:px-8">

        <div

          class="mb-10 flex flex-wrap items-end justify-between gap-5"

        >

          <div>

            <p

              class="mb-3 text-xs font-bold uppercase tracking-[0.3em] text-[#B3915F]"

            >

              Curated Developments

            </p>

            <h2 class="text-4xl font-semibold md:text-5xl">

              Dự án bất động sản

              <span class="text-[#B3915F]">nổi bật.</span>

            </h2>

            <p class="mt-4 max-w-2xl text-sm leading-7 text-[#637083]">

              Khám phá những dự án tại Đà Nẵng, từ khu căn hộ trung tâm

              đến các không gian sống ven sông và đô thị hiện đại.

            </p>

          </div>

        </div>

 

        <div class="grid gap-7 md:grid-cols-2 xl:grid-cols-3">

          <article

            v-for="project in projects"

            :key="project.id"

            class="group overflow-hidden rounded-3xl border border-[#E7E1D7] bg-white shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-xl"

          >

            <div class="relative h-64 overflow-hidden">

              <img

                :src="project.image"

                :alt="project.name"

                class="h-full w-full object-cover transition duration-700 group-hover:scale-105"

              />

              <span

                class="absolute left-5 top-5 rounded-full bg-[#142B4F]/90 px-4 py-2 text-xs font-semibold text-white"

              >

                {{ project.type }}

              </span>

            </div>

 

            <div class="p-6">

              <p

                class="mb-3 text-xs font-bold uppercase tracking-widest text-[#B3915F]"

              >

                Đà Nẵng

              </p>

              <h3 class="text-2xl font-bold">{{ project.name }}</h3>

              <p class="mt-2 text-sm text-[#637083]">

                📍 {{ project.location }}

              </p>

              <p class="mt-4 min-h-[72px] text-sm leading-6 text-[#637083]">

                {{ project.description }}

              </p>

 

              <div class="mt-6 border-t border-[#EAE5DD] pt-5">

                <p class="mb-4 text-xs text-[#637083]">

                  Đơn vị phát triển: {{ project.developer }}

                </p>

                <button

                  @click="selectedProject = project"

                  class="w-full rounded-full bg-[#142B4F] px-5 py-3 text-sm font-bold text-white transition hover:bg-[#24456D]"

                >

                  Khám phá dự án ↗

                </button>

              </div>

            </div>

          </article>

        </div>

      </section>

 

      <!-- AREAS -->

      <section id="areas" class="bg-[#EEEAE2] py-24">

        <div class="mx-auto max-w-7xl px-5 lg:px-8">

          <div class="mb-10">

            <p

              class="mb-3 text-xs font-bold uppercase tracking-[0.3em] text-[#B3915F]"

            >

              Explore Da Nang

            </p>

            <h2 class="text-4xl font-semibold md:text-5xl">

              Khám phá bất động sản

              <span class="text-[#B3915F]">theo khu vực.</span>

            </h2>

            <p class="mt-4 text-sm text-[#637083]">

              Mỗi khu vực là một phong cách sống khác biệt.

            </p>

          </div>

 

          <div class="grid gap-5 md:grid-cols-4">

            <button

              v-for="(area, index) in areas"

              :key="area.name"

              @click="selectArea(area.name)"

              class="group relative min-h-[260px] overflow-hidden rounded-3xl text-left text-white md:min-h-[300px]"

              :class="index === 0 ? 'md:col-span-2' : ''"

            >

              <img

                :src="area.image"

                :alt="area.name"

                class="absolute inset-0 h-full w-full object-cover transition duration-700 group-hover:scale-110"

              />

              <div

                class="absolute inset-0 bg-gradient-to-t from-[#081B32]/95 via-[#081B32]/30 to-transparent"

              ></div>

 

              <div class="absolute bottom-0 left-0 right-0 p-6">

                <h3 class="text-2xl font-bold">{{ area.name }}</h3>

                <p class="mt-2 text-sm text-white/75">

                  {{ area.description }}

                </p>

                <p class="mt-4 text-xs font-bold text-[#E5C18C]">

                  Khám phá khu vực ↗

                </p>

              </div>

            </button>

          </div>

        </div>

      </section>

 

      <!-- PROPERTIES -->

      <section

        id="properties"

        class="mx-auto max-w-7xl scroll-mt-24 px-5 py-24 lg:px-8"

      >

        <div

          class="mb-9 flex flex-wrap items-end justify-between gap-5"

        >

          <div>

            <p

              class="mb-3 text-xs font-bold uppercase tracking-[0.3em] text-[#B3915F]"

            >

              Selected Properties

            </p>

            <h2 class="text-4xl font-semibold md:text-5xl">

              Không gian sống

              <span class="text-[#B3915F]">đầy cảm hứng.</span>

            </h2>

            <p class="mt-4 text-sm text-[#637083]">

              Khám phá, so sánh và lựa chọn bất động sản phù hợp.

            </p>

          </div>

 

          <div class="flex flex-wrap gap-3">

            <button

              @click="searchOpen = true"

              class="rounded-full border border-[#142B4F]/20 px-5 py-3 text-sm font-bold hover:bg-white"

            >

              Bộ lọc nâng cao

            </button>

            <button

              @click="compareOpen = true"

              :disabled="compareIds.length < 2"

              class="rounded-full bg-[#142B4F] px-5 py-3 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-40"

            >

              So sánh ({{ compareIds.length }}/3)

            </button>

          </div>

        </div>

 

        <div

          v-if="activeArea !== 'Tất cả'"

          class="mb-6 flex flex-wrap items-center gap-3"

        >

          <span class="text-sm text-[#637083]">

            Khu vực: <strong>{{ activeArea }}</strong>

          </span>

          <button

            @click="activeArea = 'Tất cả'"

            class="text-sm font-bold text-[#B3915F] underline"

          >

            Xóa lựa chọn

          </button>

        </div>

 

        <div

          v-if="displayedProperties.length === 0"

          class="rounded-3xl border border-[#E7E1D7] bg-white px-6 py-20 text-center"

        >

          <h3 class="text-2xl font-bold">Chưa tìm thấy bất động sản</h3>

          <p class="mt-3 text-[#637083]">

            Hãy thử thay đổi khu vực hoặc điều kiện tìm kiếm.

          </p>

          <button

            @click="resetFilters"

            class="mt-6 rounded-full bg-[#142B4F] px-6 py-3 font-bold text-white"

          >

            Xóa bộ lọc

          </button>

        </div>

 

        <div v-else class="grid gap-7 md:grid-cols-2 xl:grid-cols-3">

          <article

            v-for="property in displayedProperties"

            :key="property.id"

            class="overflow-hidden rounded-3xl border border-[#E7E1D7] bg-white shadow-sm transition hover:shadow-xl"

          >

            <div class="relative h-64 overflow-hidden">

              <img

                :src="property.image"

                :alt="property.name"

                class="h-full w-full object-cover"

              />

              <span

                class="absolute left-5 top-5 rounded-full bg-white px-4 py-2 text-xs font-bold text-[#142B4F]"

              >

                {{ property.type }}

              </span>

            </div>

 

            <div class="p-6">

              <p class="text-xs text-[#B3915F]">

                {{ property.address }}

              </p>

              <h3 class="mt-2 text-xl font-bold">

                {{ property.name }}

              </h3>

              <p class="mt-4 text-2xl font-black">

                {{ formatPrice(property.price) }}

              </p>

 

              <div

                class="mt-5 grid grid-cols-3 gap-2 border-y border-[#EEEAE2] py-5 text-center text-sm"

              >

                <div>

                  <p class="font-bold">{{ property.area }} m²</p>

                  <p class="mt-1 text-xs text-[#637083]">Diện tích</p>

                </div>

                <div>

                  <p class="font-bold">

                    {{ property.bedrooms || '—' }}

                  </p>

                  <p class="mt-1 text-xs text-[#637083]">Phòng ngủ</p>

                </div>

                <div>

                  <p class="font-bold">{{ property.legal }}</p>

                  <p class="mt-1 text-xs text-[#637083]">Pháp lý</p>

                </div>

              </div>

 

              <p class="mt-4 text-xs text-[#637083]">

                Đơn giá tham khảo:

                {{ pricePerSquareMeter(property) }} triệu/m²

              </p>

 

              <div class="mt-6 flex gap-3">

                <button

                  @click="openViewing(property.id)"

                  class="flex-1 rounded-full bg-[#142B4F] px-4 py-3 text-xs font-bold text-white hover:bg-[#24456D]"

                >

                  Đặt lịch xem nhà ↗

                </button>

 

                <button

                  @click="toggleCompare(property.id)"

                  class="rounded-full border border-[#D8B887] px-4 py-3 text-xs font-bold"

                  :class="

                    compareIds.includes(property.id)

                      ? 'bg-[#D8B887] text-[#142B4F]'

                      : 'text-[#142B4F]'

                  "

                >

                  {{

                    compareIds.includes(property.id)

                      ? 'Đã chọn ✓'

                      : '+ So sánh'

                  }}

                </button>

              </div>

            </div>

          </article>

        </div>

 
<div class="mt-10 flex justify-center">
  <RouterLink
    to="/listings"
    class="group inline-flex items-center gap-3 rounded-full
           bg-[#142B4F] px-9 py-4 text-sm font-bold text-white
           shadow-lg transition-all duration-300
           hover:-translate-y-1 hover:bg-[#24456D] hover:shadow-xl"
  >
    Xem tất cả bất động sản

    <span class="transition-transform duration-300 group-hover:translate-x-1">
      →
    </span>
  </RouterLink>
</div>


        <p class="mt-5 text-xs text-[#8290A0]">

          Thông tin các bất động sản trong danh sách hiện chưa được kết nối

          với nguồn tin đăng xác thực.

        </p>

      </section>

 

      <!-- GIS -->

      <section id="gis" class="bg-[#10243F] py-24 text-white">

        <div

          class="mx-auto grid max-w-7xl items-center gap-12 px-5 lg:grid-cols-2 lg:px-8"

        >

          <div>

            <p

              class="mb-4 text-xs font-bold uppercase tracking-[0.3em] text-[#D8B887]"

            >

              GIS Explorer

            </p>

            <h2 class="text-4xl font-semibold leading-tight md:text-5xl">

              Hiểu vị trí.

              <span class="text-[#D8B887]">Nhìn xa hơn.</span>

            </h2>

            <p class="mt-6 max-w-xl leading-8 text-white/70">

              Khám phá vị trí bất động sản và mối liên hệ với hạ tầng,

              khu dân cư và các tiện ích đô thị.

            </p>

 

            <div class="mt-8 grid grid-cols-2 gap-4">

              <div class="rounded-2xl border border-white/15 p-5">

                <p class="text-2xl font-bold text-[#D8B887]">GIS</p>

                <p class="mt-2 text-sm text-white/65">

                  Phân tích không gian

                </p>

              </div>

              <div class="rounded-2xl border border-white/15 p-5">

                <p class="text-2xl font-bold text-[#D8B887]">360°</p>

                <p class="mt-2 text-sm text-white/65">

                  Góc nhìn khu vực

                </p>

              </div>

            </div>

          </div>

 

          <div

            class="relative min-h-[400px] overflow-hidden rounded-3xl border border-white/15 bg-[#193654] p-6"

          >

            <div

              class="absolute inset-0 opacity-20"

              style="background-image: linear-gradient(#D8B887 1px, transparent 1px), linear-gradient(90deg, #D8B887 1px, transparent 1px); background-size: 45px 45px;"

            ></div>

 

            <div

              class="absolute left-[15%] top-[25%] h-32 w-32 rounded-full border border-[#D8B887]/40"

            ></div>

            <div

              class="absolute left-[45%] top-[42%] h-48 w-48 rounded-full border border-[#D8B887]/30"

            ></div>

            <div

              class="absolute left-[55%] top-[18%] h-24 w-24 rounded-full border border-[#D8B887]/40"

            ></div>

 

            <div

              class="absolute left-[28%] top-[34%] rounded-full bg-[#D8B887] px-3 py-2 text-xs font-bold text-[#142B4F]"

            >

              Hải Châu

            </div>

            <div

              class="absolute left-[58%] top-[54%] rounded-full bg-white px-3 py-2 text-xs font-bold text-[#142B4F]"

            >

              Sơn Trà

            </div>

            <div

              class="absolute left-[37%] top-[72%] rounded-full bg-white px-3 py-2 text-xs font-bold text-[#142B4F]"

            >

              Cẩm Lệ

            </div>

 

            <div class="absolute bottom-6 left-6 right-6">

              <div

                class="rounded-2xl border border-white/15 bg-[#10243F]/90 p-5 backdrop-blur"

              >

                <p class="text-sm font-bold">Spatial Intelligence</p>

                <p class="mt-2 text-xs leading-6 text-white/60">

                  Khu vực phân tích không gian. Bản đồ tương tác thực tế

                  sẽ được tích hợp khi có dịch vụ bản đồ.

                </p>

              </div>

            </div>

          </div>

        </div>

      </section>

 

      <!-- AMENITIES -->

      <section class="mx-auto max-w-7xl px-5 py-24 lg:px-8">

        <p

          class="mb-3 text-xs font-bold uppercase tracking-[0.3em] text-[#B3915F]"

        >

          Neighborhood Intelligence

        </p>

        <h2 class="max-w-3xl text-4xl font-semibold md:text-5xl">

          Không chỉ là ngôi nhà.

          <span class="text-[#B3915F]">Còn là nơi sống.</span>

        </h2>

 

        <div class="mt-9 flex flex-wrap gap-4">

          <select

            v-model="amenityDistrict"

            class="rounded-xl border border-[#E0D9CE] bg-white px-5 py-3"

          >

            <option v-for="area in areas" :key="area.name" :value="area.name">{{ area.name }}</option>

          </select>

 

          <select

            v-model="amenityType"

            class="rounded-xl border border-[#E0D9CE] bg-white px-5 py-3"

          >

            <option>Tất cả</option>

            <option v-for="item in amenities" :key="item.name">

              {{ item.name }}

            </option>

          </select>

        </div>

 

        <div class="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-5">

          <div

            v-for="item in visibleAmenities"

            :key="item.name"

            class="rounded-3xl border border-[#E7E1D7] bg-white p-6"

          >

            <div class="text-3xl">{{ item.icon }}</div>

            <h3 class="mt-5 text-lg font-bold">{{ item.name }}</h3>

            <p class="mt-2 text-xs leading-6 text-[#637083]">

              Khám phá tiện ích tại {{ amenityDistrict }}

            </p>

          </div>

        </div>

 

        <p class="mt-5 text-xs text-[#8290A0]">

          Danh mục tiện ích chưa hiển thị địa chỉ và khoảng cách thực tế.

        </p>

      </section>

 

      <!-- VALUATION -->

      <section id="valuation" class="bg-[#EEEAE2] py-24">

        <div

          class="mx-auto grid max-w-7xl items-center gap-12 px-5 lg:grid-cols-2 lg:px-8"

        >

          <div>

            <p

              class="mb-4 text-xs font-bold uppercase tracking-[0.3em] text-[#B3915F]"

            >

              Property Valuation

            </p>

            <h2 class="text-4xl font-semibold leading-tight md:text-5xl">

              Định giá với

              <span class="text-[#B3915F]">góc nhìn dữ liệu.</span>

            </h2>

            <p class="mt-6 max-w-xl leading-8 text-[#637083]">

              Ước tính giá trị bất động sản từ diện tích, đơn giá tham

              khảo và hệ số điều chỉnh. Kết quả chỉ là phép tính, chưa

              phải định giá AI dựa trên giao dịch thực tế.

            </p>

          </div>

 

          <div class="rounded-3xl bg-white p-7 shadow-xl md:p-9">

            <h3 class="text-xl font-bold">Ước tính giá trị bất động sản</h3>

 

            <div class="mt-7 space-y-5">

              <label class="block">

                <span class="mb-2 block text-sm font-semibold">

                  Diện tích (m²)

                </span>

                <input

                  v-model.number="valuation.area"

                  type="number"

                  min="1"

                  class="w-full rounded-xl border border-[#E0D9CE] p-3"

                />

              </label>

 

              <label class="block">

                <span class="mb-2 block text-sm font-semibold">

                  Đơn giá tham khảo (triệu/m²)

                </span>

                <input

                  v-model.number="valuation.unitPrice"

                  type="number"

                  min="0"

                  class="w-full rounded-xl border border-[#E0D9CE] p-3"

                />

              </label>

 

              <label class="block">

                <span class="mb-2 block text-sm font-semibold">

                  Điều chỉnh (%)

                </span>

                <input

                  v-model.number="valuation.adjustment"

                  type="number"

                  min="-90"

                  max="100"

                  class="w-full rounded-xl border border-[#E0D9CE] p-3"

                />

              </label>

            </div>

 

            <div class="mt-7 rounded-2xl bg-[#142B4F] p-6 text-white">

              <p class="text-sm text-white/60">

                Giá trị ước tính

              </p>

              <p class="mt-3 text-4xl font-bold text-[#D8B887]">

                {{ estimatedValue.toFixed(2) }} tỷ

              </p>

              <p class="mt-3 text-xs text-white/55">

                Tính toán theo thông số người dùng nhập.

              </p>

            </div>

          </div>

        </div>

      </section>

 

      <!-- FINANCE -->

      <section

        id="investment"

        class="mx-auto grid max-w-7xl items-center gap-12 px-5 py-24 lg:grid-cols-2 lg:px-8"

      >

        <div>

          <p

            class="mb-4 text-xs font-bold uppercase tracking-[0.3em] text-[#B3915F]"

          >

            Investment Studio

          </p>

          <h2 class="text-4xl font-semibold leading-tight md:text-5xl">

            Tính toán trước.

            <span class="text-[#B3915F]">Quyết định vững vàng.</span>

          </h2>

          <p class="mt-6 leading-8 text-[#637083]">

            Ước tính khoản trả góp hàng tháng theo phương pháp trả đều

            gốc và lãi. Kết quả chưa bao gồm phí, bảo hiểm hoặc các thay

            đổi lãi suất trong tương lai.

          </p>

        </div>

 

        <div

          class="rounded-3xl border border-[#E7E1D7] bg-white p-7 shadow-xl md:p-9"

        >

          <h3 class="text-xl font-bold">Tính khoản vay mua nhà</h3>

 

          <div class="mt-7 grid gap-5 sm:grid-cols-2">

            <label>

              <span class="mb-2 block text-sm font-semibold">

                Giá bất động sản (tỷ)

              </span>

              <input

                v-model.number="loan.propertyPrice"

                type="number"

                min="0"

                step="0.1"

                class="w-full rounded-xl border border-[#E0D9CE] p-3"

              />

            </label>

 

            <label>

              <span class="mb-2 block text-sm font-semibold">

                Trả trước (%)

              </span>

              <input

                v-model.number="loan.downPayment"

                type="number"

                min="0"

                max="100"

                class="w-full rounded-xl border border-[#E0D9CE] p-3"

              />

            </label>

 

            <label>

              <span class="mb-2 block text-sm font-semibold">

                Thời hạn (năm)

              </span>

              <input

                v-model.number="loan.years"

                type="number"

                min="1"

                class="w-full rounded-xl border border-[#E0D9CE] p-3"

              />

            </label>

 

            <label>

              <span class="mb-2 block text-sm font-semibold">

                Lãi suất (%/năm)

              </span>

              <input

                v-model.number="loan.interest"

                type="number"

                min="0"

                step="0.1"

                class="w-full rounded-xl border border-[#E0D9CE] p-3"

              />

            </label>

          </div>

 

          <div class="mt-7 rounded-2xl bg-[#142B4F] p-6 text-white">

            <p class="text-sm text-white/60">

              Khoản trả góp hàng tháng

            </p>

            <p class="mt-3 text-3xl font-bold text-[#D8B887]">

              {{ moneyVnd(monthlyPayment) }}

            </p>

            <p class="mt-4 text-xs text-white/55">

              Khoản vay: {{ moneyVnd(loanPrincipal) }}

            </p>

          </div>

        </div>

      </section>

 

      <!-- CTA -->

      <section class="bg-[#142B4F] px-5 py-20 text-center text-white">

        <p

          class="text-xs font-bold uppercase tracking-[0.3em] text-[#D8B887]"

        >

          Your Next Move

        </p>

        <h2 class="mx-auto mt-5 max-w-3xl text-4xl font-semibold md:text-5xl">

          Bắt đầu hành trình tìm kiếm không gian sống lý tưởng.

        </h2>

        <div class="mt-9 flex flex-wrap justify-center gap-4">

          <button

            @click="searchOpen = true"

            class="rounded-full bg-[#D8B887] px-7 py-4 text-sm font-bold text-[#142B4F]"

          >

            Tìm bất động sản ↗

          </button>

          <a

            href="#projects"

            class="rounded-full border border-white/30 px-7 py-4 text-sm font-bold text-white"

          >

            Khám phá dự án

          </a>

        </div>

      </section>

    </main>

 

    <!-- FOOTER -->

    <footer class="bg-[#0C1B30] px-5 py-12 text-white/65">

      <div

        class="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-6"

      >

        <div>

          <p class="text-2xl font-bold text-white">

            Smart<span class="text-[#D8B887]">Prop</span>

          </p>

          <p class="mt-3 text-sm">

            Intelligent Real Estate Experience

          </p>

        </div>

        <p class="text-xs">

          © {{ new Date().getFullYear() }} SmartProp.

        </p>

      </div>

    </footer>

 

    <!-- PROJECT DETAIL MODAL -->

    <div

      v-if="selectedProject"

      class="fixed inset-0 z-50 flex items-center justify-center bg-[#07162B]/75 p-4"

      @click.self="selectedProject = null"

    >

      <div

        class="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl bg-white"

        role="dialog"

        aria-modal="true"

      >

        <div class="relative h-64">

          <img

            :src="selectedProject.image"

            :alt="selectedProject.name"

            class="h-full w-full object-cover"

          />

          <button

            @click="selectedProject = null"

            class="absolute right-5 top-5 rounded-full bg-white px-4 py-2 font-bold"

          >

            ✕

          </button>

        </div>

 

        <div class="p-7">

          <p class="text-xs font-bold uppercase tracking-widest text-[#B3915F]">

            Project Overview

          </p>

          <h2 class="mt-3 text-3xl font-bold">

            {{ selectedProject.name }}

          </h2>

          <p class="mt-3 text-sm text-[#637083]">

            📍 {{ selectedProject.location }}

          </p>

 

          <div class="mt-6 grid gap-4 sm:grid-cols-2">

            <div class="rounded-xl bg-[#F7F5F0] p-4">

              <p class="text-xs text-[#637083]">Loại hình</p>

              <p class="mt-2 font-bold">

                {{ selectedProject.type }}

              </p>

            </div>

            <div class="rounded-xl bg-[#F7F5F0] p-4">

              <p class="text-xs text-[#637083]">Đơn vị phát triển</p>

              <p class="mt-2 font-bold">

                {{ selectedProject.developer }}

              </p>

            </div>

          </div>

 

          <p class="mt-6 leading-7 text-[#637083]">

            {{ selectedProject.description }}

          </p>

 

          <a

            :href="selectedProject.website"

            target="_blank"

            rel="noopener noreferrer"

            class="mt-7 inline-flex rounded-full bg-[#142B4F] px-6 py-3 text-sm font-bold text-white"

          >

            Xem thông tin dự án ↗

          </a>

        </div>

      </div>

    </div>

 

    <!-- ADVANCED SEARCH MODAL -->

    <div

      v-if="searchOpen"

      class="fixed inset-0 z-50 flex items-center justify-center bg-[#07162B]/75 p-4"

      @click.self="searchOpen = false"

    >

      <div

        class="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl bg-white p-6 md:p-8"

        role="dialog"

        aria-modal="true"

      >

        <div class="mb-7 flex items-center justify-between">

          <h2 class="text-2xl font-bold">Tìm kiếm nâng cao</h2>

          <button

            @click="searchOpen = false"

            class="rounded-full bg-[#F1EEE8] px-4 py-2"

          >

            ✕

          </button>

        </div>

 

        <div class="grid gap-5 sm:grid-cols-2">

          <label class="sm:col-span-2">

            <span class="mb-2 block text-sm font-semibold">

              Từ khóa

            </span>

            <input

              v-model="filters.keyword"

              class="w-full rounded-xl border p-3"

              placeholder="Tên bất động sản, địa điểm..."

            />

          </label>

 

          <label>

            <span class="mb-2 block text-sm font-semibold">

              Khu vực

            </span>

            <select

              v-model="filters.district"

              class="w-full rounded-xl border p-3"

            >

              <option>Tất cả</option>

              <option v-for="area in areas" :key="area.name" :value="area.name">{{ area.name }}</option>

            </select>

          </label>

 

          <label>

            <span class="mb-2 block text-sm font-semibold">

              Loại bất động sản

            </span>

            <select

              v-model="filters.type"

              class="w-full rounded-xl border p-3"

            >

              <option>Tất cả</option>

              <option>Nhà phố</option>

              <option>Căn hộ</option>

              <option>Đất nền</option>

            </select>

          </label>

 

          <label>

            <span class="mb-2 block text-sm font-semibold">

              Giá từ (tỷ)

            </span>

            <input

              v-model="filters.minPrice"

              type="number"

              min="0"

              step="0.1"

              class="w-full rounded-xl border p-3"

            />

          </label>

 

          <label>

            <span class="mb-2 block text-sm font-semibold">

              Giá đến (tỷ)

            </span>

            <input

              v-model="filters.maxPrice"

              type="number"

              min="0"

              step="0.1"

              class="w-full rounded-xl border p-3"

            />

          </label>

 

          <label>

            <span class="mb-2 block text-sm font-semibold">

              Diện tích tối thiểu (m²)

            </span>

            <input

              v-model="filters.minArea"

              type="number"

              min="0"

              class="w-full rounded-xl border p-3"

            />

          </label>

 

          <label>

            <span class="mb-2 block text-sm font-semibold">

              Phòng ngủ tối thiểu

            </span>

            <select

              v-model="filters.bedrooms"

              class="w-full rounded-xl border p-3"

            >

              <option>Tất cả</option>

              <option value="1">1</option>

              <option value="2">2</option>

              <option value="3">3</option>

              <option value="4">4</option>

            </select>

          </label>

 

          <label class="sm:col-span-2">

            <span class="mb-2 block text-sm font-semibold">

              Pháp lý

            </span>

            <select

              v-model="filters.legal"

              class="w-full rounded-xl border p-3"

            >

              <option>Tất cả</option>

              <option>Sổ hồng</option>

              <option>Sổ đỏ</option>

            </select>

          </label>

        </div>

 

        <div class="mt-8 flex flex-wrap gap-3">

          <button

            @click="resetFilters"

            class="rounded-full border px-6 py-3 font-bold"

          >

            Xóa bộ lọc

          </button>

          <button

            @click="activeArea = 'Tất cả'; goToProperties()"

            class="flex-1 rounded-full bg-[#142B4F] px-6 py-3 font-bold text-white"

          >

            Xem {{ filteredProperties.length }} kết quả ↗

          </button>

        </div>

      </div>

    </div>

 

    <!-- COMPARISON MODAL -->

    <div

      v-if="compareOpen"

      class="fixed inset-0 z-50 flex items-center justify-center bg-[#07162B]/75 p-4"

      @click.self="compareOpen = false"

    >

      <div

        class="max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-3xl bg-white p-6 md:p-8"

        role="dialog"

        aria-modal="true"

      >

        <div class="mb-7 flex items-center justify-between">

          <h2 class="text-2xl font-bold">So sánh bất động sản</h2>

          <button

            @click="compareOpen = false"

            class="rounded-full bg-[#F1EEE8] px-4 py-2"

          >

            ✕

          </button>

        </div>

 

        <div class="overflow-x-auto">

          <table class="w-full min-w-[600px] text-left text-sm">

            <thead>

              <tr class="border-b">

                <th class="p-4">Tiêu chí</th>

                <th

                  v-for="property in comparedProperties"

                  :key="property.id"

                  class="p-4"

                >

                  {{ property.name }}

                </th>

              </tr>

            </thead>

            <tbody>

              <tr class="border-b">

                <td class="p-4 font-bold">Giá</td>

                <td

                  v-for="p in comparedProperties"

                  :key="p.id"

                  class="p-4"

                >

                  {{ formatPrice(p.price) }}

                </td>

              </tr>

              <tr class="border-b">

                <td class="p-4 font-bold">Khu vực</td>

                <td

                  v-for="p in comparedProperties"

                  :key="p.id"

                  class="p-4"

                >

                  {{ p.district }}

                </td>

              </tr>

              <tr class="border-b">

                <td class="p-4 font-bold">Diện tích</td>

                <td

                  v-for="p in comparedProperties"

                  :key="p.id"

                  class="p-4"

                >

                  {{ p.area }} m²

                </td>

              </tr>

              <tr class="border-b">

                <td class="p-4 font-bold">Giá/m²</td>

                <td

                  v-for="p in comparedProperties"

                  :key="p.id"

                  class="p-4"

                >

                  {{ pricePerSquareMeter(p) }} triệu

                </td>

              </tr>

              <tr class="border-b">

                <td class="p-4 font-bold">Phòng ngủ</td>

                <td

                  v-for="p in comparedProperties"

                  :key="p.id"

                  class="p-4"

                >

                  {{ p.bedrooms || '—' }}

                </td>

              </tr>

              <tr>

                <td class="p-4 font-bold">Pháp lý</td>

                <td

                  v-for="p in comparedProperties"

                  :key="p.id"

                  class="p-4"

                >

                  {{ p.legal }}

                </td>

              </tr>

            </tbody>

          </table>

        </div>

 

        <div class="mt-7 flex justify-end gap-3">

          <button

            @click="compareIds = []; compareOpen = false"

            class="rounded-full border px-6 py-3 font-bold"

          >

            Xóa so sánh

          </button>

          <button

            @click="compareOpen = false"

            class="rounded-full bg-[#142B4F] px-6 py-3 font-bold text-white"

          >

            Đóng

          </button>

        </div>

      </div>

    </div>

 

    <!-- VIEWING MODAL -->

    <div

      v-if="viewingOpen"

      class="fixed inset-0 z-50 flex items-center justify-center bg-[#07162B]/75 p-4"

      @click.self="viewingOpen = false"

    >

      <div

        class="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-3xl bg-white p-6 md:p-8"

        role="dialog"

        aria-modal="true"

      >

        <div class="mb-7 flex items-center justify-between">

          <h2 class="text-2xl font-bold">Đặt lịch xem nhà</h2>

          <button

            @click="viewingOpen = false"

            class="rounded-full bg-[#F1EEE8] px-4 py-2"

          >

            ✕

          </button>

        </div>

 

        <div

          v-if="viewingSuccess"

          class="rounded-2xl bg-[#F1F7F1] p-6 text-center"

        >

          <div class="text-4xl">✓</div>

          <h3 class="mt-4 text-xl font-bold">

            Đã ghi nhận thông tin trên giao diện

          </h3>

          <p class="mt-3 text-sm leading-7 text-[#637083]">

            Lịch hẹn chưa được gửi đến đơn vị môi giới vì SmartProp

            chưa kết nối hệ thống đặt lịch.

          </p>

          <button

            @click="viewingOpen = false"

            class="mt-6 rounded-full bg-[#142B4F] px-6 py-3 font-bold text-white"

          >

            Hoàn tất

          </button>

        </div>

 

        <form v-else class="space-y-5" @submit.prevent="submitViewing">

          <label class="block">

            <span class="mb-2 block text-sm font-semibold">

              Bất động sản

            </span>

            <select

              v-model.number="viewing.propertyId"

              class="w-full rounded-xl border p-3"

            >

              <option

                v-for="property in properties"

                :key="property.id"

                :value="property.id"

              >

                {{ property.name }}

              </option>

            </select>

          </label>

 

          <p

            v-if="selectedViewingProperty"

            class="text-xs text-[#637083]"

          >

            {{ selectedViewingProperty.address }}

          </p>

 

          <label class="block">

            <span class="mb-2 block text-sm font-semibold">

              Họ và tên

            </span>

            <input

              v-model="viewing.name"

              required

              class="w-full rounded-xl border p-3"

              placeholder="Nhập họ và tên"

            />

          </label>

 

          <label class="block">

            <span class="mb-2 block text-sm font-semibold">

              Số điện thoại

            </span>

            <input

              v-model="viewing.phone"

              required

              type="tel"

              pattern="[0-9]{9,11}"

              class="w-full rounded-xl border p-3"

              placeholder="Nhập số điện thoại"

            />

          </label>

 

          <div class="grid gap-4 sm:grid-cols-2">

            <label>

              <span class="mb-2 block text-sm font-semibold">

                Ngày xem

              </span>

              <input

                v-model="viewing.date"

                required

                type="date"

                :min="minDate"

                class="w-full rounded-xl border p-3"

              />

            </label>

 

            <label>

              <span class="mb-2 block text-sm font-semibold">

                Giờ xem

              </span>

              <input

                v-model="viewing.time"

                required

                type="time"

                class="w-full rounded-xl border p-3"

              />

            </label>

          </div>

 

          <label class="block">

            <span class="mb-2 block text-sm font-semibold">

              Ghi chú

            </span>

            <textarea

              v-model="viewing.note"

              rows="3"

              class="w-full rounded-xl border p-3"

              placeholder="Yêu cầu thêm..."

            ></textarea>

          </label>

 

          <button

            type="submit"

            class="w-full rounded-full bg-[#142B4F] px-6 py-4 font-bold text-white"

          >

            Tiếp tục đặt lịch ↗

          </button>

        </form>

      </div>

    </div>

  </div>

</template>

 

<style>

.sp-tech-grid { background-image: linear-gradient(rgba(216,184,135,.22) 1px, transparent 1px), linear-gradient(90deg, rgba(216,184,135,.22) 1px, transparent 1px); background-size: 68px 68px; mask-image: linear-gradient(to right, transparent, black 60%); }

.sp-pulse { animation: sp-pulse-animation 2.4s ease-in-out infinite; }

@keyframes sp-pulse-animation { 0%,100% { opacity:.35; transform:scale(.85) } 50% { opacity:1; transform:scale(1.2) } }

</style>

