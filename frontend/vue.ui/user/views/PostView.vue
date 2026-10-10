<script setup>
import { ref } from 'vue'

const transactionType = ref('Bán')
const propertyType = ref('Nhà phố')
const area = ref('Hải Châu')

const transactionTypes = ['Bán', 'Cho thuê']

const propertyTypes = [
  { name: 'Nhà phố', icon: '🏠' },
  { name: 'Căn hộ chung cư', icon: '▣' },
  { name: 'Đất nền', icon: '▱' },
  { name: 'Biệt thự', icon: '🏡' },
  { name: 'Phòng trọ', icon: '🛏' },
  { name: 'Kho / Mặt bằng', icon: '🏢' }
]

const areas = [
  'Hải Châu',
  'Thanh Khê',
  'Sơn Trà',
  'Ngũ Hành Sơn',
  'Cẩm Lệ',
  'Liên Chiểu',
  'Hoà Vang'
]
</script>

<template>
  <div class="min-h-screen bg-[#e9e7e1] text-[#1E325A]">

    <!-- ================= HERO ================= -->
    <section class="relative h-[250px] overflow-hidden">

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
      <div class="absolute inset-0 bg-black/50"></div>

      <!-- Hero content -->
      <div class="relative z-10 max-w-7xl mx-auto px-8 h-full">

        <!-- Navbar -->
        <header class="flex items-center justify-between pt-7">

          <!-- Logo -->
          <RouterLink
            to="/home"
            class="flex items-center gap-3"
          >
            <div
              class="w-8 h-8 rounded-lg bg-white text-[#1E325A]
                     flex items-center justify-center font-bold"
            >
              S
            </div>

            <span class="text-white text-lg font-semibold">
              SmartProp
            </span>
          </RouterLink>

          <!-- Account -->
          <button
            class="px-5 py-2 rounded-full border border-white/40
                   text-white/90 text-sm hover:bg-white/10 transition"
          >
            Tài khoản
          </button>
        </header>

        <!-- Page title -->
        <div class="absolute left-8 bottom-8 text-white">

          <h1 class="text-3xl font-light mb-2">
            Đăng tin mới
          </h1>

          <div
            class="text-[10px] uppercase tracking-[0.25em]
                   text-white/70"
          >
            BƯỚC 1 / 4 · LOẠI HÌNH & HÌNH THỨC
          </div>

        </div>
      </div>
    </section>


    <!-- ================= PROGRESS ================= -->

    <div class="max-w-7xl mx-auto px-8 py-6">
      <div class="grid grid-cols-4 gap-1">

        <div class="h-[2px] bg-[#1E325A]"></div>

        <div class="h-[2px] bg-gray-300"></div>

        <div class="h-[2px] bg-gray-300"></div>

        <div class="h-[2px] bg-gray-300"></div>

      </div>
    </div>


    <!-- ================= MAIN ================= -->

    <main class="max-w-7xl mx-auto px-8 pb-16">

      <div
        class="grid grid-cols-1
               lg:grid-cols-[minmax(0,1fr)_270px]
               gap-4 items-start"
      >

        <!-- ===================================== -->
        <!-- LEFT -->
        <!-- ===================================== -->

        <div class="space-y-4">


          <!-- ========== TRANSACTION ========== -->

          <section class="bg-white/80 rounded-3xl p-6">

            <div class="mb-5">

              <h2 class="text-sm font-semibold text-[#1E325A]">
                Hình thức giao dịch
              </h2>

              <p class="text-[11px] text-gray-400 mt-1">
                Chọn hình thức phù hợp với tin đăng của bạn.
              </p>

            </div>


            <div class="grid grid-cols-2 gap-2">

              <button
                v-for="type in transactionTypes"
                :key="type"
                type="button"
                @click="transactionType = type"
                :class="[
                  'h-12 rounded-xl border text-sm font-medium transition',
                  
                  transactionType === type
                    ? 'bg-[#1E325A] border-[#1E325A] text-white'
                    : 'bg-white border-gray-200 text-gray-400 hover:border-[#1E325A] hover:text-[#1E325A]'
                ]"
              >
                {{ type }}
              </button>

            </div>

          </section>


          <!-- ========== PROPERTY TYPE ========== -->

          <section class="bg-white/80 rounded-3xl p-6">

            <div class="mb-5">

              <h2 class="text-sm font-semibold text-[#1E325A]">
                Loại hình bất động sản
              </h2>

              <p class="text-[11px] text-gray-400 mt-1">
                Loại hình ảnh hưởng đến các trường thông tin ở bước tiếp theo.
              </p>

            </div>


            <div
              class="grid grid-cols-1
                     sm:grid-cols-2
                     lg:grid-cols-3
                     gap-2"
            >

              <button
                v-for="property in propertyTypes"
                :key="property.name"
                type="button"
                @click="propertyType = property.name"
                :class="[
                  'h-[82px] rounded-xl border p-3 text-left transition',
                  
                  propertyType === property.name
                    ? 'border-orange-500 bg-orange-50/40'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                ]"
              >

                <!-- icon -->
                <div
                  :class="[
                    'w-7 h-7 rounded-lg flex items-center justify-center text-xs mb-2',

                    propertyType === property.name
                      ? 'bg-orange-100'
                      : 'bg-gray-100'
                  ]"
                >
                  {{ property.icon }}
                </div>

                <!-- name -->
                <div
                  :class="[
                    'text-xs font-medium',

                    propertyType === property.name
                      ? 'text-orange-700'
                      : 'text-gray-500'
                  ]"
                >
                  {{ property.name }}
                </div>

              </button>

            </div>

          </section>


          <!-- ========== AREA ========== -->

          <section class="bg-white/80 rounded-3xl p-6">

            <div class="mb-4">

              <h2 class="text-sm font-semibold text-[#1E325A]">
                Khu vực
              </h2>

              <p class="text-[11px] text-gray-400 mt-1">
                Chọn quận/huyện tại Đà Nẵng để hệ thống gợi ý giá tham chiếu chính xác hơn.
              </p>

            </div>


            <div class="flex flex-wrap gap-2">

              <button
                v-for="item in areas"
                :key="item"
                type="button"
                @click="area = item"
                :class="[
                  'px-4 py-2 rounded-full border text-[11px] transition',

                  area === item
                    ? 'border-[#1E325A] bg-white text-[#1E325A]'
                    : 'border-gray-200 bg-white text-gray-400 hover:border-[#1E325A]'
                ]"
              >
                {{ item }}
              </button>

            </div>

          </section>

        </div>


        <!-- ===================================== -->
        <!-- RIGHT SIDEBAR -->
        <!-- ===================================== -->

        <aside class="lg:sticky lg:top-5">

          <!-- Process box -->

          <div
            class="bg-[#1E325A]
                   rounded-3xl
                   p-6
                   text-white"
          >

            <p
              class="text-[9px]
                     tracking-[0.2em]
                     uppercase
                     text-white/60"
            >
              Quy trình đăng tin
            </p>


            <h3 class="text-base font-medium mt-2">
              4 bước, khoảng 5 phút
            </h3>


            <p
              class="text-[10px]
                     leading-relaxed
                     text-white/50
                     mt-2"
            >
              Giá tham chiếu XGBoost và các yếu tố ảnh hưởng
              sẽ xuất hiện sau khi hoàn tất.
            </p>


            <!-- STEPS -->

            <div
              class="border-t
                     border-white/10
                     mt-14
                     pt-4
                     space-y-4"
            >


              <!-- STEP 1 -->

              <div class="flex items-center gap-3 text-xs">

                <div
                  class="w-5 h-5
                         rounded-full
                         bg-emerald-300
                         text-[#1E325A]
                         flex items-center
                         justify-center
                         text-[9px]
                         font-bold"
                >
                  1
                </div>

                <span>
                  Loại hình & hình thức
                </span>

              </div>


              <!-- STEP 2 -->

              <div
                class="flex items-center
                       gap-3
                       text-xs
                       text-white/50"
              >

                <div
                  class="w-5 h-5
                         rounded-full
                         bg-white/15
                         flex items-center
                         justify-center
                         text-[9px]"
                >
                  2
                </div>

                <span>
                  Thông tin & ảnh
                </span>

              </div>


              <!-- STEP 3 -->

              <div
                class="flex items-center
                       gap-3
                       text-xs
                       text-white/50"
              >

                <div
                  class="w-5 h-5
                         rounded-full
                         bg-white/15
                         flex items-center
                         justify-center
                         text-[9px]"
                >
                  3
                </div>

                <span>
                  Xác minh & pháp lý
                </span>

              </div>


              <!-- STEP 4 -->

              <div
                class="flex items-center
                       gap-3
                       text-xs
                       text-white/50"
              >

                <div
                  class="w-5 h-5
                         rounded-full
                         bg-white/15
                         flex items-center
                         justify-center
                         text-[9px]"
                >
                  4
                </div>

                <span>
                  Xem lại & đăng tin
                </span>

              </div>

            </div>

          </div>


          <!-- CONTINUE -->

          <button
            type="button"
             @click="$router.push('/post/step-2')"
            class="w-full
                   h-11
                   mt-3
                   rounded-full
                   bg-[#1E325A]
                   text-white
                   text-xs
                   hover:opacity-90
                   transition"
          >
            Tiếp tục ↗
          </button>


          <!-- SAVE -->

          <button
            type="button"
            class="w-full
                   h-11
                   mt-2
                   rounded-full
                   bg-white
                   border
                   border-gray-200
                   text-gray-400
                   text-xs
                   hover:text-[#1E325A]
                   hover:border-[#1E325A]
                   transition"
          >
            Lưu nháp
          </button>

        </aside>

      </div>

    </main>

  </div>
</template>