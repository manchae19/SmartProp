<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { session } from '../../services/api.js'
import { canRequestBroker } from '../../services/brokerApplication.js'
import { canPublish } from '../../services/siteNavigation.js'
import NotificationBadge from '../NotificationBadge.vue'
defineProps({ busy: Boolean, error: String })
const emit = defineEmits(['navigate', 'logout'])
const route = useRoute()
const links = computed(() => {
  if (!session.token) return [{ label: 'Đăng nhập', to: '/login' }, { label: 'Tạo tài khoản', to: '/register' }]
  return [
    { label: 'Hồ sơ cá nhân', to: '/account' }, { label: 'Tin đã lưu', to: '/favorites' },
    { label: 'Tin nhắn', to: '/account/messages' }, { label: 'Phiên đăng nhập', to: '/account/sessions' },
    { label: 'Xác minh email', to: '/account/verify-email' }, { label: 'Báo cáo của tôi', to: '/account/reports' },
    ...(canRequestBroker(session.user) ? [{label:'Quyền đăng tin',to:'/account/broker-application'}] : []),
    ...(canPublish(session.user) ? [{ label: 'Đăng tin', to: '/post' }, { label: 'Quản lý tin đăng', to: '/my-listing' }] : []),
    ...(session.user?.status === 'ACTIVE' && session.user?.role === 'ADMIN' ? [{ label: 'Quản trị hệ thống', to: '/admin' }] : []),
  ]
})
</script>
<template>
  <section aria-label="Tài khoản" class="border-t border-brand-line pt-5">
    <div v-if="session.token" class="mb-4 rounded-panel bg-brand-surface p-4"><p class="break-words text-sm font-semibold">{{ session.user?.fullName || 'Tài khoản SmartProp' }}</p><p class="mt-1 text-xs text-brand-muted">{{ ({ BUYER: 'Người mua / người thuê', BROKER: 'Môi giới', ADMIN: 'Quản trị viên' })[session.user?.role] || 'Thành viên' }}</p></div>
    <p class="mb-2 text-[10px] font-semibold tracking-[.2em] text-brand-accent">TÀI KHOẢN CỦA BẠN</p>
    <nav aria-label="Chức năng tài khoản" class="grid gap-1"><RouterLink v-for="link in links" :key="link.to" :to="link.to" class="rounded-control px-3 py-3 text-sm font-medium transition-colors hover:bg-brand-surface focus-visible:outline-2 focus-visible:outline-brand-gold" :class="route.path === link.to ? 'bg-brand-surface text-brand-accent' : 'text-brand-navy'" :aria-current="route.path === link.to ? 'page' : undefined" @click="emit('navigate')">{{ link.label }}</RouterLink><div v-if="session.token" class="rounded-control px-3 py-3 text-sm font-medium hover:bg-brand-surface" @click="emit('navigate')"><NotificationBadge /></div></nav>
    <p v-if="error" role="alert" class="mt-4 rounded-control bg-red-50 p-3 text-sm leading-6 text-red-800">{{ error }}</p>
    <button v-if="session.token" type="button" :disabled="busy" class="sp-button sp-button-secondary mt-5 w-full" @click="emit('logout')">{{ busy ? 'Đang đăng xuất…' : 'Đăng xuất' }}</button>
  </section>
</template>
