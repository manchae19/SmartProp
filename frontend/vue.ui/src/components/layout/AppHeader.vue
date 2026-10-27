<script setup>
import { computed, nextTick, ref, useId, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { session, logout, errorText } from '../../services/api.js'
import { canPublish, scrollHomeSection } from '../../services/siteNavigation.js'
import { normalizeFilters, listingLink } from '../../services/listingFilters.js'
import { useComparison } from '../../services/useComparison.js'
import AppNavigation from './AppNavigation.vue'
import MobileDrawer from './MobileDrawer.vue'
import AccountNavigation from './AccountNavigation.vue'
const route = useRoute(), router = useRouter(), compare = useComparison()
const open = ref(false), busy = ref(false), error = ref(''), trigger = ref(null)
const drawerId = 'app-navigation-' + useId()
const homeLink = computed(() => listingLink('/home', normalizeFilters(route.query)))
const restoreFocus = ref(true)
const initials = computed(() => (session.user?.fullName || 'Tài khoản').split(/\s+/).filter(Boolean).slice(-2).map(word => word[0]).join('').toUpperCase())
watch(() => route.fullPath, async () => { if (open.value) { restoreFocus.value = false; open.value = false; await nextTick(); document.getElementById('page-content')?.focus({ preventScroll: true }) } })
async function signOut() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try { await logout(); compare.clear(); open.value = false; await router.replace('/login') }
  catch (failure) { error.value = errorText(failure) }
  finally { busy.value = false }
}
function toggle() { error.value = ''; restoreFocus.value = true; open.value = !open.value }
function show() { restoreFocus.value = true; open.value = true }
async function drawerChanged(value) { if (!value && restoreFocus.value) { await nextTick(); trigger.value?.focus({ preventScroll: true }) } }
async function navigate() { restoreFocus.value = false; open.value = false; await nextTick(); document.getElementById('page-content')?.focus({ preventScroll: true }) }
</script>
<template>
  <header class="app-header sticky top-0 z-50 h-[var(--sp-header-height)] border-b border-brand-line bg-brand-cream/95 text-brand-navy backdrop-blur-xl">
    <div class="sp-container flex h-full items-center justify-between gap-4">
      <RouterLink :to="homeLink" class="inline-flex shrink-0 items-center gap-2.5 text-xl font-bold tracking-tight focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand-gold" aria-label="SmartProp — Trang chủ" @click="route.path === '/home' && scrollHomeSection('home')"><span class="grid size-9 place-items-center rounded-control bg-brand-navy text-lg text-white">S</span><span>SmartProp<span class="text-brand-accent">.</span></span></RouterLink>
      <div class="hidden xl:block"><AppNavigation /></div>
      <div class="flex shrink-0 items-center gap-2 sm:gap-3"><RouterLink v-if="session.token && canPublish(session.user)" to="/post" class="sp-button hidden border-brand-gold bg-brand-highlight text-brand-navy sm:inline-flex">Đăng tin ↗</RouterLink><RouterLink v-else-if="!session.token" to="/login" class="hidden text-xs font-semibold text-brand-navy sm:block">Đăng nhập</RouterLink><button ref="trigger" type="button" :aria-expanded="open" :aria-controls="drawerId" aria-haspopup="dialog" :aria-label="session.token ? 'Mở menu tài khoản và điều hướng' : 'Mở menu điều hướng'" class="sp-button sp-button-secondary gap-2 px-3" data-app-menu-trigger @click="toggle" @keydown.down.prevent="show"><span v-if="session.token" class="grid size-6 place-items-center rounded-full bg-brand-navy text-[10px] text-white" aria-hidden="true">{{ initials }}</span><svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" /></svg><span class="hidden text-xs sm:inline">{{ session.token ? 'Tài khoản' : 'Menu' }}</span></button></div>
    </div>
    <MobileDrawer :id="drawerId" v-model:open="open" @update:open="drawerChanged" @closed="drawerChanged(false)"><div class="mb-5"><p class="mb-2 text-[10px] font-semibold tracking-[.2em] text-brand-accent">KHÁM PHÁ SMARTPROP</p><AppNavigation vertical @navigate="navigate" /></div><AccountNavigation :busy="busy" :error="error" @navigate="navigate" @logout="signOut" /></MobileDrawer>
  </header>
</template>
