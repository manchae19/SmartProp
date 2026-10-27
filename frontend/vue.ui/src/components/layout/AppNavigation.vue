<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { normalizeFilters } from '../../services/listingFilters.js'
import { activeNavigation, siteNavigation, scrollHomeSection } from '../../services/siteNavigation.js'
defineProps({ vertical: Boolean })
const emit = defineEmits(['navigate'])
const route = useRoute()
const items = computed(() => siteNavigation(normalizeFilters(route.query)))
function navigate(item) { if (item.key === 'home' && route.path === '/home') scrollHomeSection('home'); emit('navigate') }
</script>
<template>
  <nav :aria-label="vertical ? 'Điều hướng website trong menu' : 'Điều hướng website'" :class="vertical ? 'grid gap-1' : 'flex items-center gap-1'">
    <RouterLink v-for="item in items" :key="item.key" :to="item.to" :aria-current="activeNavigation(item.key, route) ? 'page' : undefined" class="rounded-control px-3 py-3 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-gold" :class="[activeNavigation(item.key, route) ? 'bg-brand-navy text-white' : 'text-brand-muted hover:bg-brand-surface hover:text-brand-navy', vertical ? 'block' : 'whitespace-nowrap text-[13px]']" @click="navigate(item)">{{ item.label }}</RouterLink>
  </nav>
</template>
