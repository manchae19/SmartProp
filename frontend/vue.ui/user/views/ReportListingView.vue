<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

// ==================== LISTING DATA ====================

const listings = {
  1: {
    title: 'Nhà 3 tầng hẻm xe hơi, gần cầu Rồng',
    location: 'Hải Châu, Đà Nẵng',
    price: '4,85 tỷ đ',
    image: '/images/image0.png',
  },

  2: {
    title: 'Căn hộ 2PN view sông Hàn',
    location: 'Hải Châu, Đà Nẵng',
    price: '3,20 tỷ đ',
    image: '/images/image1.png',
  },

  3: {
    title: 'Đất nền Hoà Xuân, sổ đỏ riêng',
    location: 'Cẩm Lệ, Đà Nẵng',
    price: '2,95 tỷ đ',
    image: '/images/image2.png',
  },
}

const listing = computed(() => {
  return listings[route.params.id] || listings[1]
})

// ==================== REPORT FORM ====================

const reasons = [
  'Nghi ngờ ảnh giả mạo',
  'Thông tin sai lệch',
  'Nghi ngờ lừa đảo',
  'Tin đăng trùng lặp',
  'BĐS đã bán / đã cho thuê',
  'Lý do khác',
]

const selectedReason = ref('')

const description = ref(
  'Ảnh nội thất và mặt tiền trông giống hệt một tin đăng khác tôi từng xem ở khu vực Hải Châu, nghi ngờ ảnh không chụp tại địa chỉ này.'
)

const email = ref('hoang.binh@gmail.com')

const confirmed = ref(false)

const selectedFile = ref(null)

const isSubmitted = ref(false)

// ==================== FUNCTIONS ====================

const selectReason = (reason) => {
  selectedReason.value = reason
}

const handleFile = (event) => {
  const file = event.target.files?.[0]

  if (!file) return

  const allowedTypes = [
    'image/jpeg',
    'image/png',
    'application/pdf',
  ]

  if (!allowedTypes.includes(file.type)) {
    alert('Chỉ hỗ trợ JPG, PNG hoặc PDF.')
    event.target.value = ''
    return
  }

  if (file.size > 10 * 1024 * 1024) {
    alert('Tệp không được vượt quá 10MB.')
    event.target.value = ''
    return
  }

  selectedFile.value = file
}

const removeFile = () => {
  selectedFile.value = null
}

const submitReport = () => {
  if (!selectedReason.value) {
    alert('Vui lòng chọn lý do báo cáo.')
    return
  }

  if (!description.value.trim()) {
    alert('Vui lòng nhập mô tả chi tiết.')
    return
  }

  if (!email.value.trim()) {
    alert('Vui lòng nhập email liên hệ.')
    return
  }

  if (!confirmed.value) {
    alert('Vui lòng xác nhận thông tin báo cáo.')
    return
  }

  // Sau này có Backend/API thì gửi dữ liệu tại đây.
  console.log({
    listingId: route.params.id,
    reason: selectedReason.value,
    description: description.value,
    email: email.value,
    file: selectedFile.value,
  })

  isSubmitted.value = true
}

const goBack = () => {
  router.push(`/listing/${route.params.id}`)
}

const goHome = () => {
  router.push('/home')
}

const goAccount = () => {
  router.push('/account')
}
</script>

