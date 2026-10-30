<template>
  <div class="main"><p class="text-xs text-gray-500 mb-4">Giao diện cấu hình AI; tính năng lưu chưa được kích hoạt.</p>
    <!-- Tiêu đề trang -->
    <div class="section-header">
      <div class="header-titles">
        <div class="badge-tag">QUẢN TRỊ</div>
        <div class="section-title">Cấu hình AI</div>
        <div class="section-desc">Điều chỉnh tham số và ngưỡng cảnh báo cho các mô hình AI đang vận hành hệ thống.</div>
      </div>
      
    </div>

    <div class="ai-config-container">
      <!-- 1. Định giá bất động sản -->
      <div class="config-card">
        <div class="card-top">
          <div class="card-info">
            <div class="card-title-row">
              <span class="card-title">Định giá bất động sản</span>
              <span class="badge-version">XGBoost · v2.3</span>
            </div>
            <div class="card-desc">Dự đoán giá tham chiếu và các yếu tố ảnh hưởng (SHAP) cho tin đăng mới.</div>
          </div>
          <div class="card-meta">
            <div class="meta-highlight">MAE: 6.2%</div>
            <div class="meta-date">Huấn luyện lại: 14/09/2026</div>
          </div>
        </div>

        <div class="config-option">
          <div class="option-info">
            <div class="option-title">Gợi ý giá tự động cho tin đăng mới</div>
            <div class="option-desc">Hiển thị giá tham chiếu ngay khi người dùng nhập thông tin cơ bản.</div>
          </div>
          <div class="toggle-switch" :class="{ active: config.autoPriceSuggest }" @click="config.autoPriceSuggest = !config.autoPriceSuggest">
            <div class="toggle-thumb"></div>
          </div>
        </div>

        <div class="config-option">
          <div class="option-info">
            <div class="option-title">Độ lệch cảnh báo giá bất thường</div>
            <div class="option-desc">Gắn cờ tin đăng khi giá niêm yết lệch quá ngưỡng so với giá dự đoán.</div>
          </div>
          <div class="option-control">
            <div class="slider-mock"><div class="slider-fill" style="width: 30%"></div></div>
            <span class="control-value">± 15%</span>
          </div>
        </div>
      </div>

      <!-- 2. Phát hiện ảnh trùng lặp -->
      <div class="config-card">
        <div class="card-top">
          <div class="card-info">
            <div class="card-title-row">
              <span class="card-title">Phát hiện ảnh trùng lặp</span>
              <span class="badge-version">Siamese Network · v1.4</span>
            </div>
            <div class="card-desc">So khớp ảnh tin đăng để phát hiện sao chép hoặc đăng trùng từ nguồn khác.</div>
          </div>
          <div class="card-meta">
            <div class="meta-highlight">Độ chính xác: 91.4%</div>
            <div class="meta-date">Huấn luyện lại: 08/09/2026</div>
          </div>
        </div>

        <div class="config-option">
          <div class="option-info">
            <div class="option-title">Ngưỡng cảnh báo trùng ảnh</div>
            <div class="option-desc">Tỉ lệ tương đồng tối thiểu để gắn cờ "nghi ngờ trùng ảnh".</div>
          </div>
          <div class="option-control">
            <div class="slider-mock"><div class="slider-fill" style="width: 92%"></div></div>
            <span class="control-value">92%</span>
          </div>
        </div>

        <div class="config-option">
          <div class="option-info">
            <div class="option-title">Tự động gắn cờ tin đăng nghi trùng ảnh</div>
            <div class="option-desc">Đưa tin đăng vào hàng chờ duyệt thủ công thay vì hiển thị ngay.</div>
          </div>
          <div class="toggle-switch" :class="{ active: config.autoFlagDuplicate }" @click="config.autoFlagDuplicate = !config.autoFlagDuplicate">
            <div class="toggle-thumb"></div>
          </div>
        </div>
      </div>

      <!-- 3. Nhận diện & đối chiếu tiện ích -->
      <div class="config-card">
        <div class="card-top">
          <div class="card-info">
            <div class="card-title-row">
              <span class="card-title">Nhận diện & đối chiếu tiện ích</span>
              <span class="badge-version">YOLOv8 · v1.1</span>
            </div>
            <div class="card-desc">Phát hiện tiện ích trong ảnh và đối chiếu với mô tả tin đăng.</div>
          </div>
          <div class="card-meta">
            <div class="meta-highlight">mAP: 0.87</div>
            <div class="meta-date">Huấn luyện lại: 02/09/2026</div>
          </div>
        </div>

        <div class="config-option">
          <div class="option-info">
            <div class="option-title">Độ tin cậy tối thiểu để nhận diện</div>
            <div class="option-desc">Bỏ qua các phát hiện có độ tin cậy thấp hơn ngưỡng này.</div>
          </div>
          <div class="option-control">
            <div class="slider-mock"><div class="slider-fill" style="width: 70%"></div></div>
            <span class="control-value">70%</span>
          </div>
        </div>

        <div class="config-option">
          <div class="option-info">
            <div class="option-title">Cảnh báo khi mô tả không khớp ảnh</div>
            <div class="option-desc">Hiển thị nhãn cảnh báo cho người xem khi phát hiện sai lệch.</div>
          </div>
          <div class="toggle-switch" :class="{ active: config.mismatchAlert }" @click="config.mismatchAlert = !config.mismatchAlert">
            <div class="toggle-thumb"></div>
          </div>
        </div>
      </div>

      <!-- 4. Kiểm duyệt tự động -->
      <div class="config-card">
        <div class="card-top">
          <div class="card-info">
            <div class="card-title-row">
              <span class="card-title">Kiểm duyệt tự động</span>
            </div>
            <div class="card-desc">Quy tắc tự động ẩn hoặc gắn cờ tin đăng có dấu hiệu vi phạm nghiêm trọng.</div>
          </div>
        </div>

        <div class="config-option">
          <div class="option-info">
            <div class="option-title">Tự động ẩn tin đăng vi phạm nghiêm trọng</div>
            <div class="option-desc">Ẩn ngay lập tức khỏi kết quả tìm kiếm, chờ quản trị viên xem xét.</div>
          </div>
          <div class="toggle-switch" :class="{ active: config.autoHideSevere }" @click="config.autoHideSevere = !config.autoHideSevere">
            <div class="toggle-thumb"></div>
          </div>
        </div>

        <div class="config-option">
          <div class="option-info">
            <div class="option-title">Điểm rủi ro tối thiểu để tự động ẩn</div>
            <div class="option-desc">Tổng hợp từ các tín hiệu: trùng ảnh, sai lệch mô tả, báo cáo người dùng.</div>
          </div>
          <div class="option-control">
            <div class="slider-mock"><div class="slider-fill" style="width: 85%"></div></div>
            <span class="control-value">85 / 100</span>
          </div>
        </div>
      </div>

      <!-- Thanh hành động cuối trang -->
      <div class="form-actions-bar">
        <div class="action-notice">
          Thay đổi cấu hình sẽ áp dụng cho các tin đăng mới và có thể mất vài phút để đồng bộ tới toàn hệ thống.
        </div>
        <div class="action-buttons">
          <button disabled class="btn-secondary" @click="resetDefaults">Khôi phục mặc định</button>
          <button disabled class="btn-success" @click="saveConfig">Lưu cấu hình</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AiConfigView',
  data() {
    return {
      config: {
        autoPriceSuggest: true,
        autoFlagDuplicate: true,
        mismatchAlert: true,
        autoHideSevere: false
      }
    }
  },
  methods: {
    handlePostAction() {
      alert('Chức năng đăng tin nhanh');
    },
    resetDefaults() {
      alert('Đã khôi phục cấu hình mặc định!');
    },
    saveConfig() {
      alert('Đã lưu cấu hình AI thành công!');
    }
  }
}
</script>

