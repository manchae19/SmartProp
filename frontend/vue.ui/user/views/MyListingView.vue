
<script setup>
import {computed,ref,watch} from 'vue'
import PropertyModerationFeedback from '../../src/components/PropertyModerationFeedback.vue'
import { useRouter } from 'vue-router'
import {api,session} from '../../src/services/api.js'
import {useList,LegacyState,LegacyPager,PrivateImage} from '../../src/services/legacy.js'
import {collectionProperty} from '../../src/services/collection.js'

import {useCollection,ownStatus} from '../../src/services/useCollection.js'
const router = useRouter()

// SMARTPROP MY LISTINGS 2.0
// Data is loaded from the existing backend.

const activeFilter = ref('all')
const searchText = ref('')
const selectedListing = ref(null)
const showEditNotice = ref(false)

const state=useCollection('/users/me/properties','/users/me/properties/summary',()=>({keyword:searchText.value.trim(),status:ownStatus[activeFilter.value]}))
const listings=computed(()=>state.items.map(collectionProperty))

const count=id=>state.summary?.byStatus?.[ownStatus[id]]??'—';
const filters=computed(()=>[{id:'all',label:'Tất cả',count:state.summary?.totalListings??'—'},...Object.entries({draft:'Bản nháp',showing:'Đang hiển thị',pending:'Chờ duyệt',rejected:'Bị từ chối',hidden:'Đã ẩn',closed:'Đã đóng',expired:'Hết hạn'}).map(([id,label])=>({id,label,count:count(id)}))]);
const filteredListings=listings;
const totalViews=computed(()=>state.summary?.viewRecordingEnabled?state.summary.recordedViews:'—');
const totalSaves=computed(()=>state.summary?.savedRecords??'—');

function statusClass(status) {
  if (status === 'showing') {
    return 'bg-[#E5F4EB] text-[#287B56]'
  }
  if (status === 'pending') {
    return 'bg-[#FFF1D9] text-[#A36A19]'
  }
  if (status === 'rejected') {
    return 'bg-[#FCE8E3] text-[#BD5D48]'
  }
  return 'bg-[#EDF0F3] text-[#64748B]'
}

function openListing(item) {
  selectedListing.value = item
}

function closeListing() {
  selectedListing.value = null
}

function goToDetail(item){router.push({path:'/listing/'+item.id,query:{own:'1'}})}
function editListing(item){router.push({path:'/post',query:{edit:item.id}})}


function closeEditNotice() {
  showEditNotice.value = false
  selectedListing.value = null
}

function goHome() {
  router.push('/home')
}

function goMap() {
  router.push('/map')
}

function goPost(){if(!canPost.value){state.notice=publishNotice;return}router.push('/post')}

function goAccount() {
  router.push('/account')
}

const canPost=computed(()=>['BROKER','ADMIN'].includes(session.user?.role));
const publishNotice='Bạn đang dùng tài khoản Người mua / người thuê (BUYER). Để đăng tin, hãy đăng nhập bằng tài khoản Chủ nhà / môi giới (BROKER) hoặc ADMIN.';
watch(()=>session.user?.role,role=>{if(role==='BUYER')state.notice=publishNotice;else if(state.notice===publishNotice)state.notice=''}, {immediate:true});

async function act(p,action){await state.run(async()=>{await api('/properties/'+p.id+(action==='delete'?'?expectedVersion='+p.raw.contentVersion:'/'+action),{method:action==='delete'?'DELETE':'POST',...(action==='delete'?{}:{body:{expectedVersion:p.raw.contentVersion}})});await state.reload()})}
</script>

