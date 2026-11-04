<script setup>
import {computed,ref,watch,onMounted} from 'vue'
import {useRouter,useRoute} from 'vue-router'
import {api,login,register,errorText} from '../services/api.js'
import {safeLoginDestination} from '../services/authNavigation.js'
import GoogleLoginButton from './GoogleLoginButton.vue'

const props=defineProps({initialRegister:Boolean}),router=useRouter(),route=useRoute()
const isRegister=computed(()=>props.initialRegister||route.path==='/register'),forgot=ref(false)
const fullName=ref(''),email=ref(''),password=ref(''),confirmPassword=ref(''),showPassword=ref(false),showConfirm=ref(false)
const busy=ref(false),message=ref(''),error=ref(''),video=ref(null),playing=ref(false)
const reasons={'password-changed':'Đổi mật khẩu thành công. Vui lòng đăng nhập bằng mật khẩu mới.','session-expired':'Phiên đã hết hạn hoặc bị thu hồi. Vui lòng đăng nhập lại.','session-unavailable':'Vui lòng đăng nhập lại để tiếp tục.','login-required':'Đăng nhập để sử dụng chức năng này.','google-failed':'Chưa hoàn tất đăng nhập Google. Vui lòng thử lại hoặc đăng nhập bằng email.'}
watch(()=>route.fullPath,()=>{message.value=route.query.registered==='1'?'Tạo tài khoản thành công. Bạn có thể đăng nhập ngay.':reasons[route.query.reason]||'';error.value='';forgot.value=false},{immediate:true})
const heading=computed(()=>forgot.value?'Khôi phục mật khẩu':isRegister.value?'Bắt đầu cùng SmartProp':'Chào mừng bạn trở lại')
function switchTab(path){if(!busy.value)router.push(path)}
async function toggleVideo(){if(!video.value)return;if(playing.value){video.value.pause();playing.value=false}else{try{await video.value.play();playing.value=true}catch{playing.value=false}}}
onMounted(()=>{if(!window.matchMedia('(prefers-reduced-motion: reduce)').matches)toggleVideo()})
async function submit(){
 if(busy.value)return;error.value=message.value=''
 if(!forgot.value&&new TextEncoder().encode(password.value).length>72){error.value='Mật khẩu tối đa 72 byte UTF-8. Vui lòng kiểm tra lại.';return}
 if(isRegister.value&&!forgot.value&&password.value!==confirmPassword.value){error.value='Mật khẩu xác nhận không khớp.';return}
 busy.value=true
 try{
  if(forgot.value){await api('/auth/password/forgot',{method:'POST',body:{email:email.value.trim()},authenticated:false});message.value='Nếu tài khoản đủ điều kiện, liên kết đặt lại mật khẩu sẽ được gửi đến email của bạn.'}
  else if(isRegister.value){await register({fullName:fullName.value.trim(),email:email.value,password:password.value,role:'BUYER'});password.value=confirmPassword.value='';await router.replace({path:'/login',query:{registered:'1'}})}
  else{const user=await login(email.value,password.value,false);password.value='';await router.replace(safeLoginDestination(route.query.next,user.role))}
 }catch(e){error.value=errorText(e)}finally{busy.value=false}
}
</script>

