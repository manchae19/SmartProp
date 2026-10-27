<script setup>
import {session} from './services/api.js'
import SessionRecovery from './components/SessionRecovery.vue'
import PageLayout from './components/layout/PageLayout.vue'
import ComparisonTray from './components/ComparisonTray.vue'
import { usesPageLayout } from './services/siteNavigation.js'
</script>
<template>
  <div v-if="session.status==='INITIALIZING'" role="status" class="grid min-h-screen place-items-center bg-brand-cream text-brand-navy">Đang khôi phục phiên đăng nhập…</div>
  <SessionRecovery v-else-if="session.status==='UNAVAILABLE'" />
  <RouterView v-else v-slot="{ Component, route }">
    <PageLayout v-if="usesPageLayout(route.path)"><component :is="Component" :key="['/verify-email', '/reset-password'].includes(route.path) ? route.path : undefined" /></PageLayout>
    <component :is="Component" v-else :key="['/verify-email', '/reset-password'].includes(route.path) ? route.path : undefined" />
  </RouterView>
  <ComparisonTray />
</template>
