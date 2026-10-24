
<script setup>
import {ref,computed} from 'vue'
import { useRouter } from 'vue-router'
import {api} from '../../src/services/api.js'
import {useList,LegacyState,LegacyPager,PrivateImage} from '../../src/services/legacy.js'
import {collectionProperty} from '../../src/services/collection.js'

import {useCollection,typeCode} from '../../src/services/useCollection.js'
const router = useRouter()

// SMARTPROP FAVORITES 2.0
// Data is loaded from the existing backend.

const activeFilter = ref('Tất cả')
const sortType = ref('Mới lưu')
const searchText = ref('')
const removedItem = ref(null)

const filters = ['Tất cả', 'Nhà phố', 'Căn hộ', 'Đất nền']

const state=useCollection('/users/me/saved-properties','/users/me/saved-properties/summary',()=>({keyword:searchText.value.trim(),propertyType:typeCode[activeFilter.value],sort:({'Mới lưu':'newest','Cũ nhất':'oldest','Giá thấp':'priceAsc','Giá cao':'priceDesc'})[sortType.value]}));
const listings=computed(()=>state.items.map(collectionProperty));
const filteredListings=listings;
const propertyTypeCount=computed(()=>state.summary?Object.keys(state.summary.byPropertyType||{}).length:'—');
const priceGroups=computed(()=>state.summary?.priceGroups||[]);
const filterCount=label=>state.summary?(label==='Tất cả'?state.summary.totalVisible:state.summary.byPropertyType?.[typeCode[label]]||0):'—';

