<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { listingLink, normalizeFilters } from '../../features/property/listingFilters.js'
import { session } from '../../features/auth/api.js'
const route = useRoute(), filters = computed(() => normalizeFilters(route.query))
</script>
<template>
  <footer id="account" class="app-footer mt-auto bg-brand-navy py-10 pb-36 text-white">
    <div class="sp-container grid gap-8 md:grid-cols-[1.4fr_1fr_1fr]"><div><RouterLink :to="listingLink('/home', filters)" class="text-2xl font-bold tracking-tight">SmartProp<span class="text-brand-highlight">.</span></RouterLink><p class="mt-3 max-w-sm text-sm leading-7 text-slate-300">Khám phá bất động sản và không gian sống tại Đà Nẵng.</p></div><nav aria-label="Khám phá cuối trang" class="grid content-start gap-3 text-sm text-slate-200"><RouterLink :to="listingLink('/listings', filters)">Bất động sản</RouterLink><RouterLink to="/projects">Dự án</RouterLink><RouterLink :to="listingLink('/map', filters)">Bản đồ GIS</RouterLink></nav><nav aria-label="Tiện ích cuối trang" class="grid content-start gap-3 text-sm text-slate-200"><RouterLink :to="{ ...listingLink('/home', filters), hash: '#market' }">Dữ liệu thị trường</RouterLink><RouterLink to="/valuation">Định giá AI</RouterLink><RouterLink :to="session.token ? '/account' : '/login'">{{ session.token ? 'Hồ sơ cá nhân' : 'Đăng nhập / Tạo tài khoản' }}</RouterLink></nav></div>
  </footer>
</template>