<template>
  <main class="min-h-screen relative isolation-auto bg-[#10233f] flex items-center justify-center p-4 sm:p-6 lg:p-10 font-sans selection:bg-[#b3915f] selection:text-white">
    <!-- CINEMATIC VIDEO BACKGROUND -->
    <video
      ref="video"
      class="absolute inset-0 w-full h-full object-cover z-0 pointer-events-none opacity-50"
      src="/background.mp4"
      poster="/media/home/hero-poster.jpg"
      loop
      muted
      playsinline
      aria-hidden="true"
    />

    <!-- GRADIENT AMBIENT OVERLAY (PRESERVING SMARTPROP'S SIGNATURE NAVY TONE) -->
    <div class="absolute inset-0 bg-gradient-to-tr from-[#07182d]/95 via-[#0c2344]/80 to-[#07182d]/95 z-0 pointer-events-none"></div>

    <!-- MAIN TWO-COLUMN CONTAINER -->
    <div class="relative z-10 w-full max-w-[1200px] mx-auto grid grid-cols-1 lg:grid-cols-[1.1fr_480px] gap-8 lg:gap-14 items-center">

      <!-- ==================== LEFT COLUMN: SMARTPROP BRAND & COPY ==================== -->
      <section class="hidden lg:flex flex-col justify-between min-h-[600px] text-white py-4 pr-6" aria-label="SmartProp">
        <!-- BRAND LOGO -->
        <div>
          <RouterLink to="/home" class="inline-flex items-center gap-3 group">
            <span class="w-11 h-11 rounded-xl bg-white text-[#10233f] font-black text-2xl flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform duration-200">
              S
            </span>
            <span class="text-2xl font-bold tracking-tight text-white block">SmartProp.</span>
          </RouterLink>
        </div>

        <!-- MAIN INTRO COPY -->
        <div class="space-y-5 my-auto max-w-[500px]">
          <p class="text-xs font-semibold tracking-[0.18em] text-[#e7c58e] uppercase">
            ĐÀ NẴNG · SMARTPROP
          </p>

          <h1 class="text-4xl xl:text-5xl font-medium tracking-tight text-white leading-[1.25]">
            Không gian sống.<br/>
            <em class="font-serif not-italic text-[#e7c58e]">Khởi đầu của bạn.</em>
          </h1>

          <p class="text-slate-200 text-sm xl:text-base leading-relaxed">
            Khám phá bất động sản, lưu những lựa chọn yêu thích và tìm hiểu giá trị từ dữ liệu.
          </p>
        </div>

        <!-- VIDEO CONTROL -->
        <div class="pt-4">
          <button
            type="button"
            class="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-white/40 hover:border-white text-xs text-white transition-all cursor-pointer backdrop-blur-sm"
            :aria-pressed="playing"
            @click="toggleVideo"
          >
            <span>{{ playing ? 'Ⅱ' : '▷' }}</span>
            <span>{{ playing ? 'Tạm dừng nền' : 'Phát video nền' }}</span>
          </button>
        </div>
      </section>

      <!-- ==================== RIGHT COLUMN: AUTH CARD (REDESIGNED FORM) ==================== -->
      <section
        class="bg-white/95 backdrop-blur-xl rounded-3xl p-6 sm:p-9 shadow-2xl border border-white/60 relative"
        :aria-busy="busy"
        aria-labelledby="auth-heading"
      >
        <!-- BACK TO HOME SHORTCUT -->
        <div class="mb-5">
          <RouterLink
            to="/home"
            class="inline-flex items-center gap-1.5 text-xs font-semibold text-[#536178] hover:text-[#10233f] transition-all cursor-pointer"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
            <span>Trang chủ SmartProp</span>
          </RouterLink>
        </div>

        <!-- REFINED SEGMENTED TABS (LOGIN VS REGISTER) -->
        <div v-if="!forgot" class="bg-slate-100 p-1.5 rounded-2xl flex border border-slate-200/80 mb-6" role="tablist" aria-label="Đăng nhập hoặc đăng ký">
          <button
            type="button"
            role="tab"
            :aria-selected="!isRegister"
            :disabled="busy"
            class="w-1/2 py-2.5 px-4 rounded-xl text-xs font-bold transition-all duration-150 cursor-pointer text-center"
            :class="!isRegister ? 'bg-white text-[#10233f] shadow-xs' : 'text-slate-500 hover:text-[#10233f]'"
            @click="switchTab('/login')"
          >
            Đăng nhập
          </button>

          <button
            type="button"
            role="tab"
            :aria-selected="isRegister"
            :disabled="busy"
            class="w-1/2 py-2.5 px-4 rounded-xl text-xs font-bold transition-all duration-150 cursor-pointer text-center"
            :class="isRegister ? 'bg-white text-[#10233f] shadow-xs' : 'text-slate-500 hover:text-[#10233f]'"
            @click="switchTab('/register')"
          >
            Đăng ký
          </button>
        </div>

        <!-- BACK TO LOGIN BUTTON (WHEN IN FORGOT PASSWORD MODE) -->
        <button
          v-else
          type="button"
          class="inline-flex items-center gap-1.5 text-xs font-bold text-[#536178] hover:text-[#10233f] transition mb-5 cursor-pointer"
          @click="forgot=false;message=error=''"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
          <span>Quay lại đăng nhập</span>
        </button>

        <!-- FORM TITLE & INTRO -->
        <div class="mb-5">
          <h2 id="auth-heading" class="text-2xl sm:text-3xl font-extrabold text-[#10233f] tracking-tight">
            {{ heading }}
          </h2>
          <p class="text-xs sm:text-sm text-[#536178] mt-1.5 leading-relaxed">
            {{ forgot ? 'Nhập email để nhận liên kết đặt lại mật khẩu.' : isRegister ? 'Một tài khoản cho mọi trải nghiệm của bạn.' : 'Đăng nhập để tiếp tục từ những điều bạn quan tâm.' }}
          </p>
        </div>

        <!-- STATUS & ERROR MESSAGES -->
        <div
          v-if="message"
          role="status"
          class="p-3.5 rounded-xl bg-[#eaf5ee] border border-emerald-200 text-xs font-semibold text-[#1c6347] flex items-center gap-2 mb-4"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="shrink-0 text-[#1c6347]">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <span>{{ message }}</span>
        </div>

        <div
          v-if="error"
          role="alert"
          class="p-3.5 rounded-xl bg-[#fff0eb] border border-rose-200 text-xs font-semibold text-[#8d302d] flex items-center gap-2 mb-4"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="shrink-0 text-[#8d302d]">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <span>{{ error }}</span>
        </div>

        <!-- INFORMATION BOX FOR REGISTER -->
        <div
          v-if="isRegister && !forgot"
          class="p-3.5 rounded-xl bg-[#f0f4f7] border border-[#dce3e9] text-xs text-[#10233f] flex items-start gap-2.5 mb-5"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="shrink-0 text-[#b3915f] mt-0.5">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
          <div>
            <strong class="font-bold">Thông tin tài khoản</strong>
            <p class="text-[11px] text-[#536178] mt-0.5 leading-relaxed">
              Tài khoản mới có quyền người dùng thông thường. Để đăng bán hoặc cho thuê, bạn có thể đăng ký quyền đăng tin trong Hồ sơ cá nhân và chờ quản trị viên xét duyệt.
            </p>
          </div>
        </div>

        <!-- ==================== FORM FIELDS ==================== -->
        <form class="space-y-4" @submit.prevent="submit">
          <!-- FIELD: FULL NAME (REGISTER ONLY) -->
          <div v-if="isRegister && !forgot" class="space-y-1.5">
            <label class="block text-xs font-bold text-[#10233f]" for="name-input">
              Họ và tên
            </label>
            <div class="relative flex items-center">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="absolute left-3.5 text-slate-400 pointer-events-none">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              <input
                id="name-input"
                v-model="fullName"
                type="text"
                autocomplete="name"
                required
                maxlength="100"
                placeholder="Họ và tên của bạn"
                :disabled="busy"
                class="w-full pl-10 pr-4 py-2.5 sm:py-3 rounded-xl border border-slate-200 bg-white text-[#10233f] text-xs sm:text-sm font-normal placeholder:text-slate-400 focus:outline-none focus:border-[#b3915f] focus:ring-4 focus:ring-[#b3915f]/15 transition-all duration-150 disabled:bg-slate-50 shadow-2xs"
              />
            </div>
          </div>

          <!-- FIELD: EMAIL / USERNAME -->
          <div class="space-y-1.5">
            <label class="block text-xs font-bold text-[#10233f]" for="email-input">
              {{ !isRegister && !forgot ? 'Email / tên quản trị' : 'Email' }}
            </label>
            <div class="relative flex items-center">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="absolute left-3.5 text-slate-400 pointer-events-none">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                <polyline points="22,6 12,13 2,6"/>
              </svg>
              <input
                id="email-input"
                v-model="email"
                :type="!isRegister && !forgot ? 'text' : 'email'"
                :autocomplete="!isRegister && !forgot ? 'username' : 'email'"
                maxlength="254"
                required
                :placeholder="!isRegister && !forgot ? 'Email hoặc Admin' : 'ban@email.com'"
                :disabled="busy"
                class="w-full pl-10 pr-4 py-2.5 sm:py-3 rounded-xl border border-slate-200 bg-white text-[#10233f] text-xs sm:text-sm font-normal placeholder:text-slate-400 focus:outline-none focus:border-[#b3915f] focus:ring-4 focus:ring-[#b3915f]/15 transition-all duration-150 disabled:bg-slate-50 shadow-2xs"
              />
            </div>
          </div>

          <!-- FIELD: PASSWORD -->
          <div v-if="!forgot" class="space-y-1.5">
            <div class="flex items-center justify-between">
              <label class="block text-xs font-bold text-[#10233f]" for="password-input">
                Mật khẩu
              </label>
              <button
                v-if="!isRegister && !forgot"
                type="button"
                class="text-xs text-[#536178] hover:text-[#10233f] hover:underline cursor-pointer"
                @click="forgot=true;error=message=''"
              >
                Quên mật khẩu?
              </button>
            </div>

            <div class="relative flex items-center">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="absolute left-3.5 text-slate-400 pointer-events-none">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              <input
                id="password-input"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                :autocomplete="isRegister ? 'new-password' : 'current-password'"
                :minlength="isRegister ? 8 : undefined"
                maxlength="72"
                required
                :placeholder="isRegister ? 'Tối thiểu 8 ký tự' : 'Nhập mật khẩu'"
                :disabled="busy"
                class="w-full pl-10 pr-11 py-2.5 sm:py-3 rounded-xl border border-slate-200 bg-white text-[#10233f] text-xs sm:text-sm font-normal placeholder:text-slate-400 focus:outline-none focus:border-[#b3915f] focus:ring-4 focus:ring-[#b3915f]/15 transition-all duration-150 disabled:bg-slate-50 shadow-2xs"
              />
              <button
                type="button"
                class="absolute right-2.5 p-1.5 text-slate-400 hover:text-[#10233f] transition cursor-pointer"
                :aria-label="showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'"
                @click="showPassword = !showPassword"
              >
                <svg v-if="showPassword" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
                <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              </button>
            </div>
            <p v-if="isRegister" class="text-[11px] text-[#536178]">
              Từ 8 ký tự, tối đa 72 byte UTF-8.
            </p>
          </div>

          <!-- FIELD: CONFIRM PASSWORD (REGISTER ONLY) -->
          <div v-if="isRegister && !forgot" class="space-y-1.5">
            <label class="block text-xs font-bold text-[#10233f]" for="confirm-password-input">
              Xác nhận mật khẩu
            </label>
            <div class="relative flex items-center">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="absolute left-3.5 text-slate-400 pointer-events-none">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              <input
                id="confirm-password-input"
                v-model="confirmPassword"
                :type="showConfirm ? 'text' : 'password'"
                autocomplete="new-password"
                minlength="8"
                maxlength="72"
                required
                placeholder="Nhập lại mật khẩu"
                :disabled="busy"
                class="w-full pl-10 pr-11 py-2.5 sm:py-3 rounded-xl border border-slate-200 bg-white text-[#10233f] text-xs sm:text-sm font-normal placeholder:text-slate-400 focus:outline-none focus:border-[#b3915f] focus:ring-4 focus:ring-[#b3915f]/15 transition-all duration-150 disabled:bg-slate-50 shadow-2xs"
              />
              <button
                type="button"
                class="absolute right-2.5 p-1.5 text-slate-400 hover:text-[#10233f] transition cursor-pointer"
                :aria-label="showConfirm ? 'Ẩn mật khẩu xác nhận' : 'Hiện mật khẩu xác nhận'"
                @click="showConfirm = !showConfirm"
              >
                <svg v-if="showConfirm" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
                <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- PRIMARY SUBMIT BUTTON (SIGNATURE SMARTPROP NAVY) -->
          <button
            type="submit"
            class="w-full min-h-[48px] py-3.5 px-6 rounded-xl bg-[#10233f] hover:bg-[#1f3f6e] active:bg-[#0a1728] text-white font-bold text-sm tracking-wide shadow-md flex items-center justify-center gap-2 transition-all duration-150 active:scale-[0.99] disabled:opacity-60 disabled:cursor-wait cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#b3915f]"
            :disabled="busy"
          >
            <svg v-if="busy" class="animate-spin w-4 h-4 text-white" viewBox="0 0 24 24" fill="none">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>
              {{ busy ? 'Đang xử lý…' : forgot ? 'Gửi liên kết đặt lại' : isRegister ? 'Tạo tài khoản' : 'Đăng nhập' }}
            </span>
          </button>
        </form>

        <!-- GOOGLE LOGIN COMPONENT -->
        <GoogleLoginButton v-if="!forgot" :disabled="busy" />

        <!-- FOOTNOTE -->
        <p class="text-xs text-[#536178] text-center mt-6">
          Tiếp tục khám phá không gian sống cùng SmartProp.
        </p>
      </section>
    </div>
  </main>
</template>
