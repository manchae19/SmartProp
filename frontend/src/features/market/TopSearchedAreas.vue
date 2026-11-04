<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { DISTRICT_PROFILES } from './marketData.js'

const props = defineProps({
  currentSlug: {
    type: String,
    default: ''
  },
  eyebrow: {
    type: String,
    default: 'XU HƯỚNG TÌM KIẾM · ĐÀ NẴNG'
  },
  mode: {
    type: String,
    default: 'market' // 'market' -> navigates to /market/:slug, 'listings' -> navigates to /listings?district=...
  }
})

const emit = defineEmits(['select-district'])
const router = useRouter()

// Ordered by search popularity (viewsCount)
const orderedDistricts = computed(() => {
  const all = [
    DISTRICT_PROFILES['Sơn Trà'],
    DISTRICT_PROFILES['Hải Châu'],
    DISTRICT_PROFILES['Ngũ Hành Sơn'],
    DISTRICT_PROFILES['Liên Chiểu'],
    DISTRICT_PROFILES['Cẩm Lệ'],
    DISTRICT_PROFILES['Thanh Khê']
  ].filter(Boolean)

  // If currentSlug is provided and matches one of the top 5, we can either keep Top 5 or rotate so all 5 other districts show
  if (props.currentSlug) {
    const others = all.filter(d => d.slug !== props.currentSlug)
    if (others.length === 5) return others
  }
  return all.slice(0, 5)
})

const featuredDistrict = computed(() => orderedDistricts.value[0] || null)
const secondaryDistricts = computed(() => orderedDistricts.value.slice(1, 5))

