<template>
  <div class="login-container">
    <div class="section">
      <!-- Thẻ video làm nền -->
      <video class="bg-video" autoplay loop muted playsinline>
        <source src="/background.mp4" type="video/mp4" />
      </video>

      <div class="gradient-overlay"></div>
      
      <!-- Chữ Đà Nẵng nằm ngang ở góc dưới bên trái -->
      <div class="horizontal-location">ĐÀ NẴNG</div>

      <div class="content-wrapper">
        <!-- Cột trái -->
        <div class="left-col">
          <div class="brand">
            <div class="logo">
              <div class="s">S</div>
            </div>
            <div class="smart-prop">SmartProp</div>
          </div>

          
          <div class="footer-spacer"></div>
        </div>
        
        <!-- Cột phải: Các trạng thái form -->
        <div class="right-col">
          <div class="auth-card">
            
            <!-- TRƯỜNG HỢP 3: ĐẶT MẬT KHẨU MỚI -->
            <template v-if="isResettingPassword">
              <div class="titles">
                <h2 class="welcome-title">Đặt mật khẩu mới</h2>
                <p class="welcome-desc">
                  Tạo mật khẩu mới cho tài khoản <span class="highlight-email">{{ email || 'ban@email.com' }}</span>
                </p>
              </div>

              <form class="form" @submit.prevent="handleResetPasswordSubmit">
                <div class="field">
                  <label class="label" for="new-password">Mật khẩu mới</label>
                  <div class="input-box">
                    <input 
                      type="password" 
                      id="new-password" 
                      v-model="newPassword" 
                      placeholder="Tối thiểu 8 ký tự" 
                      required 
                    />
                  </div>
                </div>

                <div class="field">
                  <label class="label" for="confirm-new-password">Xác nhận mật khẩu mới</label>
                  <div class="input-box">
                    <input 
                      type="password" 
                      id="confirm-new-password" 
                      v-model="confirmNewPassword" 
                      placeholder="Nhập lại mật khẩu" 
                      required 
                    />
                  </div>
                  
                  <div class="password-strength-container" v-if="newPassword.length > 0">
                    <div class="strength-bars">
                      <div class="strength-bar" :class="{ active: passwordScore >= 1, [strengthColorClass]: passwordScore >= 1 }"></div>
                      <div class="strength-bar" :class="{ active: passwordScore >= 2, [strengthColorClass]: passwordScore >= 2 }"></div>
                      <div class="strength-bar" :class="{ active: passwordScore >= 3, [strengthColorClass]: passwordScore >= 3 }"></div>
                      <div class="strength-bar" :class="{ active: passwordScore >= 4, [strengthColorClass]: passwordScore >= 4 }"></div>
                    </div>
                    <span class="strength-label" :style="{ color: strengthHexColor }">{{ strengthText }}</span>
                  </div>
                </div>

                <button type="submit" class="submit-btn mt-10">
                  <span>Đặt lại mật khẩu</span>
                </button>
                
                <p class="security-note">
                  Mật khẩu được mã hóa, phiên làm việc dùng JWT, kết nối qua TLS.
                </p>
              </form>
            </template>

            <!-- TRƯỜNG HỢP 2: ĐÃ GỬI EMAIL THÀNH CÔNG -->
            <template v-else-if="isEmailSent">
              <div class="sent-success-container">
                <div class="success-icon-box">
                  <svg class="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                </div>
                
                <div class="titles text-center">
                  <h2 class="welcome-title">Kiểm tra email của bạn</h2>
                  <p class="welcome-desc">
                    Chúng tôi đã gửi liên kết đặt lại mật khẩu đến <span class="highlight-email">{{ email || 'ban@email.com' }}</span>
                  </p>
                </div>

                <div class="sent-actions">
                  <button type="button" class="submit-btn" @click="handleOpenEmailApp">
                    <span>Mở ứng dụng email</span>
                  </button>
                  
                  <p class="resend-text">
                    (Mock) Đã nhận được email? <a href="#" @click.prevent="goToResetPasswordStep">Nhấp để đặt lại mật khẩu</a>
                  </p>
                  
                  <p class="resend-text mt-5">
                    Không nhận được email? <a href="#" @click.prevent="handleResendEmail">Gửi lại</a>
                  </p>
                  
                  <a href="#" class="admin-link mt-10" @click.prevent="backToLogin">
                    Quay lại đăng nhập
                  </a>
                </div>
              </div>
            </template>

            <!-- TRƯỜNG HỢP 1: ĐĂNG NHẬP / ĐĂNG KÝ / KHÔI PHỤC MẬT KHẨU -->
            <template v-else>
              <!-- Nút Quay lại đăng nhập (Chỉ hiện khi đang ở màn hình Quên mật khẩu) -->
              <a href="#" class="back-link-top" v-if="isForgotPassword" @click.prevent="isForgotPassword = false">
                &lt; Quay lại đăng nhập
              </a>

              <div class="toggle" v-if="!isForgotPassword">
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
              
              <div class="titles" :class="{ 'mt-titles-forgot': isForgotPassword }">
                <h2 class="welcome-title">
                  {{ isForgotPassword ? 'Khôi phục mật khẩu' : (isLoginTab ? 'Chào bạn trở lại' : 'Tạo tài khoản mới') }}
                </h2>
                <p class="welcome-desc">
                  {{ isForgotPassword ? 'Nhập email đã đăng ký, chúng tôi sẽ gửi liên kết để đặt lại mật khẩu.' : (isLoginTab ? 'Đăng nhập để xem lại tin yêu thích và kết quả đánh giá giá đã lưu.' : 'Đăng ký tài khoản mới để trải nghiệm đầy đủ tính năng hệ thống.') }}
                </p>
              </div>
              
              <form class="form" @submit.prevent="handleSubmit">
                <div class="field" v-if="!isLoginTab && !isForgotPassword">
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
                
                <div class="field" v-if="!isForgotPassword">
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
                  
                  <div class="forgot-row" v-if="isLoginTab">
                    <a href="#" class="forgot-link-new" @click.prevent="isForgotPassword = true">
                      Quên mật khẩu?
                    </a>
                  </div>
                </div>

                <div class="field" v-if="!isLoginTab && !isForgotPassword">
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
                
                <!-- Nút submit thay đổi chữ cho phù hợp màn hình quên mật khẩu -->
                <button type="submit" class="submit-btn">
                  <span>{{ isForgotPassword ? 'Gửi liên kết đặt lại ↗' : (isLoginTab ? 'Đăng nhập' : 'Đăng ký') }}</span>
                </button>
                
                <!-- Chú thích chân trang thay đổi theo thiết kế mới khi ở màn hình quên mật khẩu -->
                <p class="security-note">
                  {{ isForgotPassword ? 'Liên kết có hiệu lực trong 15 phút và chỉ dùng được một lần.' : 'Mật khẩu được mã hóa, phiên làm việc dùng JWT, kết nối qua TLS.' }}
                </p>
                
                <a href="#" class="admin-link" v-if="!isForgotPassword" @click.prevent="handleLinkClick">
                  {{ isLoginTab ? 'Đăng nhập quản trị' : 'Đã có tài khoản? Đăng nhập' }}
                </a>
              </form>
            </template>

          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const isLoginTab = ref(true)
