<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// ===== Giấy tờ sở hữu =====
const documentType = ref('Sổ đỏ / Giấy chứng nhận QSDĐ')
const documentNumber = ref('CT 01234567')
const issueDate = ref('12/03/2019')
const ownerName = ref('Nguyễn Văn A')

// ===== Thông tin liên hệ =====
const contactName = ref('Nguyễn Văn A')
const phone = ref('090 123 4567')
const contact = ref('090xxx hoặc email liên hệ')

// Chuyển sang bước 4
function goNext() {
  router.push('/post/step-4')
}
</script>

<template>
  <div class="min-h-screen bg-[#e9e7e1] text-[#1E325A]">

    <!-- ========================================= -->
    <!-- HEADER -->
    <!-- ========================================= -->
    <section class="relative h-[270px] overflow-hidden text-white">

      <!-- Video Background -->
      <video
        autoplay
        muted
        loop
        playsinline
        class="absolute inset-0 w-full h-full object-cover"
      >
        <source src="/background.mp4" type="video/mp4" />
      </video>

      <!-- Overlay -->
      <div class="absolute inset-0 bg-black/45"></div>

      <!-- Navbar -->
      <header
        class="relative z-10 max-w-[1280px] mx-auto px-6 pt-7
               flex items-center justify-between"
      >
        <!-- Logo -->
        <div
          class="flex items-center gap-3 cursor-pointer"
          @click="router.push('/home')"
        >
          <div
            class="w-9 h-9 rounded-lg bg-white text-[#1E325A]
                   flex items-center justify-center font-bold shadow"
          >
            S
          </div>

          <span class="text-lg font-semibold text-white">
            SmartProp
          </span>
        </div>

        <!-- Tài khoản -->
        <button
          class="border border-white/40 rounded-full
                 px-6 py-2 text-sm text-white
                 bg-white/5 hover:bg-white/10 transition"
        >
          Tài khoản
        </button>
      </header>

      <!-- Tiêu đề -->
      <div
        class="relative z-10 max-w-[1280px] mx-auto
               px-6 pt-[95px]"
      >
        <h1 class="text-3xl font-light tracking-tight">
          Đăng tin mới
        </h1>

        <p
          class="mt-2 text-[12px] uppercase tracking-[0.22em]
                 text-gray-200 font-semibold"
        >
          BƯỚC 3 / 4 · XÁC MINH & PHÁP LÝ
        </p>
      </div>

    </section>

    <!-- ========================================= -->
    <!-- MAIN -->
    <!-- ========================================= -->
    <main class="max-w-[1280px] mx-auto px-6 pb-16">

      <!-- Progress -->
      <div class="grid grid-cols-4 gap-1 pt-6 mb-5">
        <div class="h-[2px] bg-[#1E325A]"></div>
        <div class="h-[2px] bg-[#1E325A]"></div>
        <div class="h-[2px] bg-[#1E325A]"></div>
        <div class="h-[2px] bg-[#cfd2d4]"></div>
      </div>

      <!-- Layout -->
      <div
        class="grid grid-cols-1 lg:grid-cols-[1fr_260px]
               gap-5 items-start"
      >

        <!-- ===================================== -->
        <!-- CỘT TRÁI -->
        <!-- ===================================== -->
        <div class="space-y-4">

          <!-- GIẤY TỜ SỞ HỮU -->
          <section class="bg-white/90 rounded-[22px] p-6">

            <h2 class="text-sm font-semibold mb-5">
              Giấy tờ sở hữu
            </h2>

            <!-- Loại giấy tờ -->
            <div class="mb-4">
              <label
                class="block text-[12px] font-medium
                       text-[#1E325A] mb-1.5"
              >
                Loại giấy tờ
              </label>

              <select
                v-model="documentType"
                class="w-full h-10 px-4 rounded-lg
                       border border-gray-200
                       bg-white text-xs text-gray-600
                       outline-none focus:border-[#1E325A]"
              >
                <option>Sổ đỏ / Giấy chứng nhận QSDĐ</option>
                <option>Sổ hồng</option>
                <option>Hợp đồng mua bán</option>
                <option>Giấy tờ khác</option>
              </select>
            </div>

            <!-- 3 ô -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">

              <!-- Số giấy -->
              <div>
                <label
                  class="block text-[12px] font-medium
                         text-[#1E325A] mb-1.5"
                >
                  Số giấy chứng nhận
                </label>

                <input
                  v-model="documentNumber"
                  type="text"
                  class="w-full h-10 px-4 rounded-lg
                         border border-gray-200 bg-white
                         text-xs text-gray-600 outline-none
                         focus:border-[#1E325A]"
                />
              </div>

              <!-- Ngày cấp -->
              <div>
                <label
                  class="block text-[12px] font-medium
                         text-[#1E325A] mb-1.5"
                >
                  Ngày cấp
                </label>

                <input
                  v-model="issueDate"
                  type="text"
                  class="w-full h-10 px-4 rounded-lg
                         border border-gray-200 bg-white
                         text-xs text-gray-600 outline-none
                         focus:border-[#1E325A]"
                />
              </div>

              <!-- Chủ sở hữu -->
              <div>
                <label
                  class="block text-[12px] font-medium
                         text-[#1E325A] mb-1.5"
                >
                  Chủ sở hữu
                </label>

                <input
                  v-model="ownerName"
                  type="text"
                  class="w-full h-10 px-4 rounded-lg
                         border border-gray-200 bg-white
                         text-xs text-gray-600 outline-none
                         focus:border-[#1E325A]"
                />
              </div>

            </div>
          </section>

          <!-- ===================================== -->
          <!-- THÔNG TIN LIÊN HỆ -->
          <!-- ===================================== -->
          <section class="bg-white/90 rounded-[22px] p-6">

            <h2 class="text-sm font-semibold mb-5">
              Thông tin liên hệ
            </h2>

            <!-- Họ tên + SĐT -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">

              <div>
                <label
                  class="block text-[12px] font-medium
                         text-[#1E325A] mb-1.5"
                >
                  Họ tên người đăng
                </label>

                <input
                  v-model="contactName"
                  type="text"
                  class="w-full h-10 px-4 rounded-lg
                         border border-gray-200 bg-white
                         text-xs text-gray-600 outline-none
                         focus:border-[#1E325A]"
                />
              </div>

              <div>
                <label
                  class="block text-[12px] font-medium
                         text-[#1E325A] mb-1.5"
                >
                  Số điện thoại
                </label>

                <input
                  v-model="phone"
                  type="text"
                  class="w-full h-10 px-4 rounded-lg
                         border border-gray-200 bg-white
                         text-xs text-gray-600 outline-none
                         focus:border-[#1E325A]"
                />
              </div>

            </div>

            <!-- Zalo / Email -->
            <div>
              <label
                class="block text-[12px] font-medium
                       text-[#1E325A] mb-1.5"
              >
                Zalo / Email liên hệ
              </label>

              <input
                v-model="contact"
                type="text"
                class="w-full h-10 px-4 rounded-lg
                       border border-gray-200 bg-white
                       text-xs text-gray-600 outline-none
                       focus:border-[#1E325A]"
              />
            </div>

          </section>

          <!-- ===================================== -->
          <!-- KẾT QUẢ AI -->
          <!-- ===================================== -->
          <section class="bg-white/90 rounded-[22px] p-6">

            <h2 class="text-sm font-semibold mb-4">
              Kết quả đối chiếu ảnh AI
            </h2>

            <div
              class="inline-flex items-center gap-2
                     bg-emerald-50 text-emerald-600
                     rounded-full px-4 py-2
                     text-[11px]"
            >
              <span
                class="w-4 h-4 rounded-full
                       bg-emerald-400 text-white
                       flex items-center justify-center
                       text-[10px]"
              >
                ✓
              </span>

              <span class="font-medium">
                Đã xác minh ảnh
              </span>

              <span class="text-gray-400">
                Đủ mặt 3 ảnh, không phát hiện trùng lặp
                với tin đăng khác trong bán kính 500m.
              </span>
            </div>

          </section>

        </div>

        <!-- ===================================== -->
        <!-- CỘT PHẢI -->
        <!-- ===================================== -->
        <aside class="lg:sticky lg:top-5">

          <!-- XGBOOST -->
          <div
            class="bg-[#1E325A]
                   text-white
                   rounded-[22px]
                   p-6"
          >
            <p
              class="text-[10px]
                     tracking-[0.18em]
                     text-white/60"
            >
              GIÁ THAM CHIẾU XGBOOST
            </p>

            <div class="text-2xl font-light mt-2">
              4,62 tỷ
            </div>

            <p
              class="text-[10px]
                     text-white/60
                     leading-relaxed mt-2"
            >
              Giá chào của bạn cao hơn khoảng 5% so với
              giá tham chiếu tại Hải Châu.
            </p>

            <!-- Đường kẻ -->
            <div class="h-px bg-white/10 my-6"></div>

            <h3 class="text-xs font-medium mb-4">
              Yếu tố ảnh hưởng
            </h3>

            <div class="space-y-4 text-[11px]">

              <!-- Hải Châu -->
              <div
                class="grid grid-cols-[1fr_55px_45px]
                       items-center gap-2"
              >
                <span>Hải Châu</span>

                <div
                  class="h-[3px] bg-emerald-300 rounded-full"
                ></div>

                <span class="text-emerald-300 text-right">
                  +610tr
                </span>
              </div>

              <!-- Diện tích -->
              <div
                class="grid grid-cols-[1fr_55px_45px]
                       items-center gap-2"
              >
                <span>Diện tích 92m²</span>

                <div
                  class="h-[3px] bg-emerald-300 rounded-full"
                ></div>

                <span class="text-emerald-300 text-right">
                  +420tr
                </span>
              </div>

              <!-- Phòng ngủ -->
              <div
                class="grid grid-cols-[1fr_55px_45px]
                       items-center gap-2"
              >
                <span>3 phòng ngủ</span>

                <div
                  class="h-[3px] bg-emerald-300 rounded-full"
                ></div>

                <span class="text-emerald-300 text-right">
                  +150tr
                </span>
              </div>

              <!-- Hẻm -->
              <div
                class="grid grid-cols-[1fr_55px_45px]
                       items-center gap-2"
              >
                <span>Hẻm dưới 4m</span>

                <div
                  class="h-[3px] bg-orange-300 rounded-full"
                ></div>

                <span class="text-orange-300 text-right">
                  -280tr
                </span>
              </div>

            </div>

            <div class="h-px bg-white/10 my-6"></div>

            <p
              class="text-[10px]
                     leading-relaxed
                     text-white/50"
            >
              Thông tin tham khảo, không phải kết quả
              thẩm định chính thức.
            </p>

          </div>

          <!-- Buttons -->
          <div class="mt-3 space-y-2">

            <RouterLink
  to="/post/step-4"
  class="block w-full bg-[#1E325A] text-white text-center rounded-full py-3 text-xs"
>
  Tiếp tục ↗
</RouterLink>

            <button
              class="w-full h-10
                     bg-white
                     border border-gray-200
                     text-gray-500
                     rounded-full
                     text-xs
                     hover:bg-gray-50 transition"
            >
              Lưu nháp
            </button>

          </div>

        </aside>

      </div>
    </main>

  </div>
</template>