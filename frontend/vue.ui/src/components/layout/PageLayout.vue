<script setup>
import { nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from './AppHeader.vue'
import AppFooter from './AppFooter.vue'
const route = useRoute()
watch(() => route.path, async () => { await nextTick(); document.getElementById('page-content')?.focus({ preventScroll: true }) })
</script>
<template>
  <div class="page-layout flex min-h-dvh flex-col bg-brand-cream text-brand-navy"><a href="#page-content" class="fixed -top-20 left-4 z-[100] rounded-control bg-white px-5 py-3 text-sm font-semibold shadow-lg focus:top-3">Đến nội dung chính</a><AppHeader /><main id="page-content" tabindex="-1" class="min-w-0 flex-1 outline-none"><slot /></main><AppFooter /></div>
</template>