<template>
  <div class="sp-my-listings min-h-screen bg-[#F7F5F0] text-[#142B4F]">

    <!-- HEADER -->


    <!-- PAGE INTRO -->
    <section class="relative overflow-hidden border-b border-[#E7E2D8]">
      <div class="pointer-events-none absolute -right-28 -top-32 h-[420px] w-[420px] rounded-full border border-[#C6A77A]/20"></div>
      <div class="pointer-events-none absolute -right-10 -top-12 h-[280px] w-[280px] rounded-full border border-[#C6A77A]/20"></div>

      <div class="relative mx-auto max-w-[1440px] px-5 py-12 md:px-10 md:py-16">
        <div class="flex flex-wrap items-end justify-between gap-8">
          <div>
            <div class="flex items-center gap-3">
              <span class="h-px w-9 bg-[#B49362]"></span>
              <p class="text-xs font-bold uppercase tracking-[0.22em] text-[#B49362]">
                SMARTPROP / PROPERTY MANAGEMENT
              </p>
            </div>

            <h1 class="mt-6 text-[39px] font-medium leading-tight tracking-tight sm:text-[56px]">
              Quản lý
              <span class="block italic text-[#B49362]">bất động sản của bạn.</span>
            </h1>

            <p class="mt-5 max-w-xl text-sm leading-7 text-[#7B8798]">
              Theo dõi trạng thái tin đăng, lượt quan tâm và quản lý danh mục
              bất động sản của bạn trong một không gian trực quan.
            </p>

            <span class="mt-5 inline-flex rounded-full border border-[#E2D8C8] bg-[#EEE7DB] px-4 py-2 text-xs font-bold uppercase tracking-widest text-[#94774F]">
              Dữ liệu từ hệ thống
            </span>
          </div>

          <button
            @click="goPost"
            class="rounded-full bg-[#142B4F] px-7 py-4 text-xs font-bold text-white shadow-lg transition hover:-translate-y-0.5 hover:bg-[#25466B]"
          >
            + Đăng bất động sản mới ↗
          </button>
        </div>
      </div>
    </section>

    <!-- STATS -->
    <section class="mx-auto max-w-[1440px] px-5 pt-10 md:px-10">
      <div class="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-5">
        <div class="rounded-[20px] border border-[#E8E3DA] bg-white p-5 sm:p-7">
          <p class="text-xs font-bold uppercase tracking-widest text-[#8D99A8]">
            Tổng tin đăng
          </p>
          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ state.summary?.totalListings ?? '—' }}</span>
            <span class="text-xl text-[#C6A77A]">⌂</span>
          </div>
          <p class="mt-3 text-xs text-[#8D99A8]">Danh mục của bạn</p>
        </div>

        <div class="rounded-[20px] bg-[#142B4F] p-5 text-white sm:p-7">
          <p class="text-xs font-bold uppercase tracking-widest text-white/60">
            Đang hiển thị
          </p>
          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">
              {{ count('showing') }}
            </span>
            <span class="h-3 w-3 rounded-full bg-[#7BD4B0]"></span>
          </div>
          <p class="mt-3 text-xs text-white/55">Tin đang hoạt động</p>
        </div>

        <div class="rounded-[20px] border border-[#E8E3DA] bg-white p-5 sm:p-7">
          <p class="text-xs font-bold uppercase tracking-widest text-[#8D99A8]">
            Tổng lượt xem
          </p>
          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ totalViews }}</span>
            <span class="text-xl text-[#C6A77A]">↗</span>
          </div>
          <p class="mt-3 text-xs text-[#8D99A8]">Chưa có số liệu tương tác</p>
        </div>

        <div class="rounded-[20px] border border-[#E8E3DA] bg-white p-5 sm:p-7">
          <p class="text-xs font-bold uppercase tracking-widest text-[#8D99A8]">
            Lượt lưu tin
          </p>
          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ totalSaves }}</span>
            <span class="text-xl text-[#C6A77A]">♡</span>
          </div>
          <p class="mt-3 text-xs text-[#8D99A8]">Người dùng quan tâm</p>
        </div>
      </div>
    </section>

    <!-- MANAGEMENT -->
    <div class="mx-auto max-w-[1440px] px-5 pb-20 pt-12 md:px-10">