<template>
  <div class="min-h-screen bg-[#ebe9e2] text-[#1E325A]">

    <!-- ================= HEADER ================= -->

    <header class="max-w-[1400px] mx-auto px-6 md:px-10 pt-5">
      <div
        class="flex items-center justify-between border-b border-[#1E325A]/40 pb-4"
      >
        <!-- LEFT -->
        <div class="flex items-center gap-5">
          <button
            @click="goHome"
            class="flex items-center gap-2.5"
          >
            <div
              class="w-7 h-7 rounded-lg bg-[#1E325A] text-white
                     flex items-center justify-center text-xs font-bold"
            >
              S
            </div>

            <span class="font-semibold text-sm">
              SmartProp
            </span>
          </button>

          <div class="hidden sm:block w-px h-5 bg-[#1E325A]/20"></div>

          <button
            @click="goBack"
            class="hidden sm:block text-xs text-gray-500
                   hover:text-[#1E325A] transition"
          >
            ‹ Quay lại tin đăng
          </button>
        </div>

        <!-- RIGHT -->
        <div class="flex items-center gap-2">
          <button
            class="hidden sm:block px-5 py-2 rounded-full
                   bg-white border border-gray-200
                   text-xs text-gray-500"
          >
            Đăng tin
          </button>

          <button
            @click="goAccount"
            class="px-5 py-2 rounded-full
                   bg-[#1E325A] text-white text-xs
                   hover:opacity-90 transition"
          >
            Tài khoản
          </button>
        </div>
      </div>
    </header>

    <!-- ================= MAIN ================= -->

    <main class="max-w-[1180px] mx-auto px-6 md:px-10 py-10">

      <!-- MOBILE BACK -->
      <button
        @click="goBack"
        class="sm:hidden text-xs text-gray-500 mb-6"
      >
        ‹ Quay lại tin đăng
      </button>

      <!-- TITLE -->
      <section class="mb-8">
        <h1
          class="text-3xl md:text-[36px] font-semibold
                 tracking-tight text-[#1E325A]"
        >
          Báo cáo tin đăng
        </h1>

        <p class="text-sm text-gray-500 mt-2">
          Cho chúng tôi biết vấn đề bạn gặp phải với tin đăng này.
        </p>
      </section>

      <!-- ================= SUCCESS ================= -->

      <section
        v-if="isSubmitted"
        class="bg-white rounded-[26px] p-8 md:p-12
               shadow-sm text-center max-w-[720px] mx-auto"
      >
        <div
          class="w-16 h-16 rounded-full bg-[#e5f3ea]
                 text-[#438665] flex items-center justify-center
                 text-2xl mx-auto"
        >
          ✓
        </div>

        <h2 class="text-2xl font-semibold mt-6">
          Báo cáo đã được gửi
        </h2>

        <p
          class="text-sm text-gray-500 mt-3
                 max-w-[500px] mx-auto leading-6"
        >
          Cảm ơn bạn đã giúp SmartProp xây dựng môi trường
          bất động sản an toàn hơn. Đội ngũ quản trị sẽ xem xét
          báo cáo của bạn.
        </p>

        <div
          class="mt-7 bg-[#f5f4ef] rounded-2xl
                 px-5 py-4 text-sm"
        >
          Thời gian xem xét dự kiến:
          <strong>24–48 giờ</strong>
        </div>

        <button
          @click="goBack"
          class="mt-7 px-7 py-3 rounded-full
                 bg-[#1E325A] text-white text-sm"
        >
          Quay lại tin đăng
        </button>
      </section>

      <!-- ================= FORM ================= -->

      <div
        v-else
        class="grid grid-cols-1 lg:grid-cols-[1fr_310px]
               gap-6 items-start"
      >

        <!-- ================= LEFT ================= -->

        <div class="space-y-5">

          <!-- REPORTED LISTING -->

          <section
            class="bg-white rounded-[24px] p-6 md:p-7 shadow-sm"
          >
            <h2 class="text-sm font-semibold mb-4">
              Tin đăng được báo cáo
            </h2>

            <div
              class="flex items-center gap-4
                     bg-[#f5f4ef] rounded-[18px] p-3"
            >
              <!-- IMAGE -->

              <div
                class="w-[105px] h-[78px] rounded-[14px]
                       overflow-hidden bg-[#d9d6ce] shrink-0"
              >
                <img
                  :src="listing.image"
                  :alt="listing.title"
                  class="w-full h-full object-cover"
                />
              </div>

              <!-- INFO -->

              <div class="min-w-0">
                <h3
                  class="text-sm font-semibold
                         text-[#1E325A] truncate"
                >
                  {{ listing.title }}
                </h3>

                <p class="text-[11px] text-gray-400 mt-1">
                  {{ listing.location }}
                </p>

                <p
                  class="text-sm font-semibold
                         text-[#1E325A] mt-2"
                >
                  {{ listing.price }}
                </p>
              </div>
            </div>
          </section>

          <!-- ================= REPORT REASON ================= -->

          <section
            class="bg-white rounded-[24px] p-6 md:p-7 shadow-sm"
          >
            <h2 class="text-base font-semibold">
              Lý do báo cáo
            </h2>

            <p class="text-xs text-gray-400 mt-1.5">
              Chọn lý do phù hợp nhất với vấn đề bạn phát hiện.
            </p>

            <!-- REASONS -->

            <div
              class="grid grid-cols-1 sm:grid-cols-2
                     gap-3 mt-5"
            >
              <button
                v-for="reason in reasons"
                :key="reason"
                type="button"
                @click="selectReason(reason)"
                class="relative text-left px-4 py-4
                       rounded-[16px] border
                       text-xs font-medium transition"
                :class="
                  selectedReason === reason
                    ? 'border-[#1E325A] bg-[#eef0f4] text-[#1E325A] ring-1 ring-[#1E325A]'
                    : 'border-gray-200 bg-white text-gray-600 hover:border-[#1E325A]/40'
                "
              >
                <span
                  class="inline-flex items-center gap-3"
                >
                  <span
                    class="w-4 h-4 rounded-full border
                           flex items-center justify-center"
                    :class="
                      selectedReason === reason
                        ? 'border-[#1E325A]'
                        : 'border-gray-300'
                    "
                  >
                    <span
                      v-if="selectedReason === reason"
                      class="w-2 h-2 rounded-full bg-[#1E325A]"
                    ></span>
                  </span>

                  {{ reason }}
                </span>
              </button>
            </div>

            <!-- DESCRIPTION -->

            <div class="mt-7">
              <label
                class="block text-sm font-semibold mb-2"
              >
                Mô tả chi tiết
              </label>

              <textarea
                v-model="description"
                rows="6"
                maxlength="1000"
                placeholder="Mô tả vấn đề bạn phát hiện..."
                class="w-full resize-none rounded-[16px]
                       border border-gray-200
                       px-4 py-4 text-xs text-gray-600
                       leading-6 outline-none
                       focus:border-[#1E325A]
                       focus:ring-1 focus:ring-[#1E325A]"
              ></textarea>

              <div
                class="text-right text-[10px]
                       text-gray-400 mt-1"
              >
                {{ description.length }}/1000
              </div>
            </div>

            <!-- FILE UPLOAD -->

            <div class="mt-5">
              <label
                class="block text-sm font-semibold mb-2"
              >
                Đính kèm minh chứng
                <span class="font-normal text-gray-400">
                  (không bắt buộc)
                </span>
              </label>

              <label
                class="relative flex flex-col
                       items-center justify-center
                       min-h-[135px]
                       border border-dashed border-gray-300
                       rounded-[16px]
                       bg-[#faf9f6]
                       cursor-pointer
                       hover:border-[#1E325A]/50
                       transition"
              >
                <input
                  type="file"
                  accept=".jpg,.jpeg,.png,.pdf"
                  class="hidden"
                  @change="handleFile"
                />

                <template v-if="!selectedFile">
                  <div class="text-xl">
                    📎
                  </div>

                  <p
                    class="text-xs text-gray-500
                           text-center mt-2 px-5"
                  >
                    Kéo thả ảnh chụp màn hình hoặc tệp vào đây,
                    hoặc bấm để chọn
                  </p>

                  <p class="text-[10px] text-gray-400 mt-1">
                    Hỗ trợ JPG, PNG, PDF · tối đa 10MB
                  </p>
                </template>

                <template v-else>
                  <div
                    class="w-10 h-10 rounded-full
                           bg-[#e5f3ea] text-[#438665]
                           flex items-center justify-center"
                  >
                    ✓
                  </div>

                  <p
                    class="text-xs font-medium
                           text-[#1E325A] mt-2"
                  >
                    {{ selectedFile.name }}
                  </p>

                  <p class="text-[10px] text-gray-400 mt-1">
                    {{
                      (selectedFile.size / 1024 / 1024).toFixed(2)
                    }} MB
                  </p>
                </template>
              </label>

              <button
                v-if="selectedFile"
                type="button"
                @click="removeFile"
                class="text-[10px] text-red-500
                       mt-2 hover:underline"
              >
                Xoá tệp
              </button>
            </div>

            <!-- EMAIL -->

            <div class="mt-6">
              <label
                class="block text-sm font-semibold mb-2"
              >
                Email liên hệ
              </label>

              <input
                v-model="email"
                type="email"
                placeholder="example@gmail.com"
                class="w-full h-12 rounded-[14px]
                       border border-gray-200
                       px-4 text-xs outline-none
                       focus:border-[#1E325A]
                       focus:ring-1 focus:ring-[#1E325A]"
              />

              <p class="text-[10px] text-gray-400 mt-2">
                Chúng tôi sẽ gửi kết quả xử lý báo cáo tới email này.
              </p>
            </div>

            <!-- CONFIRM -->

            <label
              class="flex items-start gap-3 mt-6 cursor-pointer"
            >
              <input
                v-model="confirmed"
                type="checkbox"
                class="mt-0.5 w-4 h-4 accent-[#1E325A]"
              />

              <span
                class="text-[11px] text-gray-500 leading-5"
              >
                Tôi xác nhận thông tin báo cáo trên là đúng sự thật.
                Báo cáo sai sự thật có thể ảnh hưởng đến tài khoản
                của tôi.
              </span>
            </label>

            <!-- BUTTONS -->

            <div
              class="flex flex-col-reverse sm:flex-row
                     gap-3 mt-7"
            >
              <button
                type="button"
                @click="submitReport"
                class="sm:flex-1 h-12 rounded-full
                       bg-[#1E325A] text-white text-xs
                       font-medium hover:opacity-90 transition"
              >
                Gửi báo cáo
              </button>

              <button
                type="button"
                @click="goBack"
                class="sm:w-[130px] h-12 rounded-full
                       bg-white border border-gray-200
                       text-gray-500 text-xs
                       hover:bg-gray-50 transition"
              >
                Huỷ
              </button>
            </div>
          </section>
        </div>

        <!-- ================= RIGHT ================= -->

        <aside class="space-y-4 lg:sticky lg:top-5">

          <!-- NEXT STEPS -->

          <section
            class="bg-[#1E325A] text-white
                   rounded-[24px] p-6 shadow-sm"
          >
            <p
              class="text-[9px] text-white/40
                     tracking-[0.18em] font-semibold"
            >
              SAU KHI BẠN GỬI BÁO CÁO
            </p>

            <h2 class="text-lg font-semibold mt-2">
              Chuyện gì xảy ra tiếp theo?
            </h2>

            <div class="space-y-5 mt-6">

              <!-- STEP 1 -->

              <div class="flex items-start gap-3">
                <div
                  class="w-7 h-7 rounded-full
                         bg-white/10 border border-white/10
                         flex items-center justify-center
                         text-[10px] shrink-0"
                >
                  1
                </div>

                <p
                  class="text-[11px] text-white/65
                         leading-5 pt-1"
                >
                  Đội ngũ quản trị xem xét trong vòng
                  24–48 giờ.
                </p>
              </div>

              <!-- STEP 2 -->

              <div class="flex items-start gap-3">
                <div
                  class="w-7 h-7 rounded-full
                         bg-white/10 border border-white/10
                         flex items-center justify-center
                         text-[10px] shrink-0"
                >
                  2
                </div>

                <p
                  class="text-[11px] text-white/65
                         leading-5 pt-1"
                >
                  Tin đăng có thể bị tạm ẩn nếu vi phạm
                  rõ ràng.
                </p>
              </div>

              <!-- STEP 3 -->

              <div class="flex items-start gap-3">
                <div
                  class="w-7 h-7 rounded-full
                         bg-white/10 border border-white/10
                         flex items-center justify-center
                         text-[10px] shrink-0"
                >
                  3
                </div>

                <p
                  class="text-[11px] text-white/65
                         leading-5 pt-1"
                >
                  Bạn nhận kết quả qua email và tại trang
                  "Báo cáo của tôi".
                </p>
              </div>

            </div>
          </section>

          <!-- PRIVACY -->

          <section
            class="bg-white rounded-[24px] p-6 shadow-sm"
          >
            <div class="flex items-center gap-2">
              <div
                class="w-7 h-7 rounded-full
                       bg-[#e5f3ea]
                       flex items-center justify-center"
              >
                🔒
              </div>

              <h3 class="text-sm font-semibold">
                Quyền riêng tư
              </h3>
            </div>

            <p
              class="text-[11px] text-gray-400
                     leading-5 mt-3"
            >
              Danh tính người báo cáo được giữ kín và
              không chia sẻ với người đăng tin.
            </p>
          </section>

        </aside>
      </div>
    </main>
  </div>
</template>