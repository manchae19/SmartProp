<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { scrollHomeSection } from '../services/siteNavigation.js'
import AppIcon from './AppIcon.vue'

defineProps({ district: String, filters: Object })
const sections = [
  { id: 'properties', label: 'Bất động sản', icon: 'properties' },
  { id: 'gis', label: 'GIS Explorer', icon: 'gis' },
  { id: 'lifestyle', label: 'Phong cách sống', icon: 'lifestyle' },
  { id: 'market', label: 'Thị trường', icon: 'market' },
  { id: 'projects', label: 'Dự án', icon: 'projects' },
  { id: 'finance', label: 'Tài chính', icon: 'tools' },
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
  const boundary = headerHeight + bar.value.offsetHeight + 64
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
  <div ref="bar" class="home-section-nav sticky top-[var(--sp-header-height)] z-40 bg-brand-cream/95 text-brand-navy backdrop-blur-xl" :class="{ 'shadow-lg shadow-[#142B4F]/5': pinned }" :data-pinned="pinned">
    <div class="sp-container flex h-[var(--sp-section-nav-height)] items-center gap-3">
      <nav ref="list" aria-label="Điều hướng các mục trang chủ" class="mx-auto min-w-0 max-w-[1040px] flex-1 overflow-x-auto overscroll-x-contain">
        <div class="mx-auto flex w-max items-center gap-1 p-1.5">
          <a v-for="section in sections" :key="section.id" :href="'#' + section.id" :aria-current="active === section.id ? 'location' : undefined" class="inline-flex min-h-10 items-center gap-2 whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B3915F] sm:text-[13px]" :class="active === section.id ? 'bg-[#142B4F] text-white shadow-sm' : 'text-[#536178] hover:bg-[#EAE5DC] hover:text-[#142B4F]'" @click.prevent="navigate(section.id)"><AppIcon :name="section.icon" class="!size-4"/><span>{{ section.label }}</span></a>
        </div>
      </nav>
    </div>
  </div>
</template>

<style scoped>
.home-section-nav{padding-block:8px}.home-section-nav nav{border:1px solid #e7e1d7;border-radius:999px;background:rgba(255,255,255,.9);box-shadow:0 3px 14px #10233f05;scrollbar-width:thin;scrollbar-color:#d8c6a8 transparent}.home-section-nav a{line-height:1.4}
@media (prefers-reduced-motion: reduce) { .home-section-nav a { transition: none; } }
</style>
