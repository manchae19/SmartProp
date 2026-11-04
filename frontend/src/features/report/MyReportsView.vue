
<script setup>
import {computed,ref} from 'vue'
import { useRouter } from 'vue-router'
import {api} from '../auth/api.js'
import {useList,LegacyState,LegacyPager,PrivateImage} from '../../lib/legacy.js'
import {collectionReport} from '../home/collection.js'

import ReportDetails from './ReportDetails.vue'
import {useCollection} from '../home/useCollection.js'
const router = useRouter()

// SMARTPROP MY REPORTS 2.0
// Data is loaded from the existing backend.

const activeFilter = ref('all')
const searchText = ref('')
const selectedReport = ref(null)

const reportStatuses={open:'OPEN',processing:'PROCESSING',resolved:'RESOLVED',rejected:'REJECTED'};
const state=useCollection('/users/me/reports','/reports/summary',()=>({keyword:searchText.value.trim(),status:reportStatuses[activeFilter.value],sort:'newest'}));
const reports=computed(()=>state.items.map(collectionReport)),filteredReports=reports;
const count=key=>state.summary?.byStatus?.[reportStatuses[key]]??'—';
const processingCount=computed(()=>count('processing')),resolvedCount=computed(()=>count('resolved')),rejectedCount=computed(()=>count('rejected'));
const filters=computed(()=>[{key:'all',label:'Tất cả',count:state.summary?.totalReports??'—'},...Object.entries({open:'Mới gửi',processing:'Đang xử lý',resolved:'Đã xử lý',rejected:'Từ chối'}).map(([key,label])=>({key,label,count:count(key)}))]);

function statusClass(status) {
  if (status === 'processing') {
    return 'bg-[#FFF1D9] text-[#A36A19]'
  }

  if (status === 'resolved') {
    return 'bg-[#E5F4EB] text-[#287B56]'
  }

  return 'bg-[#FCE8E3] text-[#BD5D48]'
}

function statusDot(status) {
  if (status === 'processing') return 'bg-[#D69C44]'
  if (status === 'resolved') return 'bg-[#4DAD80]'
  return 'bg-[#D17760]'
}

async function openReport(report){await state.run(async()=>{selectedReport.value=collectionReport(await api('/reports/'+report.id))})}
async function reportUpdated(report){selectedReport.value=collectionReport(report);await state.reload()}

function closeReport() {
  selectedReport.value = null
}

function resetFilters() {
  activeFilter.value = 'all'
  searchText.value = ''
}

function goHome() {
  router.push('/home')
}

function goAccount() {
  router.push('/account')
}

function goPost() {
  router.push('/post')
}

function goMap() {
  router.push('/map')
}
</script>

