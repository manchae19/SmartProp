<script setup>
import { computed } from 'vue'
import PrivateImage from '../../components/PrivateImage.vue'
import { price, compactPrice, displayDecimal, types, states } from './property.js'

const props = defineProps({
  property: { type: Object, required: true },
  own: Boolean,
  list: Boolean
})

const detail = computed(() => ({
  path: '/listing/' + props.property.id,
  query: props.own ? { own: '1' } : {}
}))

const cover = computed(() => (props.property.images?.find(image => image.cover) || props.property.images?.[0])?.url)
const imageCount = computed(() => props.property.images?.length || 1)

const fullAddress = computed(() => {
  const parts = [props.property.address, props.property.ward, props.property.district].filter(Boolean)
  if (parts.length) return parts.join(', ')
  return [props.property.district, props.property.city].filter(Boolean).join(', ') || 'Đà Nẵng'
})

const area = computed(() => displayDecimal(props.property.areaSqmExact ?? props.property.areaSqm))

const unitPriceText = computed(() => {
  const pr = Number(props.property.priceExact ?? props.property.price ?? 0)
  const ar = Number(props.property.areaSqmExact ?? props.property.areaSqm ?? 0)
  if (pr > 0 && ar > 0 && props.property.transactionType === 'SALE' && props.property.priceUnit === 'TOTAL') {
    const perSqm = Math.round(pr / ar)
    if (perSqm >= 1000000) {
      return `~ ${(perSqm / 1000000).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} tr/m²`
    }
    return `~ ${perSqm.toLocaleString('vi-VN')} đ/m²`
  }
  return null
})
</script>

<template>
  <article class="property-card" :class="{ 'property-card-list': list }">
    <RouterLink :to="detail" class="property-main" :aria-label="'Xem chi tiết ' + property.title">
      <!-- Image Container -->
      <div class="property-image">
        <PrivateImage :src="cover" :alt="property.title" />

        <!-- Top Badges -->
        <div class="image-top-tags">
          <span class="badge-transaction" :class="property.transactionType === 'RENT' ? 'rent' : 'sale'">
            {{ own ? states[property.status] : property.transactionType === 'SALE' ? 'Bán' : 'Cho thuê' }}
          </span>
          <span class="badge-type">{{ types[property.propertyType] || property.propertyType }}</span>
        </div>

        <!-- Bottom Tags (Photo Count) -->
        <div class="image-bottom-tags">
          <span v-if="imageCount > 1" class="badge-photo-count">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
            {{ imageCount }} ảnh
          </span>
        </div>
      </div>

      <!-- Card Body -->
      <div class="property-body">
        <h3 class="property-title" :title="property.title">{{ property.title }}</h3>

        <!-- Price & Area Metrics -->
        <div class="property-metrics">
          <div class="price-container">
            <span class="main-price" :title="price(property)">{{ compactPrice(property) }}</span>
            <span v-if="unitPriceText" class="unit-price">{{ unitPriceText }}</span>
          </div>
          <div class="area-container" :aria-label="'Diện tích ' + area + ' m²'">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M3 3l6 6m12-6-6 6M3 21l6-6m12 6-6-6" /></svg>
            <span>{{ area }} m²</span>
          </div>
        </div>

        <!-- Location -->
        <p class="property-location" :title="fullAddress">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></svg>
          <span>{{ fullAddress }}</span>
        </p>

        <!-- Specifications -->
        <div class="property-specs">
          <span v-if="property.direction" class="spec-pill">
            🧭 Hướng {{ property.direction }}
          </span>
          <span v-if="property.bedrooms > 0" class="spec-pill">
            🛏️ <strong>{{ property.bedrooms }}</strong> PN
          </span>
          <span v-if="property.bathrooms > 0" class="spec-pill">
            🚿 <strong>{{ property.bathrooms }}</strong> PT
          </span>
          <span v-if="property.propertyType === 'LAND'" class="spec-pill land-tag">
            📑 Sổ đỏ sẵn sàng
          </span>
        </div>
      </div>
    </RouterLink>

    <!-- Unified Action Toolbar -->
    <div class="property-actions">
      <RouterLink :to="detail" class="detail-link">Xem chi tiết ↗</RouterLink>
      <slot />
    </div>
  </article>
</template>

<style scoped>
.property-card {
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: white;
  border: 1px solid #ebe5dc;
  border-radius: 18px;
  color: #142b4f;
  overflow: hidden;
  box-shadow: 0 4px 18px rgba(20, 43, 79, 0.04);
  transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.22s, border-color 0.22s;
}

.property-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 36px rgba(20, 43, 79, 0.1);
  border-color: #d8cbba;
}

.property-main {
  display: flex;
  flex-direction: column;
  color: inherit;
  text-decoration: none;
  flex: 1;
  min-width: 0;
}

/* Image Container */
.property-image {
  height: 215px;
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
  background: #ebe7de;
}

.property-image :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s ease;
}

.property-card:hover .property-image :deep(img) {
  transform: scale(1.04);
}

.image-top-tags {
  position: absolute;
  top: 12px;
  left: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  pointer-events: none;
}

