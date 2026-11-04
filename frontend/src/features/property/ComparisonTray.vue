<script setup>
import { ref, computed, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useComparison } from '../../hooks/useComparison.js'
import { api } from '../auth/api.js'
import { isPublicProperty } from './usePublicListings.js'
import { price, compactPrice, types, states } from './property.js'
import PrivateImage from '../../components/PrivateImage.vue'
import BrowseTileMap from '../map/BrowseTileMap.vue'

const route = useRoute()
const compare = useComparison()
const dialog = ref(null)
const busy = ref(false)
const error = ref('')
const showOnlyDiff = ref(false)
const showMap = ref(true)

const visible = computed(() => ['/home', '/listings', '/map'].includes(route.path))
const mixed = computed(() => new Set(compare.items.value.map(p => `${p.transactionType}:${p.priceUnit}`)).size > 1)

let sequence = 0
async function open() {
  const run = ++sequence
  busy.value = true
  error.value = ''
  const originals = [...compare.items.value]
  const result = await Promise.allSettled(originals.map(p => api('/properties/' + encodeURIComponent(p.id), { authenticated: false })))
  if (run !== sequence) return
  busy.value = false
  if (compare.items.value.map(p => p.id).join('|') !== originals.map(p => p.id).join('|')) {
    error.value = 'Lựa chọn đã thay đổi trong lúc kiểm tra. Hãy bấm so sánh lại.'
    return
  }
  if (result.some(r => r.status === 'rejected' && r.reason?.status !== 404)) {
    error.value = 'Chưa xác minh được trạng thái mới nhất của các tin. Hãy thử lại.'
    return
  }
  const current = result.flatMap(r => r.status === 'fulfilled' && isPublicProperty(r.value) ? [r.value] : [])
  compare.replace(current)
  if (current.length !== originals.length) {
    error.value = 'Đã bỏ tin không còn công khai. Hãy chọn ít nhất 2 tin hợp lệ.'
    return
  }
  if (current.length < 2) return
  dialog.value.showModal()
}

function close() {
  dialog.value?.close()
}

watch(() => route.fullPath, () => {
  sequence++
  busy.value = false
  close()
})

onBeforeUnmount(() => {
  sequence++
  close()
})

// Helper methods for calculations & visuals
function cover(p) {
  return (p.images?.find(i => i.cover) || p.images?.[0])?.url
}

function getNumericPrice(p) {
  const raw = Number(p.priceExact ?? p.price ?? 0)
  return Number.isFinite(raw) ? raw : 0
}

function getNumericArea(p) {
  const raw = Number(p.areaSqmExact ?? p.areaSqm ?? 0)
  return Number.isFinite(raw) ? raw : 0
}

function getUnitPricePerSqm(p) {
  const pr = getNumericPrice(p)
  const ar = getNumericArea(p)
  if (pr > 0 && ar > 0 && p.transactionType === 'SALE' && p.priceUnit === 'TOTAL') {
    return Math.round(pr / ar)
  }
  return null
}

function formatUnitPrice(p) {
  const u = getUnitPricePerSqm(p)
  if (!u) return '—'
  const million = (u / 1000000).toLocaleString('vi-VN', { maximumFractionDigits: 1 })
  return `${million} tr/m²`
}

