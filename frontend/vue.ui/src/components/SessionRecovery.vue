<script setup>
import {ref} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import {initializeAuth,session} from '../services/api.js'
const router=useRouter(),route=useRoute(),busy=ref(false)
async function retry(){if(busy.value)return;busy.value=true;try{await initializeAuth({force:true});if(session.status!=='UNAVAILABLE'){
 const target=typeof route.query.returnTo==='string'&&route.query.returnTo.startsWith('/')&&!route.query.returnTo.startsWith('//')?route.query.returnTo:route.path==='/session-recovery'?'/home':route.fullPath
 await router.replace(target)
}}finally{busy.value=false}}
</script>
<template><main class="grid min-h-screen place-items-center bg-brand-cream p-6 text-brand-navy"><section class="w-full max-w-lg rounded-panel border border-brand-line bg-white p-7"><h1 class="text-2xl font-semibold">Chưa thể kiểm tra phiên đăng nhập</h1><p class="mt-4 text-sm leading-6">Kết nối đang gián đoạn. Bạn có thể thử lại khi máy chủ hoặc mạng hoạt động trở lại.</p><p v-if="session.error" role="alert" class="mt-3 text-sm leading-6 text-brand-muted">{{session.error}}</p><button class="sp-button sp-button-primary mt-5" :disabled="busy" @click="retry">{{busy?'Đang kiểm tra…':'Thử lại kết nối'}}</button></section></main></template>
