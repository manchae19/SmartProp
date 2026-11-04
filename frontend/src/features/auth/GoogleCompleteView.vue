<script setup>
import {onMounted,ref} from 'vue'
import {useRouter} from 'vue-router'
import {completeGoogleLogin,session,errorText} from './api.js'
const router=useRouter(),error=ref('')
onMounted(async()=>{try{await completeGoogleLogin();await router.replace(session.user?.role==='ADMIN'?'/admin':'/home')}catch(e){error.value=errorText(e)}})
</script>
<template><main class="sp-container py-16"><section class="mx-auto max-w-lg rounded-panel border border-brand-line bg-white p-8"><p class="text-xs font-semibold tracking-widest text-brand-accent">SMARTPROP · GOOGLE</p><h1 class="mt-3 text-2xl font-semibold">Hoàn tất đăng nhập</h1><p v-if="!error" role="status" class="mt-4 text-sm leading-7 text-brand-muted">Đang xác minh tài khoản và khởi tạo phiên của bạn…</p><div v-else role="alert" class="mt-4"><p class="text-sm leading-7 text-red-800">{{error}}</p><RouterLink to="/login" class="sp-button sp-button-primary mt-6">Quay lại đăng nhập</RouterLink></div></section></main></template>