function calculateDistanceKm(lat1, lon1, lat2, lon2) {
  if (lat1 == null || lon1 == null || lat2 == null || lon2 == null) return null
  const y1 = Number(lat1), x1 = Number(lon1), y2 = Number(lat2), x2 = Number(lon2)
  if (!Number.isFinite(y1) || !Number.isFinite(x1) || !Number.isFinite(y2) || !Number.isFinite(x2)) return null
  const R = 6371 // km
  const dLat = (y2 - y1) * Math.PI / 180
  const dLon = (x2 - x1) * Math.PI / 180
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(y1 * Math.PI / 180) * Math.cos(y2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  const d = R * c
  return d < 1 ? `${Math.round(d * 1000)} m` : `${d.toFixed(1)} km`
}

// Visual comparisons
const metricsComparison = computed(() => {
  const items = compare.items.value
  if (items.length < 2) return null

  // 1. Price
  const prices = items.map(getNumericPrice)
  const maxPrice = Math.max(...prices) || 1
  const priceBars = items.map(p => ({
    id: p.id,
    pct: Math.max(10, Math.round((getNumericPrice(p) / maxPrice) * 100)),
    label: compactPrice(p),
    isLowest: getNumericPrice(p) === Math.min(...prices) && prices.some(v => v !== prices[0])
  }))

  // 2. Unit Price
  const units = items.map(getUnitPricePerSqm).filter(Boolean)
  let unitBars = []
  if (units.length === items.length) {
    const maxUnit = Math.max(...units) || 1
    const minUnit = Math.min(...units)
    unitBars = items.map(p => {
      const u = getUnitPricePerSqm(p)
      return {
        id: p.id,
        pct: Math.max(10, Math.round((u / maxUnit) * 100)),
        label: formatUnitPrice(p),
        isLowest: u === minUnit && minUnit !== maxUnit,
        savingPct: u === minUnit && minUnit !== maxUnit ? Math.round((maxUnit - minUnit) / maxUnit * 100) : 0
      }
    })
  }

  // 3. Area
  const areas = items.map(getNumericArea)
  const maxArea = Math.max(...areas) || 1
  const areaBars = items.map(p => ({
    id: p.id,
    pct: Math.max(10, Math.round((getNumericArea(p) / maxArea) * 100)),
    label: `${p.areaSqmExact ?? p.areaSqm} m²`,
    isLargest: getNumericArea(p) === maxArea && areas.some(v => v !== areas[0])
  }))

  // 4. Distance (if 2 properties)
  let distance = null
  if (items.length === 2 && items[0].latitude && items[1].latitude) {
    distance = calculateDistanceKm(items[0].latitude, items[0].longitude, items[1].latitude, items[1].longitude)
  }

  return { priceBars, unitBars, areaBars, distance }
})

// Smart highlights per property
function getPropertyHighlights(p) {
  const items = compare.items.value
  if (items.length < 2) return []
  const badges = []
  const prices = items.map(getNumericPrice)
  const units = items.map(getUnitPricePerSqm).filter(Boolean)
  const areas = items.map(getNumericArea)

  if (prices.length > 1 && getNumericPrice(p) === Math.min(...prices) && new Set(prices).size > 1) {
    badges.push({ text: 'Giá tổng tốt nhất', type: 'best-price' })
  }
  const u = getUnitPricePerSqm(p)
  if (units.length === items.length && u === Math.min(...units) && new Set(units).size > 1) {
    badges.push({ text: 'Đơn giá/m² tối ưu', type: 'best-unit' })
  }
  if (areas.length > 1 && getNumericArea(p) === Math.max(...areas) && new Set(areas).size > 1) {
    badges.push({ text: 'Diện tích lớn nhất', type: 'best-area' })
  }
  if (p.bedrooms && items.some(other => (other.bedrooms || 0) < p.bedrooms)) {
    badges.push({ text: `${p.bedrooms} phòng ngủ`, type: 'highlight' })
  }
  return badges
}

// Amenities Union
const allAmenities = computed(() => {
  const set = new Set()
  for (const p of compare.items.value) {
    if (Array.isArray(p.declaredAmenities)) {
      for (const a of p.declaredAmenities) {
        if (a && typeof a === 'string' && a.trim()) set.add(a.trim())
      }
    }
  }
  return Array.from(set)
})

// Grouped Criteria Matrix
const criteriaGroups = computed(() => {
  const groups = [
    {
      name: 'Tài chính & Hiệu quả',
      icon: '💰',
      rows: [
        {
          label: 'Tổng giá chào',
          isDiff: (items) => new Set(items.map(p => getNumericPrice(p))).size > 1,
          render: (p) => ({ highlight: true, text: compactPrice(p), sub: price(p) })
        },
        {
          label: 'Đơn giá / m²',
          isDiff: (items) => new Set(items.map(p => getUnitPricePerSqm(p))).size > 1,
          render: (p) => ({ text: formatUnitPrice(p), highlight: false })
        }
      ]
    },
    {
      name: 'Vị trí & Quy hoạch',
      icon: '📍',
      rows: [
        {
          label: 'Quận / Huyện',
          isDiff: (items) => new Set(items.map(p => p.district || '')).size > 1,
          render: (p) => ({ text: p.district || '—' })
        },
        {
          label: 'Tuyến đường & Phường',
          isDiff: (items) => new Set(items.map(p => `${p.address}-${p.ward}`)).size > 1,
          render: (p) => ({ text: [p.address, p.ward].filter(Boolean).join(', ') || '—' })
        },
        {
          label: 'Hướng phong thủy',
          isDiff: (items) => new Set(items.map(p => p.direction || '')).size > 1,
          render: (p) => ({ text: p.direction ? `🧭 Hướng ${p.direction}` : '—' })
        }
      ]
    },
    {
      name: 'Quy mô & Thiết kế',
      icon: '📐',
      rows: [
        {
          label: 'Loại hình BĐS',
          isDiff: (items) => new Set(items.map(p => p.propertyType)).size > 1,
          render: (p) => ({ text: types[p.propertyType] || p.propertyType })
        },
        {
          label: 'Diện tích đất / sàn',
          isDiff: (items) => new Set(items.map(p => getNumericArea(p))).size > 1,
          render: (p) => ({ text: `${p.areaSqmExact ?? p.areaSqm} m²` })
        },
        {
          label: 'Số phòng ngủ',
          isDiff: (items) => new Set(items.map(p => p.bedrooms ?? '')).size > 1,
          render: (p) => ({ text: p.bedrooms != null ? `${p.bedrooms} phòng ngủ` : '—' })
        },
        {
          label: 'Số phòng tắm / WC',
          isDiff: (items) => new Set(items.map(p => p.bathrooms ?? '')).size > 1,
          render: (p) => ({ text: p.bathrooms != null ? `${p.bathrooms} phòng tắm` : '—' })
        },
        {
          label: 'Số tầng kết cấu',
          isDiff: (items) => new Set(items.map(p => p.floor ?? '')).size > 1,
          render: (p) => ({ text: p.floor != null ? `${p.floor} tầng` : '—' })
        }
      ]
    }
  ]

  if (!showOnlyDiff.value) return groups

  return groups
    .map(g => ({
      ...g,
      rows: g.rows.filter(r => r.isDiff(compare.items.value))
    }))
    .filter(g => g.rows.length > 0)
})

// Map points for BrowseTileMap
const mapPoints = computed(() => {
  return compare.items.value
    .filter(p => Number.isFinite(Number(p.latitude)) && Number.isFinite(Number(p.longitude)))
    .map(p => ({
      id: p.id,
      latitude: Number(p.latitude),
      longitude: Number(p.longitude),
      title: p.title,
      transactionType: p.transactionType,
      priceExact: p.priceExact,
      price: p.price,
      priceUnit: p.priceUnit
    }))
})
</script>

<template>
  <!-- Floating Tray in viewport -->
  <aside v-if="visible && compare.items.value.length" class="comparison-tray" aria-label="Các tin đã chọn để so sánh">
    <div class="tray-items">
      <div class="tray-count-badge">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 3h5v5M4 20L21 3m0 13v5h-5M4 4l5 5"/></svg>
        <strong>So sánh {{ compare.items.value.length }}/3</strong>
      </div>
      <div v-for="item in compare.items.value" :key="item.id" class="tray-chip">
        <div class="chip-thumb">
          <PrivateImage :src="cover(item)" :alt="item.title" />
        </div>
        <span class="chip-title" :title="item.title">{{ item.title }}</span>
        <button type="button" :disabled="busy" :aria-label="'Bỏ so sánh ' + item.title" class="chip-remove" @click="compare.toggle(item)">×</button>
      </div>
    </div>
    <div class="tray-actions">
      <button type="button" class="btn-clear" :disabled="busy" @click="compare.clear">Xóa hết</button>
      <button type="button" class="btn-compare primary" :disabled="busy || compare.items.value.length < 2" @click="open">
        {{ busy ? 'Đang kiểm tra…' : `So sánh ngay (${compare.items.value.length}) ↗` }}
      </button>
    </div>
    <p v-if="compare.notice.value || error" class="tray-status" role="status">{{ error || compare.notice.value }}</p>
  </aside>

  <!-- Detailed Modal Comparison Dialog -->
  <dialog ref="dialog" class="comparison-dialog" aria-labelledby="compare-heading" @click="event => { if (event.target === dialog) close() }">
    <div class="dialog-inner">
      <!-- Header Bar -->
      <header class="dialog-header">
        <div>
          <div class="dialog-badge">SMARTPROP / BỘ SO SÁNH TRỰC QUAN</div>
          <h2 id="compare-heading">So sánh bất động sản</h2>
          <p class="dialog-subtitle">Phân tích đa chiều về giá cả, đơn giá/m², quy mô và vị trí địa lý tương quan</p>
        </div>
        <div class="dialog-controls">
          <label class="toggle-btn" :class="{ active: showOnlyDiff }">
            <input type="checkbox" v-model="showOnlyDiff" />
            <span>⚡ Chỉ xem điểm khác biệt</span>
          </label>
          <button v-if="mapPoints.length" type="button" class="btn-map-toggle" :class="{ active: showMap }" @click="showMap = !showMap">
            🗺️ {{ showMap ? 'Ẩn bản đồ' : 'Xem bản đồ vị trí' }}
          </button>
          <button type="button" class="btn-close" aria-label="Đóng so sánh" @click="close">✕</button>
        </div>
      </header>

      <div v-if="mixed" class="mixed-note">
        ⚠️ <strong>Lưu ý:</strong> Các tin có hình thức giao dịch hoặc đơn vị tính khác nhau (Bán vs Cho thuê). Hệ thống không so sánh trực tiếp tổng giá bán với giá thuê theo kỳ.
      </div>

      <!-- Section 1: Visual Interactive Comparison Metrics (Progress Bars) -->
      <section v-if="metricsComparison" class="metrics-dashboard">
        <h3 class="section-title">📊 Trực quan hóa tương quan chỉ số</h3>

        <div class="metrics-grid">
          <!-- Total Price Meter -->
          <div class="metric-card">
            <div class="metric-head">
              <span class="metric-name">Tổng giá chào</span>
              <span class="metric-sub">Thấp nhất là lợi thế</span>
            </div>
            <div class="metric-bars">
              <div v-for="(b, idx) in metricsComparison.priceBars" :key="b.id" class="bar-row">
                <span class="bar-index" :class="'prop-idx-' + idx">Căn {{ idx + 1 }}</span>
                <div class="bar-track">
                  <div class="bar-fill" :class="['fill-' + idx, { best: b.isLowest }]" :style="{ width: b.pct + '%' }"></div>
                </div>
                <span class="bar-val">{{ b.label }}</span>
                <span v-if="b.isLowest" class="bar-badge green">✓ Giá tốt</span>
              </div>
            </div>
          </div>

          <!-- Unit Price Meter -->
          <div v-if="metricsComparison.unitBars.length" class="metric-card">
            <div class="metric-head">
              <span class="metric-name">Đơn giá trên mỗi m²</span>
              <span class="metric-sub">Đo lường độ đắt / rẻ thực tế</span>
            </div>
            <div class="metric-bars">
              <div v-for="(b, idx) in metricsComparison.unitBars" :key="b.id" class="bar-row">
                <span class="bar-index" :class="'prop-idx-' + idx">Căn {{ idx + 1 }}</span>
                <div class="bar-track">
                  <div class="bar-fill" :class="['fill-' + idx, { best: b.isLowest }]" :style="{ width: b.pct + '%' }"></div>
                </div>
                <span class="bar-val">{{ b.label }}</span>
                <span v-if="b.isLowest && b.savingPct > 0" class="bar-badge green">Tiết kiệm {{ b.savingPct }}%</span>
              </div>
            </div>
          </div>

          <!-- Area Meter -->
          <div class="metric-card">
            <div class="metric-head">
              <span class="metric-name">Diện tích sử dụng</span>
              <span class="metric-sub">Không gian sống</span>
            </div>
            <div class="metric-bars">
              <div v-for="(b, idx) in metricsComparison.areaBars" :key="b.id" class="bar-row">
                <span class="bar-index" :class="'prop-idx-' + idx">Căn {{ idx + 1 }}</span>
                <div class="bar-track">
                  <div class="bar-fill" :class="['fill-' + idx, { best: b.isLargest }]" :style="{ width: b.pct + '%' }"></div>
                </div>
                <span class="bar-val">{{ b.label }}</span>
                <span v-if="b.isLargest" class="bar-badge gold">Rộng nhất</span>
              </div>
            </div>
          </div>

          <!-- Spatial Distance Card (when 2 properties) -->
          <div v-if="metricsComparison.distance" class="metric-card distance-card">
            <div class="metric-head">
              <span class="metric-name">Khoảng cách địa lý</span>
              <span class="metric-sub">Giữa 2 bất động sản</span>
            </div>
            <div class="distance-content">
              <div class="distance-icon">📍 ⟷ 📍</div>
              <div class="distance-number">{{ metricsComparison.distance }}</div>
              <p class="distance-desc">Khoảng cách đường chim bay giữa 2 vị trí trên bản đồ Đà Nẵng</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Section 2: Interactive Dual Map Preview -->
      <section v-if="showMap && mapPoints.length" class="map-section">
        <div class="map-header">
          <div class="map-title">
            <span class="pin-symbol">📍</span>
            <strong>Bản đồ so sánh vị trí địa lý tương quan</strong>
            <span class="map-hint">Đã ghim {{ mapPoints.length }} bất động sản trên cùng bản đồ</span>
          </div>
        </div>
        <div class="map-viewport-wrapper">
          <BrowseTileMap :points="mapPoints" />
        </div>
      </section>

      <!-- Section 3: Visual Cards Header & Detailed Matrix Table -->
      <section class="table-container">
        <h3 class="section-title">📋 Bảng ma trận so sánh chi tiết</h3>

        <div class="table-scroll" tabindex="0" role="region" aria-label="Bảng so sánh chi tiết, cuộn ngang để xem thêm">
          <table class="comparison-table">
            <thead>
              <tr>
                <th scope="col" class="corner-header">
                  <div class="criteria-header-box">
                    <span>Tiêu chí so sánh</span>
                    <small v-if="showOnlyDiff">Đang lọc điểm khác</small>
                  </div>
                </th>
                <th v-for="(p, idx) in compare.items.value" :key="p.id" scope="col" class="property-col-header">
                  <!-- Visual Card Header in each Column -->
                  <div class="prop-card-header">
                    <div class="card-badge-row">
                      <span class="card-num-pill" :class="'bg-idx-' + idx">Căn {{ idx + 1 }}</span>
                      <span class="card-type-pill">{{ types[p.propertyType] || p.propertyType }}</span>
                      <button type="button" class="btn-remove-col" :title="'Bỏ so sánh ' + p.title" @click="compare.toggle(p)">×</button>
                    </div>

                    <div class="card-img-box">
                      <PrivateImage :src="cover(p)" :alt="p.title" />
                      <span class="card-tag">{{ p.transactionType === 'RENT' ? 'Cho thuê' : 'Bán' }}</span>
                    </div>

                    <div class="card-info-box">
                      <RouterLink :to="'/listing/' + p.id" class="card-title-link" :title="p.title" @click="close">
                        {{ p.title }} ↗
                      </RouterLink>
                      <div class="card-price-row">
                        <strong class="card-price-compact">{{ compactPrice(p) }}</strong>
                        <span class="card-price-full">{{ price(p) }}</span>
                      </div>
                    </div>

                    <!-- Smart Advantages Badges -->
                    <div class="card-advantages">
                      <span v-for="badge in getPropertyHighlights(p)" :key="badge.text" class="advantage-pill" :class="badge.type">
                        ★ {{ badge.text }}
                      </span>
                    </div>

                    <RouterLink :to="'/listing/' + p.id" class="btn-view-detail" @click="close">
                      Xem chi tiết tin ↗
                    </RouterLink>
                  </div>
                </th>
              </tr>
            </thead>

            <tbody>
              <!-- Grouped Rows -->
              <template v-for="group in criteriaGroups" :key="group.name">
                <tr class="group-header-row">
                  <th :colspan="compare.items.value.length + 1" scope="colgroup">
                    <span class="group-icon">{{ group.icon }}</span>
                    <span class="group-title">{{ group.name }}</span>
                  </th>
                </tr>
                <tr v-for="row in group.rows" :key="row.label" class="data-row">
                  <th scope="row" class="row-label">{{ row.label }}</th>
                  <td v-for="p in compare.items.value" :key="p.id" class="row-cell">
                    <div v-if="row.render(p).sub" class="cell-price-box">
                      <strong class="cell-main-price">{{ row.render(p).text }}</strong>
                      <small class="cell-sub-price">{{ row.render(p).sub }}</small>
                    </div>
                    <span v-else class="cell-text" :class="{ 'text-highlight': row.render(p).highlight }">
                      {{ row.render(p).text }}
                    </span>
                  </td>
                </tr>
              </template>

              <!-- Amenities Matrix Row -->
              <tr v-if="allAmenities.length" class="group-header-row">
                <th :colspan="compare.items.value.length + 1" scope="colgroup">
                  <span class="group-icon">✨</span>
                  <span class="group-title">Tiện ích khai báo & Điểm nổi bật</span>
                </th>
              </tr>
              <tr v-for="amenity in allAmenities" :key="amenity" class="data-row">
                <th scope="row" class="row-label">{{ amenity }}</th>
                <td v-for="p in compare.items.value" :key="p.id" class="row-cell">
                  <span v-if="p.declaredAmenities?.includes(amenity)" class="amenity-pill has">
                    ✓ Có sẵn
                  </span>
                  <span v-else class="amenity-pill missing">
                    — Chưa có
                  </span>
                </td>
              </tr>

              <!-- Legal Documents Row -->
              <tr class="group-header-row">
                <th :colspan="compare.items.value.length + 1" scope="colgroup">
                  <span class="group-icon">🛡️</span>
                  <span class="group-title">Pháp lý & Giấy tờ</span>
                </th>
              </tr>
              <tr class="data-row">
                <th scope="row" class="row-label">Tình trạng pháp lý</th>
                <td v-for="p in compare.items.value" :key="p.id" class="row-cell">
                  <span class="legal-badge">Sổ đỏ / Sổ hồng chính chủ</span>
                  <small class="legal-note">Xem hồ sơ công khai tại trang chi tiết tin đăng</small>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <footer class="dialog-footer">
        <p class="dialog-disclaimer">
          * Thông tin, hình ảnh và giá chào do người đăng cung cấp. SmartProp hỗ trợ công cụ so sánh trực quan độc lập nhằm giúp bạn đưa ra quyết định tối ưu nhất.
        </p>
        <button type="button" class="btn-close-bottom" @click="close">Đóng bảng so sánh</button>
      </footer>
    </div>
  </dialog>
</template>

<style scoped>
/* Floating Tray */
.comparison-tray {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 50;
  width: min(1080px, calc(100% - 32px));
  border: 1px solid #c9b48c;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(16px);
  border-radius: 20px;
  padding: 12px 20px;
  box-shadow: 0 12px 48px rgba(20, 43, 79, 0.22);
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  color: #142b4f;
  animation: traySlideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes traySlideUp {
  from { transform: translate(-50%, 20px); opacity: 0; }
  to { transform: translate(-50%, 0); opacity: 1; }
}

.tray-items {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
  flex-wrap: wrap;
}

.tray-count-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #142b4f;
  background: #f4efe6;
  padding: 6px 12px;
  border-radius: 30px;
}

.tray-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f5f2eb;
  border: 1px solid #e5ded3;
  border-radius: 30px;
  padding: 4px 10px 4px 4px;
  max-width: 210px;
}

