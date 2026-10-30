<script setup>
import {computed} from 'vue'
import {useRoute} from 'vue-router'
import {normalizeFilters} from '../../services/listingFilters.js'
import {activeNavigation,siteNavigation,scrollHomeSection} from '../../services/siteNavigation.js'
import AppIcon from '../AppIcon.vue'
defineProps({vertical:Boolean})
const emit=defineEmits(['navigate']),route=useRoute()
const items=computed(()=>siteNavigation(normalizeFilters(route.query)))
function navigate(item){if(item.key==='home'&&route.path==='/home')scrollHomeSection('home');emit('navigate')}
</script>
<template><nav :aria-label="vertical?'Điều hướng website trong menu':'Điều hướng website'" :class="vertical?'grid gap-1.5':'flex items-center gap-1'">
 <RouterLink v-for="item in items" :key="item.key" :to="item.to" :aria-current="activeNavigation(item.key,route)?'page':undefined" class="flex min-h-12 items-center gap-3 rounded-xl px-4 py-3 text-[15px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-gold" :class="activeNavigation(item.key,route)?'bg-brand-navy text-white':'text-brand-navy hover:bg-brand-surface'" @click="navigate(item)"><AppIcon :name="item.key==='home'?'home':item.key"/><span>{{item.label}}</span><span v-if="activeNavigation(item.key,route)" class="ml-auto size-1.5 rounded-full bg-current" aria-hidden="true"/></RouterLink>
</nav></template>
