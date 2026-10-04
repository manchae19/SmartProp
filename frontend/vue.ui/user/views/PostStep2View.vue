<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const title = ref('Nhà 3 tầng hẻm xe hơi, gần cầu Rồng')
const propertyType = ref('Nhà phố')
const transactionType = ref('Bán')
const area = ref('92')
const price = ref('4.850.000.000')
const bedrooms = ref('3')
const bathrooms = ref('2')
const address = ref('123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng')

const amenities = [
  'Sofa',
  'Tivi',
  'Máy lạnh',
  'Tủ lạnh',
  'Máy giặt',
  'Giường',
  'Bàn ăn'
]

const selectedAmenities = ref([])

function toggleAmenity(item) {
  if (selectedAmenities.value.includes(item)) {
    selectedAmenities.value =
      selectedAmenities.value.filter(x => x !== item)
  } else {
    selectedAmenities.value.push(item)
  }
}

function goNext() {
  router.push('/post/step-3')
}
</script>

<template>
  <div class="min-h-screen bg-[#e9e7e1] text-[#1E325A]">

    <!-- ================= HEADER ================= -->
    <section class="relative h-[270px] overflow-hidden text-white">

      <!-- Video background -->
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
            class="w-9 h-9 bg-white text-[#1E325A]
                   rounded-lg flex items-center justify-center
                   font-bold shadow"
          >
            S
          </div>

          <span class="text-lg font-semibold text-white">
            SmartProp
          </span>
        </div>

        <!-- Account -->
        <button
          class="border border-white/40 rounded-full
                 px-6 py-2 text-sm text-white
                 bg-white/5 hover:bg-white/10 transition"
        >
          Tài khoản
        </button>
      </header>

      <!-- Header title -->
      <div
        class="relative z-10 max-w-[1280px] mx-auto
               px-6 pt-[95px]"
      >
        <h1 class="text-3xl font-light tracking-tight">
          Đăng tin mới
        </h1>

        <p
          class="mt-2 text-[11px] uppercase
                 tracking-[0.22em] text-gray-200 font-semibold"
        >
          BƯỚC 2 / 4 · THÔNG TIN & ẢNH
        </p>
      </div>
    </section>

    <!-- ================= MAIN ================= -->
    <main class="max-w-[1280px] mx-auto px-6 pb-14">

      <!-- Progress -->
      <div class="grid grid-cols-4 gap-1 pt-6 mb-5">
        <div class="h-[2px] bg-[#1E325A]"></div>
        <div class="h-[2px] bg-[#1E325A]"></div>
        <div class="h-[2px] bg-[#cfd2d4]"></div>
        <div class="h-[2px] bg-[#cfd2d4]"></div>
      </div>

      <div
        class="grid grid-cols-1 lg:grid-cols-[1fr_260px]
               gap-5 items-start"
      >

        <!-- ================= LEFT ================= -->
        <div class="space-y-4">

          <!-- THÔNG TIN CƠ BẢN -->
          <section class="bg-white/90 rounded-[22px] p-6">

            <h2 class="text-sm font-semibold mb-5">
              Thông tin cơ bản
            </h2>

            <!-- Title -->
            <div class="mb-4">
              <label
                class="block text-[11px] font-medium
                       text-[#1E325A] mb-1.5"
              >
                Tiêu đề tin đăng
              </label>

              <input
                v-model="title"
                type="text"
                class="w-full h-10 px-4 rounded-lg
                       border border-gray-200
                       bg-white text-xs text-gray-600
                       outline-none
                       focus:border-[#1E325A]"
              />
            </div>

            <!-- Row 1 -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">

              <div>
                <label class="form-label">
                  Loại hình
                </label>

                <input
                  v-model="propertyType"
                  class="form-input"
                />
              </div>

              <div>
                <label class="form-label">
                  Hình thức
                </label>

                <input
                  v-model="transactionType"
                  class="form-input"
                />
              </div>

              <div>
                <label class="form-label">
                  Diện tích (m²)
                </label>

                <input
                  v-model="area"
                  type="number"
                  class="form-input"
                />
              </div>
            </div>

            <!-- Row 2 -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">

              <div>
                <label class="form-label">
                  Giá chào (VNĐ)
                </label>

                <input
                  v-model="price"
                  class="form-input"
                />
              </div>

              <div>
                <label class="form-label">
                  Phòng ngủ
                </label>

                <input
                  v-model="bedrooms"
                  type="number"
                  class="form-input"
                />
              </div>

              <div>
                <label class="form-label">
                  Phòng tắm
                </label>

                <input
                  v-model="bathrooms"
                  type="number"
                  class="form-input"
                />
              </div>

            </div>
          </section>

          <!-- ================= VỊ TRÍ ================= -->
          <section class="bg-white/90 rounded-[22px] p-6">

            <h2 class="text-sm font-semibold">
              Vị trí
            </h2>

            <p
              class="text-[10px] text-gray-400
                     leading-relaxed mb-4"
            >
              Tọa độ lưu dưới dạng POINT trong MySQL Spatial
              để phục vụ truy vấn khoảng cách.
            </p>

            <input
              v-model="address"
              type="text"
              class="w-full h-10 px-4 rounded-lg
                     border border-gray-200 bg-white
                     text-xs text-gray-500 outline-none
                     focus:border-[#1E325A]"
            />

            <!-- Map placeholder -->
            <div
              class="mt-3 h-[150px]
                     rounded-xl bg-[#dedbd3]
                     flex items-center justify-center"
            >
              <div
                class="bg-white rounded-md
                       px-5 py-2
                       text-[10px] text-gray-400"
              >
                mapbox gl js — kéo ghim để chỉnh tọa độ
              </div>
            </div>

          </section>

          <!-- ================= ẢNH ================= -->
          <section class="bg-white/90 rounded-[22px] p-6">

            <h2 class="text-sm font-semibold">
              Ảnh tin đăng
            </h2>

            <p
              class="text-[10px] text-gray-400
                     leading-relaxed mb-4"
            >
              Ảnh sẽ được đối chiếu tương đồng và nhận diện
              tiện ích sau khi tải lên. JPG hoặc PNG, tối đa 5MB.
            </p>

            <div
              class="grid grid-cols-2 md:grid-cols-4 gap-3"
            >

              <!-- Cover -->
              <div
                class="relative h-[115px]
                       bg-[#dedbd3] rounded-xl"
              >
                <span
                  class="absolute top-2 left-2
                         bg-[#1E325A] text-white
                         text-[9px] px-2 py-1 rounded"
                >
                  Ảnh bìa
                </span>
              </div>

              <div
                class="h-[115px]
                       bg-[#dedbd3] rounded-xl"
              ></div>

              <div
                class="h-[115px]
                       bg-[#dedbd3] rounded-xl"
              ></div>

              <!-- Upload -->
              <label
                class="h-[115px]
                       rounded-xl
                       border border-[#b9c0cc]
                       flex flex-col
                       items-center justify-center
                       cursor-pointer
                       text-gray-400
                       hover:border-[#1E325A]
                       hover:text-[#1E325A]
                       transition"
              >
                <span class="text-xl">
                  +
                </span>

                <span class="text-[10px] mt-1">
                  Thêm ảnh
                </span>

                <input
                  type="file"
                  accept="image/png,image/jpeg"
                  multiple
                  class="hidden"
                />
              </label>

            </div>
          </section>

          <!-- ================= TIỆN ÍCH ================= -->
          <section class="bg-white/90 rounded-[22px] p-6">

            <h2 class="text-sm font-semibold">
              Tiện ích khai báo
            </h2>

            <p
              class="text-[10px] text-gray-400
                     leading-relaxed mb-4"
            >
              Những tiện ích bạn chọn sẽ được so với vật thể
              nhận diện được trong ảnh.
            </p>

            <div class="flex flex-wrap gap-2">

              <button
                v-for="item in amenities"
                :key="item"
                type="button"
                @click="toggleAmenity(item)"
                :class="[
                  'px-4 py-1.5 rounded-full border text-[10px] transition',
                  selectedAmenities.includes(item)
                    ? 'bg-[#1E325A] border-[#1E325A] text-white'
                    : 'bg-white border-gray-200 text-gray-500 hover:border-[#1E325A]'
                ]"
              >
                {{ item }}
              </button>

            </div>

          </section>

        </div>

        <!-- ================= RIGHT ================= -->
        <aside class="lg:sticky lg:top-5">

          <!-- XGBoost Card -->
          <div
            class="bg-[#1E325A]
                   text-white
                   rounded-[22px]
                   p-6"
          >
            <p
              class="text-[9px]
                     tracking-[0.18em]
                     text-white/60"
            >
              GIÁ THAM CHIẾU XGBOOST
            </p>

            <div class="text-2xl font-light mt-2">
              4,62 tỷ
            </div>

            <p
              class="text-[9px]
                     text-white/60
                     leading-relaxed mt-2"
            >
              Giá chào của bạn cao hơn khoảng 5% so với
              giá tham chiếu cho nhà tương tự tại Hải Châu.
            </p>

            <!-- Divider -->
            <div class="h-px bg-white/10 my-6"></div>

            <h3 class="text-xs font-medium mb-4">
              Yếu tố ảnh hưởng
            </h3>

            <!-- Factor -->
            <div class="space-y-4 text-[10px]">

              <div
                class="grid grid-cols-[1fr_55px_45px]
                       items-center gap-2"
              >
                <span>Hải Châu</span>

                <div
                  class="h-[3px]
                         bg-emerald-300 rounded-full"
                ></div>

                <span class="text-emerald-300 text-right">
                  +610tr
                </span>
              </div>

              <div
                class="grid grid-cols-[1fr_55px_45px]
                       items-center gap-2"
              >
                <span>Diện tích 92m²</span>

                <div
                  class="h-[3px]
                         bg-emerald-300 rounded-full"
                ></div>

                <span class="text-emerald-300 text-right">
                  +420tr
                </span>
              </div>

              <div
                class="grid grid-cols-[1fr_55px_45px]
                       items-center gap-2"
              >
                <span>3 phòng ngủ</span>

                <div
                  class="h-[3px]
                         bg-emerald-300 rounded-full"
                ></div>

                <span class="text-emerald-300 text-right">
                  +150tr
                </span>
              </div>

              <div
                class="grid grid-cols-[1fr_55px_45px]
                       items-center gap-2"
              >
                <span>Hẻm dưới 4m</span>

                <div
                  class="h-[3px]
                         bg-red-300 rounded-full"
                ></div>

                <span class="text-red-300 text-right">
                  −280tr
                </span>
              </div>

            </div>

            <div class="h-px bg-white/10 my-6"></div>

            <p
              class="text-[9px]
                     leading-relaxed text-white/50"
            >
              Thông tin tham khảo, không phải kết quả
              thẩm định chính thức.
            </p>
          </div>

          <!-- Buttons -->
          <div class="mt-3 space-y-2">

            <button
              @click="goNext"
              class="w-full h-10
                     bg-[#1E325A]
                     hover:bg-[#172746]
                     text-white
                     rounded-full
                     text-xs
                     transition"
            >
              Tiếp tục ↗
            </button>

            <button
              class="w-full h-10
                     bg-white
                     border border-gray-200
                     text-gray-500
                     rounded-full
                     text-xs
                     hover:bg-gray-50
                     transition"
            >
              Lưu nháp
            </button>

          </div>

        </aside>

      </div>
    </main>

  </div>
</template>

<style>
.form-label {
  display: block;
  font-size: 11px;
  font-weight: 500;
  color: #1e325a;
  margin-bottom: 6px;
}

.form-input {
  width: 100%;
  height: 40px;
  padding: 0 16px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: white;
  font-size: 12px;
  color: #6b7280;
  outline: none;
}

.form-input:focus {
  border-color: #1e325a;
}
</style>