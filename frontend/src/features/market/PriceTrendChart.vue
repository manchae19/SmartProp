<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  history: {
    type: Object,
    required: true,
    default: () => ({ labels: [], land: [], house: [], apartment: [] })
  }
})

// Toggle series visibility
const visibleSeries = ref({
  land: true,
  house: true,
  apartment: true
})

const seriesConfig = {
  land: {
    key: 'land',
    name: 'Đất nền đô thị',
    color: '#10233f', // Signature SmartProp Navy
    dotColor: '#10233f',
    gradientFrom: 'rgba(16, 35, 63, 0.14)',
    gradientTo: 'rgba(16, 35, 63, 0.0)'
  },
  house: {
    key: 'house',
    name: 'Nhà phố & Biệt thự',
    color: '#b3915f', // Signature Champagne Gold / Bronze
    dotColor: '#957344',
    gradientFrom: 'rgba(179, 145, 95, 0.16)',
    gradientTo: 'rgba(179, 145, 95, 0.0)'
  },
  apartment: {
    key: 'apartment',
    name: 'Căn hộ cao cấp',
    color: '#207760', // Signature Forest Emerald
    dotColor: '#185c49',
    gradientFrom: 'rgba(32, 119, 96, 0.14)',
    gradientTo: 'rgba(32, 119, 96, 0.0)'
  }
}

const timeRanges = ['Tất cả (2024–2026)', '2 năm gần nhất', '1 năm gần nhất']
const activeRange = ref('Tất cả (2024–2026)')

const filteredLabels = computed(() => {
  const all = props.history?.labels || []
  if (activeRange.value === '1 năm gần nhất') return all.slice(-4)
  if (activeRange.value === '2 năm gần nhất') return all.slice(-8)
  return all
})

const filteredData = computed(() => {
  const count = filteredLabels.value.length
  return {
    land: (props.history?.land || []).slice(-count),
    house: (props.history?.house || []).slice(-count),
    apartment: (props.history?.apartment || []).slice(-count)
  }
})

const hoveredIndex = ref(null)

// SVG Chart Geometry
const svgWidth = 860
const svgHeight = 320
const padding = { top: 32, right: 32, bottom: 44, left: 56 }

const chartMetrics = computed(() => {
  const labels = filteredLabels.value
  if (!labels.length) return { min: 0, max: 200, series: [], yTicks: [] }

  let allVals = []
  if (visibleSeries.value.land) allVals.push(...filteredData.value.land)
  if (visibleSeries.value.house) allVals.push(...filteredData.value.house)
  if (visibleSeries.value.apartment) allVals.push(...filteredData.value.apartment)

  if (!allVals.length) allVals = [50, 150]
  const rawMin = Math.min(...allVals)
  const rawMax = Math.max(...allVals)
  const range = rawMax - rawMin || 1

  const min = Math.max(0, Math.floor((rawMin - range * 0.12) / 10) * 10)
  const max = Math.ceil((rawMax + range * 0.12) / 10) * 10
  const delta = max - min || 1

  const chartW = svgWidth - padding.left - padding.right
  const chartH = svgHeight - padding.top - padding.bottom

  const tickCount = 4
  const yTicks = []
  for (let i = 0; i <= tickCount; i++) {
    const val = Math.round(min + (i / tickCount) * delta)
    const y = padding.top + chartH - (i / tickCount) * chartH
    yTicks.push({ y, value: val })
  }

  const series = Object.entries(seriesConfig).map(([key, cfg]) => {
    const vals = filteredData.value[key] || []
    const isVisible = visibleSeries.value[key]
    if (!isVisible || !vals.length) return { ...cfg, points: [], pathD: '', areaD: '', isVisible: false }

    const points = vals.map((val, idx) => {
      const x = padding.left + (idx / Math.max(1, vals.length - 1)) * chartW
      const y = padding.top + chartH - ((val - min) / delta) * chartH
      return { x, y, value: val, label: labels[idx] }
    })

    let pathD = `M ${points[0].x} ${points[0].y}`
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i]
      const p1 = points[i + 1]
      const cpX = (p0.x + p1.x) / 2
      pathD += ` C ${cpX} ${p0.y}, ${cpX} ${p1.y}, ${p1.x} ${p1.y}`
    }

    const baseLineY = padding.top + chartH
    const areaD = `${pathD} L ${points[points.length - 1].x} ${baseLineY} L ${points[0].x} ${baseLineY} Z`

    return { ...cfg, points, pathD, areaD, isVisible: true }
  })

  return { min, max, series, yTicks }
})

