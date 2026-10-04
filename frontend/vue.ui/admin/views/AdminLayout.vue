<template>
  <div class="section">
    <!-- Header phía trên có chèn video nền -->
    <div class="header">
      <video autoplay muted loop playsinline class="header-video">
        <source src="/background.mp4" type="video/mp4" />
        Trình duyệt của bạn không hỗ trợ thẻ video.
      </video>

      <!-- Lớp phủ tối mờ -->
      <div class="video-overlay"></div>

      <!-- Nội dung chữ và nút bên trên -->
      <div class="hcontent">
        <div class="left">
          <div class="badge">
            <div class="qu-n-tr">QUẢN TRỊ</div>
          </div>
          <div class="b-ng-i-u-khi-n">Bảng điều khiển</div>
          <div class="theo-d-i-tin-ng-n">
            Theo dõi tin đăng, người dùng và trạng thái xử lý AI trong toàn hệ thống.
          </div>
        </div>
        <div class="postbtn">
          <div class="ng-tin">Đăng tin</div>
          <div class="div">+</div>
        </div>
      </div>
    </div>

    <!-- Phần thân chứa Sidebar và Nội dung thay đổi -->
    <div class="body-layout">
      <!-- Sidebar bên trái -->
      <div class="sidebar">
        <div class="m-c-qu-n-tr">MỤC QUẢN TRỊ</div>
        
        <router-link to="/admin/dashboard" class="nav" active-class="active-nav">
          <div class="th-ng-k-t-ng-quan">Thống kê tổng quan</div>
        </router-link>

        <router-link to="/admin/posts" class="nav2" active-class="active-nav">
          <div class="tin-ch-duy-t">Tin chờ duyệt</div>
          <div class="count">
            <div class="_18">18</div>
          </div>
        </router-link>

        <router-link to="/admin/users" class="nav2" active-class="active-nav">
          <div class="ng-i-d-ng">Người dùng</div>
        </router-link>

        <router-link to="/admin/reports" class="nav2" active-class="active-nav">
          <div class="b-o-c-o-tin-ng">Báo cáo tin đăng</div>
          <div class="count">
            <div class="_7">7</div>
          </div>
        </router-link>
        <router-link to="/admin/audit-logs" class="nav" active-class="active-nav">
      <div class="nh-t-ký-ki-m-to-n">Nhật ký kiểm toán</div>
    </router-link>

    <router-link to="/admin/ai-config" class="nav" active-class="active-nav">
      <div class="c-u-h-nh-ai">Cấu hình AI</div>
    </router-link>
      </div>

      <!-- Khu vực hiển thị các trang con -->
      <div class="main-content-area">
        <router-view />
      </div>
    </div>
  </div>
</template>

<style scoped>
.section {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #e5e5e5;
  font-family: sans-serif;
}

.header {
  position: relative;
  overflow: hidden;
  color: white;
  padding: 40px;
}

.header-video {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  min-width: 100%;
  min-height: 100%;
  width: auto;
  height: auto;
  object-fit: cover;
  z-index: 1;
}

.video-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(11, 19, 36, 0.75);
  z-index: 2;
}

.hcontent {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  z-index: 3;
}

.left {
  text-align: left;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.badge {
  background: rgba(255, 255, 255, 0.15);
  padding: 4px 10px;
  border-radius: 4px;
  display: inline-block;
  margin-bottom: 8px;
}

.qu-n-tr {
  font-size: 10px;
  letter-spacing: 1px;
}

.b-ng-i-u-khi-n {
  font-size: 26px;
  font-weight: bold;
  margin-bottom: 6px;
}

.theo-d-i-tin-ng-n {
  font-size: 13px;
  color: #cbd5e1;
}

.postbtn {
  background: #ffffff;
  color: #1e325a;
  padding: 10px 20px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: bold;
  cursor: pointer;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: opacity 0.2s;
}

.postbtn:hover {
  opacity: 0.9;
}

.body-layout {
  display: flex;
  flex: 1;
}

.sidebar {
  width: 260px;
  background: #f4f5f7;
  border-right: 1px solid #e5e7eb;
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.m-c-qu-n-tr {
  font-size: 11px;
  color: #6b7280;
  font-weight: bold;
  margin-bottom: 8px;
  padding-left: 8px;
  text-align: left;
}

.nav, .nav2 {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-radius: 8px;
  color: #374151;
  text-decoration: none;
  font-size: 14px;
  text-align: left;
  transition: background 0.2s;
}

/* Chuẩn màu xanh navy #1E325A khi hover hoặc active */
.nav:hover, .nav2:hover, .active-nav {
  background: #1e325a;
  color: #ffffff;
}

/* Đổi màu nền badge số 18 và 7 thành màu xám nhạt giống hình mẫu */
.count {
  background: #e2e8f0;
  color: #1e293b;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: bold;
}

/* Khi menu đang được chọn (active), đổi màu chữ bên trong badge thành sáng hơn hoặc giữ nguyên tùy ý */
.active-nav .count {
  background: #cbd5e1;
  color: #0f172a;
}

.main-content-area {
  flex: 1;
  padding: 30px;
  background: #fdfbf7;
  overflow-y: auto;
}
</style>