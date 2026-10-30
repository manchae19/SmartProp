<script setup>
import { ref, computed } from 'vue'

// Dữ liệu giả lập để trình diễn giao diện; chưa kết nối API thị trường.
const marketType = ref('Tất cả')
const marketPeriod = ref(12)

const marketTypes = [
  { name: 'Căn hộ', color: '#38BDF8', values: [36, 37, 38, 37, 39, 40, 41, 40, 42, 43, 44, 46] },
  { name: 'Nhà phố', color: '#D8B887', values: [54, 55, 54, 57, 58, 59, 61, 60, 62, 65, 66, 68] },
  { name: 'Đất nền', color: '#34D399', values: [42, 43, 42, 44, 45, 44, 46, 48, 47, 49, 50, 52] },
]

const marketDistrictData = [
  { name: 'Hải Châu', prices: { 'Căn hộ': 52, 'Nhà phố': 80, 'Đất nền': 60 } },
  { name: 'Sơn Trà', prices: { 'Căn hộ': 48, 'Nhà phố': 69, 'Đất nền': 54 } },
  { name: 'Ngũ Hành Sơn', prices: { 'Căn hộ': 44, 'Nhà phố': 61, 'Đất nền': 49 } },
  { name: 'Cẩm Lệ', prices: { 'Căn hộ': 32, 'Nhà phố': 48, 'Đất nền': 38 } },
]

const visibleMarketSeries = computed(() =>
  marketType.value === 'Tất cả'
    ? marketTypes
    : marketTypes.filter((item) => item.name === marketType.value)
)

const marketSummary = computed(() => {
  const series = visibleMarketSeries.value
  const first = series.reduce((sum, item) => sum + item.values[12 - marketPeriod.value], 0) / series.length
  const last = series.reduce((sum, item) => sum + item.values[11], 0) / series.length

  return {
    price: last,
    change: ((last - first) / first) * 100,
  }
})

const marketDistricts = computed(() =>
  marketDistrictData.map((item) => ({
    name: item.name,
    price: marketType.value === 'Tất cả'
      ? Object.values(item.prices).reduce((sum, price) => sum + price, 0) / 3
      : item.prices[marketType.value],
  })).sort((a, b) => b.price - a.price)
)

const marketChart = computed(() => {
  const start = 12 - marketPeriod.value
  const series = visibleMarketSeries.value
  const values = series.flatMap((item) => item.values.slice(start))
  const low = Math.floor((Math.min(...values) - 5) / 10) * 10
  const high = Math.ceil((Math.max(...values) + 5) / 10) * 10

  const x = (index) => 52 + (index * 650) / (marketPeriod.value - 1)
  const y = (value) => 245 - ((value - low) / (high - low)) * 205

  return {
    lines: series.map((item) => ({
      name: item.name,
      color: item.color,
      points: item.values.slice(start).map((value, index) => `${x(index)},${y(value)}`).join(' '),
      latest: item.values[11],
    })),
    grid: Array.from({ length: 5 }, (_, i) => ({
      value: low + ((high - low) * i) / 4,
      y: y(low + ((high - low) * i) / 4),
    })),
    labels: Array.from({ length: marketPeriod.value }, (_, i) => ({
      text: `T${start + i + 1}`,
      x: x(i),
    })),
  }
})
</script>