<style scoped>
.main {
  display: flex;
  flex-direction: column;
  gap: 24px;
  text-align: left;
  padding-bottom: 40px;
}

/* Header */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-titles {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.badge-tag {
  font-size: 12px;
  font-weight: bold;
  color: #4f46e5;
  background: #eef2ff;
  padding: 2px 8px;
  border-radius: 4px;
  align-self: flex-start;
}

.section-title {
  font-size: 23px;
  font-weight: bold;
  color: #1e325a;
}

.section-desc {
  font-size: var(--text-sm);
  color: #6b7280;
}

.btn-primary {
  background: #2563eb;
  color: #ffffff;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
}

.btn-primary:hover {
  background: #1d4ed8;
}

/* Container */
.ai-config-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Thẻ cấu hình AI */
.config-card {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid #f3f4f6;
  padding-bottom: 16px;
}

.card-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-title {
  font-size: 18px;
  font-weight: bold;
  color: #1e325a;
}

.badge-version {
  background: #f3f4f6;
  color: #374151;
  font-size: var(--text-xs);
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 6px;
}

.card-desc {
  font-size: var(--text-sm);
  color: #6b7280;
}

.card-meta {
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.meta-highlight {
  font-size: var(--text-sm);
  font-weight: bold;
  color: #059669;
}

.meta-date {
  font-size: var(--text-xs);
  color: #9ca3af;
}

/* Tùy chọn cấu hình chi tiết */
.config-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}

.option-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-width: 70%;
}

.option-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: #1f2937;
}

.option-desc {
  font-size: 14px;
  color: #6b7280;
}

/* Toggle Switch */
.toggle-switch {
  width: 44px;
  height: 24px;
  background: #d1d5db;
  border-radius: 12px;
  position: relative;
  cursor: pointer;
  transition: background 0.2s;
}

.toggle-switch.active {
  background: #2563eb;
}

.toggle-thumb {
  width: 20px;
  height: 20px;
  background: #ffffff;
  border-radius: 50%;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: transform 0.2s;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.toggle-switch.active .toggle-thumb {
  transform: translateX(20px);
}

/* Control Value & Slider mock */
.option-control {
  display: flex;
  align-items: center;
  gap: 14px;
}

.slider-mock {
  width: 120px;
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
}

.slider-fill {
  height: 100%;
  background: #2563eb;
  border-radius: 3px;
}

.control-value {
  font-size: var(--text-sm);
  font-weight: bold;
  color: #1f2937;
  min-width: 50px;
  text-align: right;
}

/* Thanh hành động cuối trang */
.form-actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  padding: 16px 24px;
  border-radius: 12px;
}

.action-notice {
  font-size: 14px;
  color: #6b7280;
  max-width: 60%;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.btn-secondary {
  background: #ffffff;
  color: #374151;
  border: 1px solid #d1d5db;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
}

.btn-secondary:hover {
  background: #f3f4f6;
}

.btn-success {
  background: #059669;
  color: #ffffff;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
}

.btn-success:hover {
  background: #047857;
}
</style>