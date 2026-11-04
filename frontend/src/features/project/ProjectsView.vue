<script setup>
import ProjectDirectory from './ProjectDirectory.vue'
import { usePublicProjects } from './usePublicProjects.js'
import { LegacyState, LegacyPager } from '../../lib/legacy.js'
const state = usePublicProjects()
</script>
<template>
  <div class="sp-container py-10 sm:py-14" data-projects-page>
    <p class="mb-3 text-xs font-semibold tracking-[.24em] text-brand-accent">PROJECTS · ĐÀ NẴNG</p><h1 class="text-3xl font-semibold tracking-tight sm:text-5xl">Dự án bất động sản</h1><p class="mt-4 max-w-2xl text-sm leading-7 text-brand-muted">Khám phá các dự án giới thiệu qua website chính thức và các dự án được công bố trên SmartProp.</p>
    <section aria-labelledby="project-directory-heading" class="mt-10"><h2 id="project-directory-heading" class="mb-3 text-2xl font-semibold">Danh mục giới thiệu</h2><p class="mb-6 text-sm leading-7 text-brand-muted">Website chủ đầu tư và đơn vị phát triển.</p><ProjectDirectory /></section>
    <section aria-labelledby="backend-projects-heading" class="mt-12 border-t border-brand-line pt-10"><h2 id="backend-projects-heading" class="text-2xl font-semibold">Dự án trên SmartProp</h2><p class="mt-3 text-sm text-brand-muted">Thông tin dự án được công bố từ Backend.</p><LegacyState :state="state" /><div v-if="state.busy" class="mt-6 grid gap-5 md:grid-cols-3" aria-hidden="true"><div v-for="n in 3" :key="n" class="h-48 rounded-panel bg-brand-surface"></div></div><div v-else-if="state.items.length" class="mt-6 grid gap-5 md:grid-cols-2 xl:grid-cols-3"><RouterLink v-for="project in state.items" :key="project.id" :to="'/projects/' + project.id" class="flex min-w-0 flex-col gap-3 rounded-panel border border-brand-line bg-white p-6 transition-shadow hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-gold" :data-project-card="project.id"><span class="text-xs text-brand-accent">{{ project.developer || 'Chưa cung cấp chủ đầu tư' }}</span><h3 class="break-words text-xl font-semibold">{{ project.name }}</h3><p class="text-sm leading-7 text-brand-muted">{{ project.address || 'Chưa cung cấp địa chỉ' }}</p><span class="mt-auto pt-2 text-xs font-semibold">Xem thông tin dự án ↗</span></RouterLink></div><div v-else-if="!state.error" class="mt-6 rounded-panel border border-brand-line bg-white p-8 text-sm text-brand-muted">Chưa có dự án được công bố trên SmartProp.</div><LegacyPager :state="state" /></section>
  </div>
</template>