<template>
<section id="market-demo" aria-labelledby="market-heading" class="bg-[#F1EEE8] py-14 text-[#142B4F] md:py-20">
  <div class="mx-auto max-w-7xl px-5 lg:px-8">
    <div class="flex flex-wrap items-end justify-between gap-6">
      <div>
        <p class="mb-3 text-xs font-bold uppercase tracking-[0.3em] text-[#B3915F]">
          Market Intelligence
        </p>
        <h2 id="market-heading" class="text-3xl font-semibold leading-tight sm:text-4xl md:text-5xl">
          Dữ liệu kể <span class="text-[#B3915F]">câu chuyện thị trường.</span>
        </h2>
        <p class="mt-4 max-w-2xl text-sm leading-7 text-[#536178]">
          Khám phá xu hướng giá căn hộ, nhà phố và đất nền tại Đà Nẵng.
          <span class="ml-1 inline-block font-semibold text-[#8B683A]">Dữ liệu mô phỏng.</span>
        </p>
      </div>

      <div class="flex flex-wrap gap-2" role="group" aria-label="Lọc loại hình bất động sản">
        <button
          v-for="item in ['Tất cả', 'Căn hộ', 'Nhà phố', 'Đất nền']"
          :key="item"
          type="button"
          @click="marketType = item"
          :aria-pressed="marketType === item"
          class="cursor-pointer rounded-full border px-4 py-2.5 text-xs font-bold transition focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#B3915F]"
          :class="marketType === item
            ? 'border-[#142B4F] bg-[#142B4F] text-white'
            : 'border-[#DCD5CA] bg-white text-[#142B4F] hover:border-[#B3915F]'"
        >
          {{ item }}
        </button>
      </div>
    </div>

    <div class="mt-9 grid gap-4 sm:grid-cols-3">
      <div class="rounded-2xl border border-[#E7E1D7] bg-white p-6">
        <p class="text-xs font-semibold text-[#536178]">
          Giá trung bình theo loại hình
        </p>
        <p class="mt-3 text-3xl font-bold text-[#142B4F]">
          {{ marketSummary.price.toFixed(1) }}
          <span class="text-sm font-medium">triệu/m²</span>
        </p>
      </div>

      <div class="rounded-2xl border border-[#E7E1D7] bg-white p-6">
        <p class="text-xs font-semibold text-[#536178]">
          Biến động trong kỳ
        </p>
        <p
          class="mt-3 text-3xl font-bold"
          :class="marketSummary.change >= 0 ? 'text-emerald-700' : 'text-rose-700'"
        >
          {{ marketSummary.change >= 0 ? '+' : '' }}{{ marketSummary.change.toFixed(1) }}%
        </p>
      </div>

      <div class="rounded-2xl border border-[#E7E1D7] bg-white p-6">
        <p class="text-xs font-semibold text-[#536178]">
          Phạm vi phân tích
        </p>
        <p class="mt-3 text-3xl font-bold text-[#142B4F]">
          4 <span class="text-sm font-medium">khu vực</span>
        </p>
      </div>
    </div>

    <div class="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)]">

      <!-- BIỂU ĐỒ GIÁ -->
      <div class="min-w-0 rounded-3xl border border-[#E7E1D7] bg-white p-5 shadow-sm md:p-7">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 class="text-xl font-bold">
              Xu hướng giá theo loại hình
            </h3>
            <p class="mt-1 text-xs text-[#536178]">
              Đơn vị: triệu đồng/m²
            </p>
          </div>

          <div class="flex gap-2" role="group" aria-label="Khoảng thời gian thống kê">
            <button
              v-for="period in [3, 6, 12]"
              :key="period"
              type="button"
              @click="marketPeriod = period"
              :aria-pressed="marketPeriod === period"
              class="cursor-pointer rounded-full px-3 py-2.5 text-xs font-bold transition focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#B3915F]"
              :class="marketPeriod === period
                ? 'bg-[#D8B887] text-[#142B4F]'
                : 'bg-[#F1EEE8] text-[#536178] hover:bg-[#E7E1D7]'"
            >
              {{ period }} tháng
            </button>
          </div>
        </div>

        <div class="mt-6 w-full overflow-x-auto overscroll-x-contain">
          <svg
            viewBox="0 0 750 295"
            role="img"
            aria-label="Biểu đồ đường xu hướng giá bất động sản minh họa"
            class="block w-full min-w-[420px]"
          >
            <g v-for="tick in marketChart.grid" :key="tick.value">
              <line
                x1="52"
                :y1="tick.y"
                x2="702"
                :y2="tick.y"
                stroke="#E7E1D7"
                stroke-dasharray="4 5"
              />
              <text
                x="43"
                :y="tick.y + 4"
                text-anchor="end"
                fill="#64748B"
                font-size="12"
              >
                {{ tick.value.toFixed(0) }}
              </text>
            </g>

            <g v-for="label in marketChart.labels" :key="label.text">
              <text
                :x="label.x"
                y="275"
                text-anchor="middle"
                fill="#64748B"
                font-size="12"
              >
                {{ label.text }}
              </text>
            </g>

            <polyline
              v-for="line in marketChart.lines"
              :key="line.name"
              :points="line.points"
              fill="none"
              :stroke="line.color"
              stroke-width="3.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </div>

        <div class="mt-3 flex flex-wrap gap-x-6 gap-y-3">
          <div
            v-for="line in marketChart.lines"
            :key="line.name"
            class="flex items-center gap-2 text-xs text-[#536178]"
          >
            <span
              class="h-2.5 w-2.5 rounded-full"
              :style="{ backgroundColor: line.color }"
            ></span>
            <span>
              {{ line.name }}:
              <strong class="text-[#142B4F]">
                {{ line.latest }} triệu/m²
              </strong>
            </span>
          </div>
        </div>
      </div>

      <!-- SO SÁNH KHU VỰC -->
      <div class="rounded-3xl bg-[#142B4F] p-6 text-white shadow-sm md:p-8">
        <p class="text-xs font-bold uppercase tracking-[0.2em] text-[#D8B887]">
          District Comparison
        </p>
        <h3 class="mt-3 text-2xl font-semibold">
          Giá theo khu vực
        </h3>
        <p class="mt-2 text-xs leading-6 text-white/60">
          Giá trung bình tham khảo · triệu đồng/m²
        </p>

        <div class="mt-7 space-y-6">
          <div
            v-for="district in marketDistricts"
            :key="district.name"
          >
            <div class="mb-2 flex items-center justify-between gap-3 text-sm">
              <span class="font-medium">
                {{ district.name }}
              </span>
              <span class="font-bold text-[#D8B887]">
                {{ district.price.toFixed(1) }}
              </span>
            </div>

            <div class="h-2 overflow-hidden rounded-full bg-white/15">
              <div
                class="h-full rounded-full bg-[#D8B887] transition-all duration-300"
                :style="{ width: `${district.price / 90 * 100}%` }"
              ></div>
            </div>
          </div>
        </div>

        <p class="mt-8 border-t border-white/15 pt-5 text-xs leading-6 text-white/60">
          Dữ liệu mô phỏng phục vụ trình diễn giao diện, không phải báo cáo giá thực tế hay tư vấn đầu tư.
        </p>
      </div>
    </div>
  </div>
</section>
</template>
