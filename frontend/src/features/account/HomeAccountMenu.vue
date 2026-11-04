<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import { useRoute } from 'vue-router'
import { listingLink } from '../property/listingFilters.js'
import { session } from '../auth/api.js'
import NotificationBadge from '../notification/NotificationBadge.vue'

defineProps({ district: String, filters: Object, light: Boolean })
const route = useRoute()
const open = ref(false)
const container = ref(null)
const trigger = ref(null)
const menuId = 'home-account-' + useId()

function close() { open.value = false }
function outside(event) {
  if (!container.value?.contains(event.target)) close()
}
function escape(event) {
  if (event.key === 'Escape' && open.value) {
    close()
    trigger.value?.focus()
  }
}
async function focusFirst() {
  open.value = true
  await nextTick()
  container.value?.querySelector('nav a')?.focus()
}
function focusOut(event) {
  if (event.relatedTarget && !container.value?.contains(event.relatedTarget)) close()
}

watch(() => route.fullPath, close)
onMounted(() => {
  document.addEventListener('pointerdown', outside)
  window.addEventListener('keydown', escape)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', outside)
  window.removeEventListener('keydown', escape)
})
</script>

<template>
  <div ref="container" class="relative shrink-0" data-home-account-menu @focusout="focusOut">
    <button
      ref="trigger"
      type="button"
      :aria-label="open ? 'Đóng menu' : 'Mở menu'"
      :aria-expanded="open"
      :aria-controls="menuId"
      class="flex h-11 items-center justify-center gap-3 rounded-xl border px-3.5 transition focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#D8B887]"
      :class="light ? 'border-[#DCD5CA] bg-white text-[#142B4F] hover:bg-[#F1EEE8]' : 'border-white/35 bg-[#091728]/30 text-white backdrop-blur-md hover:bg-white/15'"
      @click="open = !open"
      @keydown.down.prevent="focusFirst"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true">
        <path v-if="open" d="m6 6 12 12M6 18 18 6" />
        <path v-else d="M4 6h16M4 12h16M4 18h16" />
      </svg>
      <span class="hidden text-xs font-semibold sm:inline">Menu</span>
    </button>

    <nav
      v-if="open"
      :id="menuId"
      aria-label="Menu tài khoản và tiện ích"
      class="absolute right-0 top-full z-50 mt-3 w-[min(19rem,calc(100vw-2.5rem))] rounded-2xl border border-[#E7E1D7] bg-white p-2.5 text-[#142B4F] shadow-2xl shadow-[#071525]/20"
    >
      <p class="px-4 pb-2 pt-3 text-xs font-bold uppercase tracking-[0.2em] text-[#967444]">Khám phá SmartProp</p>
      <RouterLink :to="listingLink('/listings', filters || { district })" class="block rounded-xl px-4 py-3 text-sm font-medium transition hover:bg-[#F1EEE8] focus-visible:outline-2 focus-visible:outline-[#B3915F]" @click="close">Danh sách bất động sản</RouterLink>
      <RouterLink :to="listingLink('/map', filters || { district })" class="block rounded-xl px-4 py-3 text-sm font-medium transition hover:bg-[#F1EEE8] focus-visible:outline-2 focus-visible:outline-[#B3915F]" @click="close">Bản đồ GIS</RouterLink>
      <RouterLink :to="session.token ? '/account' : '/login'" class="block rounded-xl px-4 py-3 text-sm font-medium transition hover:bg-[#F1EEE8] focus-visible:outline-2 focus-visible:outline-[#B3915F]" @click="close">{{ session.token ? 'Tài khoản' : 'Đăng nhập' }}</RouterLink>
      <template v-if="session.token"><RouterLink to="/favorites" class="account-item" @click="close">Tin đã lưu</RouterLink><div class="account-item"><NotificationBadge /></div><RouterLink to="/account/messages" class="account-item" @click="close">Tin nhắn</RouterLink><RouterLink to="/account/sessions" class="account-item" @click="close">Phiên đăng nhập</RouterLink><RouterLink to="/account/verify-email" class="account-item" @click="close">Xác minh email</RouterLink><RouterLink v-if="['BROKER', 'ADMIN'].includes(session.user?.role)" to="/my-listing" class="account-item" @click="close">Tin đăng của tôi</RouterLink><RouterLink v-if="session.user?.role === 'ADMIN'" to="/admin" class="account-item" @click="close">Quản trị</RouterLink></template><RouterLink v-else to="/register" class="account-item" @click="close">Tạo tài khoản</RouterLink>
      <div class="mx-3 my-2 border-t border-[#E7E1D7]"></div>
      <RouterLink v-if="!session.token || ['BROKER', 'ADMIN'].includes(session.user?.role)" to="/post" class="block rounded-xl bg-[#142B4F] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#24456D] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B3915F]" @click="close">Đăng tin <span aria-hidden="true">↗</span></RouterLink>
    </nav>
  </div>
</template>

<style scoped>
nav{max-height:min(75dvh,40rem);overflow-y:auto;overscroll-behavior:contain}
button { cursor: pointer; }.account-item{display:block;padding:12px 16px;border-radius:12px;font-size:14px;font-weight:500}.account-item:hover{background:#f1eee8}.account-item:focus-visible{outline:2px solid #b3915f}
</style>