<template>
  <div class="sp-my-reports min-h-screen bg-[#F7F5F0] text-[#142B4F]">

    


    
    <section class="relative overflow-hidden border-b border-[#E7E2D8]">
      <div class="pointer-events-none absolute -right-28 -top-32 h-[420px] w-[420px] rounded-full border border-[#C6A77A]/20"></div>
      <div class="pointer-events-none absolute -right-10 -top-12 h-[280px] w-[280px] rounded-full border border-[#C6A77A]/20"></div>

      <div class="relative mx-auto max-w-[1440px] px-5 py-12 md:px-10 md:py-16">
        <div class="flex flex-wrap items-end justify-between gap-8">
          <div>
            <div class="flex items-center gap-3">
              <span class="h-px w-9 bg-[#B49362]"></span>
              <p class="text-xs font-bold uppercase tracking-[0.22em] text-[#B49362]">
                SMARTPROP / TRUST & TRANSPARENCY
              </p>
            </div>

            <h1 class="mt-6 text-[39px] font-medium leading-tight tracking-tight sm:text-[56px]">
              Theo dõi
              <span class="block italic text-[#B49362]">báo cáo của bạn.</span>
            </h1>

            <p class="mt-5 max-w-2xl text-sm leading-7 text-[#7B8798]">
              Quản lý các báo cáo đã gửi, theo dõi tiến độ xem xét
              và xem kết quả xử lý trong một không gian trực quan,
              minh bạch và dễ sử dụng.
            </p>

            <span class="mt-5 inline-flex rounded-full border border-[#E2D8C8] bg-[#EEE7DB] px-4 py-2 text-xs font-bold uppercase tracking-widest text-[#94774F]">
              Dữ liệu từ hệ thống
            </span>
          </div>

          <button
            type="button"
            @click="goMap"
            class="rounded-full border border-[#DCD4C7] bg-white px-7 py-4 text-xs font-bold transition hover:border-[#C6A77A]"
          >
            Khám phá GIS Explorer ↗
          </button>
        </div>
      </div>
    </section>

    
    <section class="mx-auto max-w-[1440px] px-5 pt-10 md:px-10">
      <div class="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-5">

        <div class="rounded-[20px] border border-[#E8E3DA] bg-white p-5 sm:p-7">
          <p class="text-xs font-bold uppercase tracking-widest text-[#8D99A8]">
            Tổng báo cáo
          </p>

          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ state.summary?.totalReports ?? '—' }}</span>
            <span class="text-xl text-[#C6A77A]">▤</span>
          </div>

          <p class="mt-3 text-xs text-[#8D99A8]">
            Báo cáo đã gửi
          </p>
        </div>

        <div class="rounded-[20px] bg-[#142B4F] p-5 text-white sm:p-7">
          <p class="text-xs font-bold uppercase tracking-widest text-white/60">
            Đang xử lý
          </p>

          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ processingCount }}</span>
            <span class="h-3 w-3 rounded-full bg-[#E5B76A]"></span>
          </div>

          <p class="mt-3 text-xs text-white/55">
            Đang chờ kết quả
          </p>
        </div>

        <div class="rounded-[20px] border border-[#E8E3DA] bg-white p-5 sm:p-7">
          <p class="text-xs font-bold uppercase tracking-widest text-[#8D99A8]">
            Đã xử lý
          </p>

          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ resolvedCount }}</span>
            <span class="text-xl text-[#3A9A70]">✓</span>
          </div>

          <p class="mt-3 text-xs text-[#8D99A8]">
            Đã có kết quả xem xét
          </p>
        </div>

        <div class="rounded-[20px] border border-[#E8E3DA] bg-white p-5 sm:p-7">
          <p class="text-xs font-bold uppercase tracking-widest text-[#8D99A8]">
            Bị từ chối
          </p>

          <div class="mt-4 flex items-end justify-between">
            <span class="text-4xl font-semibold">{{ rejectedCount }}</span>
            <span class="text-xl text-[#C56E56]">!</span>
          </div>

          <p class="mt-3 text-xs text-[#8D99A8]">
            Báo cáo không được chấp nhận
          </p>
        </div>
      </div>
    </section>

    
    <div class="mx-auto max-w-[1440px] px-5 pb-20 pt-12 md:px-10">