function formatPrice(price) {
  return price.toLocaleString('vi-VN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

async function removeFavorite(id){const item=listings.value.find(x=>x.id===id);if(!item||state.busy)return;await state.run(async()=>{await api('/users/me/saved-properties/'+id,{method:'DELETE'});removedItem.value=item;await state.reload()})}
async function undoRemove(){if(!removedItem.value||state.busy)return;await state.run(async()=>{await api('/users/me/saved-properties/'+removedItem.value.id,{method:'PUT'});removedItem.value=null;await state.reload()})}
function openListing(id){router.push('/listing/'+id)}


function resetFilters() {
  activeFilter.value = 'Tất cả'
  searchText.value = ''
  sortType.value = 'Mới lưu'
}
</script>

<template>
  <div class="sp-favorites min-h-screen bg-[#F7F5F0] text-[#142B4F]">

    <!-- HEADER -->
    <header class="border-b border-[#E7E2D8] bg-[#F7F5F0]">
      <div class="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-4 px-5 py-5 md:px-10">
        <div class="flex items-center gap-5">
          <RouterLink to="/home" class="flex items-center gap-3">
            <span class="flex h-10 w-10 items-center justify-center rounded-full bg-[#142B4F] font-bold text-white">
              S
            </span>
            <span class="text-xl font-bold">
              SmartProp<span class="text-[#C6A77A]">.</span>
            </span>
          </RouterLink>

          <RouterLink to="/home" class="hidden text-xs text-[#8290A0] hover:text-[#142B4F] sm:block">
            ← Trang chủ
          </RouterLink>
        </div>

        <div class="flex items-center gap-2">
          <RouterLink
            to="/listings"
            class="hidden rounded-full border border-[#E4DED3] bg-white px-5 py-3 text-xs font-semibold hover:border-[#C6A77A] sm:block"
          >
            Khám phá tin đăng ↗
          </RouterLink>

          <RouterLink
            to="/post"
            class="hidden rounded-full border border-[#E4DED3] bg-white px-5 py-3 text-xs font-semibold hover:border-[#C6A77A] md:block"
          >
            Đăng tin
          </RouterLink>

          <RouterLink
            to="/account"
            class="rounded-full bg-[#142B4F] px-5 py-3 text-xs font-semibold text-white hover:bg-[#25466B]"
          >
            Tài khoản
          </RouterLink>
        </div>
      </div>
    </header>

    <!-- INTRO -->
    <section class="relative overflow-hidden border-b border-[#E7E2D8]">
      <div class="pointer-events-none absolute -right-28 -top-32 h-[420px] w-[420px] rounded-full border border-[#C6A77A]/20"></div>
      <div class="pointer-events-none absolute -right-10 -top-12 h-[280px] w-[280px] rounded-full border border-[#C6A77A]/20"></div>

      <div class="relative mx-auto max-w-[1440px] px-5 py-12 md:px-10 md:py-16">
        <div class="flex flex-wrap items-end justify-between gap-8">
          <div>
            <div class="flex items-center gap-3">
              <span class="h-px w-9 bg-[#B49362]"></span>
              <p class="text-[10px] font-bold uppercase tracking-[0.22em] text-[#B49362]">
                SMARTPROP / SAVED COLLECTION
              </p>
            </div>

            <h1 class="mt-6 text-[39px] font-medium leading-tight tracking-tight sm:text-[56px]">
              Những lựa chọn
              <span class="block italic text-[#B49362]">bạn yêu thích.</span>
            </h1>

            <p class="mt-5 max-w-2xl text-sm leading-7 text-[#7B8798]">
              Lưu giữ những bất động sản đáng quan tâm, so sánh mức giá
              và dễ dàng quay lại khám phá những không gian sống phù hợp.
            </p>

            <span class="mt-5 inline-flex rounded-full border border-[#E2D8C8] bg-[#EEE7DB] px-4 py-2 text-[10px] font-bold uppercase tracking-widest text-[#94774F]">
              Dữ liệu từ hệ thống
            </span>
          </div>

          <RouterLink
            to="/listings"
            class="rounded-full bg-[#142B4F] px-7 py-4 text-xs font-bold text-white transition hover:bg-[#25466B]"
          >
            Khám phá thêm bất động sản ↗
          </RouterLink>
        </div>
      </div>
    </section>

    <!-- STATS -->
    <section class="mx-auto max-w-[1440px] px-5 pt-10 md:px-10">
      <div class="grid grid-cols-2 gap-3 lg:grid-cols-3 lg:gap-5">
        <div class="rounded-[20px] border border-[#E8E3DA] bg-white p-5 sm:p-7">
          <p class="text-[10px] font-bold uppercase tracking-widest text-[#8D99A8]">
            Đã yêu thích
          </p>
          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ state.summary?.totalVisible ?? '—' }}</span>
            <span class="text-xl text-[#C6A77A]">♥</span>
          </div>
          <p class="mt-3 text-[11px] text-[#8D99A8]">Bất động sản đã lưu</p>
        </div>

        <div class="rounded-[20px] bg-[#142B4F] p-5 text-white sm:p-7">
          <p class="text-[10px] font-bold uppercase tracking-widest text-white/60">
            Loại hình quan tâm
          </p>
          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ propertyTypeCount }}</span>
            <span class="text-xl text-[#C6A77A]">⌂</span>
          </div>
          <p class="mt-3 text-[11px] text-white/55">Nhà phố · Căn hộ · Đất nền</p>
        </div>

        <div class="col-span-2 rounded-[20px] border border-[#E8E3DA] bg-white p-5 sm:p-7 lg:col-span-1">
          <p class="text-[10px] font-bold uppercase tracking-widest text-[#8D99A8]">
            Tổng giá trị tham khảo
          </p>
          <div class="mt-4 flex items-end justify-between">
            <span class="text-3xl font-semibold sm:text-4xl">
              <span v-if="!priceGroups.length">—</span><span v-for="g in priceGroups" :key="g.transactionType+g.currency+g.priceUnit" class="block text-sm">{{Number(g.amounts.totalAskingPrice).toLocaleString('vi-VN')}} {{g.currency}} · {{g.transactionType==='SALE'?'Bán':'Thuê'}} / {{g.priceUnit}}</span>
            </span>
            <span class="text-xl text-[#C6A77A]">↗</span>
          </div>
          <p class="mt-3 text-[11px] text-[#8D99A8]">Giá chào toàn bộ tin còn hiển thị, tách theo giao dịch/đơn vị</p>
        </div>
      </div>
    </section>

    <!-- COLLECTION -->
    <main class="mx-auto max-w-[1440px] px-5 pb-20 pt-12 md:px-10">
