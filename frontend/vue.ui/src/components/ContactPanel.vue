<script setup>
import {reactive, watch, ref, onBeforeUnmount} from 'vue'
import {useRouter} from 'vue-router'
import {api, session} from '../services/api.js'
import {createContact} from '../services/contact.js'

const props = defineProps({propertyId: String})
const emit = defineEmits(['revealed'])
const router = useRouter()
const contact = createContact(api)
const ui = reactive({busy: false, data: null, message: '', status: 0, retryAt: 0})
let sequence = 0
const clock = ref(Date.now())
const timer = setInterval(() => clock.value = Date.now(), 1000)

const copiedPhone = ref(false)
const copiedEmail = ref(false)

function copyText(text, isEmail = false) {
  if (!text) return
  try {
    navigator.clipboard.writeText(text)
    if (isEmail) {
      copiedEmail.value = true
      setTimeout(() => copiedEmail.value = false, 2000)
    } else {
      copiedPhone.value = true
      setTimeout(() => copiedPhone.value = false, 2000)
    }
  } catch (e) {
    // fallback
  }
}

const reset = () => {
  sequence++
  contact.reset()
  Object.assign(ui, contact.state)
  emit('revealed', null)
}

watch(() => [props.propertyId, session.user?.id, session.token], reset)
onBeforeUnmount(() => {
  clearInterval(timer)
  reset()
})

async function reveal() {
  if (!session.token) {
    return router.push({path: '/login', query: {reason: 'login-required'}})
  }
  const run = ++sequence
  ui.busy = true
  await contact.reveal(props.propertyId)
  if (run === sequence) {
    Object.assign(ui, contact.state)
    if (ui.data?.available) {
      emit('revealed', ui.data)
    }
  }
}

const telephone = value => /^\+?[0-9 ().-]{5,30}$/.test(value || '') ? 'tel:' + value.replace(/[ ().-]/g, '') : null
const email = value => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value || '') ? 'mailto:' + value : null
const zaloUrl = value => {
  if (!value) return null
  const clean = value.replace(/[^0-9]/g, '')
  return clean ? `https://zalo.me/${clean}` : null
}
</script>

