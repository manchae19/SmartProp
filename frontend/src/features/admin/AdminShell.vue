<script setup>
import AppShell from '../../components/layout/AppShell.vue'
</script>
<template><AppShell><nav class="sp-row" aria-label="Quản trị"><RouterLink v-for="(label,path) in {dashboard:'Tổng quan',posts:'Tin đăng',users:'Tài khoản',reports:'Báo cáo','audit-logs':'Nhật ký'}" :key="path" class="sp-btn" :to="'/admin/'+path">{{label}}</RouterLink></nav><RouterView /></AppShell></template>