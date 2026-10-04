<script setup>
// Khởi tạo logic trang Home nếu cần
</script>

<template>
  <div class="min-h-screen bg-[#f4f3ec] text-[#6b6375] font-sans antialiased selection:bg-blue-500 selection:text-white">
    <!-- Hero Section (Giống Ảnh 2) -->
    <div class="relative min-h-[430px] md:min-h-[500px] bg-[#1a1c23] text-white overflow-hidden">
      <!-- Background Video & Gradient Overlay -->
      <div class="absolute inset-0 opacity-40 overflow-hidden pointer-events-none">
        <video autoplay muted loop playsinline class="w-full h-full object-cover">
          <source src="/background.mp4" type="video/mp4" />
        </video>
      </div>
      <div class="absolute inset-0 bg-gradient-to-b from-black/60 via-black/20 to-[#1a1c23]/90"></div>

      <!-- Header / Navbar -->
      <header class="relative z-10 max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <div class="w-9 h-9 rounded-xl bg-white flex items-center justify-center font-bold text-lg text-gray-900 shadow-md">
  S
</div>
          <span class="text-lg font-semibold tracking-wide text-white">SmartProp</span>
        </div>
        <nav class="hidden md:flex items-center space-x-8 text-sm font-medium text-gray-300">
          <RouterLink to="/post" class="hover:text-white transition">Đăng tin</RouterLink>
          <RouterLink
  to="/account"
  class="hover:text-white transition"
>
  Tài khoản
</RouterLink>
        </nav>
        <div>
          <RouterLink
  to="/map" class="flex items-center space-x-2 bg-white/10 hover:bg-white/20 px-4 py-2 rounded-full text-sm backdrop-blur-md transition text-white border border-white/10">
            <span>Xem bản đồ</span>
          </RouterLink>
        </div>
      </header>

      <!-- Hero Content -->
      <div class="relative z-10 max-w-4xl mx-auto text-center px-6 pt-4 pb-16">
        <div class="inline-flex items-center space-x-2 bg-white/10 backdrop-blur-md px-4 py-1.5 rounded-full text-xs font-medium tracking-wide mb-6 text-gray-200 border border-white/10 shadow-sm">
          <span>◇</span>
          <span>Định giá có giải thích</span>
        </div>
        <h1 class="text-4xl md:text-5xl font-bold tracking-tight mb-5 text-white leading-tight">
          Nhìn xuyên một tin nhà đất
        </h1>
        <p class="text-gray-300 text-sm md:text-base max-w-2xl mx-auto leading-relaxed">
          Bản đồ GIS, giá tham chiếu kèm lý do, và đối chiếu hình ảnh — đủ cơ sở để bạn tự đánh giá một tin đăng ở Đà Nẵng.
        </p>
      </div>

      <!-- Bottom floating elements inside Hero -->
      <div class="relative z-10 max-w-7xl mx-auto px-6 flex flex-col sm:flex-row justify-between items-end gap-4 mt-4">
        <!-- Stats Box (Left) -->
        <div class="bg-white/10 backdrop-blur-xl border border-white/15 rounded-xl px-4 py-3 flex items-center space-x-3 shadow-xl">
          <div>
            <div class="text-2xl font-bold text-white tracking-tight">2.417</div>
            <div class="text-[10px] text-gray-400 uppercase tracking-widest font-semibold">TIN ĐĂNG ĐÀ NẴNG</div>
          </div>
          <RouterLink
  to="/listings" class="bg-white hover:bg-gray-100 text-gray-900 px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center space-x-1 shadow-md">
  <span>Bắt đầu tìm</span>
  </RouterLink>
        </div>

        <!-- Explain Box (Right) -->
        <div class="bg-white/10 backdrop-blur-xl border border-white/15 rounded-xl px-3 py-2.5 flex items-center space-x-2.5 shadow-xl">
          <div class="w-7 h-7 rounded-lg bg-white/10 flex items-center justify-center text-white text-xs">ℹ</div>
          <div class="text-left">
            <div class="text-xs font-semibold text-white">Giá này từ đâu ra?</div>
            <a href="#" class="text-[11px] text-gray-300 hover:text-white transition underline">Xem cách hệ thống giải thích ›</a>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content Container (Giống Ảnh 3) -->
    <main class="max-w-[1120px] mx-auto px-6 -mt-0 relative z-20 space-y-12 pb-20">
      <!-- Section: Why Choose SmartProp -->
     <section class="bg-[#e9e7e1] rounded-[28px] px-8 py-10 md:px-12 md:py-12 border-0 shadow-none">
        <div class="text-center max-w-xl mx-auto mb-10">
          <h2 class="text-[11px] font-bold uppercase tracking-widest text-gray-400 mb-2">Vì sao chọn SmartProp</h2>
          <h3 class="text-2xl md:text-3xl font-bold text-gray-900 tracking-tight">Đủ dữ liệu để tự tin ra quyết định</h3>
        </div>

       <div class="grid grid-cols-1 md:grid-cols-3 gap-3 max-w-[760px] mx-auto">
          <!-- Card 1 -->