<LegacyState :state="state" /><p v-if="state.summaryError" role="alert">{{state.summaryError}} <button @click="state.loadSummary">Tải lại thống kê</button></p><p class="mb-4 text-xs text-[#87919F]">{{state.totalElements}} kết quả · kết quả đã lọc trên toàn bộ dữ liệu. Số đếm trạng thái là tổng danh mục.</p>

      <div class="flex flex-wrap items-end justify-between gap-5">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-[#B49362]">
            YOUR COLLECTION / 01
          </p>
          <h2 class="mt-3 text-3xl font-medium tracking-tight sm:text-4xl">
            Danh sách <span class="italic text-[#B49362]">tin đăng.</span>
          </h2>
          <p class="mt-3 text-xs text-[#87919F]">
            Quản lý và theo dõi các bất động sản đã đăng.
          </p>
        </div>

        <div class="flex w-full items-center gap-3 rounded-xl border border-[#E4DED3] bg-white px-4 sm:w-[300px]">
          <span class="text-[#B49362]">⌕</span>
          <input
            v-model="searchText"
            type="search"
            placeholder="Tìm tin đăng hoặc khu vực..."
            aria-label="Tìm tin đăng"
            class="h-12 min-w-0 w-full bg-transparent text-xs outline-none"
          />
        </div>
      </div>

      <!-- FILTERS -->
      <div class="mt-8 flex flex-wrap gap-2">
        <button
          v-for="filter in filters"
          :key="filter.id"
          @click="activeFilter = filter.id"
          class="rounded-full border px-4 py-2.5 text-xs font-semibold transition sm:px-5"
          :class="activeFilter === filter.id
            ? 'border-[#142B4F] bg-[#142B4F] text-white'
            : 'border-[#E4DED3] bg-white text-[#64748B] hover:border-[#C6A77A]'"
        >
          {{ filter.label }}
          <span class="ml-1 opacity-65">{{ filter.count }}</span>
        </button>
      </div>

      <div class="mb-5 mt-7 flex items-center justify-between gap-4">
        <p class="text-xs text-[#87919F]">
          Hiển thị <strong class="text-[#142B4F]">{{ filteredListings.length }}</strong> tin đăng
        </p>
        <span class="text-xs uppercase tracking-widest text-[#B49362]">
          PROPERTY PORTFOLIO
        </span>
      </div>

      <!-- LISTINGS -->
      <div v-if="filteredListings.length" class="space-y-5">
        <article
          v-for="listing in filteredListings"
          :key="listing.id"
          class="group grid min-w-0 overflow-hidden rounded-[22px] border border-[#E8E3DA] bg-white transition duration-300 hover:border-[#C6A77A] hover:shadow-[0_16px_45px_rgba(20,43,79,0.08)] lg:grid-cols-[245px_minmax(0,1fr)_230px]"
        >
          <!-- IMAGE -->
          <div class="relative h-[230px] overflow-hidden bg-[#E7E2D8] lg:h-full lg:min-h-[220px]">
            <PrivateImage
              :src="listing.image"
              :alt="`${listing.title}`"
              loading="lazy"
              class="h-full w-full object-cover transition duration-700 group-hover:scale-105"
             />

            <div class="absolute inset-0 bg-gradient-to-t from-[#142B4F]/45 to-transparent"></div>

            <span class="absolute bottom-4 left-4 text-xs font-bold uppercase tracking-[0.15em] text-white">
              {{ listing.location }}
            </span>
          </div>

          <!-- INFORMATION -->
          <div class="flex min-w-0 flex-col justify-center p-5 sm:p-7">
            <div class="flex flex-wrap items-center gap-3">
              <span
                class="rounded-full px-3 py-1.5 text-xs font-bold"
                :class="statusClass(listing.status)"
              >
                {{ listing.statusText }}
              </span>

              <span v-if="listing.statusSub" class="text-xs text-[#9AA4B1]">
                {{ listing.statusSub }}
              </span>
            </div>

            <h3 class="mt-4 text-lg font-semibold leading-7 sm:text-xl">
              {{ listing.title }}
            </h3>

            <p class="mt-2 text-xs text-[#87919F]">
              ⌖ {{ listing.location }}
            </p>

            <p class="mt-3 text-xs leading-6 text-[#64748B]">
              {{ listing.info }}
            </p>

            <div class="mt-5 flex flex-wrap gap-5 border-t border-[#EEEAE3] pt-4">
              <template v-if="listing.views !== null">
                <span class="text-xs text-[#87919F]">
                  <strong class="mr-1 text-sm text-[#142B4F]">{{ listing.views }}</strong>
                  lượt xem
                </span>

                <span class="text-xs text-[#87919F]">
                  <strong class="mr-1 text-sm text-[#142B4F]">{{ listing.saves }}</strong>
                  lượt lưu
                </span>
              </template>

              <span v-else class="text-xs text-[#9AA4B1]">
                Chưa có thống kê tương tác
              </span>
            </div>
          </div>

          <!-- ACTIONS -->
          <div class="flex flex-col justify-between gap-6 border-t border-[#EEEAE3] p-5 sm:p-7 lg:border-l lg:border-t-0">
            <div class="lg:text-right">
              <p class="text-xs uppercase tracking-widest text-[#9AA4B1]">
                Giá đăng
              </p>
              <p class="mt-2 text-[25px] font-semibold tracking-tight">
                {{ listing.priceText }}
              </p>
              <p class="mt-1 text-xs text-[#B49362]">
                {{ listing.priceUnit }}
              </p>
            </div>

            <div class="flex flex-wrap gap-2 lg:justify-end">
              <button
                @click="openListing(listing)"
                class="rounded-full border border-[#E4DED3] bg-white px-5 py-3 text-xs font-semibold transition hover:border-[#C6A77A]"
              >
                Xem
              </button>

              <button
                @click="editListing(listing)"
                class="rounded-full px-5 py-3 text-xs font-semibold text-white transition hover:opacity-90"
                :class="listing.status === 'rejected'
                  ? 'bg-[#BD6A4C]'
                  : 'bg-[#142B4F]'"
              >
                {{ listing.status === 'rejected' ? 'Sửa & gửi lại' : 'Sửa tin' }}
              </button>
            <button v-if="['draft','rejected'].includes(listing.status)" :disabled="state.busy" @click="act(listing,'submit')" class="rounded-full border px-4 py-2 text-xs">Gửi duyệt</button><button v-if="!['closed','expired'].includes(listing.status)" :disabled="state.busy" @click="act(listing,'close')" class="rounded-full border px-4 py-2 text-xs">Đóng tin</button><button :disabled="state.busy" @click="act(listing,'delete')" class="rounded-full border px-4 py-2 text-xs">Xóa tin</button>
</div>
          </div>
          <PropertyModerationFeedback :id="listing.id" />
        </article>
      </div>

      <!-- EMPTY -->
      <div v-else class="rounded-[24px] border border-[#E8E3DA] bg-white px-6 py-20 text-center">
        <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[#F7F5F0] text-3xl text-[#B49362]">
          ⌕
        </div>

        <h3 class="mt-6 text-xl font-semibold">
          Không tìm thấy tin đăng
        </h3>

        <p class="mt-3 text-sm text-[#87919F]">
          Thử thay đổi trạng thái hoặc từ khóa tìm kiếm.
        </p>

        <button
          @click="activeFilter = 'all'; searchText = ''"
          class="mt-6 rounded-full bg-[#142B4F] px-6 py-3 text-xs font-semibold text-white"
        >
          Xem tất cả tin đăng
        </button>
      </div>

      <!-- CTA -->
      <section class="relative mt-14 overflow-hidden rounded-[25px] bg-[#142B4F] px-7 py-10 text-white sm:px-10">
        <div class="pointer-events-none absolute -right-12 -top-24 h-72 w-72 rounded-full border border-[#C6A77A]/20"></div>

        <div class="relative flex flex-wrap items-center justify-between gap-7">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.2em] text-[#7BD4E5]">
              SMARTPROP / YOUR NEXT LISTING
            </p>

            <h2 class="mt-4 text-3xl font-medium">
              Sẵn sàng cho <span class="italic text-[#C6A77A]">tin đăng tiếp theo?</span>
            </h2>

            <p class="mt-4 max-w-xl text-sm leading-7 text-white/60">
              Đăng tải bất động sản và tiếp tục xây dựng danh mục của bạn trên SmartProp.
            </p>
          </div>

          <button
            @click="goPost"
            class="rounded-full bg-[#C6A77A] px-7 py-4 text-xs font-bold text-[#142B4F] transition hover:bg-[#E1C394]"
          >
            + Tạo tin đăng mới ↗
          </button>
        </div>
      </section>

      <p class="mt-7 text-center text-xs leading-6 text-[#87919F]">
        Thông tin và trạng thái tin đăng được tải từ tài khoản của bạn.
      </p>
    <LegacyPager :state="state" /></div>

    <!-- DETAIL MODAL -->
    <div
      v-if="selectedListing && !showEditNotice"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[#08172B]/70 p-4"
      @click.self="closeListing"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="listing-dialog-title"
        class="w-full max-w-xl overflow-hidden rounded-[24px] bg-white shadow-2xl"
      >
        <div class="relative h-[220px]">
          <PrivateImage
            :src="selectedListing.image"
            :alt="selectedListing.title"
            class="h-full w-full object-cover"
           />

          <button
            @click="closeListing"
            aria-label="Đóng"
            class="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full bg-white text-[#142B4F]"
          >
            ✕
          </button>
        </div>

        <div class="p-6 sm:p-8">
          <span
            class="rounded-full px-3 py-1.5 text-xs font-semibold"
            :class="statusClass(selectedListing.status)"
          >
            {{ selectedListing.statusText }}
          </span>

          <h2 id="listing-dialog-title" class="mt-5 text-2xl font-semibold">
            {{ selectedListing.title }}
          </h2>

          <p class="mt-3 text-sm text-[#87919F]">
            {{ selectedListing.location }}
          </p>

          <p class="mt-3 text-sm text-[#64748B]">
            {{ selectedListing.info }}
          </p>

          <p class="mt-6 text-2xl font-semibold">
            {{ selectedListing.priceText }}
          </p>

          <div class="mt-7 flex flex-wrap gap-3">
            <button
              v-if="selectedListing"
              @click="goToDetail(selectedListing)"
              class="rounded-full bg-[#142B4F] px-6 py-3 text-xs font-semibold text-white"
            >
              Mở trang chi tiết ↗
            </button>

            <button
              @click="closeListing"
              class="rounded-full border border-[#E4DED3] px-6 py-3 text-xs font-semibold"
            >
              Đóng
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- EDIT NOTICE -->
    <div
      v-if="showEditNotice && selectedListing"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[#08172B]/70 p-4"
      @click.self="closeEditNotice"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-dialog-title"
        class="w-full max-w-md rounded-[24px] bg-white p-7 text-center shadow-2xl sm:p-9"
      >
        <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[#EEE7DB] text-2xl text-[#B49362]">
          ✎
        </div>

        <h2 id="edit-dialog-title" class="mt-5 text-2xl font-semibold">
          Chỉnh sửa tin đăng
        </h2>

        <p class="mt-4 text-sm leading-7 text-[#64748B]">
          Tin <strong>{{ selectedListing.title }}</strong> chưa có
          trang chỉnh sửa được kết nối. Chức năng này cần được
          xây dựng ở bước tiếp theo.
        </p>

        <button
          @click="closeEditNotice"
          class="mt-7 rounded-full bg-[#142B4F] px-8 py-3 text-xs font-semibold text-white"
        >
          Đã hiểu
        </button>
      </div>
    </div>

    <!-- FOOTER -->

  </div>
</template>

<style scoped>
.sp-my-listings {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
  font-family: Arial, "Segoe UI", sans-serif;
  font-synthesis: none;
}

.sp-my-listings h1,
.sp-my-listings h2,
.sp-my-listings h3 {
  font-family: Arial, "Segoe UI", sans-serif;
  font-variant-ligatures: none;
  word-spacing: normal;
}

.sp-my-listings button,
.sp-my-listings input {
  font-family: inherit;
}

.sp-my-listings img {
  display: block;
}

@media (prefers-reduced-motion: reduce) {
  .sp-my-listings *,
  .sp-my-listings *::before,
  .sp-my-listings *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}
</style>