<template>
  <div class="space-y-3" data-testid="contact-panel" aria-live="polite">
    <!-- Nút khi chưa có dữ liệu liên hệ -->
    <div v-if="!ui.data?.available">
      <button
        type="button"
        class="w-full py-3.5 px-4 rounded-2xl bg-[#1E325A] hover:bg-[#152442] text-white font-bold text-sm tracking-wide shadow-md flex items-center justify-center gap-2.5 transition-all duration-150 active:scale-[0.98] disabled:opacity-50 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E325A] focus-visible:ring-offset-2"
        :disabled="ui.busy || clock < ui.retryAt"
        @click="reveal"
      >
        <svg v-if="ui.busy" class="animate-spin w-4 h-4 text-white" viewBox="0 0 24 24" fill="none">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <svg v-else width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
        </svg>
        <span>{{ ui.busy ? 'Đang xác thực thông tin…' : 'Xem số điện thoại & Liên hệ' }}</span>
      </button>

      <div class="flex items-center justify-center gap-1.5 text-[11px] text-slate-400 mt-2">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-slate-400">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
        <span>Thông tin liên hệ bảo mật chống spam</span>
      </div>
    </div>

    <!-- Thông báo lỗi / trạng thái -->
    <p
      v-if="ui.message"
      :role="ui.status ? 'alert' : 'status'"
      class="text-xs text-amber-800 bg-amber-50/90 p-3 rounded-xl border border-amber-200/80 flex items-center gap-2"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="shrink-0 text-amber-600">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <span>{{ ui.message }}</span>
    </p>

    <!-- Khi đã mở dữ liệu liên hệ -->
    <template v-if="ui.data?.available">
      <!-- Nút Gọi điện thoại nổi bật (Primary Action) -->
      <div v-if="ui.data.contactPhone" class="space-y-2">
        <div class="flex items-center gap-2">
          <a
            v-if="telephone(ui.data.contactPhone)"
            :href="telephone(ui.data.contactPhone)"
            class="flex-1 py-3.5 px-4 rounded-2xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm shadow-md flex items-center justify-center gap-2.5 transition-all duration-150 active:scale-[0.98] text-center cursor-pointer"
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
            </svg>
            <span>{{ ui.data.contactPhone }} · Gọi ngay</span>
          </a>
          <div
            v-else
            class="flex-1 py-3.5 px-4 rounded-2xl bg-emerald-600 text-white font-bold text-sm flex items-center justify-center gap-2"
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
            </svg>
            <span>{{ ui.data.contactPhone }}</span>
          </div>

          <!-- Nút Copy số nhanh -->
          <button
            type="button"
            class="px-3.5 py-3.5 rounded-2xl border border-slate-200 hover:bg-slate-100/80 active:scale-95 text-xs font-semibold text-slate-600 transition-all duration-150 shrink-0 cursor-pointer shadow-2xs"
            :title="copiedPhone ? 'Đã sao chép!' : 'Sao chép số điện thoại'"
            @click="copyText(ui.data.contactPhone, false)"
          >
            <svg v-if="copiedPhone" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="text-emerald-600">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
          </button>
        </div>

        <!-- Row: Chat Zalo & Chat SMS -->
        <div class="grid grid-cols-2 gap-2 pt-1">
          <a
            v-if="zaloUrl(ui.data.contactPhone)"
            :href="zaloUrl(ui.data.contactPhone)"
            target="_blank"
            rel="noopener noreferrer"
            class="py-2.5 px-3 rounded-xl bg-blue-50 hover:bg-blue-100 border border-blue-200 text-blue-700 font-bold text-xs flex items-center justify-center gap-1.5 transition-all duration-150 cursor-pointer"
          >
            <span class="w-4 h-4 rounded-full bg-blue-600 text-white text-[9px] font-black flex items-center justify-center">Z</span>
            <span>Chat Zalo</span>
          </a>

          <button
            type="button"
            class="py-2.5 px-3 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 font-semibold text-xs flex items-center justify-center gap-1.5 transition-all duration-150 cursor-pointer"
            @click="copyText(ui.data.contactPhone, false)"
          >
            <span class="text-[11px]">{{ copiedPhone ? '✓ Đã chép' : '📋 Sao chép số' }}</span>
          </button>
        </div>
      </div>

      <!-- Email liên hệ -->
      <div v-if="ui.data.contactEmail" class="p-3 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-2.5">
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="w-8 h-8 rounded-xl bg-slate-100 text-[#1E325A] flex items-center justify-center text-xs shrink-0 border border-slate-200">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
              <polyline points="22,6 12,13 2,6"/>
            </svg>
          </div>
          <div class="min-w-0">
            <p class="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Email liên hệ</p>
            <a
              v-if="email(ui.data.contactEmail)"
              :href="email(ui.data.contactEmail)"
              class="text-xs font-bold text-[#1E325A] hover:text-[#b3915f] hover:underline truncate block"
            >
              {{ ui.data.contactEmail }}
            </a>
            <span v-else class="text-xs font-bold text-[#1E325A] truncate block">
              {{ ui.data.contactEmail }}
            </span>
          </div>
        </div>

        <button
          type="button"
          class="p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-white transition cursor-pointer"
          :title="copiedEmail ? 'Đã sao chép email!' : 'Sao chép email'"
          @click="copyText(ui.data.contactEmail, true)"
        >
          <svg v-if="copiedEmail" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="text-emerald-600">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
        </button>
      </div>
    </template>

    <p v-if="clock < ui.retryAt" class="text-xs text-slate-400 text-center">
      Có thể thử lại sau {{ Math.ceil((ui.retryAt - clock) / 1000) }} giây.
    </p>
  </div>
</template>