<div class="bg-[#fcfcfd] hover:bg-[#f8f8fa] transition p-4 rounded-xl border border-gray-100 flex flex-col justify-between shadow-sm">
  <div>
    <div class="w-10 h-10 rounded-xl bg-[#1E325A] text-white flex items-center justify-center font-bold mb-4 shadow-md">
      ₫
    </div>

    <h4 class="font-bold text-base text-gray-900 mb-2">
      Định giá minh bạch
    </h4>

    <p class="text-xs text-gray-500 leading-relaxed">
      Mô hình XGBoost kèm biểu đồ SHAP giải thích từng yếu tố ảnh hưởng đến giá, không chỉ đưa ra một con số.
    </p>
  </div>
</div>

          <!-- Card 2 -->
          <div class="bg-[#fcfcfd] hover:bg-[#f8f8fa] transition p-6 rounded-2xl border border-gray-100 flex flex-col justify-between shadow-sm">
            <div>
              <div class="w-10 h-10 rounded-xl bg-[#1E325A] text-white flex items-center justify-center font-bold mb-4 shadow-md">◎</div>
              <h4 class="font-bold text-base text-gray-900 mb-2">Đối chiếu ảnh bằng AI</h4>
              <p class="text-xs text-gray-500 leading-relaxed">
                Mạng nơ-ron so khớp ảnh tin đăng để phát hiện ảnh trùng lặp, hỗ trợ quản trị viên xác minh trước khi hiển thị.
              </p>
            </div>
          </div>

          <!-- Card 3 -->
          <div class="bg-[#fcfcfd] hover:bg-[#f8f8fa] transition p-6 rounded-2xl border border-gray-100 flex flex-col justify-between shadow-sm">
            <div>
              <div class="w-10 h-10 rounded-xl bg-[#1E325A] text-white flex items-center justify-center font-bold mb-4 shadow-md">⌖</div>
              <h4 class="font-bold text-base text-gray-900 mb-2">Bản đồ GIS chi tiết</h4>
              <p class="text-xs text-gray-500 leading-relaxed">
                Toạ độ chính xác, khoảng cách đến tiện ích xung quanh tính theo dữ liệu không gian thực tế.
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- Section: Featured Listings -->
      <section>
        <div class="flex items-end justify-between mb-6">
          <div>
            <h3 class="text-[11px] font-bold uppercase tracking-widest text-gray-400 mb-1">Tin đăng nổi bật</h3>
            <h4 class="text-xl md:text-2xl font-bold text-gray-900 tracking-tight">Vừa cập nhật tại Đà Nẵng</h4>
          </div>
          <RouterLink
  to="/listings" class="text-gray-900 font-semibold text-xs hover:underline flex items-center space-x-1">
            <span>Xem tất cả</span>
            <span>›</span>
          </RouterLink>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <!-- Property Item 1 -->
          <RouterLink
  to="/listing/1"
  class="bg-white rounded-2xl overflow-hidden shadow-md border border-gray-100/80 flex flex-col cursor-pointer transition-all duration-200 hover:-translate-y-1 hover:shadow-xl"
>
            <div class="h-44 bg-gray-100 relative flex items-center justify-center border-b border-gray-500/10">
              <span class="absolute top-3 left-3 bg-amber-500 text-white text-[11px] font-semibold px-2.5 py-1 rounded-md z-10 shadow-sm">Ảnh trùng 94%</span>
              <span class="text-gray-400 text-xs">Hình ảnh nhà ở</span>
            </div>
            <div class="p-5 flex flex-col flex-grow justify-between space-y-3">
  <div>
    <h5 class="font-bold text-gray-900 text-sm mb-1">
      Nhà 3 tầng hẻm xe hơi, gần cầu Rồng
    </h5>

    <p class="text-xs text-gray-400">
      Hải Châu, Đà Nẵng
    </p>
  </div>

  <div class="text-base font-bold text-gray-900">
    4,85 tỷ đ
  </div>
</div>

</RouterLink>

          <!-- Property Item 2 -->
          <RouterLink
  to="/listing/2"
  class="bg-white rounded-2xl overflow-hidden shadow-md border border-gray-100/80 flex flex-col cursor-pointer transition-all duration-200 hover:-translate-y-1 hover:shadow-xl"
