<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const accepted = ref(true)

const goHome = () => {
  router.push('/home')
}

const publishPost = () => {
  if (!accepted.value) {
    alert('Bạn cần xác nhận điều khoản đăng tin.')
    return
  }

  alert('Đăng tin thành công!')
  router.push('/home')
}
</script>

<template>
  <div class="min-h-screen bg-[#e9e7e1] text-[#1E325A]">

    <!-- ================= HEADER ================= -->
    <section class="relative h-[260px] overflow-hidden">

      <!-- Video -->
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
      <div class="absolute inset-0 bg-black/40"></div>

      <!-- Header -->
      <header
        class="relative z-10 max-w-[1280px] mx-auto px-6 pt-6 flex items-center justify-between"
      >
        <!-- Logo -->
        <button
          @click="goHome"
          class="flex items-center gap-2 text-white"
        >
          <div
            class="w-8 h-8 bg-white text-[#1E325A] rounded-lg flex items-center justify-center font-bold"
          >
            S
          </div>

          <span class="font-semibold text-lg">
            SmartProp
          </span>
        </button>

        <!-- Account -->
        <button
          class="border border-white/40 text-white px-5 py-2 rounded-full text-sm hover:bg-white/10 transition"
        >
          Tài khoản
        </button>
      </header>

      <!-- Title -->
      <div
        class="relative z-10 max-w-[1280px] mx-auto px-6 pt-[105px]"
      >
        <h1 class="text-white text-3xl font-light">
          Đăng tin mới
        </h1>

        <p
          class="text-white/70 text-[11px] uppercase tracking-[0.25em] mt-2"
        >
          Bước 4 / 4 · Xem lại & đăng tin
        </p>
      </div>
    </section>

    <!-- ================= CONTENT ================= -->
    <main class="max-w-[1280px] mx-auto px-6 pb-24">

      <!-- Progress -->
      <div class="grid grid-cols-4 gap-1 pt-6 pb-5">
        <div class="h-[2px] bg-[#1E325A]"></div>
        <div class="h-[2px] bg-[#1E325A]"></div>
        <div class="h-[2px] bg-[#1E325A]"></div>
        <div class="h-[2px] bg-[#1E325A]"></div>
      </div>

      <!-- 2 columns -->
      <div
        class="grid grid-cols-1 lg:grid-cols-[1fr_270px] gap-5 items-start"
      >

        <!-- ================= LEFT ================= -->
        <div class="space-y-4">

          <!-- REVIEW POST -->
          <section
            class="bg-white/90 rounded-[24px] p-6 shadow-sm"
          >
            <h2 class="text-sm font-semibold text-[#1E325A] mb-5">
              Xem lại tin đăng
            </h2>

            <!-- Images -->
            <div class="grid grid-cols-3 gap-3 mb-5">

              <!-- Image 1 -->
              <div
                class="relative h-[115px] bg-[#e2ded4] rounded-xl overflow-hidden"
              >
                <span
                  class="absolute top-3 left-3 bg-[#1E325A] text-white text-[9px] px-2 py-1 rounded-full"
                >
                  Ảnh bìa
                </span>
              </div>

              <!-- Image 2 -->
              <div
                class="h-[115px] bg-[#e2ded4] rounded-xl"
              ></div>

              <!-- Image 3 -->
              <div
                class="h-[115px] bg-[#e2ded4] rounded-xl"
              ></div>

            </div>

            <!-- Property information -->
            <div>
              <h3
                class="font-semibold text-[15px] text-[#1E325A]"
              >
                Nhà 3 tầng hẻm xe hơi, gần cầu Rồng
              </h3>

              <p class="text-[11px] text-gray-400 mt-1">
                Nhà phố · Bán · 92m² · 3PN · 2WC
              </p>

              <p class="text-[11px] text-gray-400 mt-1">
                123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng
              </p>

              <!-- Facilities -->
              <div class="flex flex-wrap gap-2 mt-4">

                <span
                  class="border border-gray-200 rounded-full px-3 py-1 text-[10px] text-gray-500"
                >
                  Sofa
                </span>

                <span
                  class="border border-gray-200 rounded-full px-3 py-1 text-[10px] text-gray-500"
                >
                  Tivi
                </span>

                <span
                  class="border border-gray-200 rounded-full px-3 py-1 text-[10px] text-gray-500"
                >
                  Máy lạnh
                </span>

                <span
                  class="border border-gray-200 rounded-full px-3 py-1 text-[10px] text-gray-500"
                >
                  Tủ lạnh
                </span>

                <span
                  class="border border-gray-200 rounded-full px-3 py-1 text-[10px] text-gray-500"
                >
                  Máy giặt
                </span>

                <span
                  class="border border-gray-200 rounded-full px-3 py-1 text-[10px] text-gray-500"
                >
                  Giường
                </span>

                <span
                  class="border border-gray-200 rounded-full px-3 py-1 text-[10px] text-gray-500"
                >
                  Bàn ăn
                </span>

              </div>

              <p class="text-[9px] text-gray-400 mt-4">
                Mã số: CT01234567 · Chủ sở hữu: Nguyễn Văn A
              </p>
            </div>
          </section>

          <!-- ================= TERMS ================= -->
          <section
            class="bg-white/90 rounded-[22px] p-6 shadow-sm"
          >
            <h2 class="text-sm font-semibold mb-4">
              Điều khoản đăng tin
            </h2>

            <label
              class="flex items-start gap-3 cursor-pointer"
            >
              <input
                v-model="accepted"
                type="checkbox"
                class="mt-[2px] accent-[#1E325A]"
              />

              <span class="text-[11px] text-gray-500 leading-relaxed">
                Tôi cam kết thông tin đăng tải là chính xác và tôi có
                quyền đăng tin này.
              </span>
            </label>
          </section>

        </div>

        <!-- ================= RIGHT ================= -->
        <aside class="space-y-3">

          <!-- XGBoost -->
          <div
            class="bg-[#1E325A] text-white rounded-[22px] p-6"
          >
            <p
              class="text-[9px] uppercase tracking-[0.18em] text-white/60"
            >
              Giá tham chiếu XGBoost
            </p>

            <div class="text-3xl font-light mt-2">
              4,62 tỷ
            </div>

            <p
              class="text-[9px] text-white/60 leading-relaxed mt-1"
            >
              Giá tham chiếu bạn cao hơn khoảng 5% so với giá thị trường
              tại Hải Châu.
            </p>

            <!-- Factors -->
            <div class="mt-7">

              <p class="text-[9px] text-white/50 mb-4">
                Yếu tố ảnh hưởng
              </p>

              <!-- Row -->
              <div class="space-y-3 text-[10px]">

                <div class="flex items-center justify-between">
                  <span>Hải Châu</span>

                  <div class="flex items-center gap-2">
                    <div class="w-10 h-[3px] bg-emerald-300"></div>
                    <span class="text-emerald-300">
                      +410tr
                    </span>
                  </div>
                </div>

                <div class="flex items-center justify-between">
                  <span>Diện tích 92m²</span>

                  <div class="flex items-center gap-2">
                    <div class="w-8 h-[3px] bg-emerald-300"></div>
                    <span class="text-emerald-300">
                      +420tr
                    </span>
                  </div>
                </div>

                <div class="flex items-center justify-between">
                  <span>3 phòng ngủ</span>

                  <div class="flex items-center gap-2">
                    <div class="w-6 h-[3px] bg-emerald-300"></div>
                    <span class="text-emerald-300">
                      +160tr
                    </span>
                  </div>
                </div>

                <div class="flex items-center justify-between">
                  <span>Hẻm dưới 4m</span>

                  <div class="flex items-center gap-2">
                    <div class="w-5 h-[3px] bg-orange-300"></div>
                    <span class="text-orange-300">
                      -220tr
                    </span>
                  </div>
                </div>

              </div>
            </div>

            <div
              class="border-t border-white/10 mt-6 pt-4 text-[8px] text-white/40 leading-relaxed"
            >
              Thông tin tham khảo, không phải kết quả thẩm định giá.
            </div>
          </div>

          <!-- Publish -->
          <button
            @click="publishPost"
            class="w-full bg-[#1E325A] hover:bg-[#263f70] text-white rounded-full py-3 text-xs font-medium transition"
          >
            Đăng tin ✓
          </button>

          <!-- Draft -->
          <button
            class="w-full bg-white text-gray-500 border border-gray-200 rounded-full py-3 text-xs hover:bg-gray-50 transition"
          >
            Lưu nháp
          </button>

        </aside>
      </div>
    </main>
  </div>
</template>