function toggleSeries(key) {
  visibleSeries.value[key] = !visibleSeries.value[key]
}
</script>

<template>
  <div class="rounded-3xl bg-white p-6 sm:p-8 border border-[#e7e1d7] shadow-2xs">
    <!-- Header with Editorial Title & Time Range Selector -->
    <div class="flex flex-col lg:flex-row lg:items-end justify-between gap-5 pb-6 border-b border-[#eee8de]">
      <div>
        <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-[#78572f] mb-2">
          CHỈ SỐ ĐỊNH LƯỢNG · LỊCH SỬ ĐƠN GIÁ
        </p>
        <h3 class="text-xl sm:text-2xl font-semibold text-[#10233f] tracking-tight">
          Biến động mặt bằng giá <span class="text-[#957344]">theo thời gian.</span>
        </h3>
        <p class="text-xs text-[#536178] mt-1.5 leading-relaxed">
          Đơn giá trung bình chuẩn hóa theo quý của 3 phân khúc chủ đạo · Đơn vị tính: <strong class="text-[#10233f]">Triệu VNĐ/m²</strong>
        </p>
      </div>

      <!-- Time range filter -->
      <div class="inline-flex items-center gap-1 bg-[#f7f5f0] p-1.5 rounded-full border border-[#e0d9cd] self-start lg:self-auto text-xs">
        <button
          v-for="range in timeRanges"
          :key="range"
          type="button"
          @click="activeRange = range; hoveredIndex = null"
          class="px-3.5 py-1.5 rounded-full font-semibold transition-all cursor-pointer"
          :class="activeRange === range
            ? 'bg-[#10233f] text-[#dfbe86] shadow-xs'
            : 'text-[#536178] hover:text-[#10233f]'"
        >
          {{ range }}
        </button>
      </div>
    </div>

    <!-- Series Toggles (Legend) -->
    <div class="flex flex-wrap items-center justify-between gap-4 pt-5 pb-3">
      <div class="flex flex-wrap items-center gap-2.5">
        <span class="text-xs text-[#8c7760] font-semibold mr-1">Phân khúc hiển thị:</span>
        <button
          v-for="(cfg, key) in seriesConfig"
          :key="key"
          type="button"
          @click="toggleSeries(key)"
          class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-xs font-semibold transition-all cursor-pointer"
          :class="visibleSeries[key]
            ? 'bg-[#f7f5f0] border-[#d4cbbd] text-[#10233f] shadow-2xs'
            : 'bg-white border-[#eee8de] text-[#8c7760] opacity-55 line-through'"
        >
          <span class="w-2.5 h-2.5 rounded-full" :style="{ backgroundColor: cfg.color }"></span>
          <span>{{ cfg.name }}</span>
        </button>
      </div>
      <span class="text-[11px] text-[#8c7760] italic">
        Rê chuột trên biểu đồ để đối chiếu đơn giá từng quý
      </span>
    </div>

    <!-- Chart SVG Container -->
    <div class="relative w-full overflow-x-auto mt-2">
      <div class="min-w-[680px]">
        <svg
          :viewBox="`0 0 ${svgWidth} ${svgHeight}`"
          class="w-full h-auto overflow-visible select-none"
        >
          <defs>
            <linearGradient
              v-for="s in chartMetrics.series"
              :key="'grad-' + s.key"
              :id="'grad-' + s.key"
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="0%" :stop-color="s.color" stop-opacity="0.14" />
              <stop offset="100%" :stop-color="s.color" stop-opacity="0.0" />
            </linearGradient>
          </defs>

          <!-- Horizontal Grid Lines & Y Ticks -->
          <g class="grid-lines">
            <template v-for="tick in chartMetrics.yTicks" :key="tick.y">
              <line
                :x1="padding.left"
                :y1="tick.y"
                :x2="svgWidth - padding.right"
                :y2="tick.y"
                stroke="#e7e1d7"
                stroke-width="1"
                stroke-dasharray="4,4"
              />
              <text
                :x="padding.left - 14"
                :y="tick.y + 4"
                text-anchor="end"
                class="text-[11px] fill-[#8c7760] font-semibold"
              >
                {{ tick.value }}
              </text>
            </template>
          </g>

          <!-- Vertical Guide Line on Hover -->
          <template v-if="hoveredIndex !== null">
            <line
              v-for="s in chartMetrics.series"
              :key="'guide-' + s.key"
              v-show="s.isVisible && s.points[hoveredIndex]"
              :x1="s.points[hoveredIndex].x"
              :y1="padding.top"
              :x2="s.points[hoveredIndex].x"
              :y2="svgHeight - padding.bottom"
              stroke="#b3915f"
              stroke-width="1.5"
              stroke-dasharray="3,3"
            />
          </template>

          <!-- Area Fills & Smooth Curves -->
          <g v-for="s in chartMetrics.series" :key="s.key">
            <path
              v-if="s.isVisible && s.areaD"
              :d="s.areaD"
              :fill="`url(#grad-${s.key})`"
              class="transition-all duration-300"
            />
            <path
              v-if="s.isVisible && s.pathD"
              :d="s.pathD"
              fill="none"
              :stroke="s.color"
              stroke-width="3"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="transition-all duration-300"
            />
          </g>

          <!-- X-Axis Labels & Hover Data Dots -->
          <g v-for="(lbl, idx) in filteredLabels" :key="idx">
            <text
              :x="padding.left + (idx / Math.max(1, filteredLabels.length - 1)) * (svgWidth - padding.left - padding.right)"
              :y="svgHeight - 12"
              text-anchor="middle"
              class="text-[11px] font-semibold transition"
              :class="hoveredIndex === idx ? 'fill-[#10233f] font-bold' : 'fill-[#8c7760]'"
            >
              {{ lbl }}
            </text>

            <rect
              :x="(padding.left + (idx / Math.max(1, filteredLabels.length - 1)) * (svgWidth - padding.left - padding.right)) - 25"
              :y="padding.top"
              width="50"
              :height="svgHeight - padding.top - padding.bottom"
              fill="transparent"
              class="cursor-pointer"
              @mouseenter="hoveredIndex = idx"
              @mouseleave="hoveredIndex = null"
            />

            <template v-for="s in chartMetrics.series" :key="s.key">
              <circle
                v-if="s.isVisible && s.points[idx]"
                :cx="s.points[idx].x"
                :cy="s.points[idx].y"
                :r="hoveredIndex === idx ? 6.5 : 4"
                fill="#ffffff"
                :stroke="s.color"
                :stroke-width="hoveredIndex === idx ? 3.5 : 2.5"
                class="transition-all duration-150 pointer-events-none"
              />
            </template>
          </g>
        </svg>

        <!-- Luxury Navy & Gold Tooltip -->
        <div
          v-if="hoveredIndex !== null"
          class="absolute pointer-events-none z-20 transition-all duration-100"
          :style="{
            left: `${Math.min(78, Math.max(12, (hoveredIndex / Math.max(1, filteredLabels.length - 1)) * 100))}%`,
            top: '14px'
          }"
        >
          <div class="bg-[#10233f]/95 backdrop-blur-md text-white p-4 rounded-2xl shadow-xl border border-[#dfbe86]/35 text-xs min-w-[220px]">
            <p class="font-bold text-[#dfbe86] pb-2 mb-2.5 border-b border-white/12 flex items-center justify-between gap-4">
              <span>Kỳ thống kê: {{ filteredLabels[hoveredIndex] }}</span>
              <span class="text-[10px] text-emerald-300 font-semibold uppercase tracking-wider">Chuẩn hóa</span>
            </p>
            <div class="space-y-2">
              <div
                v-for="s in chartMetrics.series"
                :key="s.key"
                v-show="s.isVisible && s.points[hoveredIndex]"
                class="flex items-center justify-between gap-4"
              >
                <div class="flex items-center gap-2">
                  <span class="w-2.5 h-2.5 rounded-full border border-white/40" :style="{ backgroundColor: s.color }"></span>
                  <span class="text-white/80">{{ s.name }}</span>
                </div>
                <span class="font-bold text-white">{{ s.points[hoveredIndex].value }} tr/m²</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
