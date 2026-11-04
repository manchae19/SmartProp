<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../../src/services/api.js'
import { DISTRICT_PROFILES, DISTRICT_LIST, getDistrictProfile } from '../../src/services/marketData.js'
import { useComparison } from '../../src/services/useComparison.js'
import PriceTrendChart from '../../src/components/PriceTrendChart.vue'
import BrowseTileMap from '../../src/components/BrowseTileMap.vue'
import ListingCard from '../../src/components/business/ListingCard.vue'
import TopSearchedAreas from '../../src/components/TopSearchedAreas.vue'

const route = useRoute()
const router = useRouter()
const compare = useComparison()

// District selection
const selectedDistrictSlug = ref(route.params.district || 'son-tra')
const currentDistrict = computed(() => getDistrictProfile(selectedDistrictSlug.value))

function selectDistrict(slug) {
  selectedDistrictSlug.value = slug
  router.push({ path: `/market/${slug}` })
}

watch(() => route.params.district, (newSlug) => {
  if (newSlug) selectedDistrictSlug.value = newSlug
})

// Dynamic unit prices from district history
const latestHousePrice = computed(() => {
  const arr = currentDistrict.value?.priceHistory?.house || []
  return arr.length ? `${arr[arr.length - 1]},0 triệu/m²` : '145,0 triệu/m²'
})

const latestApartmentPrice = computed(() => {
  const arr = currentDistrict.value?.priceHistory?.apartment || []
  return arr.length ? `${arr[arr.length - 1]},0 triệu/m²` : '62,0 triệu/m²'
})

// Real-time properties from database
const properties = ref([])
const loadingProperties = ref(false)
const selectedMapPropertyId = ref(null)

async function fetchDistrictProperties() {
  loadingProperties.value = true
  try {
    const districtName = currentDistrict.value.shortName
    const res = await api(`/properties?district=${encodeURIComponent(districtName)}&size=6&limit=8`, { authenticated: false })
    const items = Array.isArray(res) ? res : res?.items || []
    properties.value = items
    selectedMapPropertyId.value = items.find(p => Number.isFinite(Number(p.latitude)) && Number.isFinite(Number(p.longitude)))?.id || null
  } catch (e) {
    properties.value = []
    selectedMapPropertyId.value = null
  } finally {
    loadingProperties.value = false
  }
}

watch(() => currentDistrict.value.id, () => {
  fetchDistrictProperties()
}, { immediate: true })

// Points for BrowseTileMap
const mapPoints = computed(() => {
  return properties.value
    .filter(p => Number.isFinite(Number(p.latitude)) && Number.isFinite(Number(p.longitude)))
    .map(p => ({
      id: p.id,
      latitude: Number(p.latitude),
      longitude: Number(p.longitude),
      price: p.price,
      priceExact: p.priceExact,
      priceUnit: p.priceUnit,
      transactionType: p.transactionType,
      title: p.title
    }))
})

function focusOnDistrictMap(propertyId) {
  selectedMapPropertyId.value = propertyId
  scrollToSection('overview')
}

// In-page navigation tabs
const activeSection = ref('overview')
const inPageTabs = [
  { id: 'overview', number: '01', label: 'Tổng quan & GIS' },
  { id: 'planning', number: '02', label: 'Quy hoạch hạ tầng' },
  { id: 'price-trend', number: '03', label: 'Biến động đơn giá' },
  { id: 'listings', number: '04', label: 'Bất động sản mở bán' },
  { id: 'neighboring', number: '05', label: 'Khu vực tìm kiếm nhiều' }
]

function scrollToSection(id) {
  activeSection.value = id
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

let sectionObserver = null
onMounted(() => {
  if (typeof IntersectionObserver === 'undefined') return
  sectionObserver = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter(e => e.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)
      if (visible[0]?.target?.id) {
        activeSection.value = visible[0].target.id
      }
    },
    { rootMargin: '-20% 0px -60% 0px', threshold: [0.05, 0.25, 0.5] }
  )
  for (const tab of inPageTabs) {
    const el = document.getElementById(tab.id)
    if (el) sectionObserver.observe(el)
  }
})

onBeforeUnmount(() => {
  sectionObserver?.disconnect()
})

// Accordion toggle state for planning section
const expandedPanels = ref({
  planning1: true,
  planning2: true,
  planning3: false
})

function togglePanel(panelKey) {
  expandedPanels.value[panelKey] = !expandedPanels.value[panelKey]
}

function handleBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/listings')
  }
}
</script>

