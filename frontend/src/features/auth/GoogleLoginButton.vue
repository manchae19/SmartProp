<script setup>
import {onMounted,ref} from 'vue'
import {api,refreshEnabled} from './api.js'
defineProps({disabled:Boolean})
const ready=ref(false),loading=ref(true),starting=ref(false)
const base=(import.meta.env?.VITE_API_BASE_URL||'/api/v1').replace(/\/$/,'')
async function load(){loading.value=true;try{const config=await api('/auth/google/config',{authenticated:false});ready.value=refreshEnabled&&config.available===true&&config.authorizationPath==='/auth/oauth2/authorize/google'}catch{ready.value=false}finally{loading.value=false}}
function start(){if(!ready.value||starting.value)return;starting.value=true;window.location.assign(base+'/auth/oauth2/authorize/google')}
onMounted(load)
</script>

<template>
  <div class="w-full mt-5">
    <div class="relative flex items-center justify-center my-4">
      <div class="absolute inset-0 flex items-center">
        <div class="w-full border-t border-slate-200"></div>
      </div>
      <span class="relative bg-white px-3 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
        Hoặc tiếp tục với
      </span>
    </div>

    <button
      type="button"
      class="w-full min-h-[46px] py-2.5 px-4 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 hover:border-[#b3915f]/60 text-[#10233f] font-bold text-xs flex items-center justify-center gap-3 transition-all duration-150 active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed shadow-2xs cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#b3915f]"
      :disabled="disabled || loading || !ready || starting"
      @click="start"
    >
      <svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
        <path fill="#4285F4" d="M21.6 12.23c0-.71-.06-1.39-.18-2.05H12v3.88h5.38a4.6 4.6 0 0 1-2 3.02v2.51h3.24c1.9-1.75 2.98-4.33 2.98-7.36Z"/>
        <path fill="#34A853" d="M12 22c2.7 0 4.96-.9 6.62-2.41l-3.24-2.51c-.9.6-2.05.96-3.38.96-2.6 0-4.81-1.76-5.6-4.12H3.05v2.59A10 10 0 0 0 12 22Z"/>
        <path fill="#FBBC05" d="M6.4 13.92a6 6 0 0 1 0-3.84V7.49H3.05a10 10 0 0 0 0 9.02l3.35-2.59Z"/>
        <path fill="#EA4335" d="M12 5.96c1.47 0 2.79.51 3.83 1.51l2.87-2.87A9.6 9.6 0 0 0 12 2a10 10 0 0 0-8.95 5.49l3.35 2.59C7.19 7.72 9.4 5.96 12 5.96Z"/>
      </svg>
      <span>{{ starting ? 'Đang kết nối Google…' : 'Tiếp tục với Google' }}</span>
    </button>

    <p v-if="loading" class="text-[11px] text-slate-400 text-center mt-2" role="status">
      Đang kiểm tra phương thức đăng nhập…
    </p>
    <p v-else-if="!ready" class="text-[11px] text-slate-400 text-center mt-2">
      Đăng nhập nhanh an toàn bằng tài khoản SmartProp
    </p>
  </div>
</template>