const isForgotPassword = ref(false)
const isEmailSent = ref(false)
const isResettingPassword = ref(false)

const fullName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const newPassword = ref('')
const confirmNewPassword = ref('')

const passwordScore = computed(() => {
  const val = newPassword.value
  if (!val) return 0
  let score = 0
  if (val.length >= 8) score++
  if (/[A-Z]/.test(val) && /[a-z]/.test(val)) score++
  if (/[0-9]/.test(val)) score++
  if (/[^A-Za-z0-9]/.test(val)) score++
  return Math.max(1, score)
})

const strengthText = computed(() => {
  switch (passwordScore.value) {
    case 1: return 'Yếu'
    case 2: return 'Trung bình'
    case 3: return 'Khá'
    case 4: return 'Mạnh'
    default: return ''
  }
})

const strengthHexColor = computed(() => {
  switch (passwordScore.value) {
    case 1: return '#ef4444'
    case 2: return '#f59e0b'
    case 3: return '#3b82f6'
    case 4: return '#10b981'
    default: return '#10b981'
  }
})

const strengthColorClass = computed(() => {
  switch (passwordScore.value) {
    case 1: return 'bar-weak'
    case 2: return 'bar-medium'
    case 3: return 'bar-good'
    case 4: return 'bar-strong'
    default: return 'bar-strong'
  }
})

const handleSubmit = () => {
  if (isForgotPassword.value) {
    console.log('Xử lý gửi liên kết khôi phục cho email:', email.value)
    isEmailSent.value = true
  } else if (isLoginTab.value) {
    // Logic xác thực và phân quyền đăng nhập
    console.log('Xử lý đăng nhập:', { email: email.value, password: password.value })
    
    // Kiểm tra mẫu: Nếu email chứa từ khóa "admin" hoặc mật khẩu admin định sẵn
    const isAdmin = email.value.toLowerCase().includes('admin') || email.value === 'admin@smartprop.vn'
    
    const token = 'mock-jwt-token-' + Date.now()
    const role = isAdmin ? 'admin' : 'user'

    // Lưu vào localStorage phục vụ cho Guard kiểm tra quyền
    localStorage.setItem('token', token)
    localStorage.setItem('role', role)

    if (role === 'admin') {
      
      router.push('/admin')
    } else {
      
      router.push('/home')
    }
  } else {
    if (password.value !== confirmPassword.value) {
      alert('Mật khẩu xác nhận không khớp!')
      return
    }
    console.log('Xử lý đăng ký:', { fullName: fullName.value, email: email.value, password: password.value })
    alert('Đăng ký thành công! Vui lòng đăng nhập.')
    isLoginTab.value = true
  }
}

