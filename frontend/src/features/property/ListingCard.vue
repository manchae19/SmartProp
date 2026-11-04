<script setup>
import { computed } from 'vue'
import PrivateImage from '../../components/PrivateImage.vue'
import { price, compactPrice, displayDecimal, types, states } from './property.js'

const props = defineProps({ property: { type: Object, required: true }, own: Boolean, list: Boolean })
const detail = computed(() => ({ path: '/listing/' + props.property.id, query: props.own ? { own: '1' } : {} }))
const cover = computed(() => (props.property.images?.find(image => image.cover) || props.property.images?.[0])?.url)
const address = computed(() => [props.property.district, props.property.city].filter(Boolean).join(', ') || props.property.address || 'Chưa có địa chỉ')
const area = computed(() => displayDecimal(props.property.areaSqmExact ?? props.property.areaSqm))
</script>

<template>
  <article class="property-card" :class="{ 'property-card-list': list }">
    <RouterLink :to="detail" class="property-main" :aria-label="'Xem chi tiết ' + property.title">
      <div class="property-image">
        <PrivateImage :src="cover" :alt="property.title" />
        <span class="property-badge">{{ own ? states[property.status] : property.transactionType === 'SALE' ? 'Bán' : 'Cho thuê' }}</span>
      </div>
      <div class="property-body">
        <p class="property-type">{{ types[property.propertyType] }}</p>
        <h3 :title="property.title">{{ property.title }}</h3>
        <div class="property-highlights">
          <p class="property-price" :title="price(property)" :aria-label="'Giá ' + price(property)">{{ compactPrice(property) }}</p>
          <span class="property-area" :aria-label="'Diện tích ' + area + ' mét vuông'">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M3 3l6 6m12-6-6 6M3 21l6-6m12 6-6-6" /></svg>
            {{ area }} m²
          </span>
        </div>
        <p class="property-location" :title="address">
          <svg width="15" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></svg>
          <span>{{ address }}</span>
        </p>
        <div v-if="property.propertyType !== 'LAND' && (property.bedrooms > 0 || property.bathrooms > 0)" class="property-specs">
          <span v-if="property.bedrooms > 0">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 18v3m18-3v3M3 10V5h18v5M2 18v-6a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v6H2Zm4-8V7h5v3m2 0V7h5v3" /></svg>
            <strong>{{ property.bedrooms }}</strong> phòng ngủ
          </span>
          <span v-if="property.bathrooms > 0">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12h18v3a5 5 0 0 1-5 5H8a5 5 0 0 1-5-5v-3ZM6 12V5a3 3 0 0 1 6 0M6 20v2m12-2v2M10 5h4" /></svg>
            <strong>{{ property.bathrooms }}</strong> phòng tắm
          </span>
        </div>
      </div>
    </RouterLink>
    <details class="property-full-price"><summary>Giá đầy đủ</summary><p>{{ price(property) }}</p></details>
    <div class="property-actions"><RouterLink :to="detail" class="detail-link">Xem chi tiết ↗</RouterLink><slot /></div>
  </article>
</template>

<style scoped>
.property-full-price summary{min-height:38px;display:flex;align-items:center;gap:6px}.property-full-price summary:before{content:'▸'}.property-full-price[open] summary:before{content:'▾'}
.property-full-price{margin:12px 22px 0;font-size:13px;color:#536178}.property-full-price summary{cursor:pointer;padding:5px 0}.property-full-price p{font-size:13px;color:#142b4f;font-weight:650;line-height:1.8;margin-top:5px;overflow-wrap:anywhere}
.property-card{min-width:0;overflow:hidden;display:flex;flex-direction:column;background:white;border:1px solid #e7e1d7;border-radius:24px;color:#142b4f;transition:transform .2s,box-shadow .2s}.property-card:hover{transform:translateY(-3px);box-shadow:0 15px 35px #142b4f12}.property-main{display:flex;flex-direction:column;color:inherit;text-decoration:none;flex:1;min-width:0}.property-image{height:245px;flex-shrink:0;position:relative;overflow:hidden;background:#e5e4dd}.property-image :deep(img){width:100%;height:100%;object-fit:cover;transition:transform .3s}.property-card:hover .property-image :deep(img){transform:scale(1.025)}.property-badge{position:absolute;top:16px;left:16px;background:#fffffff0;padding:7px 13px;border-radius:30px;font-size:13px;font-weight:600}.property-body{padding:22px 22px 0;min-width:0;flex:1}.property-type{font-size:13px;font-weight:600;letter-spacing:.08em;color:#78572f}.property-body h3{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;min-height:3em;font-size:18px;line-height:1.5;font-weight:650;margin:10px 0 14px;overflow-wrap:anywhere}.property-highlights{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:9px 12px;margin:0 0 14px}.property-price{color:#b13724;font-size:25px;font-weight:750;letter-spacing:-.025em;line-height:1.3;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}.property-area{display:inline-flex;align-items:center;gap:6px;flex-shrink:0;border:1px solid #e9e2d6;border-radius:9px;padding:7px 9px;background:#f7f4ed;color:#4f402d;font-size:13px;font-weight:650;white-space:nowrap}.property-location{display:flex;align-items:center;gap:6px;font-size:12px;line-height:1.6;color:#6b7889;margin:0}.property-location svg{flex-shrink:0}.property-location span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.property-specs{display:flex;flex-wrap:wrap;gap:9px;margin-top:16px;padding-top:14px;border-top:1px solid #edeae4}.property-specs>span{display:inline-flex;align-items:center;gap:5px;border-radius:8px;background:#f3f5f8;padding:7px 9px;font-size:13px;line-height:1.4;color:#52647e}.property-specs svg{color:#7b8ba0;flex-shrink:0}.property-specs strong{font-size:12px;color:#142b4f;font-weight:700}.property-actions{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;padding:20px 22px}.detail-link{border-radius:30px;background:#142b4f;color:white;text-decoration:none;font-size:12px;font-weight:600;padding:11px 18px}.property-card :focus-visible{outline:3px solid #b3915f;outline-offset:-3px}@media(min-width:768px){.property-card-list .property-main{display:grid;grid-template-columns:38% 1fr}.property-card-list .property-image{height:100%;min-height:260px}.property-card-list .property-actions{justify-content:flex-end}}@media(max-width:600px){.property-image{height:220px}.property-price{font-size:24px}.property-body{padding:20px 18px 0}.property-actions{padding:18px}.property-body h3{font-size:18px}}@media(prefers-reduced-motion:reduce){.property-card,.property-image :deep(img){transition:none}.property-card:hover,.property-card:hover .property-image :deep(img){transform:none}}
</style>