>
            <div class="h-44 bg-gray-100 relative flex items-center justify-center border-b border-gray-500/10">
              <span class="absolute top-3 left-3 bg-emerald-600 text-white text-[11px] font-semibold px-2.5 py-1 rounded-md z-10 shadow-sm">Không cảnh báo</span>
              <span class="text-gray-400 text-xs">Hình ảnh căn hộ</span>
            </div>
            <div class="p-5 flex flex-col flex-grow justify-between space-y-3">
              <div>
                <h5 class="font-bold text-gray-900 text-sm mb-1">Căn hộ 2PN view sông Hàn</h5>
                <p class="text-xs text-gray-400">Hải Châu, Đà Nẵng</p>
              </div>
              <div class="text-base font-bold text-gray-900">3,20 tỷ ₫</div>
            </div>
          </RouterLink>

          <!-- Property Item 3 -->
<RouterLink
  to="/listing/3"
  class="bg-white rounded-2xl overflow-hidden shadow-md border border-gray-100/80 flex flex-col cursor-pointer transition-all duration-200 hover:-translate-y-1 hover:shadow-xl"
>
  <!-- Image -->
  <div
    class="h-44 bg-gray-100 relative flex items-center justify-center border-b border-gray-500/10"
  >
    <span
      class="absolute top-3 left-3 bg-emerald-600 text-white text-[11px] font-semibold px-3 py-1.5 rounded-lg"
    >
      Giá hợp lý
    </span>

    <span class="text-gray-400 text-xs">
      Hình ảnh đất nền
    </span>
  </div>

  <!-- Content -->
  <div class="p-5 flex flex-col flex-grow justify-between space-y-3">
    <div>
      <h5 class="font-bold text-gray-900 text-sm mb-1">
        Đất nền Hoà Xuân, sổ đỏ riêng
      </h5>

      <p class="text-xs text-gray-400">
        Cẩm Lệ, Đà Nẵng
      </p>
    </div>

    <div class="text-base font-bold text-gray-900">
      2,95 tỷ đ
    </div>
  </div>
</RouterLink>
</div>
      </section>

      <!-- Section: 4 Steps to Post -->
      <section class="bg-[#1E325A] text-white rounded-3xl p-8 md:p-10 relative overflow-hidden shadow-xl">
        <div class="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-6">
          <div>
            <h3 class="text-[11px] font-bold uppercase tracking-widest text-gray-400 mb-1">4 bước để đăng tin</h3>
            <h4 class="text-xl md:text-2xl font-bold text-white tracking-tight">Đăng tin của bạn trong vài phút</h4>
          </div>
          <RouterLink to="/post" class="inline-flex items-center justify-center space-x-2 bg-white text-gray-900 hover:bg-gray-100 px-5 py-2.5 rounded-xl font-semibold text-xs transition shadow-md">
            <span>Bắt đầu đăng tin</span>
            </RouterLink>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div class="bg-white/5 border border-white/10 p-4 rounded-2xl">
            <div class="text-gray-400 font-bold text-sm mb-1">01</div>
            <div class="text-xs font-medium text-gray-200">Loại tin đăng</div>
          </div>
          <div class="bg-white/5 border border-white/10 p-4 rounded-2xl">
            <div class="text-gray-400 font-bold text-sm mb-1">02</div>
            <div class="text-xs font-medium text-gray-200">Thông tin & ảnh</div>
          </div>
          <div class="bg-white/5 border border-white/10 p-4 rounded-2xl">
            <div class="text-gray-400 font-bold text-sm mb-1">03</div>
            <div class="text-xs font-medium text-gray-200">Xác nhận từ AI</div>
          </div>
          <div class="bg-white/5 border border-white/10 p-4 rounded-2xl">
            <div class="text-gray-400 font-bold text-sm mb-1">04</div>
            <div class="text-xs font-medium text-gray-200">Xem lại & đăng tin</div>
          </div>
        </div>
      </section>

    </main>

    <!-- Footer -->
    <footer class="border-t border-gray-200/60 bg-[#f4f3ec] py-10">
      <div class="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6 text-xs text-gray-500">
        <div class="flex items-center space-x-3">
          <div class="w-7 h-7 rounded-lg bg-[#1E325A] flex items-center justify-center font-bold text-white text-xs">S</div>
          <span class="font-bold text-gray-900 text-sm">SmartProp</span>
        </div>
        <div class="flex flex-wrap justify-center gap-6 font-medium">
        </div>
        <div class="text-gray-400">ĐÀ NẴNG</div>
      </div>
      <div class="max-w-7xl mx-auto px-6 mt-6 pt-6 border-t border-gray-200/40 text-center text-[11px] text-gray-400">
        © 2026 SmartProp 
      </div>
    </footer>
  </div>
</template>