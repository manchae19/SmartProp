<script setup>
import { computed, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from './AppHeader.vue'
import AppFooter from './AppFooter.vue'
const route = useRoute()
const messengerPage = computed(() => route.path === '/advisor/chat')
watch(() => route.path, async () => { await nextTick(); document.getElementById('page-content')?.focus({ preventScroll: true }) })
</script>
<template>
  <div class="page-layout flex min-h-dvh flex-col bg-brand-cream text-brand-navy" :class="{ 'messenger-layout': messengerPage }"><a href="#page-content" class="fixed -top-20 left-4 z-[100] rounded-control bg-white px-5 py-3 text-sm font-semibold shadow-lg focus:top-3">Đến nội dung chính</a><AppHeader /><main id="page-content" tabindex="-1" class="min-w-0 flex-1 outline-none" :class="{ 'messenger-main': messengerPage }"><slot /></main><AppFooter v-if="!messengerPage" /></div>
</template>
<style scoped>
.page-layout.messenger-layout{height:100dvh;min-height:0;overflow:hidden}.messenger-main{min-height:0;overflow:hidden}.messenger-layout :deep(.app-header){flex-shrink:0}
</style>