.chip-thumb {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  background: #ddd;
}

.chip-thumb :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.chip-title {
  font-size: 12px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip-remove {
  background: transparent;
  border: 0;
  color: #7a8b9e;
  font-size: 16px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  border-radius: 50%;
}

.chip-remove:hover {
  color: #b13724;
}

.tray-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.btn-clear {
  background: transparent;
  border: 1px solid #d5cbbe;
  border-radius: 30px;
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 600;
  color: #6c7d93;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-clear:hover {
  background: #efebe4;
  color: #142b4f;
}

.btn-compare {
  background: linear-gradient(135deg, #142b4f 0%, #1e3d6f 100%);
  color: white;
  border: 0;
  border-radius: 30px;
  padding: 10px 22px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(20, 43, 79, 0.25);
  transition: transform 0.15s, box-shadow 0.15s;
}

.btn-compare:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(20, 43, 79, 0.35);
}

.btn-compare:disabled {
  opacity: 0.5;
  cursor: default;
}

.tray-status {
  width: 100%;
  font-size: 12px;
  color: #b13724;
  margin: 0;
}

/* Modal Dialog */
.comparison-dialog {
  width: min(1200px, calc(100vw - 32px));
  max-height: 90vh;
  border: 0;
  border-radius: 26px;
  padding: 0;
  color: #142b4f;
  background: #faf8f5;
  margin: auto;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(7, 22, 43, 0.38);
}

.comparison-dialog::backdrop {
  background: rgba(7, 22, 43, 0.75);
  backdrop-filter: blur(8px);
}

.dialog-inner {
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  overflow-y: auto;
  padding: 30px 36px 36px;
}

.dialog-inner > * {
  flex-shrink: 0;
}

/* Dialog Header */
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  padding-bottom: 22px;
  border-bottom: 1px solid #e7ded0;
}

