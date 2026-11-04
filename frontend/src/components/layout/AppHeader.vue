<script setup>
import { computed, nextTick, ref, useId, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { session, logout, errorText } from '../../features/auth/api.js'
import { canPublish, canAccessAdmin, scrollHomeSection } from '../../lib/siteNavigation.js'
import { normalizeFilters, listingLink } from '../../features/property/listingFilters.js'
import { useComparison } from '../../hooks/useComparison.js'
import AppNavigation from './AppNavigation.vue'
import MobileDrawer from './MobileDrawer.vue'
import AccountNavigation from './AccountNavigation.vue'
import UserAvatar from '../UserAvatar.vue'
import AppIcon from '../AppIcon.vue'
const route = useRoute(), router = useRouter(), compare = useComparison()
const open = ref(false), busy = ref(false), error = ref(''), trigger = ref(null)
const drawerId = 'app-navigation-' + useId()
const homeLink = computed(() => listingLink('/home', normalizeFilters(route.query)))
const restoreFocus = ref(true)
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
      <RouterLink :to="homeLink" class="inline-flex shrink-0 items-center gap-2.5 text-xl font-bold tracking-tight focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand-gold" aria-label="SmartProp — Trang chủ" @click="route.path === '/home' && scrollHomeSection('home')"><span class="grid size-9 place-items-center rounded-control bg-brand-navy text-lg text-white">S</span><span>SmartProp<span class="text-brand-accent">.</span><span class="mt-0.5 hidden text-[13px] font-normal tracking-normal text-brand-muted 2xl:block">Không gian sống · Dữ liệu thông minh</span></span></RouterLink>

      <!-- Desktop Navigation Menu -->
      <nav aria-label="Điều hướng chính" class="hidden lg:flex items-center gap-1 xl:gap-2">
        <RouterLink :to="listingLink('/listings', normalizeFilters(route.query))" class="rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold" :class="route.path === '/listings' || route.path.startsWith('/listing/') ? 'bg-brand-navy text-white shadow-sm' : 'text-brand-navy hover:bg-brand-surface'">Bất động sản</RouterLink>
        <RouterLink to="/projects" class="rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold" :class="route.path.startsWith('/projects') ? 'bg-brand-navy text-white shadow-sm' : 'text-brand-navy hover:bg-brand-surface'">Dự án</RouterLink>
        <RouterLink :to="listingLink('/map', normalizeFilters(route.query))" class="rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold" :class="route.path === '/map' ? 'bg-brand-navy text-white shadow-sm' : 'text-brand-navy hover:bg-brand-surface'">Bản đồ GIS</RouterLink>
        <RouterLink to="/market" class="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold" :class="route.path.startsWith('/market') ? 'bg-brand-navy text-white shadow-sm' : 'text-brand-navy hover:bg-brand-surface'" data-market-header>
          <span>Thị trường BĐS</span>
          <span class="rounded-full px-1.5 py-0.5 text-[10px] font-bold border transition-colors" :class="route.path.startsWith('/market') ? 'bg-[#dfbe86] text-[#10233f] border-[#dfbe86]' : 'bg-brand-gold/20 text-amber-900 border-brand-gold/40'">Mới</span>
        </RouterLink>
        <RouterLink to="/valuation" class="rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold" :class="route.path === '/valuation' ? 'bg-brand-navy text-white shadow-sm' : 'text-brand-navy hover:bg-brand-surface'">Định giá</RouterLink>
      </nav>

      <div class="flex shrink-0 items-center gap-2 sm:gap-3">
        <RouterLink to="/advisor" class="sp-button sp-button-secondary hidden lg:inline-flex" :aria-current="route.path === '/advisor' || route.path.startsWith('/advisor/') ? 'page' : undefined" data-advisor-header>Tư vấn BĐS</RouterLink>
        <RouterLink v-if="session.token && canAccessAdmin(session.user)" to="/admin/dashboard" class="sp-button sp-button-secondary gap-2 px-3 sm:px-4" :class="route.path.startsWith('/admin') ? '!bg-brand-navy !text-white' : ''" :aria-current="route.path.startsWith('/admin') ? 'location' : undefined" aria-label="Trang quản trị" data-admin-entry><AppIcon name="shield" class="!size-4"/><span class="hidden sm:inline">Quản trị</span></RouterLink>
        <RouterLink v-if="session.token && canPublish(session.user)" to="/post" class="sp-button hidden border-brand-gold bg-brand-highlight text-brand-navy sm:inline-flex">Đăng tin ↗</RouterLink><RouterLink v-else-if="!session.token" to="/login" class="hidden text-xs font-semibold text-brand-navy sm:block">Đăng nhập</RouterLink><button ref="trigger" type="button" :aria-expanded="open" :aria-controls="drawerId" aria-haspopup="dialog" :aria-label="session.token ? 'Mở menu tài khoản và điều hướng' : 'Mở menu điều hướng'" class="sp-button sp-button-secondary gap-2 px-3" data-app-menu-trigger @click="toggle" @keydown.down.prevent="show"><UserAvatar v-if="session.token" :name="session.user?.fullName" :size="32"/><svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" /></svg><span class="hidden text-sm sm:inline">{{ session.token ? 'Tài khoản' : 'Menu' }}</span></button></div>
    </div>
    <MobileDrawer :id="drawerId" v-model:open="open" @update:open="drawerChanged" @closed="drawerChanged(false)"><div class="mb-5"><p class="mb-2 text-xs font-semibold tracking-[.2em] text-brand-accent">KHÁM PHÁ SMARTPROP</p><AppNavigation vertical @navigate="navigate" /></div><AccountNavigation :busy="busy" :error="error" @navigate="navigate" @logout="signOut" /></MobileDrawer>
  </header>
</template>
