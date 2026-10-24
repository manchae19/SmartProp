<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api, loadProfile, logout as revokeSession, clearSession, session, errorText } from '../../src/services/api'
const router = useRouter()
const fullName = ref(''), phone = ref(''), email = ref(''), district = ref(''), address = ref('')
const currentPassword = ref(''), newPassword = ref(''), confirmPassword = ref('')
const notification1 = ref(false), notification2 = ref(false), notification3 = ref(false)
const busy = ref(true), loaded = ref(false), message = ref('')
const roleLabel = computed(() => ({ BUYER: 'Người mua / người thuê', BROKER: 'Chủ nhà / môi giới', ADMIN: 'Quản trị viên' })[session.user?.role] || '')
const initials = computed(() => fullName.value.split(' ').filter(Boolean).map(v => v[0]).slice(-2).join(''))
function fill(user) {
  fullName.value = user.fullName; email.value = user.email
  phone.value = user.phone || ''; district.value = user.district || ''; address.value = user.address || ''
}
onMounted(async () => {
  try { fill(await loadProfile()); const prefs=await api('/users/me/notification-preferences'); notification1.value=prefs.matchingListings; notification2.value=prefs.brokerMessages; notification3.value=prefs.statusUpdates; loaded.value = true }
  catch (error) { message.value = errorText(error) }
  finally { busy.value = false }
})
const saveProfile = async () => {
  if (busy.value || !loaded.value) return
  busy.value = true; message.value = ''
  try {
    const user = await api('/users/me', { method: 'PATCH', body: { fullName: fullName.value, phone: phone.value, district: district.value, address: address.value } })
    session.user = user; fill(user); await api('/users/me/notification-preferences', {method:'PATCH',body:{matchingListings:notification1.value,brokerMessages:notification2.value,statusUpdates:notification3.value}}); message.value = 'Đã lưu hồ sơ và tùy chọn thông báo.'
  } catch (error) { message.value = errorText(error) }
  finally { busy.value = false }
}
const savePreferences=async()=>{if(busy.value||!loaded.value)return;busy.value=true;message.value='';try{await api('/users/me/notification-preferences',{method:'PATCH',body:{matchingListings:notification1.value,brokerMessages:notification2.value,statusUpdates:notification3.value}});message.value='Đã lưu tùy chọn thông báo.'}catch(e){message.value=errorText(e)}finally{busy.value=false}}
const changePassword = async () => {
  if (busy.value || !loaded.value) return
  if (newPassword.value !== confirmPassword.value) { message.value = 'Mật khẩu xác nhận không khớp.'; return }
  busy.value = true; message.value = ''
  try {
    await api('/users/me/password', { method: 'PUT', body: { currentPassword: currentPassword.value, newPassword: newPassword.value } })
    currentPassword.value = newPassword.value = confirmPassword.value = ''
    clearSession(); await router.replace({ path: '/login', query: { reason: 'password-changed' } })
  } catch (error) { message.value = errorText(error) }
  finally { busy.value = false }
}
const logout = async () => {
  if (busy.value) return
  busy.value = true
  try { await revokeSession(); await router.replace('/login') }
  catch (error) { message.value = errorText(error) }
  finally { busy.value = false }
}
const resetProfile = () => { if (session.user) fill(session.user) }
</script>