.dialog-badge {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: #937142;
  margin-bottom: 6px;
}

.dialog-header h2 {
  font-size: 28px;
  font-weight: 750;
  color: #142b4f;
  margin: 0 0 6px;
  letter-spacing: -0.02em;
}

.dialog-subtitle {
  font-size: 13px;
  color: #5d6d84;
  margin: 0;
}

.dialog-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toggle-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 30px;
  border: 1px solid #d5cbbe;
  background: white;
  font-size: 12px;
  font-weight: 600;
  color: #53647b;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s;
}

.toggle-btn input {
  display: none;
}

.toggle-btn.active {
  background: #142b4f;
  color: white;
  border-color: #142b4f;
}

.btn-map-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 30px;
  border: 1px solid #d5cbbe;
  background: white;
  font-size: 12px;
  font-weight: 600;
  color: #53647b;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-map-toggle.active {
  background: #f1ebd8;
  color: #8c6b36;
  border-color: #cfbe9f;
}

.btn-close {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid #e2d7c7;
  background: white;
  font-size: 16px;
  color: #53647b;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-close:hover {
  background: #f1ebd8;
  color: #142b4f;
}

.mixed-note {
  margin: 18px 0 0;
  padding: 12px 18px;
  border-radius: 12px;
  background: #fff8e8;
  border-left: 4px solid #d99b26;
  font-size: 12px;
  line-height: 1.6;
  color: #7d5918;
}