const handleResetPasswordSubmit = () => {
  if (newPassword.value.length < 8) {
    alert('Mật khẩu mới phải có tối thiểu 8 ký tự!')
    return
  }
  if (newPassword.value !== confirmNewPassword.value) {
    alert('Mật khẩu mới và xác nhận mật khẩu không khớp!')
    return
  }
  alert('Đặt lại mật khẩu thành công! Vui lòng đăng nhập lại.')
  backToLogin()
}

const handleLinkClick = () => {
  if (isLoginTab.value) {
    // Tự động điền email admin để thuận tiện test
    email.value = 'admin@smartprop.vn'
    password.value = 'Admin@123'
    alert('Đã điền sẵn tài khoản Quản trị mẫu. Bấm "Đăng nhập" để truy cập trang Admin!')
  } else {
    isLoginTab.value = true
  }
}

const handleOpenEmailApp = () => {
  window.location.href = 'mailto:'
}

const goToResetPasswordStep = () => {
  isEmailSent.value = false
  isResettingPassword.value = true
}

const handleResendEmail = () => {
  alert('Đã gửi lại email hướng dẫn khôi phục mật khẩu!')
}

const backToLogin = () => {
  isEmailSent.value = false
  isForgotPassword.value = false
  isResettingPassword.value = false
  isLoginTab.value = true
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
  padding: 30px 34px;
  width: 100%;
  max-width: 420px;
  backdrop-filter: blur(20px);
  box-shadow: 0 20px 45px rgba(0, 0, 0, 0.18);
  text-align: left;
}

.back-link-top {
  display: inline-flex;
  align-items: center;
  color: rgba(30, 50, 90, 0.7);
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  margin-bottom: 14px;
}

.back-link-top:hover {
  color: #1e325a;
  text-decoration: underline;
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
  padding: 10px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  cursor: pointer;
  font-size: 14px;
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
  margin-top: 16px;
  text-align: left;
}

.mt-titles-forgot {
  margin-top: 4px !important;
}

.text-center {
  text-align: center !important;
}

.welcome-title {
  color: #1e325a;
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 4px;
}

.welcome-desc {
  color: rgba(30, 50, 90, 0.65);
  font-size: 13px;
  line-height: 1.45;
}

.highlight-email {
  font-weight: 600;
  color: #1e325a;
}

.sent-success-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 0;
}

.success-icon-box {
  width: 56px;
  height: 56px;
  background: rgba(16, 185, 129, 0.12);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.check-icon {
  width: 28px;
  height: 28px;
  color: #10b981;
}

.sent-actions {
  margin-top: 20px;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.resend-text {
  font-size: 12.5px;
  color: rgba(30, 50, 90, 0.65);
  text-align: center;
}

.resend-text a {
  color: #1e325a;
  font-weight: 600;
  text-decoration: none;
}

.resend-text a:hover {
  text-decoration: underline;
}

.password-strength-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  margin-top: 6px;
}

.strength-bars {
  display: flex;
  gap: 6px;
  flex: 1;
  margin-right: 12px;
}

.strength-bar {
  height: 4px;
  flex: 1;
  background: rgba(30, 50, 90, 0.15);
  border-radius: 2px;
  transition: background 0.3s ease;
}

.strength-bar.bar-weak { background: #ef4444 !important; }
.strength-bar.bar-medium { background: #f59e0b !important; }
.strength-bar.bar-good { background: #3b82f6 !important; }
.strength-bar.bar-strong { background: #10b981 !important; }

.strength-label {
  font-size: 12px;
  font-weight: 600;
}

.mt-5 {
  margin-top: 5px;
}

.mt-10 {
  margin-top: 10px;
}

.form {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  align-items: flex-start;
  width: 100%;
}

.label {
  color: #1e325a;
  font-size: 12.5px;
  font-weight: 600;
  text-align: left;
  display: block;
}

.forgot-row {
  display: flex;
  justify-content: flex-end;
  width: 100%;
  margin-top: 4px;
}

.forgot-link-new {
  color: rgba(30, 50, 90, 0.7);
  font-size: 12px;
  text-decoration: none;
  font-weight: 500;
}

.forgot-link-new:hover {
  color: #1e325a;
  text-decoration: underline;
}

.input-box {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 10px;
  border: 1px solid rgba(30, 50, 90, 0.18);
  display: flex;
  align-items: center;
  width: 100%;
}

.input-box input {
  width: 100%;
  color: #1e325a;
  font-size: 14px;
  outline: none;
  background: transparent;
  border: none;
  padding: 11px 14px;
  text-align: left;
}

.submit-btn {
  background: #1e325a;
  border-radius: 999px;
  padding: 12px 0;
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
  font-size: 14.5px;
  font-weight: 600;
}

.security-note {
  color: rgba(30, 50, 90, 0.5);
  font-size: 11px;
  text-align: center;
  margin-top: 2px;
  line-height: 1.4;
}

.admin-link {
  color: rgba(30, 50, 90, 0.7);
  text-align: center;
  font-size: 12.5px;
  cursor: pointer;
  margin-top: 2px;
  display: block;
  font-weight: 500;
  text-decoration: none;
}

.admin-link:hover {
  color: #1e325a;
  text-decoration: underline;
}
</style>