<template>
  <div class="min-h-screen bg-[#e9e7e1] text-[#1E325A]">

    <!-- ==================== HEADER ==================== -->
    <header class="max-w-[1400px] mx-auto px-8 pt-5">
      <div
        class="h-[70px] border-b border-[#1E325A] flex items-center justify-between"
      >
        <!-- LEFT -->
        <div class="flex items-center gap-8">
          <button
            @click="router.push('/home')"
            class="flex items-center gap-3"
          >
            <div
              class="w-8 h-8 rounded-lg bg-[#1E325A] text-white flex items-center justify-center font-bold text-sm"
            >
              S
            </div>

            <span class="font-semibold">
              SmartProp
            </span>
          </button>

          <span class="text-gray-300">
            •
          </span>

          <button
            @click="router.push('/home')"
            class="text-xs text-gray-500 hover:text-[#1E325A] transition"
          >
            &lt; Trang chủ
          </button>
        </div>

        <!-- RIGHT -->
        <div class="flex items-center gap-3">
          <button
            @click="router.push('/post')"
            class="px-5 py-2 bg-white border border-gray-200 rounded-full text-xs text-gray-500 hover:bg-gray-50"
          >
            Đăng tin
          </button>

          <button
            :disabled="busy" @click="logout"
            class="px-5 py-2 bg-[#1E325A] text-white rounded-full text-xs hover:bg-[#263f70] transition"
          >
            Đăng xuất
          </button>
        </div>
      </div>
    </header>

    <!-- ==================== PAGE ==================== -->
    <main class="max-w-[1400px] mx-auto px-8 pt-7 pb-16">

      <p v-if="message" role="status" aria-live="polite">{{ message }}</p><p v-if="busy">Đang xử lý…</p><!-- TITLE -->
      <div class="mb-5">
        <h1 class="text-2xl font-medium">
          Hồ sơ cá nhân
        </h1>

        <p class="text-xs text-gray-400 mt-1">
          Quản lý thông tin tài khoản, bảo mật đăng nhập và tùy chọn thông báo.
        </p>
      </div>

      <!-- ==================== MAIN GRID ==================== -->
      <div
        class="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-5 items-start"
      >

        <!-- ================================================= -->
        <!-- LEFT -->
        <!-- ================================================= -->
        <aside class="space-y-4">

          <!-- PROFILE CARD -->
          <section
            class="bg-[#1E325A] text-white rounded-[25px] p-6"
          >
            <!-- Avatar -->
            <div
              class="w-14 h-14 rounded-full bg-white/15 flex items-center justify-center text-xl mb-4"
            >
              {{ initials }}
            </div>

            <h2 class="text-lg font-medium">
              {{ fullName }}
            </h2>

            <p class="text-[11px] text-white/60 mt-1">
              {{ email }}
            </p>

            <div
              class="inline-flex mt-3 bg-emerald-400/20 text-emerald-200 px-3 py-1 rounded-full text-[10px]"
            >
              {{ roleLabel }}
            </div>

            <div class="border-t border-white/10 mt-5 pt-5">
              <p class="text-[10px] text-white/50">
                Thành viên từ {{ session.user ? new Date(session.user.createdAt).toLocaleDateString("vi-VN") : "" }}
              </p>

              <p class="text-[10px] text-white/50 mt-2">
                Trạng thái: {{ session.user?.status }}
              </p>
            </div>
          </section>

          <!-- ==================== STATS ==================== -->
          <section
            class="bg-white/90 rounded-[22px] p-4 grid grid-cols-3 shadow-sm"
          >

            <!-- TIN ĐÃ ĐĂNG -->
            <RouterLink
              to="/my-listing"
              class="group min-w-0 h-[90px] flex flex-col items-center justify-center rounded-xl cursor-pointer transition-all duration-200 hover:bg-[#1E325A]/10"
            >
              <div
                class="text-lg font-medium text-[#1E325A]"
              >
                2
              </div>

              <div
                class="text-[9px] text-gray-400 mt-1 text-center leading-4 group-hover:text-[#1E325A] transition-colors duration-200"
              >
                Tin đã đăng
              </div>
            </RouterLink>

            <!-- YÊU THÍCH -->
            <RouterLink
              to="/favorites"
              class="group min-w-0 h-[90px] flex flex-col items-center justify-center rounded-xl cursor-pointer transition-all duration-200 hover:bg-[#1E325A]/10"
            >
              <div
                class="text-lg font-medium text-[#1E325A]"
              >
                8
              </div>

              <div
                class="text-[9px] text-gray-400 mt-1 text-center leading-4 group-hover:text-[#1E325A] transition-colors duration-200"
              >
                Yêu thích
              </div>
            </RouterLink>

            <!-- LƯỢT XEM HỒ SƠ -->
            <div
              class="min-w-0 h-[90px] flex flex-col items-center justify-center rounded-xl"
            >
              <div
                class="text-lg font-medium text-[#1E325A]"
              >
                14
              </div>

              <div
                class="text-[9px] text-gray-400 mt-1 text-center leading-4"
              >
                Lượt xem hồ sơ
              </div>
            </div>

          </section>

          <!-- ==================== MY REPORTS ==================== -->
          <RouterLink
            to="/account/reports"
            class="group bg-white/90 rounded-[22px] p-5 shadow-sm flex items-center justify-between transition-all duration-200 hover:bg-white hover:shadow-md"
          >
            <div class="flex items-center gap-3">

              <!-- ICON -->
              <div
                class="w-10 h-10 shrink-0 rounded-full bg-[#1E325A]/10 flex items-center justify-center text-[#1E325A]"
              >
                <span class="text-lg">
                  ⚑
                </span>
              </div>

              <!-- TEXT -->
              <div>
                <h3
                  class="text-xs font-medium text-[#1E325A]"
                >
                  Báo cáo của tôi
                </h3>

                <p
                  class="text-[9px] text-gray-400 mt-1"
                >
                  Xem trạng thái các báo cáo đã gửi
                </p>
              </div>
            </div>

            <!-- ARROW -->
            <span
              class="text-[#1E325A] text-lg transition-transform duration-200 group-hover:translate-x-1"
            >
              →
            </span>
          </RouterLink>

          <!-- ==================== AGENT ==================== -->
          <section
            class="bg-[#eadfd2] border border-[#d9c3ad] rounded-[22px] p-6"
          >
            <h3
              class="text-sm font-medium text-[#9c4e2e]"
            >
              Bạn là môi giới hoặc chủ nhà?
            </h3>

            <p
              class="text-[10px] text-[#a7745d] mt-3 leading-relaxed"
            >
              Nâng cấp lên tài khoản Môi giới để đăng tin, quản lý danh sách
              bất động sản và nhận thêm công cụ hỗ trợ.
            </p>

            <button disabled title="Chức năng nâng cấp chưa hỗ trợ ở mốc 1" class="mt-7 bg-[#c9683c] hover:bg-[#b95b32] text-white rounded-full px-5 py-2.5 text-[10px] transition"
            >
              Đăng ký tài khoản môi giới
            </button>
          </section>

        </aside>

        <!-- ================================================= -->
        <!-- RIGHT -->
        <!-- ================================================= -->
        <div class="space-y-5">

          <!-- ==================== PERSONAL INFORMATION ==================== -->
          <section
            class="bg-white/90 rounded-[25px] p-7 shadow-sm"
          >
            <h2 class="font-semibold text-sm">
              Thông tin cá nhân
            </h2>

            <p
              class="text-[10px] text-gray-400 mt-1 mb-5"
            >
              Thông tin này hiển thị với môi giới khi bạn nhắn tin hoặc yêu cầu
              liên hệ.
            </p>

            <div
              class="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-4"
            >

              <!-- NAME -->
              <div>
                <label
                  class="text-[10px] text-gray-500"
                >
                  Họ và tên
                </label>

                <input
                  v-model="fullName"
                  type="text"
                  class="mt-1 w-full h-10 border border-gray-200 rounded-xl px-4 text-xs outline-none focus:border-[#1E325A]"
                />
              </div>

              <!-- PHONE -->
              <div>
                <label
                  class="text-[10px] text-gray-500"
                >
                  Số điện thoại
                </label>

                <input
                  v-model="phone"
                  type="text"
                  class="mt-1 w-full h-10 border border-gray-200 rounded-xl px-4 text-xs outline-none focus:border-[#1E325A]"
                />
              </div>

              <!-- EMAIL -->
              <div>
                <label
                  class="text-[10px] text-gray-500"
                >
                  Email
                </label>

                <input
                  v-model="email" readonly
                  type="email"
                  class="mt-1 w-full h-10 border border-gray-200 rounded-xl px-4 text-xs outline-none focus:border-[#1E325A]"
                />
              </div>

              <!-- DISTRICT -->
              <div>
                <label
                  class="text-[10px] text-gray-500"
                >
                  Khu vực quan tâm
                </label>

                <input
                  v-model="district"
                  type="text"
                  class="mt-1 w-full h-10 border border-gray-200 rounded-xl px-4 text-xs outline-none focus:border-[#1E325A]"
                />
              </div>

              <!-- ADDRESS -->
              <div class="md:col-span-2">
                <label
                  class="text-[10px] text-gray-500"
                >
                  Địa chỉ liên hệ
                </label>

                <input
                  v-model="address"
                  type="text"
                  placeholder="Chưa cập nhật"
                  class="mt-1 w-full h-10 border border-gray-200 rounded-xl px-4 text-xs outline-none focus:border-[#1E325A]"
                />
              </div>

            </div>

            <!-- BUTTONS -->
            <div class="flex gap-3 mt-5">

              <button
                :disabled="busy || !loaded" @click="saveProfile"
                class="bg-[#1E325A] text-white rounded-full px-6 py-2.5 text-[11px] hover:bg-[#263f70] transition"
              >
                Lưu thay đổi
              </button>

              <button @click="resetProfile"
                class="bg-white border border-gray-200 text-gray-500 rounded-full px-5 py-2.5 text-[11px]"
              >
                Hủy
              </button>

            </div>
          </section>

          <!-- ==================== SECURITY ==================== -->
          <section
            class="bg-white/90 rounded-[25px] p-7 shadow-sm"
          >
            <h2 class="font-semibold text-sm">
              Bảo mật
            </h2>

            <p
              class="text-[10px] text-gray-400 mt-1 mb-5"
            >
              Đổi mật khẩu định kỳ để bảo vệ tài khoản của bạn.
            </p>

            <!-- CURRENT PASSWORD -->
            <div>
              <label
                class="text-[10px] text-gray-500"
              >
                Mật khẩu hiện tại
              </label>

              <input
                v-model="currentPassword"
                type="password"
                placeholder="••••••••"
                class="mt-1 w-full h-10 border border-gray-200 rounded-xl px-4 text-xs outline-none focus:border-[#1E325A]"
              />
            </div>

            <!-- NEW PASSWORD -->
            <div
              class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4"
            >

              <div>
                <label
                  class="text-[10px] text-gray-500"
                >
                  Mật khẩu mới
                </label>

                <input
                  v-model="newPassword"
                  type="password"
                  placeholder="••••••••"
                  class="mt-1 w-full h-10 border border-gray-200 rounded-xl px-4 text-xs outline-none focus:border-[#1E325A]"
                />
              </div>

              <!-- CONFIRM PASSWORD -->
              <div>
                <label
                  class="text-[10px] text-gray-500"
                >
                  Xác nhận mật khẩu mới
                </label>

                <input
                  v-model="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  class="mt-1 w-full h-10 border border-gray-200 rounded-xl px-4 text-xs outline-none focus:border-[#1E325A]"
                />
              </div>

            </div>

            <button
              :disabled="busy || !loaded" @click="changePassword"
              class="mt-5 bg-[#1E325A] text-white rounded-full px-6 py-2.5 text-[11px] hover:bg-[#263f70] transition"
            >
              Đổi mật khẩu
            </button>
          </section>

          <!-- ==================== NOTIFICATIONS ==================== -->
          <section
            class="bg-white/90 rounded-[25px] p-7 shadow-sm"
          >
            <h2 class="font-semibold text-sm">
              Thông báo
            </h2>

            <p
              class="text-[10px] text-gray-400 mt-1 mb-5"
            >
              Tùy chọn thông báo chưa được hỗ trợ ở mốc 1.
            </p>

            <!-- NOTIFICATION 1 -->
            <div
              class="flex items-center justify-between py-4 border-b border-[#1E325A]/30"
            >
              <div>
                <h3
                  class="text-xs font-medium"
                >
                  Tin đăng mới phù hợp
                </h3>

                <p
                  class="text-[9px] text-gray-400 mt-1"
                >
                  Lưu tùy chọn nhận tin phù hợp. Gửi email sẽ được bổ sung sau.
                </p>
              </div>

              <button :disabled="busy || !loaded" role="switch" :aria-checked="notification1" aria-label="Tùy chọn thông báo 1" @click="notification1 = !notification1"
                :class="[
                  'relative w-9 h-5 rounded-full transition',
                  notification1
                    ? 'bg-emerald-500'
                    : 'bg-gray-300'
                ]"
              >
                <span
                  :class="[
                    'absolute top-[2px] w-4 h-4 bg-white rounded-full transition-all',
                    notification1
                      ? 'left-[18px]'
                      : 'left-[2px]'
                  ]"
                ></span>
              </button>
            </div>

            <!-- NOTIFICATION 2 -->
            <div
              class="flex items-center justify-between py-4 border-b border-[#1E325A]/30"
            >
              <div>
                <h3
                  class="text-xs font-medium"
                >
                  Tin nhắn từ môi giới
                </h3>

                <p
                  class="text-[9px] text-gray-400 mt-1"
                >
                  Lưu tùy chọn liên hệ. Nhắn tin sẽ được bổ sung sau.
                </p>
              </div>

              <button :disabled="busy || !loaded" role="switch" :aria-checked="notification2" aria-label="Tùy chọn thông báo 2" @click="notification2 = !notification2"
                :class="[
                  'relative w-9 h-5 rounded-full transition',
                  notification2
                    ? 'bg-emerald-500'
                    : 'bg-gray-300'
                ]"
              >
                <span
                  :class="[
                    'absolute top-[2px] w-4 h-4 bg-white rounded-full transition-all',
                    notification2
                      ? 'left-[18px]'
                      : 'left-[2px]'
                  ]"
                ></span>
              </button>
            </div>

            <!-- NOTIFICATION 3 -->
            <div
              class="flex items-center justify-between pt-4"
            >
              <div>
                <h3
                  class="text-xs font-medium"
                >
                  Trạng thái tin đăng & báo cáo
                </h3>

                <p
                  class="text-[9px] text-gray-400 mt-1"
                >
                  Cập nhật khi tin đăng hoặc báo cáo của bạn được xử lý.
                </p>
              </div>

              <button :disabled="busy || !loaded" role="switch" :aria-checked="notification3" aria-label="Tùy chọn thông báo 3" @click="notification3 = !notification3"
                :class="[
                  'relative w-9 h-5 rounded-full transition',
                  notification3
                    ? 'bg-emerald-500'
                    : 'bg-gray-300'
                ]"
              >
                <span
                  :class="[
                    'absolute top-[2px] w-4 h-4 bg-white rounded-full transition-all',
                    notification3
                      ? 'left-[18px]'
                      : 'left-[2px]'
                  ]"
                ></span>
              </button>
            </div>

          <button :disabled="busy || !loaded" @click="savePreferences" class="mt-5 bg-[#1E325A] text-white rounded-full px-6 py-2.5 text-xs">Lưu tùy chọn thông báo</button>
</section>

        </div>
      </div>
    </main>
  </div>
</template>
