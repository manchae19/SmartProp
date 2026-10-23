<template>
  <main class="min-h-screen bg-[#efede8] p-5">
    <section
      class="relative mx-auto h-[920px] w-full max-w-[1560px] overflow-hidden rounded-[44px] bg-[#dcd9d2]"
    >
      <img
        src="/rectangle0.png"
        alt=""
        class="absolute inset-0 h-full w-full object-cover"
      />

      <div
        class="absolute inset-0 bg-[linear-gradient(70.11deg,rgba(8,16,34,0.74)_0%,rgba(8,16,34,0.5)_44%,rgba(239,237,232,0.95)_100%)]"
      ></div>

      <div class="relative flex h-full w-full flex-col overflow-hidden lg:flex-row">
        <!-- Left content -->
        <div
          class="flex w-full shrink-0 flex-col justify-between overflow-hidden p-8 sm:p-10 lg:w-[55%] lg:p-10 xl:w-[858px] xl:px-12"
        >
          <div class="flex items-center gap-2.5">
            <div
              class="flex h-[26px] w-[26px] items-center justify-center overflow-hidden rounded-lg bg-white/90"
            >
              <span class="font-sans text-[14px] font-semibold text-[#1e325a]">
                S
              </span>
            </div>

            <div class="font-sans text-[18px] font-medium tracking-[-0.3px] text-white">
              SmartProp
            </div>
          </div>

          <div class="flex flex-col items-start overflow-hidden">
            <h1
              class="w-full max-w-[560px] font-sans text-4xl font-normal leading-tight tracking-[-1.4px] text-white sm:text-[46px]"
            >
              Ba vai trò, ba quyền hạn
            </h1>

            <div class="h-4"></div>

            <p
              class="w-full max-w-[600px] font-sans text-[18px] font-normal leading-relaxed text-white"
            >
              Phân quyền được áp dụng ngay sau khi xác thực. Mỗi vai trò chỉ thấy
              phần chức năng thuộc quyền của mình.
            </p>

            <div class="h-[30px]"></div>

            <div class="flex w-full max-w-[400px] flex-col gap-2.5 overflow-hidden">
              <RoleCard
                number="01"
                title="Người mua / người thuê"
                description="Tìm kiếm, lưu tin, xem định giá và phân tích ảnh."
              />
              <RoleCard
                number="02"
                title="Chủ nhà / môi giới"
                description="Tạo tin, tải nhiều ảnh, theo dõi trạng thái duyệt."
              />
              <RoleCard
                number="03"
                title="Quản trị viên"
                description="Quản lý người dùng, tin đăng và case bị cảnh báo."
              />
            </div>
          </div>

          <div
            class="font-mono text-[12px] font-normal tracking-[0.5px] text-white/65"
          >
            ĐÀ NẴNG · C2SE.01
          </div>
        </div>

        <!-- Right auth -->
        <div
          class="flex w-full flex-1 items-center justify-center overflow-hidden p-5 lg:w-[45%] lg:p-0"
        >
          <div
            class="w-full max-w-[396px] overflow-hidden rounded-[32px] border border-white/55 bg-white/62 p-[30px] backdrop-blur-[12px]"
          >
            <div class="flex w-full gap-1 overflow-hidden rounded-full bg-[#1e325a]/7 p-1">
              <button
                type="button"
                class="flex flex-1 items-center justify-center rounded-full bg-white py-[9px] shadow-[0_2px_8px_-3px_rgba(30,50,90,0.3)]"
                @click="activeTab = 'login'"
              >
                <span class="font-sans text-[14.5px] font-medium text-[#1e325a]/95">
                  Đăng nhập
                </span>
              </button>

              <button
                type="button"
                class="flex flex-1 items-center justify-center rounded-full py-[9px]"
                @click="activeTab = 'signup'"
              >
                <span class="font-sans text-[14.5px] font-normal text-[#1e325a]/60">
                  Đăng ký
                </span>
              </button>
            </div>

            <div class="flex flex-col gap-1.5 overflow-hidden pt-6">
              <h2
                class="font-sans text-[24px] font-normal leading-tight tracking-[-0.5px] text-[#1e325a]/95"
              >
                {{ activeTab === 'login' ? 'Chào bạn trở lại' : 'Tạo tài khoản' }}
              </h2>

              <p
                class="w-full max-w-[336px] font-sans text-[14.5px] font-normal leading-relaxed text-[#1e325a]/60"
              >
                {{
                  activeTab === 'login'
                    ? 'Đăng nhập để xem lại tin yêu thích và kết quả đánh giá đã lưu.'
                    : 'Đăng ký để bắt đầu sử dụng SmartProp.'
                }}
              </p>
            </div>

            <form class="flex flex-col gap-3.5 overflow-hidden pt-6" @submit.prevent="handleSubmit">
              <label class="flex flex-col gap-1.5 overflow-hidden">
                <span class="font-sans text-[13.5px] font-medium text-[#1e325a]/75">
                  Email
                </span>

                <input
                  v-model="email"
                  type="email"
                  placeholder="ban@email.com"
                  autocomplete="email"
                  class="w-full rounded-xl border border-[#1e325a]/14 bg-white/75 px-3.5 py-3 font-sans text-sm font-normal text-[#1e325a] outline-none placeholder:text-[#1e325a]/40 focus:border-[#1e325a]/40"
                />
              </label>

              <label class="flex flex-col gap-1.5 overflow-hidden">
                <span class="font-sans text-[13.5px] font-medium text-[#1e325a]/75">
                  Mật khẩu
                </span>

                <input
                  v-model="password"
                  type="password"
                  placeholder="Tối thiểu 8 ký tự"
                  :autocomplete="activeTab === 'login' ? 'current-password' : 'new-password'"
                  class="w-full rounded-xl border border-[#1e325a]/14 bg-white/75 px-3.5 py-3 font-sans text-sm font-normal text-[#1e325a] outline-none placeholder:text-[#1e325a]/40 focus:border-[#1e325a]/40"
                />
              </label>

              <button
                type="submit"
                class="flex w-full items-center justify-center gap-[9px] rounded-full bg-[#1e325a]/90 py-[13px] font-sans text-[15.5px] font-normal text-white transition hover:bg-[#1e325a] active:scale-[0.99]"
              >
                <span>{{ activeTab === 'login' ? 'Đăng nhập' : 'Đăng ký' }}</span>
                <span class="text-[14px]">↗</span>
              </button>

              <p
                class="w-full max-w-[336px] font-sans text-[12.5px] font-normal leading-relaxed text-[#1e325a]/50"
              >
                Mật khẩu được băm, phiên làm việc dùng JWT, kết nối qua TLS.
              </p>

              <button
                type="button"
                class="w-full max-w-[336px] text-center font-sans text-xs font-normal text-[#1e325a]/55 hover:text-[#1e325a]/80"
                @click="handleAdminLogin"
              >
                Đăng nhập quản trị
              </button>
            </form>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import RoleCard from '../components/RoleCard.vue'

const activeTab = ref('login')
const email = ref('')
const password = ref('')

function handleSubmit() {
  // TODO: connect to backend authentication API.
  console.log({
    mode: activeTab.value,
    email: email.value,
    password: password.value,
  })
}

function handleAdminLogin() {
  // TODO: navigate to the admin login flow.
  console.log('Admin login')
}
</script>
