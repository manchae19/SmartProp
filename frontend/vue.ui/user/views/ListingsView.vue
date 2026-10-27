<script setup>
import { ref, computed } from 'vue'
import ListingFilters from '../../src/components/ListingFilters.vue'
import ListingCard from '../../src/components/business/ListingCard.vue'
import { useListingFilters } from '../../src/services/useListingFilters.js'
import { usePublicListings } from '../../src/services/usePublicListings.js'
import { useComparison } from '../../src/services/useComparison.js'
import { sortOptions } from '../../src/services/listingFilters.js'
import { price } from '../../src/services/property.js'
import { LegacyState, LegacyPager } from '../../src/services/legacy.js'
const search = useListingFilters(), compare = useComparison(), viewMode = ref('grid')
const state = usePublicListings(() => search.filters.value)
const averagePrice = computed(() => {
  const rows = state.items
  if (!rows.length || new Set(rows.map(p => `${p.transactionType}:${p.priceUnit}`)).size !== 1) return '—'
  const values = rows.map(p => String(p.priceExact ?? p.price))
  if (values.some(value => !/^\d+(?:\.\d{1,2})?$/.test(value))) return '—'
  const total = values.reduce((sum, value) => { const [whole, fraction = ''] = value.split('.'); return sum + BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0')) }, 0n), cents = total / BigInt(rows.length)
  return price({ priceExact: String(cents / 100n) + '.' + String(cents % 100n).padStart(2, '0'), priceUnit: rows[0].priceUnit })
})
</script>
<template>
  <div class="collection-v3">
    <div class="page-width"><div class="collection-intro"><p class="eyebrow">SMARTPROP / PROPERTY COLLECTION</p><h1>Không gian sống <span>dành riêng cho bạn.</span></h1><p>Tìm kiếm tin công khai, so sánh lựa chọn và khám phá vị trí trên bản đồ.</p></div>
      <ListingFilters :model-value="search.filters.value" @update:model-value="search.set" />
      <div class="collection-stats"><p><strong>{{ state.totalElements }}</strong> tin phù hợp<span v-if="search.filters.value.district"> · {{ search.filters.value.district }}</span></p><p>Giá chào trung bình của trang: <strong>{{ averagePrice }}</strong><small>Chỉ tính khi cùng hình thức và đơn vị giá; không phải giá thị trường.</small></p></div>
      <div class="collection-toolbar"><div class="view-buttons" aria-label="Cách hiển thị"><button type="button" :aria-pressed="viewMode === 'grid'" @click="viewMode = 'grid'">▦ Lưới</button><button type="button" :aria-pressed="viewMode === 'list'" @click="viewMode = 'list'">☷ Danh sách</button></div><label>Sắp xếp<select :value="search.filters.value.sort" @change="search.patch({ sort: $event.target.value })"><option v-for="(label, key) in sortOptions" :key="key" :value="key">{{ label }}</option></select></label><button type="button" class="clear-filter" @click="search.reset">Xóa bộ lọc</button></div>
      <LegacyState :state="state" /><div v-if="state.items.length" class="collection-grid" :class="{ 'list-mode': viewMode === 'list' }"><ListingCard v-for="property in state.items" :key="property.id" :property="property" :list="viewMode === 'list'"><RouterLink :to="search.link('/map', { propertyId: property.id })" class="on-map">⌖ Bản đồ</RouterLink><button type="button" class="compare-button" :aria-pressed="compare.has(property.id)" @click="compare.toggle(property)">{{ compare.has(property.id) ? '✓ Đã chọn' : '+ So sánh' }}</button></ListingCard></div>
      <div v-if="!state.busy && !state.error && !state.items.length" class="empty"><h2>Chưa tìm thấy bất động sản</h2><p>Hãy thử thay đổi khu vực hoặc điều kiện tìm kiếm.</p><button type="button" @click="search.reset">Xóa bộ lọc</button></div><p v-if="compare.notice.value" role="status" class="notice">{{ compare.notice.value }}</p><LegacyPager :state="state" />
    </div>
  </div>
</template>
<style scoped>
.collection-v3{min-height:100vh;background:#f7f5f0;color:#142b4f}.page-width{width:min(1280px,calc(100% - 80px));margin:auto}.collection-header{padding-block:24px;display:flex;justify-content:space-between;align-items:center;gap:20px;border-bottom:1px solid #ddd6c8}.brand{display:flex;align-items:center;gap:12px;font-size:20px;font-weight:700}.header-actions{display:flex;align-items:center;gap:20px;font-size:12px}.collection-intro{padding:55px 0 35px;max-width:750px}.eyebrow{font-size:10px;color:#967447;letter-spacing:.2em}.collection-intro h1{font-size:clamp(32px,4vw,52px);font-weight:550;line-height:1.2;letter-spacing:-.04em;margin:17px 0}.collection-intro h1 span{color:#a78655}.collection-intro>p:last-child{font-size:13px;line-height:1.8;color:#637083}.collection-stats{display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap;padding-block:28px;font-size:13px;color:#637083}.collection-stats>p:first-child strong{font-size:23px;color:#142b4f}.collection-stats strong{color:#142b4f}.collection-stats small{display:block;font-size:10px;line-height:1.8;margin-top:6px}.collection-toolbar{display:flex;align-items:center;flex-wrap:wrap;gap:15px;margin:0 0 25px;font-size:12px}.view-buttons{display:flex;gap:6px;margin-right:auto}.view-buttons button{padding:10px 16px;border:1px solid #ddd6c8;border-radius:25px;background:white}.view-buttons button[aria-pressed=true]{background:#142b4f;color:white;border-color:#142b4f}.collection-toolbar label{display:flex;align-items:center;gap:8px}.collection-toolbar select{padding:10px;border:1px solid #ddd6c8;border-radius:10px;background:white}.clear-filter{color:#967447;text-decoration:underline}.collection-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}.collection-grid.list-mode{grid-template-columns:1fr}.compare-button,.on-map{padding:8px 0;font-size:11px;color:#967447}.on-map{color:#637083}.compare-button[aria-pressed=true]{color:#23765b;font-weight:700}.empty{padding:70px 20px;background:white;border:1px solid #e7e1d7;border-radius:24px;text-align:center}.empty h2{font-size:23px;font-weight:650}.empty p{font-size:13px;color:#637083;margin:14px 0 25px}.empty button{padding:12px 22px;background:#142b4f;color:white;border-radius:25px;font-size:12px}button{cursor:pointer}.notice{font-size:12px;color:#a23e23;padding:15px}footer{display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap;font-size:12px;padding-block:40px 170px;color:#637083}:focus-visible{outline:3px solid #b3915f;outline-offset:3px}@media(max-width:1000px){.collection-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.page-width{width:calc(100% - 48px)}}@media(max-width:600px){.page-width{width:calc(100% - 32px)}.collection-grid{grid-template-columns:1fr}.collection-intro{padding-top:35px}.collection-intro h1{font-size:36px}.collection-toolbar label{margin-left:auto}.clear-filter{width:100%;text-align:right}.header-actions{gap:10px}.header-actions>a{font-size:11px}}
</style>
