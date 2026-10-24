<script setup>
import {session} from './services/api.js'
import NotificationBadge from './components/NotificationBadge.vue'
</script>

<template>
  <div id="app">
    <!-- Component này sẽ tự động hiển thị LoginView hoặc DashboardView tùy theo đường dẫn URL -->
    <nav v-if="session.token" aria-label="Tiện ích tài khoản" class="flex flex-wrap justify-end gap-4 bg-[#142B4F] px-5 py-2 text-xs text-white"><NotificationBadge/><RouterLink to="/account/messages">Tin nhắn</RouterLink><RouterLink to="/account/sessions">Phiên đăng nhập</RouterLink><RouterLink to="/account/verify-email">Xác minh email</RouterLink></nav>
    <router-view v-slot="{Component,route}"><component :is="Component" :key="['/verify-email','/reset-password'].includes(route.path)?route.path:undefined"/></router-view>
  </div>
</template>

<style>
body {
  margin: 0;
  padding: 0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
</style>