<LegacyState :state="state" /><p v-if="state.summaryError" role="alert">{{state.summaryError}} <button @click="state.loadSummary">Tải lại thống kê</button></p><p class="mb-4 text-xs text-[#87919F]">{{state.totalElements}} kết quả · kết quả đã lọc trên toàn bộ báo cáo.</p>

      <div class="flex flex-wrap items-end justify-between gap-5">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-[#B49362]">
            REPORT CENTER / 01
          </p>

          <h2 class="mt-3 text-3xl font-medium tracking-tight sm:text-4xl">
            Lịch sử <span class="italic text-[#B49362]">báo cáo.</span>
          </h2>

          <p class="mt-3 text-xs text-[#87919F]">
            Theo dõi tiến độ và kết quả xử lý của từng báo cáo.
          </p>
        </div>

        <div class="flex w-full items-center gap-3 rounded-xl border border-[#E4DED3] bg-white px-4 sm:w-[320px]">
          <span class="text-xl text-[#B49362]">⌕</span>

          <input
            v-model="searchText"
            type="search"
            aria-label="Tìm kiếm báo cáo"
            placeholder="Tìm nội dung, mã tin hoặc lý do..."
            class="h-12 min-w-0 w-full bg-transparent text-xs outline-none"
          />
        </div>
      </div>

      
      <div class="mt-8 flex flex-wrap gap-2">
        <button
          v-for="filter in filters"
          :key="filter.key"
          type="button"
          @click="activeFilter = filter.key"
          class="rounded-full border px-4 py-2.5 text-xs font-semibold transition sm:px-5"
          :class="
            activeFilter === filter.key
              ? 'border-[#142B4F] bg-[#142B4F] text-white'
              : 'border-[#E4DED3] bg-white text-[#64748B] hover:border-[#C6A77A]'
          "
        >
          {{ filter.label }}
          <span class="ml-1 opacity-65">{{ filter.count }}</span>
        </button>
      </div>

      <div class="mb-5 mt-7 flex items-center justify-between gap-4">
        <p class="text-xs text-[#87919F]">
          Hiển thị
          <strong class="text-[#142B4F]">{{ filteredReports.length }}</strong>
          báo cáo
        </p>

        <span class="text-xs uppercase tracking-widest text-[#B49362]">
          REPORT HISTORY
        </span>
      </div>

      
      <div v-if="filteredReports.length" class="space-y-5">
        <article
          v-for="report in filteredReports"
          :key="report.id"
          class="group grid min-w-0 overflow-hidden rounded-[22px] border border-[#E8E3DA] bg-white transition duration-300 hover:border-[#C6A77A] hover:shadow-[0_16px_45px_rgba(20,43,79,0.08)] lg:grid-cols-[245px_minmax(0,1fr)_225px]"
        >
          
          <div class="relative h-[225px] overflow-hidden bg-[#E7E2D8] lg:h-full lg:min-h-[230px]">
            <PrivateImage
              :src="report.image"
              :alt="`${report.title}`"
              loading="lazy"
              class="h-full w-full object-cover transition duration-700 group-hover:scale-105"
             />

            <div class="absolute inset-0 bg-gradient-to-t from-[#142B4F]/55 to-transparent"></div>

            <span class="absolute bottom-4 left-4 text-xs font-bold uppercase tracking-[0.12em] text-white">
              {{ report.location }}
            </span>
          </div>

          
          <div class="flex min-w-0 flex-col justify-center p-5 sm:p-7">
            <div class="flex flex-wrap items-center gap-3">
              <span
                class="inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold"
                :class="statusClass(report.status)"
              >
                <span
                  class="h-1.5 w-1.5 rounded-full"
                  :class="statusDot(report.status)"
                ></span>
                {{ report.statusLabel }}
              </span>

              <span class="text-xs font-semibold text-[#B49362]">
                REPORT #{{ String(report.id).padStart(3, '0') }}
              </span>
            </div>

            <h3 class="mt-4 text-lg font-semibold leading-7 sm:text-xl">
              {{ report.title }}
            </h3>

            <p class="mt-2 text-xs text-[#87919F]">
              ⌖ {{ report.location }}
            </p>

            <div class="mt-4">
              <span class="inline-flex max-w-full rounded-full bg-[#F4EFE7] px-3 py-2 text-xs font-bold tracking-wide text-[#9B7952]">
                {{ report.reason }}
              </span>
            </div>

            <p class="mt-4 text-xs text-[#87919F]">
              {{ report.sentAt }}
            </p>

            <p
              v-if="report.result"
              class="mt-4 border-l-2 border-[#C6A77A] pl-3 text-xs leading-6 text-[#64748B]"
            >
              {{ report.result }}
            </p>
          </div>

          
          <div class="flex flex-col justify-between gap-6 border-t border-[#EEEAE3] p-5 sm:p-7 lg:border-l lg:border-t-0">
            <div class="lg:text-right">
              <p class="text-xs uppercase tracking-widest text-[#9AA4B1]">
                Trạng thái hiện tại
              </p>

              <p class="mt-3 text-base font-semibold">
                {{ report.statusLabel }}
              </p>

              <p class="mt-2 text-xs leading-5 text-[#87919F]">
                {{ report.update }}
              </p>
            </div>

            <button
              type="button"
              @click="openReport(report)"
              class="self-start rounded-full border border-[#E4DED3] bg-white px-5 py-3 text-xs font-semibold transition hover:border-[#142B4F] hover:bg-[#142B4F] hover:text-white lg:self-end"
            >
              Xem báo cáo ↗
            </button>
          </div>
        </article>
      </div>

      
      <div
        v-else
        class="rounded-[24px] border border-[#E8E3DA] bg-white px-6 py-20 text-center"
      >
        <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[#F7F5F0] text-3xl text-[#B49362]">
          ⚑
        </div>

        <h3 class="mt-6 text-xl font-semibold">
          Không tìm thấy báo cáo
        </h3>

        <p class="mt-3 text-sm text-[#87919F]">
          Hãy thử thay đổi trạng thái hoặc từ khóa tìm kiếm.
        </p>

        <button
          type="button"
          @click="resetFilters"
          class="mt-6 rounded-full bg-[#142B4F] px-6 py-3 text-xs font-semibold text-white"
        >
          Xem tất cả báo cáo
        </button>
      </div>

      
      <section class="mt-10 rounded-[22px] border border-[#E8E3DA] bg-white px-6 py-6 sm:px-8">
        <div class="flex items-start gap-4">
          <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#EEE7DB] text-lg font-semibold text-[#9B7952]">
            i
          </div>

          <div>
            <h3 class="text-sm font-semibold">
              Thông tin về quá trình xử lý
            </h3>

            <p class="mt-2 max-w-3xl text-xs leading-6 text-[#87919F]">
              Bạn có thể theo dõi trạng thái xử lý và bổ sung bằng chứng trong chi tiết báo cáo.
</p>
          </div>
        </div>
      </section>

      
      <section class="relative mt-12 overflow-hidden rounded-[25px] bg-[#142B4F] px-7 py-10 text-white sm:px-10">
        <div class="pointer-events-none absolute -right-12 -top-24 h-72 w-72 rounded-full border border-[#C6A77A]/20"></div>

        <div class="relative flex flex-wrap items-center justify-between gap-7">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.2em] text-[#7BD4E5]">
              SMARTPROP / TRUST & SAFETY
            </p>

            <h2 class="mt-4 text-3xl font-medium">
              Minh bạch hơn.
              <span class="italic text-[#C6A77A]"> An tâm hơn.</span>
            </h2>

            <p class="mt-4 max-w-xl text-sm leading-7 text-white/60">
              Khám phá bất động sản và các thông tin tham khảo
              trên nền tảng SmartProp.
            </p>
          </div>

          <button
            type="button"
            @click="goMap"
            class="rounded-full bg-[#C6A77A] px-7 py-4 text-xs font-bold text-[#142B4F] transition hover:bg-[#E1C394]"
          >
            Khám phá bản đồ GIS ↗
          </button>
        </div>
      </section>

      <p class="mt-7 text-center text-xs leading-6 text-[#87919F]">
        Báo cáo và kết quả xử lý được tải từ tài khoản của bạn.
      </p>
    <LegacyPager :state="state" /></div>

    
    <div
      v-if="selectedReport"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[#08172B]/70 p-4"
      @click.self="closeReport"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-dialog-title"
        class="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-[24px] bg-white shadow-2xl"
      >
        <div class="relative h-[210px]">
          <PrivateImage
            :src="selectedReport.image"
            :alt="selectedReport.title"
            class="h-full w-full object-cover"
           />

          <button
            type="button"
            @click="closeReport"
            aria-label="Đóng chi tiết báo cáo"
            class="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full bg-white text-[#142B4F]"
          >
            ✕
          </button>
        </div>

        <div class="p-6 sm:p-8">
          <div class="flex flex-wrap items-center gap-3">
            <span
              class="rounded-full px-3 py-1.5 text-xs font-semibold"
              :class="statusClass(selectedReport.status)"
            >
              {{ selectedReport.statusLabel }}
            </span>

            <span class="text-xs text-[#B49362]">
              REPORT #{{ String(selectedReport.id).padStart(3, '0') }}
            </span>
          </div>

          <h2 id="report-dialog-title" class="mt-5 text-2xl font-semibold">
            {{ selectedReport.title }}
          </h2>

          <p class="mt-3 text-sm text-[#87919F]">
            {{ selectedReport.location }}
          </p>

          <div class="mt-6 space-y-4 border-y border-[#EEEAE3] py-5">
            <div>
              <p class="text-xs uppercase tracking-widest text-[#9AA4B1]">
                Lý do báo cáo
              </p>
              <p class="mt-2 text-sm font-semibold">
                {{ selectedReport.reason }}
              </p>
            </div>

            <div>
              <p class="text-xs uppercase tracking-widest text-[#9AA4B1]">
                Thời gian gửi
              </p>
              <p class="mt-2 text-sm">
                {{ selectedReport.sentAt }}
              </p>
            </div>

            <div>
              <p class="text-xs uppercase tracking-widest text-[#9AA4B1]">
                Cập nhật
              </p>
              <p class="mt-2 text-sm">
                {{ selectedReport.update }}
              </p>
            </div>

            <div>
              <p class="text-xs uppercase tracking-widest text-[#9AA4B1]">
                Kết quả
              </p>
              <p class="mt-2 text-sm leading-6 text-[#64748B]">
                {{ selectedReport.result || 'Báo cáo đang được xử lý, chưa có kết quả.' }}
              </p>
            </div>
          </div>

          <ReportDetails :report="selectedReport.raw" @updated="reportUpdated" />
<button
            type="button"
            @click="closeReport"
            class="mt-6 rounded-full bg-[#142B4F] px-7 py-3 text-xs font-semibold text-white"
          >
            Đóng chi tiết
          </button>
        </div>
      </div>
    </div>

    

  </div>
</template>

<style scoped>
.sp-my-reports {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
  font-family: Arial, "Segoe UI", sans-serif;
  font-synthesis: none;
}

.sp-my-reports h1,
.sp-my-reports h2,
.sp-my-reports h3 {
  font-family: Arial, "Segoe UI", sans-serif;
  font-variant-ligatures: none;
  word-spacing: normal;
}

.sp-my-reports button,
.sp-my-reports input {
  font-family: inherit;
}

.sp-my-reports img {
  display: block;
}

@media (prefers-reduced-motion: reduce) {
  .sp-my-reports *,
  .sp-my-reports *::before,
  .sp-my-reports *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}
</style>