.badge-transaction {
  font-size: 11.5px;
  font-weight: 750;
  padding: 4px 10px;
  border-radius: 20px;
  color: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.badge-transaction.sale {
  background: #b13724;
}

.badge-transaction.rent {
  background: #1c7353;
}

.badge-type {
  font-size: 11px;
  font-weight: 650;
  padding: 4px 9px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.94);
  color: #634f31;
  backdrop-filter: blur(4px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.image-bottom-tags {
  position: absolute;
  bottom: 10px;
  right: 10px;
  pointer-events: none;
}

.badge-photo-count {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(15, 23, 42, 0.72);
  color: white;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 12px;
  backdrop-filter: blur(4px);
}

/* Card Body */
.property-body {
  padding: 16px 18px 12px;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.property-title {
  font-size: 15.5px;
  font-weight: 700;
  line-height: 1.45;
  color: #142b4f;
  margin: 0 0 10px;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  min-height: 2.9em;
  transition: color 0.15s;
}

.property-card:hover .property-title {
  color: #9c4521;
}

/* Metrics Row */
.property-metrics {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f1ece4;
}

.price-container {
  display: flex;
  align-items: baseline;
  gap: 7px;
  flex-wrap: wrap;
}

.main-price {
  font-size: 21px;
  font-weight: 800;
  color: #b13724;
  letter-spacing: -0.02em;
}

.unit-price {
  font-size: 12px;
  font-weight: 600;
  color: #62748c;
}

.area-container {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12.5px;
  font-weight: 700;
  color: #55442f;
  background: #f7f3eb;
  padding: 4px 8px;
  border-radius: 8px;
  border: 1px solid #e9e1d3;
  white-space: nowrap;
}

/* Location */
.property-location {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: #64748b;
  margin: 0 0 12px;
  line-height: 1.4;
}

.property-location svg {
  color: #b13724;
  flex-shrink: 0;
}

.property-location span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Specifications */
.property-specs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: auto;
}

.spec-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  font-weight: 550;
  color: #475569;
  background: #f1f4f8;
  padding: 4px 8px;
  border-radius: 6px;
}

.spec-pill.land-tag {
  background: #eef7f0;
  color: #1a7536;
  font-weight: 600;
}

/* Action Toolbar */
.property-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px 14px;
  border-top: 1px solid #f1ece4;
  background: #faf8f5;
}

.detail-link {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 24px;
  background: linear-gradient(135deg, #142b4f 0%, #1e3d6f 100%);
  color: white;
  text-decoration: none;
  font-size: 12.5px;
  font-weight: 700;
  padding: 9px 14px;
  white-space: nowrap;
  box-shadow: 0 2px 8px rgba(20, 43, 79, 0.2);
  transition: all 0.2s;
}

.detail-link:hover {
  background: #1f4277;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(20, 43, 79, 0.28);
}

:deep(.on-map),
:deep(.compare-button) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 650;
  border-radius: 24px;
  border: 1px solid #dbd3c5;
  background: white;
  color: #516277;
  text-decoration: none;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

:deep(.on-map:hover),
:deep(.compare-button:hover) {
  background: #f1ebe0;
  color: #142b4f;
  border-color: #c5b6a0;
}

:deep(.compare-button[aria-pressed=true]) {
  background: #e6f7ec;
  color: #167a33;
  border-color: #9fe0b2;
  font-weight: 750;
}

/* List Mode Responsive */
@media (min-width: 768px) {
  .property-card-list {
    flex-direction: row;
    align-items: stretch;
    height: 185px;
    max-height: 195px;
    border-radius: 18px;
    overflow: hidden;
  }

  .property-card-list .property-main {
    flex-direction: row;
    flex: 1;
    min-width: 0;
    height: 100%;
  }

  .property-card-list .property-image {
    width: 260px;
    min-width: 260px;
    max-width: 260px;
    height: 100%;
    min-height: 100%;
  }

  .property-card-list .property-body {
    padding: 14px 18px 12px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .property-card-list .property-title {
    font-size: 15px;
    margin: 0 0 6px;
    min-height: auto;
  }

  .property-card-list .property-metrics {
    margin-bottom: 6px;
    padding-bottom: 6px;
  }

  .property-card-list .main-price {
    font-size: 19px;
  }

  .property-card-list .property-location {
    margin-bottom: 6px;
  }

  .property-card-list .property-actions {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: stretch;
    gap: 7px;
    padding: 14px 16px;
    border-top: 0;
    border-left: 1px solid #ede8de;
    min-width: 138px;
    flex-shrink: 0;
    background: #faf8f5;
  }

  .property-card-list .detail-link {
    width: 100%;
    padding: 8px 10px;
    font-size: 12px;
  }

  .property-card-list :deep(.on-map),
  .property-card-list :deep(.compare-button) {
    width: 100%;
    padding: 6px 10px;
    font-size: 11.5px;
  }
}

@media (max-width: 600px) {
  .property-image {
    height: 195px;
  }
  .property-title {
    font-size: 15px;
  }
  .main-price {
    font-size: 20px;
  }
}
</style>