<template>
  <div class="market-luxury min-h-screen bg-[#f7f5f0] text-[#142b4f] antialiased selection:bg-[#10233f] selection:text-[#dfbe86] pb-20">
    <!-- ==================== TOP EDITORIAL BAR & BREADCRUMBS ==================== -->
    <div class="max-w-[1280px] mx-auto px-5 sm:px-8 pt-6">
      <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div class="flex items-center gap-3">
          <button
            type="button"
            @click="handleBack"
            class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white text-[#142b4f] border border-[#ddd6c8] shadow-2xs hover:bg-[#f3ede2] hover:border-[#b3915f] transition-all cursor-pointer text-xs font-bold group"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" class="transition-transform group-hover:-translate-x-0.5">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            <span>Quay lại</span>
          </button>

          <nav aria-label="Breadcrumb" class="hidden sm:inline-flex items-center gap-2.5 px-4 py-2 rounded-full bg-white border border-[#e7e1d7] text-xs font-medium text-[#536178]">
            <RouterLink to="/" class="hover:text-[#10233f] transition">Trang chủ</RouterLink>
            <span class="text-[#d4cfc4]">/</span>
            <RouterLink to="/market" class="hover:text-[#10233f] transition">Dữ liệu thị trường</RouterLink>
            <span class="text-[#d4cfc4]">/</span>
            <span class="text-[#10233f] font-bold flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-[#b3915f]"></span>
              {{ currentDistrict.name }}
            </span>
          </nav>
        </div>

        <div class="flex items-center gap-2.5">
          <RouterLink
            :to="{ path: '/listings', query: { district: currentDistrict.shortName } }"
            class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-[#ddd6c8] hover:border-[#b3915f] text-xs font-bold text-[#142b4f] transition"
          >
            <span>Tin đăng {{ currentDistrict.shortName }}</span>
            <span aria-hidden="true">↗</span>
          </RouterLink>
          <RouterLink
            to="/advisor"
            class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#10233f] text-[#dfbe86] hover:bg-[#162f54] text-xs font-bold transition shadow-xs"
          >
            <span>Tư vấn đầu tư AI</span>
            <span aria-hidden="true">→</span>
          </RouterLink>
        </div>
      </div>

      <!-- ==================== LUXURY ARCHITECTURAL HERO CARD ==================== -->
      <section class="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-[#091728] via-[#10233f] to-[#162f54] text-white p-7 sm:p-10 lg:p-12 border border-[#b3915f]/30 shadow-xl">
        <!-- Subtle architectural grid decoration -->
        <div class="pointer-events-none absolute -right-20 -top-20 h-80 w-80 rounded-full bg-[#dfbe86]/8 blur-3xl" aria-hidden="true"></div>
        <div class="pointer-events-none absolute -bottom-24 left-1/3 h-64 w-64 rounded-full bg-[#207760]/10 blur-3xl" aria-hidden="true"></div>

        <div class="relative z-10 flex flex-col lg:flex-row lg:items-end justify-between gap-8 pb-8 border-b border-white/12">
          <div class="max-w-3xl">
            <div class="inline-flex items-center gap-2.5 text-xs font-bold uppercase tracking-[0.24em] text-[#dfbe86] mb-3">
              <span>⌖</span>
              <span>SMARTPROP MARKET INTELLIGENCE · ĐÀ NẴNG</span>
            </div>
            <h1 class="text-3xl sm:text-4xl lg:text-[46px] font-semibold tracking-tight leading-[1.14] text-white">
              Báo cáo thị trường
              <span class="text-[#dfbe86] block sm:inline">{{ currentDistrict.name }}.</span>
            </h1>
            <p class="text-sm sm:text-[15px] text-white/80 mt-3.5 leading-relaxed max-w-2xl">
              {{ currentDistrict.tagline }}
            </p>
          </div>

          <!-- Highlight Metric Summary Box in Hero -->
          <div class="flex flex-wrap sm:flex-nowrap items-stretch gap-3 shrink-0">
            <div class="rounded-2xl bg-white/8 backdrop-blur-md border border-white/14 px-5 py-4 min-w-[165px]">
              <p class="text-[11px] uppercase tracking-wider text-white/65 font-semibold">Đơn giá TB Đất nền</p>
              <p class="text-xl sm:text-2xl font-bold text-[#dfbe86] mt-1 tracking-tight">{{ currentDistrict.macro.avgPricePerM2 }}</p>
              <p class="text-[11px] text-emerald-300 font-semibold mt-1 flex items-center gap-1">
                <span>▲ {{ currentDistrict.macro.priceGrowthYoY }}</span>
                <span class="text-white/50 font-normal">so với cùng kỳ</span>
              </p>
            </div>
            <div class="rounded-2xl bg-white/8 backdrop-blur-md border border-white/14 px-5 py-4 min-w-[155px]">
              <p class="text-[11px] uppercase tracking-wider text-white/65 font-semibold">Chỉ số thanh khoản</p>
              <p class="text-xl sm:text-2xl font-bold text-white mt-1 tracking-tight">{{ currentDistrict.macro.liquidityRating.split(' ')[0] }} {{ currentDistrict.macro.liquidityRating.split(' ')[1] || '' }}</p>
              <p class="text-[11px] text-white/70 mt-1">
                Cập nhật Quý 4/2026
              </p>
            </div>
          </div>
        </div>

        <!-- 6 DISTRICT SELECTOR PILLS -->
        <div class="relative z-10 pt-6">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3.5">
            <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-white/60">
              CHỌN QUẬN / KHU VỰC PHÂN TÍCH CHUYÊN SÂU
            </p>
            <span class="text-xs text-[#dfbe86]/90 font-medium">
              6 quận trọng điểm · Dữ liệu chuẩn hóa & AI Valuation V6
            </span>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
            <button
              v-for="name in DISTRICT_LIST"
              :key="name"
              type="button"
              @click="selectDistrict(DISTRICT_PROFILES[name].slug)"
              class="group px-4 py-3 rounded-2xl text-left transition-all cursor-pointer border flex flex-col justify-between"
              :class="currentDistrict.shortName === name
                ? 'bg-[#dfbe86] text-[#10233f] border-[#dfbe86] shadow-lg'
                : 'bg-white/7 text-white border-white/12 hover:bg-white/14 hover:border-[#dfbe86]/50'"
            >
              <div class="flex items-center justify-between gap-2 w-full mb-1">
                <span class="text-xs font-bold tracking-tight">{{ name }}</span>
                <span
                  class="w-2 h-2 rounded-full transition"
                  :class="currentDistrict.shortName === name ? 'bg-[#10233f]' : 'bg-white/25 group-hover:bg-[#dfbe86]'"
                ></span>
              </div>
              <span
                class="text-[11px] font-semibold"
                :class="currentDistrict.shortName === name ? 'text-[#10233f]/80' : 'text-white/65'"
              >
                {{ DISTRICT_PROFILES[name].macro.avgPricePerM2 }}
              </span>
            </button>
          </div>
        </div>
      </section>

      <!-- ==================== FLOATING IN-PAGE SECTION NAV ==================== -->
      <div class="sticky top-[calc(var(--sp-header-height,64px)+10px)] z-30 my-7">
        <div class="rounded-full bg-white/95 backdrop-blur-md border border-[#e0d9cd] shadow-sm p-1.5 flex items-center justify-between gap-1 overflow-x-auto">
          <button
            v-for="tab in inPageTabs"
            :key="tab.id"
            type="button"
            @click="scrollToSection(tab.id)"
            class="flex-1 min-w-fit px-4 py-2.5 rounded-full text-xs font-bold transition-all whitespace-nowrap cursor-pointer flex items-center justify-center gap-2"
            :class="activeSection === tab.id
              ? 'bg-[#10233f] text-[#dfbe86] shadow-xs'
              : 'text-[#536178] hover:text-[#10233f] hover:bg-[#f7f5f0]'"
          >
            <span class="text-[10px] opacity-70 font-mono">{{ tab.number }}</span>
            <span>{{ tab.label }}</span>
          </button>
        </div>
      </div>

      <!-- ==================== MAIN CONTENT SECTIONS ==================== -->
      <div class="space-y-12">

        <!-- SECTION 1: OVERVIEW & GIS MAP -->
        <section id="overview" class="scroll-mt-32 grid grid-cols-1 lg:grid-cols-12 gap-7 items-start">
          <!-- LEFT: OVERVIEW & MACRO SPECS (7 cols) -->
          <div class="lg:col-span-7 bg-white rounded-3xl p-6 sm:p-8 border border-[#e7e1d7] shadow-2xs">
            <div class="pb-5 mb-6 border-b border-[#eee8de]">
              <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-[#78572f] mb-2">
                01 / TỔNG QUAN VĨ MÔ & ĐỊA LÝ
              </p>
              <h2 class="text-2xl sm:text-3xl font-semibold text-[#10233f] tracking-tight">
                Bức tranh toàn cảnh <span class="text-[#957344]">{{ currentDistrict.name }}.</span>
              </h2>
            </div>

            <!-- 2 Architectural Callout Cards -->
            <div class="space-y-4 mb-7">
              <div class="p-5 rounded-2xl bg-[#f7f5f0] border border-[#e7e1d7] border-l-4 border-l-[#10233f]">
                <div class="flex items-center gap-2 text-xs font-bold text-[#10233f] uppercase tracking-wider mb-2">
                  <svg class="size-4 text-[#957344]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span>Vị trí địa lý & Kết nối giao thông cốt lõi</span>
                </div>
                <p class="text-xs sm:text-[13px] leading-relaxed text-[#536178]">
                  {{ currentDistrict.overview }}
                </p>
              </div>

              <div class="p-5 rounded-2xl bg-[#f7f5f0] border border-[#e7e1d7] border-l-4 border-l-[#b3915f]">
                <div class="flex items-center gap-2 text-xs font-bold text-[#78572f] uppercase tracking-wider mb-2">
                  <svg class="size-4 text-[#957344]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
                    <polyline points="17 6 23 6 23 12" />
                  </svg>
                  <span>Tiềm năng phát triển & Đặc tính thị trường</span>
                </div>
                <p class="text-xs sm:text-[13px] leading-relaxed text-[#536178]">
                  {{ currentDistrict.aiInsights.growthPotential }}
                </p>
              </div>
            </div>

            <!-- 6 Key Macro Metrics -->
            <div class="pt-6 border-t border-[#eee8de]">
              <div class="flex items-center justify-between mb-4">
                <p class="text-xs font-bold text-[#78572f] uppercase tracking-[0.18em]">
                  CHỈ SỐ VĨ MÔ & MẶT BẰNG ĐƠN GIÁ
                </p>
                <span class="text-[11px] text-[#8c7760]">Đơn vị chuẩn hóa theo m²</span>
              </div>

              <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <div class="p-4 rounded-2xl bg-[#f7f5f0] border border-[#e7e1d7]">
                  <p class="text-[11px] font-semibold text-[#536178] uppercase tracking-wider">Diện tích tự nhiên</p>
                  <p class="text-lg font-bold text-[#10233f] mt-1.5">{{ currentDistrict.macro.areaKm2 }}</p>
                  <p class="text-[11px] text-[#8c7760] mt-1">Quy hoạch đô thị Đà Nẵng</p>
                </div>

                <div class="p-4 rounded-2xl bg-[#f7f5f0] border border-[#e7e1d7]">
                  <p class="text-[11px] font-semibold text-[#536178] uppercase tracking-wider">Quy mô dân số</p>
                  <p class="text-lg font-bold text-[#10233f] mt-1.5">{{ currentDistrict.macro.population }}</p>
                  <p class="text-[11px] text-[#207760] font-semibold mt-1">{{ currentDistrict.macro.density }}</p>
                </div>

                <div class="p-4 rounded-2xl bg-[#f7f5f0] border border-[#e7e1d7]">
                  <p class="text-[11px] font-semibold text-[#536178] uppercase tracking-wider">Đơn giá TB Đất nền</p>
                  <p class="text-lg font-bold text-[#b13724] mt-1.5">{{ currentDistrict.macro.avgPricePerM2 }}</p>
                  <p class="text-[11px] text-[#207760] font-semibold mt-1">▲ {{ currentDistrict.macro.priceGrowthYoY }} YoY</p>
                </div>

                <div class="p-4 rounded-2xl bg-[#f7f5f0] border border-[#e7e1d7]">
                  <p class="text-[11px] font-semibold text-[#536178] uppercase tracking-wider">Đơn giá TB Nhà phố</p>
                  <p class="text-lg font-bold text-[#10233f] mt-1.5">~ {{ latestHousePrice }}</p>
                  <p class="text-[11px] text-[#8c7760] mt-1">Trục thương mại chính</p>
                </div>

                <div class="p-4 rounded-2xl bg-[#f7f5f0] border border-[#e7e1d7]">
                  <p class="text-[11px] font-semibold text-[#536178] uppercase tracking-wider">Đơn giá TB Căn hộ</p>
                  <p class="text-lg font-bold text-[#957344] mt-1.5">~ {{ latestApartmentPrice }}</p>
                  <p class="text-[11px] text-[#8c7760] mt-1">Phân khúc thương mại & biển</p>
                </div>

                <div class="p-4 rounded-2xl bg-[#f7f5f0] border border-[#e7e1d7]">
                  <p class="text-[11px] font-semibold text-[#536178] uppercase tracking-wider">Tin niêm yết công khai</p>
                  <p class="text-lg font-bold text-[#10233f] mt-1.5">{{ properties.length }} BĐS</p>
                  <p class="text-[11px] text-[#78572f] font-semibold mt-1">Thanh khoản: {{ currentDistrict.macro.liquidityRating }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- RIGHT: INTERACTIVE GIS MAP (5 cols) -->
          <div class="lg:col-span-5 bg-white rounded-3xl p-5 sm:p-6 border border-[#e7e1d7] shadow-2xs lg:sticky lg:top-28">
            <div class="flex items-center justify-between gap-3 mb-4">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-[#78572f]">GIS SPATIAL EXPLORER</p>
                <h3 class="text-base font-bold text-[#10233f] mt-0.5">
                  Bản đồ phân bố BĐS {{ currentDistrict.shortName }}
                </h3>
              </div>
              <span class="text-xs text-[#10233f] font-bold bg-[#f7f5f0] border border-[#e0d9cd] px-3 py-1 rounded-full">
                {{ mapPoints.length }} ghim tọa độ
              </span>
            </div>

            <div class="h-[430px] rounded-2xl overflow-hidden border border-[#dcd5ca] relative bg-[#e7ece6]">
              <BrowseTileMap
                v-if="mapPoints.length"
                :points="mapPoints"
                :selected-id="selectedMapPropertyId"
                @select="(id) => router.push(`/listing/${id}`)"
              />
              <div v-else class="w-full h-full flex flex-col items-center justify-center bg-[#f7f5f0] text-[#536178] text-xs p-6 text-center">
                <p class="font-semibold text-[#10233f] mb-1">Đang tải tọa độ không gian...</p>
                <p class="text-[11px] text-[#8c7760]">Hiển thị các bất động sản có tọa độ xác thực tại {{ currentDistrict.name }}</p>
              </div>
            </div>

            <div class="mt-4 pt-3 border-t border-[#eee8de] flex items-center justify-between text-xs text-[#536178]">
              <span>Chọn nhãn giá trên bản đồ để mở chi tiết BĐS</span>
              <RouterLink
                :to="{ path: '/map', query: { district: currentDistrict.shortName } }"
                class="text-[#10233f] hover:text-[#957344] font-bold transition inline-flex items-center gap-1"
              >
                <span>Mở toàn cảnh GIS</span>
                <span aria-hidden="true">↗</span>
              </RouterLink>
            </div>
          </div>
        </section>

        <!-- SECTION 2: URBAN & INFRASTRUCTURE PLANNING -->
        <section id="planning" class="scroll-mt-32 bg-white rounded-3xl p-6 sm:p-8 lg:p-10 border border-[#e7e1d7] shadow-2xs">
          <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 mb-7 border-b border-[#eee8de]">
            <div>
              <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-[#78572f] mb-2">
                02 / ĐỊNH HƯỚNG QUY HOẠCH ĐÔ THỊ 2030 – 2045
              </p>
              <h2 class="text-2xl sm:text-3xl font-semibold text-[#10233f] tracking-tight">
                Quy hoạch hạ tầng <span class="text-[#957344]">& Động lực tăng trưởng.</span>
              </h2>
            </div>
            <p class="text-xs text-[#536178] max-w-md leading-relaxed">
              Các dự án hạ tầng trọng điểm và định hướng không gian đô thị tác động trực tiếp đến biên độ tăng giá dài hạn tại {{ currentDistrict.name }}.
            </p>
          </div>

          <div class="space-y-4">
            <!-- Accordion 1: Quy hoạch không gian -->
            <div class="rounded-2xl border border-[#e0d9cd] overflow-hidden transition-all">
              <button
                type="button"
                @click="togglePanel('planning1')"
                class="w-full px-6 py-4 flex items-center justify-between text-left text-xs sm:text-sm font-bold cursor-pointer transition-colors"
                :class="expandedPanels.planning1
                  ? 'bg-[#10233f] text-white'
                  : 'bg-[#f7f5f0] text-[#10233f] hover:bg-[#f0ede7]'"
              >
                <div class="flex items-center gap-3.5">
                  <span
                    class="text-xs font-mono px-2.5 py-1 rounded-full border"
                    :class="expandedPanels.planning1
                      ? 'border-[#dfbe86]/40 text-[#dfbe86] bg-white/8'
                      : 'border-[#d4cfc4] text-[#78572f] bg-white'"
                  >
                    01
                  </span>
                  <span>Định hướng phát triển không gian đô thị & thương mại {{ currentDistrict.name }}</span>
                </div>
                <span
                  class="text-xs transition-transform duration-200"
                  :class="[expandedPanels.planning1 ? 'rotate-180 text-[#dfbe86]' : 'text-[#78572f]']"
                >
                  ▼
                </span>
              </button>

              <div v-show="expandedPanels.planning1" class="p-6 bg-white text-xs sm:text-[13px] leading-relaxed text-[#536178] space-y-4 border-t border-[#eee8de]">
                <p>
                  Theo Quyết định điều chỉnh Quy hoạch chung TP. Đà Nẵng đến năm 2030, tầm nhìn 2045, <strong class="text-[#10233f]">{{ currentDistrict.name }}</strong> được định vị là cực tăng trưởng chiến lược với hệ sinh thái <strong class="text-[#10233f]">đô thị - thương mại dịch vụ - du lịch và cư trú chất lượng cao</strong>.
                </p>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                  <div class="p-4 rounded-2xl bg-[#f7f5f0] border border-[#e7e1d7]">
                    <p class="font-bold text-[#10233f] mb-1.5">Tái cấu trúc không gian & Trục cảnh quan chủ đạo</p>
                    <p class="text-xs text-[#536178] leading-relaxed">Ưu tiên phát triển các tổ hợp thương mại dịch vụ hiện đại, nâng cấp hạ tầng kỹ thuật ngầm hóa và mở rộng không gian công cộng phục vụ cư dân.</p>
                  </div>
                  <div class="p-4 rounded-2xl bg-[#f7f5f0] border border-[#e7e1d7]">
                    <p class="font-bold text-[#10233f] mb-1.5">Kinh tế dịch vụ & Khai thác dòng tiền</p>
                    <p class="text-xs text-[#536178] leading-relaxed">Gia tăng mật độ các tuyến phố chuyên doanh, tổ hợp văn phòng - lưu trú cao cấp nhằm tối ưu tỷ suất khai thác cho thuê bất động sản.</p>
                  </div>
                </div>
              </div>
            </div>

            <!-- Accordion 2: Quy hoạch giao thông -->
            <div class="rounded-2xl border border-[#e0d9cd] overflow-hidden transition-all">
              <button
                type="button"
                @click="togglePanel('planning2')"
                class="w-full px-6 py-4 flex items-center justify-between text-left text-xs sm:text-sm font-bold cursor-pointer transition-colors"
                :class="expandedPanels.planning2
                  ? 'bg-[#10233f] text-white'
                  : 'bg-[#f7f5f0] text-[#10233f] hover:bg-[#f0ede7]'"
              >
                <div class="flex items-center gap-3.5">
                  <span
                    class="text-xs font-mono px-2.5 py-1 rounded-full border"
                    :class="expandedPanels.planning2
                      ? 'border-[#dfbe86]/40 text-[#dfbe86] bg-white/8'
                      : 'border-[#d4cfc4] text-[#78572f] bg-white'"
                  >
                    02
                  </span>
                  <span>Danh mục dự án hạ tầng & Giao thông trọng điểm tại {{ currentDistrict.shortName }}</span>
                </div>
                <span
                  class="text-xs transition-transform duration-200"
                  :class="[expandedPanels.planning2 ? 'rotate-180 text-[#dfbe86]' : 'text-[#78572f]']"
                >
                  ▼
                </span>
              </button>

              <div v-show="expandedPanels.planning2" class="p-6 bg-white border-t border-[#eee8de]">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div
                    v-for="item in currentDistrict.infrastructure"
                    :key="item.name"
                    class="p-4 rounded-2xl bg-[#f7f5f0] border border-[#e7e1d7] flex flex-col justify-between gap-3"
                  >
                    <div>
                      <span class="text-[10px] font-bold px-2.5 py-1 rounded-full inline-block mb-2.5 bg-white border border-[#dcd5ca] text-[#78572f] uppercase tracking-wider">
                        ● {{ item.status }}
                      </span>
                      <p class="font-bold text-[#10233f] text-xs sm:text-[13px] leading-snug">{{ item.name }}</p>
                    </div>
                    <p class="text-[11px] text-[#8c7760]">Tác động trực tiếp tới giá trị kết nối khu vực</p>
                  </div>
                </div>
              </div>
            </div>

            <!-- Accordion 3: Tiện ích nổi bật -->
            <div class="rounded-2xl border border-[#e0d9cd] overflow-hidden transition-all">
              <button
                type="button"
                @click="togglePanel('planning3')"
                class="w-full px-6 py-4 flex items-center justify-between text-left text-xs sm:text-sm font-bold cursor-pointer transition-colors"
                :class="expandedPanels.planning3
                  ? 'bg-[#10233f] text-white'
                  : 'bg-[#f7f5f0] text-[#10233f] hover:bg-[#f0ede7]'"
              >
                <div class="flex items-center gap-3.5">
                  <span
                    class="text-xs font-mono px-2.5 py-1 rounded-full border"
                    :class="expandedPanels.planning3
                      ? 'border-[#dfbe86]/40 text-[#dfbe86] bg-white/8'
                      : 'border-[#d4cfc4] text-[#78572f] bg-white'"
                  >
                    03
                  </span>
                  <span>Hệ sinh thái tiện ích ngoại khu & Chất lượng sống</span>
                </div>
                <span
                  class="text-xs transition-transform duration-200"
                  :class="[expandedPanels.planning3 ? 'rotate-180 text-[#dfbe86]' : 'text-[#78572f]']"
                >
                  ▼
                </span>
              </button>

              <div v-show="expandedPanels.planning3" class="p-6 bg-white text-xs sm:text-[13px] leading-relaxed text-[#536178] border-t border-[#eee8de]">
                <p>
                  <strong class="text-[#10233f]">{{ currentDistrict.name }}</strong> sở hữu mạng lưới tiện ích đô thị hoàn chỉnh trong bán kính 1–3 km: hệ thống trường học liên cấp, bệnh viện & trạm y tế, siêu thị thương mại, công viên cây xanh và các trục giao thông kết nối thẳng ra sân bay quốc tế Đà Nẵng cũng như bãi biển.
                </p>
              </div>
            </div>
          </div>
        </section>

        <!-- SECTION 3: PRICE TREND CHART & SIGNATURE AI FORECAST CARD -->
        <section id="price-trend" class="scroll-mt-32 space-y-6">
          <PriceTrendChart :history="currentDistrict.priceHistory" />

          <!-- Signature Navy & Gold AI Market Intelligence Card (Matching ListingDetailView) -->
          <div class="rounded-3xl p-6 sm:p-8 lg:p-10 bg-gradient-to-br from-[#10233f] via-[#162f54] to-[#10233f] text-white shadow-xl border border-[#b3915f]/35 relative overflow-hidden">
            <div class="pointer-events-none absolute -right-16 -bottom-16 h-64 w-64 rounded-full bg-[#dfbe86]/10 blur-3xl" aria-hidden="true"></div>

            <div class="relative z-10 flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 mb-6 border-b border-white/12">
              <div>
                <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-[#dfbe86] text-[11px] font-bold border border-[#dfbe86]/30 tracking-wider uppercase mb-3">
                  <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                  <span>SMARTPROP AI MARKET INTELLIGENCE · MODEL V6</span>
                </div>
                <h3 class="text-xl sm:text-2xl font-semibold text-white tracking-tight">
                  Nhận định chuyên sâu & Dự báo xu hướng <span class="text-[#dfbe86]">{{ currentDistrict.name }}.</span>
                </h3>
              </div>

              <RouterLink
                to="/advisor"
                class="self-start md:self-auto inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-[#dfbe86] hover:bg-[#cca86e] text-[#10233f] text-xs font-bold transition shadow-sm"
              >
                <span>Mở AI Advisor phân tích danh mục</span>
                <span aria-hidden="true">→</span>
              </RouterLink>
            </div>

            <div class="relative z-10 grid grid-cols-1 md:grid-cols-3 gap-5 text-xs sm:text-[13px] leading-relaxed">
              <div class="bg-white/8 backdrop-blur-md rounded-2xl p-5 border border-white/12">
                <div class="flex items-center gap-2 font-bold text-[#dfbe86] uppercase tracking-wider text-xs mb-2.5">
                  <svg class="size-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
                    <polyline points="17 6 23 6 23 12" />
                  </svg>
                  <span>Động lực tăng giá</span>
                </div>
                <p class="text-white/85">{{ currentDistrict.aiInsights.growthPotential }}</p>
              </div>

              <div class="bg-white/8 backdrop-blur-md rounded-2xl p-5 border border-white/12">
                <div class="flex items-center gap-2 font-bold text-emerald-300 uppercase tracking-wider text-xs mb-2.5">
                  <svg class="size-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                    <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                  </svg>
                  <span>Thanh khoản thị trường</span>
                </div>
                <p class="text-white/85">{{ currentDistrict.aiInsights.liquidity }}</p>
              </div>

              <div class="bg-white/8 backdrop-blur-md rounded-2xl p-5 border border-white/12">
                <div class="flex items-center gap-2 font-bold text-sky-300 uppercase tracking-wider text-xs mb-2.5">
                  <svg class="size-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                  <span>Khuyến nghị chiến lược</span>
                </div>
                <p class="text-white/85">{{ currentDistrict.aiInsights.recommendation }}</p>
              </div>
            </div>
          </div>
        </section>

        <!-- SECTION 4: VERIFIED LISTINGS IN DISTRICT (USING SIGNATURE LISTINGCARD) -->
        <section id="listings" class="scroll-mt-32 bg-[#f0ede7] rounded-3xl p-6 sm:p-8 lg:p-10 border border-[#e0d9cd]">
          <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-6 mb-7 border-b border-[#ddd6c8]">
            <div>
              <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-[#78572f] mb-2">
                04 / BẤT ĐỘNG SẢN THỰC TẾ ĐANG NIÊM YẾT
              </p>
              <h2 class="text-2xl sm:text-3xl font-semibold text-[#10233f] tracking-tight">
                Tin đăng công khai tại <span class="text-[#957344]">{{ currentDistrict.name }}.</span>
              </h2>
              <p class="text-xs text-[#536178] mt-1.5">
                Tin đã kiểm duyệt trên hệ thống SmartProp · Hỗ trợ đối chiếu bản đồ GIS và so sánh trực tiếp
              </p>
            </div>

            <RouterLink
              :to="{ path: '/listings', query: { district: currentDistrict.shortName } }"
              class="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#10233f] text-white hover:bg-[#162f54] text-xs font-bold transition self-start sm:self-auto shadow-xs"
            >
              <span>Xem tất cả tại {{ currentDistrict.shortName }}</span>
              <span aria-hidden="true">→</span>
            </RouterLink>
          </div>

          <div v-if="loadingProperties" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div v-for="n in 3" :key="n" class="h-[420px] rounded-3xl bg-white/60 animate-pulse border border-[#e7e1d7]"></div>
          </div>

          <div v-else-if="properties.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <ListingCard
              v-for="item in properties.slice(0, 6)"
              :key="item.id"
              :property="item"
              :class="{ 'ring-2 ring-[#b3915f] ring-offset-2': selectedMapPropertyId === item.id }"
            >
              <button
                type="button"
                class="market-card-action"
                :aria-pressed="selectedMapPropertyId === item.id"
                @click="focusOnDistrictMap(item.id)"
              >
                ⌖ Bản đồ
              </button>
              <button
                type="button"
                class="market-card-action compare"
                :aria-pressed="compare.has(item.id)"
                @click="compare.toggle(item)"
              >
                {{ compare.has(item.id) ? '✓ Đã chọn' : '+ So sánh' }}
              </button>
            </ListingCard>
          </div>

          <div v-else class="rounded-3xl bg-white p-12 text-center border border-[#e7e1d7]">
            <p class="text-lg font-semibold text-[#10233f]">Chưa có tin đăng công khai tại khu vực này</p>
            <p class="text-xs text-[#536178] mt-2 mb-5">Hãy khám phá các quận lân cận hoặc xem toàn bộ danh sách bất động sản Đà Nẵng.</p>
            <RouterLink to="/listings" class="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#10233f] text-white text-xs font-bold">
              <span>Mở danh sách BĐS</span>
              <span aria-hidden="true">→</span>
            </RouterLink>
          </div>
        </section>

        <!-- SECTION 5: TOP SEARCHED AREAS BENTO GRID & NEIGHBORING DISTRICTS -->
        <section id="neighboring" class="scroll-mt-32 bg-white rounded-3xl p-6 sm:p-8 lg:p-10 border border-[#e7e1d7] shadow-2xs space-y-8">
          <TopSearchedAreas
            :current-slug="currentDistrict.slug"
            eyebrow="05 / XU HƯỚNG TÌM KIẾM · ĐÀ NẴNG"
            mode="market"
            @select-district="selectDistrict"
          />
        </section>

      </div>
    </div>
  </div>
</template>

<style scoped>
.market-card-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 650;
  border-radius: 20px;
  border: 1px solid #dcd4c7;
  background: white;
  color: #516277;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.market-card-action:hover {
  background: #f3ede2;
  color: #10233f;
  border-color: #c4b59f;
}
.market-card-action[aria-pressed="true"] {
  background: #10233f;
  color: #dfbe86;
  border-color: #10233f;
}
.market-card-action.compare[aria-pressed="true"] {
  background: #e6f7ec;
  color: #167a33;
  border-color: #9fe0b2;
}
</style>
