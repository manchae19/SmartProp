<template>
  <div class="login-container">
    <div class="section">
      <!-- Thẻ video làm nền -->
      <video class="bg-video" autoplay loop muted playsinline>
        <source src="/background.mp4" type="video/mp4" />
      </video>

      <div class="gradient-overlay"></div>
      
      <!-- Chữ Đà Nẵng nằm ngang ở góc dưới bên trái -->
      <div class="horizontal-location">ĐÀ NẴNG · C2SE.01</div>

      <div class="content-wrapper">
        <!-- Cột trái -->
        <div class="left-col">
          <div class="brand">
            <div class="logo">
              <div class="s">S</div>
            </div>
            <div class="smart-prop">SmartProp</div>
          </div>
          
          <div class="hero-content">
            <div class="text-group">
              <h1 class="main-title">Ba vai trò, ba quyền hạn</h1>
              <p class="sub-title">
                Phân quyền được áp dụng ngay sau khi xác thực. Mỗi vai trò chỉ thấy phần chức năng thuộc quyền của mình.
              </p>
            </div>
            
            <div class="roles">
              <div class="role-card">
                <span class="role-num">01</span>
                <div>
                  <div class="role-title">Người mua / Người thuê</div>
                  <div class="role-desc">Tìm kiếm, lưu tin, xem định giá và phân tích ảnh.</div>
                </div>
              </div>
              
              <div class="role-card">
                <span class="role-num">02</span>
                <div>
                  <div class="role-title">Chủ nhà / Môi giới</div>
                  <div class="role-desc">Tạo tin, tải nhiều ảnh, theo dõi trạng thái duyệt.</div>
                </div>
              </div>
              
              <div class="role-card">
                <span class="role-num">03</span>
                <div>
                  <div class="role-title">Quản trị viên</div>
                  <div class="role-desc">Quản lý người dùng, tin đăng và case bị cảnh báo.</div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="footer-spacer"></div>
        </div>
        
        <!-- Cột phải: Form Đăng nhập / Đăng ký -->
        <div class="right-col">
          <div class="auth-card">
            <div class="toggle">
              <button 
                type="button"
                class="toggle-btn" 
                :class="{ active: isLoginTab }" 
                @click="isLoginTab = true"
              >
                Đăng nhập
              </button>
              <button 
                type="button"
                class="toggle-btn" 
                :class="{ active: !isLoginTab }" 
                @click="isLoginTab = false"
              >
                Đăng ký
              </button>
            </div>
            
            <div class="titles">
              <h2 class="welcome-title">
                {{ isLoginTab ? 'Chào bạn trở lại' : 'Tạo tài khoản mới' }}
              </h2>
              <p class="welcome-desc">
                {{ isLoginTab ? 'Đăng nhập để xem lại tin yêu thích và kết quả đánh giá giá đã lưu.' : 'Tạo tài khoản để lưu tin yêu thích, đăng tin bán/cho thuê và nhận định giá tức thì.' }}
              </p>
            </div>
            
            <form class="form" @submit.prevent="handleSubmit">
              <!-- Họ và tên (Chỉ hiển thị khi Đăng ký) -->
              <div class="field" v-if="!isLoginTab">
                <label class="label" for="name-input">Họ và tên</label>
                <div class="input-box">
                  <input 
                    type="text" 
                    id="name-input" 
                    v-model="fullName" 
                    placeholder="Nguyễn Văn A" 
                    required 
                  />
                </div>
              </div>

              <!-- Email -->
              <div class="field">
                <label class="label" for="email-input">Email</label>
                <div class="input-box">
                  <input 
                    type="email" 
                    id="email-input" 
                    v-model="email" 
                    placeholder="ban@email.com" 
                    required 
                  />
                </div>
              </div>
              
              <!-- Mật khẩu -->
              <div class="field">
                <label class="label" for="password-input">Mật khẩu</label>
                <div class="input-box">
                  <input 
                    type="password" 
                    id="password-input" 
                    v-model="password" 
                    placeholder="Tối thiểu 8 ký tự" 
                    required 
                  />
                </div>
              </div>

              <!-- Xác nhận mật khẩu (Chỉ hiển thị khi Đăng ký) -->
              <div class="field" v-if="!isLoginTab">
                <label class="label" for="confirm-password-input">Xác nhận mật khẩu</label>
                <div class="input-box">
                  <input 
                    type="password" 
                    id="confirm-password-input" 
                    v-model="confirmPassword" 
                    placeholder="Nhập lại mật khẩu" 
                    required 
                  />
                </div>
              </div>
              
              <!-- Nút Submit -->
              <button type="submit" class="submit-btn">
                <span>{{ isLoginTab ? 'Đăng nhập' : 'Đăng ký' }}</span>
              </button>
              
              <!-- Dòng chữ bảo mật -->
              <p class="security-note">
                Mật khẩu được băm, phiên làm việc dùng JWT, kết nối qua TLS.
              </p>
              
              <!-- Chuyển đổi đăng nhập/đăng ký -->
              <div class="switch-auth-mode">
                <span v-if="isLoginTab">Chưa có tài khoản? <a href="#" @click.prevent="isLoginTab = false">Đăng ký ngay</a></span>
                <span v-else>Đã có tài khoản? <a href="#" @click.prevent="isLoginTab = true">Đăng nhập</a></span>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const isLoginTab = ref(true)
const fullName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')