/* Section Title */
.section-title {
  font-size: 17px;
  font-weight: 700;
  color: #142b4f;
  margin: 28px 0 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Metrics Dashboard */
.metrics-dashboard {
  margin-top: 10px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.metric-card {
  background: white;
  border: 1px solid #e7dfd2;
  border-radius: 18px;
  padding: 18px 20px;
  box-shadow: 0 4px 18px rgba(20, 43, 79, 0.04);
}

.metric-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 14px;
}

.metric-name {
  font-size: 14px;
  font-weight: 700;
  color: #142b4f;
}

.metric-sub {
  font-size: 11px;
  color: #7b8ba0;
}

.metric-bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}

.bar-index {
  font-weight: 700;
  font-size: 11px;
  padding: 3px 7px;
  border-radius: 6px;
  min-width: 44px;
  text-align: center;
}

.prop-idx-0 { background: #e6eef9; color: #1e427b; }
.prop-idx-1 { background: #faede6; color: #9c4521; }
.prop-idx-2 { background: #edf7ed; color: #236c2e; }

.bar-track {
  flex: 1;
  height: 10px;
  background: #f0ece3;
  border-radius: 10px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 10px;
  transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.fill-0 { background: #1f4782; }
.fill-1 { background: #c2572b; }
.fill-2 { background: #2f8540; }

.bar-val {
  font-weight: 700;
  min-width: 65px;
  text-align: right;
  color: #142b4f;
}

.bar-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 6px;
  white-space: nowrap;
}

.bar-badge.green {
  background: #e6f7ec;
  color: #1b7a37;
}

.bar-badge.gold {
  background: #fbf2df;
  color: #997327;
}

/* Distance Card */
.distance-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.distance-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 10px 0;
}

.distance-icon {
  font-size: 18px;
  letter-spacing: 4px;
  margin-bottom: 4px;
}

.distance-number {
  font-size: 26px;
  font-weight: 800;
  color: #142b4f;
  letter-spacing: -0.02em;
}

.distance-desc {
  font-size: 11px;
  color: #697a92;
  margin: 4px 0 0;
}

/* Map Section */
.map-section {
  margin-top: 18px;
  background: white;
  border: 1px solid #e7ded0;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(20, 43, 79, 0.05);
}

.map-header {
  padding: 12px 18px;
  background: #fbf9f5;
  border-bottom: 1px solid #ece4d7;
}

.map-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #142b4f;
}

.map-hint {
  font-size: 11px;
  color: #7b8ba0;
  margin-left: auto;
}

.map-viewport-wrapper {
  position: relative;
  height: 270px;
  width: 100%;
}

/* Detailed Table Section */
.table-container {
  margin-top: 24px;
}

.table-scroll {
  overflow-x: auto;
  border: 1px solid #e7dfd2;
  border-radius: 20px;
  background: white;
  box-shadow: 0 4px 22px rgba(20, 43, 79, 0.04);
}

.comparison-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
  min-width: 760px;
}

.corner-header {
  width: 220px;
  background: #faf7f2;
  border-bottom: 2px solid #e5ded2;
  border-right: 1px solid #e5ded2;
  padding: 20px;
  vertical-align: bottom;
  text-align: left;
}

.criteria-header-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.criteria-header-box span {
  font-size: 15px;
  font-weight: 750;
  color: #142b4f;
}

.criteria-header-box small {
  font-size: 11px;
  color: #b13724;
  font-weight: 600;
}

/* Property Header Cards */
.property-col-header {
  padding: 18px;
  background: #faf7f2;
  border-bottom: 2px solid #e5ded2;
  border-right: 1px solid #e5ded2;
  vertical-align: top;
  text-align: left;
}

.property-col-header:last-child {
  border-right: 0;
}

.prop-card-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-badge-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.card-num-pill {
  font-size: 11px;
  font-weight: 750;
  padding: 3px 8px;
  border-radius: 6px;
}

.bg-idx-0 { background: #1f4782; color: white; }
.bg-idx-1 { background: #c2572b; color: white; }
.bg-idx-2 { background: #2f8540; color: white; }

.card-type-pill {
  font-size: 11px;
  font-weight: 600;
  color: #7b623f;
  background: #f1ebd8;
  padding: 3px 8px;
  border-radius: 6px;
  margin-right: auto;
}

.btn-remove-col {
  background: transparent;
  border: 0;
  font-size: 18px;
  color: #8c9cb0;
  cursor: pointer;
  line-height: 1;
}

.btn-remove-col:hover {
  color: #b13724;
}

.card-img-box {
  position: relative;
  height: 150px;
  border-radius: 12px;
  overflow: hidden;
  background: #e8e4dc;
}

.card-img-box :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.card-img-box:hover :deep(img) {
  transform: scale(1.03);
}

.card-tag {
  position: absolute;
  top: 8px;
  left: 8px;
  background: rgba(255, 255, 255, 0.92);
  color: #142b4f;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 20px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.card-info-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-title-link {
  font-size: 14px;
  font-weight: 700;
  color: #142b4f;
  text-decoration: none;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  min-height: 2.8em;
}

.card-title-link:hover {
  color: #b13724;
}

.card-price-row {
  display: flex;
  flex-direction: column;
}

.card-price-compact {
  font-size: 21px;
  font-weight: 800;
  color: #b13724;
  line-height: 1.2;
}

.card-price-full {
  font-size: 11px;
  color: #697a92;
}

.card-advantages {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  min-height: 24px;
}

.advantage-pill {
  font-size: 10px;
  font-weight: 700;
  padding: 3px 7px;
  border-radius: 6px;
  white-space: nowrap;
}

.advantage-pill.best-price { background: #e6f7ec; color: #167a33; }
.advantage-pill.best-unit { background: #e0f2fe; color: #0369a1; }
.advantage-pill.best-area { background: #fef3c7; color: #92400e; }
.advantage-pill.highlight { background: #f3f4f6; color: #4b5563; }

.btn-view-detail {
  display: block;
  text-align: center;
  background: #142b4f;
  color: white;
  text-decoration: none;
  font-size: 12px;
  font-weight: 600;
  padding: 8px 12px;
  border-radius: 20px;
  transition: background 0.2s;
}

.btn-view-detail:hover {
  background: #1f3d6f;
}

/* Group Headers */
.group-header-row th {
  background: #f3eee4;
  padding: 10px 18px;
  border-top: 1px solid #e0d7c7;
  border-bottom: 1px solid #e0d7c7;
  text-align: left;
}

.group-icon {
  margin-right: 8px;
  font-size: 14px;
}

.group-title {
  font-size: 13px;
  font-weight: 750;
  letter-spacing: 0.04em;
  color: #6d542d;
  text-transform: uppercase;
}

/* Data Rows */
.data-row {
  transition: background 0.15s;
}

.data-row:hover {
  background: #faf8f5;
}

.row-label {
  padding: 14px 20px;
  font-size: 13px;
  font-weight: 650;
  color: #4b586e;
  border-bottom: 1px solid #ede8de;
  border-right: 1px solid #ede8de;
  text-align: left;
  vertical-align: middle;
}

.row-cell {
  padding: 14px 18px;
  font-size: 13px;
  color: #142b4f;
  border-bottom: 1px solid #ede8de;
  border-right: 1px solid #ede8de;
  vertical-align: middle;
}

.row-cell:last-child {
  border-right: 0;
}

.cell-price-box {
  display: flex;
  flex-direction: column;
}

.cell-main-price {
  font-size: 16px;
  font-weight: 750;
  color: #b13724;
}

.cell-sub-price {
  font-size: 11px;
  color: #7b8ba0;
}

.cell-text {
  font-weight: 550;
}

.cell-text.text-highlight {
  color: #142b4f;
  font-weight: 700;
}

/* Amenity Badges */
.amenity-pill {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 650;
  padding: 4px 9px;
  border-radius: 8px;
}

.amenity-pill.has {
  background: #eaf7ee;
  color: #167a33;
}

.amenity-pill.missing {
  color: #98a6b8;
  font-weight: 500;
}

/* Legal Badges */
.legal-badge {
  display: block;
  font-weight: 700;
  color: #167a33;
  margin-bottom: 2px;
}

.legal-note {
  font-size: 11px;
  color: #7b8ba0;
}

/* Dialog Footer */
.dialog-footer {
  margin-top: 26px;
  padding-top: 20px;
  border-top: 1px solid #e7ded0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.dialog-disclaimer {
  font-size: 11px;
  color: #7d8ea5;
  line-height: 1.6;
  max-width: 750px;
  margin: 0;
}

.btn-close-bottom {
  background: #e9e4da;
  color: #142b4f;
  border: 0;
  border-radius: 20px;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-close-bottom:hover {
  background: #ded7cb;
}

/* Responsive Rules */
@media (max-width: 768px) {
  .comparison-dialog {
    padding: 0;
  }
  .dialog-inner {
    padding: 20px 16px;
  }
  .dialog-header {
    flex-direction: column;
  }
  .dialog-controls {
    width: 100%;
    justify-content: space-between;
  }
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  .comparison-tray {
    bottom: 10px;
    padding: 10px 14px;
  }
  .tray-items {
    gap: 6px;
  }
  .tray-chip {
    max-width: 130px;
  }
  .tray-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
