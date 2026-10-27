<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { scrollHomeSection } from '../services/siteNavigation.js'

defineProps({ district: String, filters: Object })
const sections = [
  { id: 'properties', label: 'Bất động sản' },
  { id: 'gis', label: 'GIS Explorer' },
  { id: 'lifestyle', label: 'Phong cách sống' },
  { id: 'market', label: 'Thị trường' },
  { id: 'projects', label: 'Dự án' },
  { id: 'finance', label: 'Tài chính' },
]
const bar = ref(null)
const list = ref(null)
const pinned = ref(false)
const active = ref('')
let frame = 0
let observer

function reducedMotion() { return window.matchMedia('(prefers-reduced-motion: reduce)').matches }
function update() {
  frame = 0
  if (!bar.value) return
  const headerHeight = document.querySelector('.app-header')?.offsetHeight || 0
  pinned.value = bar.value.getBoundingClientRect().top <= headerHeight + 1
  const boundary = headerHeight + bar.value.offsetHeight + 24
  let current = ''
  for (const section of sections) {
    const target = document.getElementById(section.id)
    if (target && target.getBoundingClientRect().top <= boundary) current = section.id
  }
  active.value = current
}
function schedule() {
  if (!frame) frame = requestAnimationFrame(update)
}
function navigate(id) {
  scrollHomeSection(id)
}

watch(active, async id => {
  await nextTick()
  const link = list.value?.querySelector(`[href="#${id}"]`)
  if (!link || !list.value) return
  const bounds = link.getBoundingClientRect()
  const viewport = list.value.getBoundingClientRect()
  if (bounds.left < viewport.left || bounds.right > viewport.right) {
    list.value.scrollTo({ left: list.value.scrollLeft + bounds.left - viewport.left - (viewport.width - bounds.width) / 2,
      behavior: reducedMotion() ? 'instant' : 'smooth' })
  }
})

onMounted(() => {
  window.addEventListener('scroll', schedule, { passive: true })
  window.addEventListener('resize', schedule)
  observer = new ResizeObserver(schedule)
  observer.observe(bar.value)
  for (const section of sections) {
    const target = document.getElementById(section.id)
    if (target) observer.observe(target)
  }
  schedule()
  const initial = window.location.hash.slice(1)
  if (sections.some(section => section.id === initial)) requestAnimationFrame(() => navigate(initial))
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', schedule)
  window.removeEventListener('resize', schedule)
  observer?.disconnect()
  if (frame) cancelAnimationFrame(frame)
})
</script>

<template>
  <div ref="bar" class="home-section-nav sticky top-[var(--sp-header-height)] z-40 border-y border-brand-line bg-brand-cream/95 text-brand-navy backdrop-blur-xl" :class="{ 'shadow-lg shadow-[#142B4F]/5': pinned }" :data-pinned="pinned">
    <div class="sp-container flex h-[var(--sp-section-nav-height)] items-center gap-3">
      <nav ref="list" aria-label="Điều hướng các mục trang chủ" class="min-w-0 flex-1 overflow-x-auto overscroll-x-contain">
        <div class="mx-auto flex w-max items-center gap-1.5 py-2 sm:gap-2">
          <a v-for="section in sections" :key="section.id" :href="'#' + section.id" :aria-current="active === section.id ? 'location' : undefined" class="whitespace-nowrap rounded-full px-4 py-2.5 text-xs font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B3915F] sm:text-[13px]" :class="active === section.id ? 'bg-[#142B4F] text-white shadow-sm' : 'text-[#637083] hover:bg-[#EAE5DC] hover:text-[#142B4F]'" @click.prevent="navigate(section.id)">{{ section.label }}</a>
        </div>
      </nav>
    </div>
  </div>
</template>

<style scoped>
.home-section-nav nav { scrollbar-width: thin; scrollbar-color: #d8c6a8 transparent; }
@media (prefers-reduced-motion: reduce) { .home-section-nav a { transition: none; } }
</style>
