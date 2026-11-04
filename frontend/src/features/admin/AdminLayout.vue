<script setup>
import {ref,nextTick,watch} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import {api} from '../auth/api.js'
import AppHeader from '../../components/layout/AppHeader.vue'
const router=useRouter(),route=useRoute(),pending=ref('—'),openReports=ref('—')
api('/admin/dashboard').then(s=>{pending.value=s.pendingProperties;openReports.value=s.openReports}).catch(()=>{})
watch(()=>route.path,async()=>{await nextTick();document.getElementById('page-content')?.focus({preventScroll:true})})
</script>
<template>
  <div class="admin-layout">
    <a href="#page-content" class="fixed -top-20 left-4 z-[100] rounded-control bg-white px-5 py-3 text-sm font-semibold shadow-lg focus:top-3">Đến nội dung chính</a>
    <AppHeader />
  <div class="section">
    
    <div class="header">
      <video autoplay muted loop playsinline class="header-video">
        <source src="/background.mp4" type="video/mp4" />
        Trình duyệt của bạn không hỗ trợ thẻ video.
      </video>

      
      <div class="video-overlay"></div>

      
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
        <button type="button" class="postbtn" @click="router.push('/post')">
          <div class="ng-tin">Đăng tin</div>
          <div class="div">+</div>
        </button>
      </div>
    </div>

    
    <div class="body-layout">
      
      <aside class="sidebar" aria-label="Điều hướng quản trị">
        <div class="m-c-qu-n-tr">MỤC QUẢN TRỊ</div>
        
        <router-link to="/admin/dashboard" class="nav" active-class="active-nav">
          <div class="th-ng-k-t-ng-quan">Thống kê tổng quan</div>
        </router-link>

        <router-link to="/admin/posts" class="nav2" active-class="active-nav">
          <div class="tin-ch-duy-t">Tin chờ duyệt</div>
          <div class="count">
            <div class="_18">{{pending}}</div>
          </div>
        </router-link>

        <router-link to="/admin/broker-applications" class="nav2" active-class="active-nav"><div>Duyệt quyền đăng tin</div></router-link>

        <router-link to="/admin/users" class="nav2" active-class="active-nav">
          <div class="ng-i-d-ng">Người dùng</div>
        </router-link>

        <router-link to="/admin/reports" class="nav2" active-class="active-nav">
          <div class="b-o-c-o-tin-ng">Báo cáo tin đăng</div>
          <div class="count">
            <div class="_7">{{openReports}}</div>
          </div>
        </router-link>
        <router-link to="/admin/audit-logs" class="nav" active-class="active-nav">
      <div class="nh-t-ký-ki-m-to-n">Nhật ký kiểm toán</div>
    </router-link>

    <router-link to="/admin/projects" class="nav" active-class="active-nav"><div>Dự án</div></router-link>
    <router-link to="/admin/ai-config" class="nav" active-class="active-nav">
      <div class="c-u-h-nh-ai">Cấu hình AI</div>
    </router-link>
      </aside>

      
      <main id="page-content" tabindex="-1" class="main-content-area outline-none"><router-view /></main>
    </div>
  </div>
  </div>
</template>

<style scoped>
.admin-layout{min-height:100dvh;background:var(--color-brand-cream);color:var(--color-brand-navy)}
.section {
  display: flex;
  flex-direction: column;
  min-height: calc(100dvh - var(--sp-header-height));
  background-color: #e5e5e5;
  font-family: var(--font-sans);
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
  font-size:13px;
  letter-spacing: 1px;
}

.b-ng-i-u-khi-n {
  font-size: 28px;
  font-weight: bold;
  margin-bottom: 6px;
}

.theo-d-i-tin-ng-n {
  font-size: 14px;
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
  font-size: 12px;
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
  font-size: var(--text-sm);
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
  font-size: 12px;
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
@media(max-width:900px){.body-layout{flex-direction:column}.sidebar{width:100%;display:flex;flex-direction:row;flex-wrap:wrap;gap:8px;border-right:0;border-bottom:1px solid #e4ded3;padding:16px}.sidebar>.m-c-qu-n-tr{width:100%;margin-bottom:4px}.sidebar>a{padding:10px 12px;margin:0;font-size:13px}.main-content-area{width:100%;min-width:0;padding:20px}.header{padding:24px}.hcontent{flex-wrap:wrap;gap:20px}}
.main-content-area{min-width:0}
</style>