const handleSubmit = () => {
  if (isLoginTab.value) {
    console.log('Xử lý đăng nhập:', { email: email.value, password: password.value })
    alert('Đăng nhập thành công!')
  } else {
    if (password.value !== confirmPassword.value) {
      alert('Mật khẩu xác nhận không khớp!')
      return
    }
    console.log('Xử lý đăng ký:', { fullName: fullName.value, email: email.value, password: password.value })
    alert('Đăng ký thành công!')
  }
}
</script>

<style>
html, body, #app {
  margin: 0 !important;
  padding: 0 !important;
  min-width: 100vw;
  min-height: 100vh;
  overflow: auto !important;
  background-color: #0b111e !important;
}
</style>

<style scoped>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
}

.login-container {
  background: #0b111e;
  min-width: 100vw;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  overflow: auto;
}

.section {
  width: 95vw;
  min-width: 1200px;
  height: 92vh;
  min-height: 720px;
  max-width: 1600px;
  max-height: 900px;
  position: relative;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.12);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bg-video {
  width: 100%;
  height: 100%;
  position: absolute;
  inset: 0;
  object-fit: cover;
  z-index: 1;
}

.gradient-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    75deg,
    rgba(10, 18, 34, 0.92) 0%,
    rgba(10, 18, 34, 0.65) 50%,
    rgba(239, 237, 232, 0.85) 100%
  );
  z-index: 2;
}

.horizontal-location {
  position: absolute;
  left: 56px;
  bottom: 40px;
  z-index: 4;
  color: rgba(255, 255, 255, 0.55);
  font-family: monospace;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 3px;
  text-transform: uppercase;
}

.content-wrapper {
  position: absolute;
  inset: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 44px 56px;
  z-index: 3;
  overflow: auto;
}

.left-col {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
  width: 52%;
  min-width: 480px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.logo {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 10px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.s {
  color: #1e325a;
  font-weight: 800;
  font-size: 20px;
}

.smart-prop {
  color: #ffffff;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.hero-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin: auto 0;
}

.text-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  max-width: 540px;
  text-align: left;
}

.main-title {
  color: #ffffff;
  font-size: 36px;
  font-weight: 700;
  line-height: 1.2;
  text-align: left;
}

.sub-title {
  color: rgba(255, 255, 255, 0.85);
  font-size: 14.5px;
  line-height: 1.5;
  text-align: left;
}

.roles {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  max-width: 540px;
}

.role-card {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  padding: 12px 16px;
  display: flex;
  gap: 16px;
  align-items: center;
  backdrop-filter: blur(10px);
  text-align: left;
}

.role-num {
  color: rgba(255, 255, 255, 0.6);
  font-family: monospace;
  font-size: 13px;
  font-weight: 700;
}

.role-title {
  color: #ffffff;
  font-size: 14.5px;
  font-weight: 600;
  margin-bottom: 2px;
}

.role-desc {
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  line-height: 1.35;
}

.footer-spacer {
  height: 20px;
}

.right-col {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  height: 100%;
  width: 44%;
  min-width: 380px;
}

.auth-card {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.95);
  padding: 18px 28px;
  width: 100%;
  max-width: 420px;
  backdrop-filter: blur(20px);
  box-shadow: 0 20px 45px rgba(0, 0, 0, 0.18);
  text-align: left;
}

.toggle {
  background: rgba(30, 50, 90, 0.06);
  border-radius: 999px;
  padding: 4px;
  display: flex;
  gap: 6px;
}

.toggle-btn {
  border-radius: 999px;
  padding: 6px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  cursor: pointer;
  font-size: 13px;
  color: rgba(30, 50, 90, 0.65);
  font-weight: 600;
  border: none;
  background: transparent;
  transition: all 0.2s ease;
}

.toggle-btn.active {
  background: #ffffff;
  color: #1e325a;
  font-weight: 700;
  box-shadow: 0 3px 10px rgba(30, 50, 90, 0.12);
}

.titles {
  margin-top: 8px;
  text-align: left;
}

.welcome-title {
  color: #1e325a;
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 2px;
  text-align: left;
}

.welcome-desc {
  color: rgba(30, 50, 90, 0.65);
  font-size: 11.5px;
  line-height: 1.35;
  text-align: left;
}

.form {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: flex-start;
  width: 100%;
}

.label {
  color: #1e325a;
  font-size: 11px;
  font-weight: 600;
  text-align: left;
  display: block;
  width: 100%;
}

.input-box {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 7px;
  border: 1px solid rgba(30, 50, 90, 0.18);
  display: flex;
  align-items: center;
  width: 100%;
}

.input-box input {
  width: 100%;
  color: #1e325a;
  font-size: 12.5px;
  outline: none;
  background: transparent;
  border: none;
  padding: 7px 10px;
  text-align: left;
}

.submit-btn {
  background: #1e325a;
  border-radius: 999px;
  padding: 8px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  margin-top: 4px;
  border: none;
  width: 100%;
  transition: background 0.2s, transform 0.1s;
}

.submit-btn:hover {
  background: #284278;
}

.submit-btn:active {
  transform: scale(0.98);
}

.submit-btn span {
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
}

.security-note {
  color: rgba(30, 50, 90, 0.5);
  font-size: 10px;
  text-align: center;
  margin-top: 4px;
  line-height: 1.3;
}

.switch-auth-mode {
  text-align: center;
  font-size: 11.5px;
  color: rgba(30, 50, 90, 0.7);
  margin-top: 4px;
}

.switch-auth-mode a {
  color: #1e325a;
  font-weight: 600;
  text-decoration: none;
}

.switch-auth-mode a:hover {
  text-decoration: underline;
}
</style>