<LegacyState :state="state" /><p v-if="state.summaryError" role="alert">{{state.summaryError}} <button @click="state.loadSummary">Tải lại thống kê</button></p><p class="mb-4 text-xs text-[#87919F]">{{state.totalElements}} kết quả · kết quả đã lọc toàn bộ danh mục.</p>

      <div class="flex flex-wrap items-end justify-between gap-5">
        <div>
          <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-[#B49362]">
            YOUR FAVORITES / 01
          </p>

          <h2 class="mt-3 text-3xl font-medium tracking-tight sm:text-4xl">
            Bộ sưu tập <span class="italic text-[#B49362]">của bạn.</span>
          </h2>

          <p class="mt-3 text-xs text-[#87919F]">
            {{ state.totalElements }} bất động sản phù hợp với bộ lọc.
          </p>
        </div>

        <div class="flex w-full flex-wrap gap-3 sm:w-auto">
          <div class="flex min-w-0 flex-1 items-center gap-2 rounded-xl border border-[#E4DED3] bg-white px-4 sm:w-[260px]">
            <span class="text-lg text-[#B49362]">⌕</span>

            <input
              v-model="searchText"
              type="search"
              aria-label="Tìm kiếm tin đã lưu"
              placeholder="Tìm tin đăng, khu vực..."
              class="h-12 min-w-0 w-full bg-transparent text-xs outline-none"
            />
          </div>

          <select
            v-model="sortType"
            aria-label="Sắp xếp tin yêu thích"
            class="h-12 rounded-xl border border-[#E4DED3] bg-white px-4 text-xs outline-none"
          >
            <option>Mới lưu</option>
            <option>Cũ nhất</option>
            <option>Giá thấp</option>
            <option>Giá cao</option>
          </select>
        </div>
      </div>

      <!-- FILTERS -->
      <div class="mt-8 flex flex-wrap gap-2">
        <button
          v-for="filter in filters"
          :key="filter"
          type="button"
          @click="activeFilter = filter"
          class="rounded-full border px-4 py-2.5 text-[11px] font-semibold transition sm:px-5"
          :class="
            activeFilter === filter
              ? 'border-[#142B4F] bg-[#142B4F] text-white'
              : 'border-[#E4DED3] bg-white text-[#64748B] hover:border-[#C6A77A]'
          "
        >
          {{ filter }}
          <span class="ml-1 opacity-65">
            {{ filterCount(filter) }}
          </span>
        </button>
      </div>

      <!-- UNDO -->
      <div
        v-if="removedItem"
        class="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-[#DCD4C7] bg-[#EEE7DB] px-5 py-4"
      >
        <p class="text-xs text-[#7B6648]">
          Đã bỏ yêu thích: <strong>{{ removedItem.title }}</strong>
        </p>

        <button
          type="button"
          @click="undoRemove"
          class="text-xs font-bold text-[#142B4F] underline underline-offset-4"
        >
          Hoàn tác
        </button>
      </div>

      <!-- CARDS -->
      <div
        v-if="filteredListings.length"
        class="mt-8 grid min-w-0 grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3"
      >
        <article
          v-for="item in filteredListings"
          :key="item.id"
          class="group min-w-0 overflow-hidden rounded-[22px] border border-[#E8E3DA] bg-white transition duration-300 hover:-translate-y-1 hover:border-[#C6A77A] hover:shadow-[0_18px_50px_rgba(20,43,79,.10)]"
        >
          <!-- IMAGE -->
          <div class="relative h-[260px] overflow-hidden bg-[#E7E2D8]">
            <PrivateImage
              :src="item.image"
              :alt="`${item.title}`"
              loading="lazy"
              class="h-full w-full object-cover transition duration-700 group-hover:scale-105"
             />

            <div class="absolute inset-0 bg-gradient-to-t from-[#142B4F]/50 via-transparent to-transparent"></div>

            <span
              class="absolute left-4 top-4 rounded-full px-3 py-2 text-[10px] font-bold shadow-sm"
              :class="
                item.badgeColor === 'green'
                  ? 'bg-[#E5F4EB] text-[#287B56]'
                  : 'bg-[#FFF1D9] text-[#A36A19]'
              "
            >
              {{ item.badge }}
            </span>

            <button
              type="button"
              @click="removeFavorite(item.id)"
              :aria-label="`Bỏ yêu thích ${item.title}`"
              title="Bỏ yêu thích"
              class="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-full bg-[#142B4F] text-lg text-white transition hover:scale-110 hover:bg-[#BD6A4C]"
            >
              ♥
            </button>

            <span class="absolute bottom-5 left-5 text-[10px] font-bold uppercase tracking-[0.15em] text-white">
              {{ item.type }} / Đà Nẵng
            </span>
          </div>

          <!-- CONTENT -->
          <div class="p-6 sm:p-7">
            <p class="text-[10px] font-bold uppercase tracking-[0.15em] text-[#B49362]">
              {{ item.type }}
            </p>

            <h3 class="mt-3 min-h-[56px] text-xl font-semibold leading-7">
              {{ item.title }}
            </h3>

            <p class="mt-3 text-xs text-[#87919F]">
              ⌖ {{ item.location }}
            </p>

            <div class="mt-6 border-y border-[#EEEAE3] py-4">
              <p class="text-xs text-[#64748B]">
                {{ item.info }}
              </p>
            </div>

            <div class="mt-5 flex items-end justify-between gap-4">
              <div>
                <p class="text-[10px] uppercase tracking-widest text-[#9AA4B1]">
                  Giá tham khảo
                </p>

                <p class="mt-2 text-[27px] font-semibold tracking-tight">
                  {{ item.priceText }}
                  <span class="text-base text-[#B49362]"></span>
                </p>
              </div>

              <button
                type="button"
                @click="openListing(item.id)"
                :aria-label="`Xem chi tiết ${item.title}`"
                class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-[#E4DED3] text-lg transition group-hover:border-[#142B4F] group-hover:bg-[#142B4F] group-hover:text-white"
              >
                ↗
              </button>
            </div>

            <div class="mt-5 flex items-center justify-between border-t border-[#EEEAE3] pt-4">
              <span class="text-[11px] text-[#9AA4B1]">
                ♡ {{ item.saved }}
              </span>

              <button
                type="button"
                @click="openListing(item.id)"
                class="text-[11px] font-bold text-[#142B4F] hover:text-[#B49362]"
              >
                Xem chi tiết →
              </button>
            </div>
          </div>
        </article>
      </div>

      <!-- EMPTY -->
      <div
        v-else
        class="mt-8 rounded-[24px] border border-[#E8E3DA] bg-white px-6 py-20 text-center"
      >
        <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[#F7F5F0] text-3xl text-[#B49362]">
          ♡
        </div>

        <h3 class="mt-6 text-xl font-semibold">
          Chưa có bất động sản phù hợp
        </h3>

        <p class="mt-3 text-sm text-[#87919F]">
          Hãy thay đổi bộ lọc hoặc khám phá thêm tin đăng.
        </p>

        <button
          type="button"
          @click="resetFilters"
          class="mt-6 rounded-full bg-[#142B4F] px-6 py-3 text-xs font-semibold text-white"
        >
          Xem tất cả tin yêu thích
        </button>
      </div>

      <!-- CTA -->
      <section class="relative mt-14 overflow-hidden rounded-[25px] bg-[#142B4F] px-7 py-10 text-white sm:px-10">
        <div class="pointer-events-none absolute -right-12 -top-24 h-72 w-72 rounded-full border border-[#C6A77A]/20"></div>

        <div class="relative flex flex-wrap items-center justify-between gap-7">
          <div>
            <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-[#7BD4E5]">
              SMARTPROP / DISCOVER MORE
            </p>

            <h2 class="mt-4 text-3xl font-medium">
              Lựa chọn tiếp theo
              <span class="italic text-[#C6A77A]"> đang chờ bạn.</span>
            </h2>

            <p class="mt-4 max-w-xl text-sm leading-7 text-white/60">
              Tiếp tục khám phá các bất động sản, tìm kiếm theo nhu cầu
              và mở rộng bộ sưu tập yêu thích của bạn.
            </p>
          </div>

          <RouterLink
            to="/listings"
            class="rounded-full bg-[#C6A77A] px-7 py-4 text-xs font-bold text-[#142B4F] transition hover:bg-[#E1C394]"
          >
            Khám phá bất động sản ↗
          </RouterLink>
        </div>
      </section>

      <p class="mt-7 text-center text-[11px] leading-6 text-[#87919F]">
        Tin đăng và trạng thái được tải từ hệ thống.
        Danh sách yêu thích được lưu theo tài khoản của bạn.
      </p>
    <LegacyPager :state="state" /></main>

    <!-- FOOTER -->
    <footer class="border-t border-[#E7E2D8]">
      <div class="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-4 px-5 py-7 md:px-10">
        <RouterLink to="/home" class="text-lg font-bold">
          SmartProp<span class="text-[#C6A77A]">.</span>
        </RouterLink>

        <p class="text-[11px] text-[#87919F]">
          © 2026 SmartProp · Favorites 2.0
        </p>

        <RouterLink to="/home" class="text-xs text-[#64748B]">
          Về trang chủ ↗
        </RouterLink>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.sp-favorites {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
  font-family: Arial, "Segoe UI", sans-serif;
  font-synthesis: none;
}

.sp-favorites h1,
.sp-favorites h2,
.sp-favorites h3 {
  font-family: Arial, "Segoe UI", sans-serif;
  font-variant-ligatures: none;
  word-spacing: normal;
}

.sp-favorites button,
.sp-favorites input,
.sp-favorites select {
  font-family: inherit;
}

.sp-favorites img {
  display: block;
}

@media (prefers-reduced-motion: reduce) {
  .sp-favorites *,
  .sp-favorites *::before,
  .sp-favorites *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}
</style>