function handleSelect(district) {
  emit('select-district', district.slug)
  if (props.mode === 'listings') {
    router.push({ path: '/listings', query: { district: district.shortName } })
  } else {
    router.push({ path: `/market/${district.slug}` })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}
</script>

<template>
  <div class="top-searched-areas">
    <!-- Section Heading -->
    <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
      <div>
        <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-[#78572f] mb-2">
          {{ eyebrow }}
        </p>
        <h2 class="text-2xl sm:text-3xl font-semibold text-[#10233f] tracking-tight">
          Khu vực được tìm kiếm <span class="text-[#957344]">nhiều nhất.</span>
        </h2>
      </div>

      <RouterLink
        to="/listings"
        class="inline-flex items-center gap-2 text-xs font-bold text-[#10233f] hover:text-[#957344] transition self-start sm:self-auto"
      >
        <span>Khám phá toàn bộ tin đăng Đà Nẵng</span>
        <span aria-hidden="true">→</span>
      </RouterLink>
    </div>

    <!-- Bento Grid: 1 Large Left Card + 2x2 Right Grid -->
    <div v-if="featuredDistrict" class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
      <!-- LEFT FEATURED CARD (6 cols, spans full height) -->
      <article
        @click="handleSelect(featuredDistrict)"
        role="button"
        tabindex="0"
        @keydown.enter.prevent="handleSelect(featuredDistrict)"
        @keydown.space.prevent="handleSelect(featuredDistrict)"
        :aria-label="`${featuredDistrict.name}, Đà Nẵng - ${featuredDistrict.viewsCount} lượt xem`"
        class="lg:col-span-6 relative min-h-[340px] sm:min-h-[400px] lg:h-[468px] rounded-[22px] overflow-hidden cursor-pointer group shadow-md border border-[#e0d9cd] select-none"
      >
        <img
          :src="featuredDistrict.image"
          :alt="featuredDistrict.name"
          loading="lazy"
          class="absolute inset-0 w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-105"
        />

        <!-- Cinematic Multi-stop Dark Gradient Overlay -->
        <div
          class="absolute inset-0 bg-gradient-to-t from-[#061224]/90 via-[#091728]/25 to-black/15 transition-opacity duration-300 group-hover:from-[#061224]/95"
          aria-hidden="true"
        ></div>

        <!-- Top-Left View Count Pill (Exact match to reference screenshot) -->
        <div class="absolute top-4 left-4 z-10 flex items-center gap-2">
          <span class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-[#faf3e8]/95 backdrop-blur-md text-[#6e4720] text-xs font-bold shadow-md border border-[#ebdcc5]">
            <svg class="size-3.5 text-[#c87528] shrink-0" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 23c-4.97 0-9-3.58-9-8 0-3.19 2.13-6.02 4.5-7.86.37-.29.91-.03.91.44 0 1.18.47 2.26 1.29 3.01.29.27.76.11.83-.28.36-2.06 1.68-4.58 4.13-6.15.39-.25.9.06.86.52-.12 1.46.38 2.86 1.38 3.92 2.41 2.55 4.1 5.13 4.1 8.4 0 4.42-4.03 8-9 8z" />
            </svg>
            <span>{{ featuredDistrict.viewsCount }} lượt xem</span>
          </span>
        </div>

        <!-- Top-Right Price Growth Badge -->
        <div class="absolute top-4 right-4 z-10">
          <span class="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-[#10233f]/85 backdrop-blur-md text-[#dfbe86] text-xs font-bold border border-[#dfbe86]/35">
            <span>{{ featuredDistrict.macro.avgPricePerM2 }}</span>
            <span class="text-emerald-300 ml-1">▲ {{ featuredDistrict.macro.priceGrowthYoY }}</span>
          </span>
        </div>

        <!-- Bottom-Left District Info -->
        <div class="absolute inset-x-0 bottom-0 p-6 sm:p-7 z-10 flex items-end justify-between gap-4">
          <div>
            <h3 class="text-2xl sm:text-[26px] font-bold text-white tracking-tight leading-tight group-hover:text-[#dfbe86] transition-colors">
              {{ featuredDistrict.name }}, Đà Nẵng
            </h3>
            <p class="text-xs sm:text-sm text-white/90 font-medium mt-1.5">
              {{ featuredDistrict.activeListingsCount }} bất động sản đang bán
            </p>
          </div>

          <span class="w-10 h-10 rounded-full bg-white/15 backdrop-blur-md border border-white/25 text-white flex items-center justify-center group-hover:bg-[#dfbe86] group-hover:text-[#10233f] group-hover:border-[#dfbe86] transition-all shrink-0">
            ↗
          </span>
        </div>
      </article>

      <!-- RIGHT 2x2 GRID (6 cols, 4 cards) -->
      <div class="lg:col-span-6 grid grid-cols-1 sm:grid-cols-2 gap-5">
        <article
          v-for="item in secondaryDistricts"
          :key="item.id"
          @click="handleSelect(item)"
          role="button"
          tabindex="0"
          @keydown.enter.prevent="handleSelect(item)"
          @keydown.space.prevent="handleSelect(item)"
          :aria-label="`${item.name}, Đà Nẵng - ${item.viewsCount} lượt xem`"
          class="relative h-[224px] rounded-[20px] overflow-hidden cursor-pointer group shadow-sm border border-[#e0d9cd] select-none"
        >
          <img
            :src="item.image"
            :alt="item.name"
            loading="lazy"
            class="absolute inset-0 w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-105"
          />

          <!-- Dark Bottom Gradient Overlay -->
          <div
            class="absolute inset-0 bg-gradient-to-t from-[#061224]/90 via-[#091728]/25 to-black/10 transition-opacity duration-300 group-hover:from-[#061224]/95"
            aria-hidden="true"
          ></div>

          <!-- Top-Left View Count Pill -->
          <div class="absolute top-3.5 left-3.5 z-10">
            <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-[#faf3e8]/95 backdrop-blur-md text-[#6e4720] text-[11px] font-bold shadow-sm border border-[#ebdcc5]">
              <svg class="size-3 text-[#c87528] shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 23c-4.97 0-9-3.58-9-8 0-3.19 2.13-6.02 4.5-7.86.37-.29.91-.03.91.44 0 1.18.47 2.26 1.29 3.01.29.27.76.11.83-.28.36-2.06 1.68-4.58 4.13-6.15.39-.25.9.06.86.52-.12 1.46.38 2.86 1.38 3.92 2.41 2.55 4.1 5.13 4.1 8.4 0 4.42-4.03 8-9 8z" />
              </svg>
              <span>{{ item.viewsCount }} lượt xem</span>
            </span>
          </div>

          <!-- Top-Right Unit Price Pill -->
          <div class="absolute top-3.5 right-3.5 z-10">
            <span class="px-2.5 py-1 rounded-lg bg-[#10233f]/80 backdrop-blur-md text-[#dfbe86] text-[10px] font-bold border border-white/15">
              {{ item.macro.avgPricePerM2 }}
            </span>
          </div>

          <!-- Bottom-Left District Title & Count -->
          <div class="absolute inset-x-0 bottom-0 p-4 sm:p-5 z-10 flex items-end justify-between gap-2">
            <div>
              <h3 class="text-base sm:text-[17px] font-bold text-white tracking-tight leading-snug group-hover:text-[#dfbe86] transition-colors">
                {{ item.name }}, Đà Nẵng
              </h3>
              <p class="text-xs text-white/85 font-medium mt-0.5">
                {{ item.activeListingsCount }} bất động sản đang bán
              </p>
            </div>

            <span class="w-8 h-8 rounded-full bg-white/15 backdrop-blur-md border border-white/20 text-white text-xs flex items-center justify-center group-hover:bg-[#dfbe86] group-hover:text-[#10233f] transition-all shrink-0">
              ↗
            </span>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>
