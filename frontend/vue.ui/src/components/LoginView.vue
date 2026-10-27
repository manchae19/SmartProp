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
          <div class="auth-card"><p v-if="message" role="status" aria-live="polite">{{ message }}</p>
            
            <!-- TRƯỜNG HỢP 1: ĐĂNG NHẬP / ĐĂNG KÝ / KHÔI PHỤC MẬT KHẨU -->
              <!-- Nút Quay lại đăng nhập (Chỉ hiện khi đang ở màn hình Quên mật khẩu) -->
              <a href="#" class="back-link-top" v-if="isForgotPassword" @click.prevent="isForgotPassword = false">
                &lt; Quay lại đăng nhập
              </a>

              <div class="toggle" v-if="!isForgotPassword">
                <button 
                  :disabled="busy" type="button"
                  class="toggle-btn" 
                  :class="{ active: isLoginTab }" 
                  @click="isLoginTab = true"
                >
                  Đăng nhập
                </button>
                <button 
                  :disabled="busy" type="button"
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
                  {{ isForgotPassword ? 'Nhập email tài khoản để yêu cầu liên kết đặt lại mật khẩu.' : (isLoginTab ? 'Đăng nhập để xem lại tin yêu thích và kết quả đánh giá giá đã lưu.' : 'Đăng ký tài khoản mới để trải nghiệm đầy đủ tính năng hệ thống.') }}
                </p>
              </div>
              
              <form class="form" @submit.prevent="handleSubmit">
                <p v-if="!isLoginTab && !isForgotPassword" class="text-sm leading-6">Tài khoản mới là người mua / người thuê. Bạn có thể đăng ký quyền đăng tin tại trang Tài khoản để quản trị viên xét duyệt.</p><div class="field" v-if="!isLoginTab && !isForgotPassword">
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
                  <label class="label" for="email-input">{{ isLoginTab && !isForgotPassword ? 'Email / tên quản trị' : 'Email' }}</label>
                  <div class="input-box">
                    <input 
                      :type="isLoginTab && !isForgotPassword ? 'text' : 'email'" 
                      id="email-input" 
                      v-model="email" 
                      :placeholder="isLoginTab && !isForgotPassword ? 'Email hoặc Admin' : 'ban@email.com'" 
                      required 
                    />
                  </div>
                </div>
                
                <div class="field" v-if="!isForgotPassword">
                  <label class="label" for="password-input">Mật khẩu</label>
                  <div class="input-box">
                    <input minlength="8" maxlength="72" type="password" 
                      id="password-input" 
                      v-model="password" 
                      placeholder="Tối thiểu 8 ký tự" 
                      required 
                    />
                  </div>
                  
                  <div class="forgot-row" v-if="isLoginTab">
                    <a href="#" class="forgot-link-new" @click.prevent="isForgotPassword = true; message = ''">
                      Quên mật khẩu?
                    </a>
                  </div>
                </div>

                <div class="field" v-if="!isLoginTab && !isForgotPassword">
                  <label class="label" for="confirm-password-input">Xác nhận mật khẩu</label>
                  <div class="input-box">
                    <input minlength="8" maxlength="72" type="password" 
                      id="confirm-password-input" 
                      v-model="confirmPassword" 
                      placeholder="Nhập lại mật khẩu" 
                      required 
                    />
                  </div>
                </div>
                
                <label v-if="isLoginTab && !isForgotPassword" class="flex items-start gap-3 text-sm leading-6"><input v-model="rememberMe" type="checkbox" class="mt-1"/>Ghi nhớ đăng nhập trong 30 ngày</label><p v-if="isLoginTab && !isForgotPassword" class="text-xs leading-5 text-gray-500">Tài khoản quản trị áp dụng giới hạn phiên riêng, tối đa 8 giờ.</p>
                <!-- Nút submit thay đổi chữ cho phù hợp màn hình quên mật khẩu -->
                <button :disabled="busy" type="submit" class="submit-btn">
                  <span>{{ busy ? 'Đang xử lý…' : (isForgotPassword ? 'Gửi liên kết đặt lại ↗' : (isLoginTab ? 'Đăng nhập' : 'Đăng ký')) }}</span>
                </button>
                
                <!-- Chú thích chân trang thay đổi theo thiết kế mới khi ở màn hình quên mật khẩu -->
                <p class="security-note">
                  {{ isForgotPassword ? 'Vui lòng liên hệ quản trị viên khi cần hỗ trợ tài khoản.' : 'Mật khẩu được mã hóa, phiên làm việc dùng JWT, kết nối qua TLS.' }}
                </p>
                
                <a href="#" class="admin-link" v-if="!isForgotPassword" @click.prevent="handleLinkClick">
                  {{ isLoginTab ? 'Đăng nhập quản trị' : 'Đã có tài khoản? Đăng nhập' }}
                </a>
              </form>

          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { login, register, errorText,api } from '../services/api'
const router = useRouter()
const props = defineProps({ initialRegister: Boolean })
const isLoginTab = ref(!props.initialRegister)
const isForgotPassword = ref(false)
const fullName = ref(''), email = ref(''), password = ref(''), confirmPassword = ref('')
const busy = ref(false), message = ref(''), rememberMe=ref(false)
const route = useRoute()
const reasons = {
  'password-changed': 'Đổi mật khẩu thành công. Vui lòng đăng nhập bằng mật khẩu mới.',
  'session-expired': 'Phiên đã hết hạn hoặc bị thu hồi. Vui lòng đăng nhập lại.',
  'session-unavailable': 'Không thể kiểm tra phiên. Vui lòng kiểm tra kết nối và đăng nhập lại.',
  'login-required': 'Vui lòng đăng nhập để sử dụng chức năng này.',
}
message.value = reasons[route.query.reason] || ''

const handleSubmit = async () => {
  if (busy.value) return
  message.value = ''
  if (isForgotPassword.value) { busy.value=true;try{await api('/auth/password/forgot',{method:'POST',body:{email:email.value.trim()},authenticated:false});message.value='Nếu tài khoản đủ điều kiện, yêu cầu đã được tiếp nhận. Vui lòng kiểm tra email.'}catch(e){message.value=errorText(e)}finally{busy.value=false}return }
  if (!isLoginTab.value && password.value !== confirmPassword.value) { message.value = 'Mật khẩu xác nhận không khớp.'; return }
  busy.value = true
  try {
    if (isLoginTab.value) {
      const user = await login(email.value, password.value, rememberMe.value)
      password.value = ''
      await router.push(user.role === 'ADMIN' ? '/admin' : '/home')
    } else {
      await register({ fullName: fullName.value, email: email.value, password: password.value, role: 'BUYER' })
      password.value = confirmPassword.value = ''
      isLoginTab.value = true
      message.value = 'Đăng ký thành công. Vui lòng đăng nhập.'
    }
  } catch (error) { message.value = errorText(error) }
  finally { busy.value = false }
}
const handleLinkClick = () => { isLoginTab.value = true; message.value = 'Dùng tài khoản được quản trị viên cấp để đăng nhập quản trị.' }
</script>

<style scoped>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
}

.login-container {
  background: #0b111e;
  width: 100%;
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
