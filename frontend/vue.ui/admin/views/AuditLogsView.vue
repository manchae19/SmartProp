<template>
  <div class="main">
    <!-- Tiêu đề trang -->
    <div class="section-header">
      <div class="header-titles">
        <div class="badge-tag">QUẢN TRỊ</div>
        <div class="section-title">Nhật ký kiểm toán</div>
        <div class="section-desc">Lịch sử toàn bộ thao tác của quản trị viên và hệ thống tự động.</div>
      </div>
      
    </div>

    <!-- Thẻ thống kê tổng quan -->
    <div class="stats-container">
      <div class="stat-card">
        <div class="stat-label">Thao tác hôm nay</div>
        <div class="stat-value">6</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Tài khoản bị khoá</div>
        <div class="stat-value">1</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Cảnh báo hệ thống</div>
        <div class="stat-value">0</div>
      </div>
    </div>

    <!-- Thanh lọc theo tab -->
    <div class="filter-tabs">
      <button 
        v-for="tab in tabs" 
        :key="tab.id"
        :class="['tab-btn', { active: currentTab === tab.id }]"
        @click="currentTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Danh sách hoạt động gần đây -->
    <div class="logs-section">
      <div class="logs-header">10 hoạt động gần đây</div>
      
      <div class="logs-list">
        <div class="log-item" v-for="log in filteredLogs" :key="log.id">
          <div :class="['log-indicator', log.typeClass]"></div>
          <div class="log-content-wrapper">
            <div class="log-text">{{ log.content }}</div>
            <div class="log-meta">{{ log.meta }}</div>
          </div>
          <div class="log-time">{{ log.time }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AuditLogsView',
  data() {
    return {
      currentTab: 'all',
      tabs: [
        { id: 'all', label: 'Tất cả · 10' },
        { id: 'post', label: 'Duyệt / Từ chối tin' },
        { id: 'account', label: 'Tài khoản' },
        { id: 'ai', label: 'Cấu hình AI' },
        { id: 'system', label: 'Hệ thống tự động' }
      ],
      logsList: [
        {
          id: 1,
          category: 'post',
          content: 'Trần Minh Đức (Admin) duyệt tin đăng "Căn hộ 2PN view sông Hàn" · Hải Châu',
          meta: 'ADMIN-04 · IP 10.0.4.12',
          time: '09:42, 18/09',
          typeClass: 'type-approve'
        },
        {
          id: 2,
          category: 'post',
          content: 'Trần Minh Đức (Admin) từ chối tin đăng "Villa sân vườn Điện Ngọc" · lý do: nghi ngờ ảnh giả mạo',
          meta: 'ADMIN-04 · IP 10.0.4.12',
          time: '08:15, 18/09',
          typeClass: 'type-reject'
        },
        {
          id: 3,
          category: 'post',
          content: 'Ngô Thuỳ Trang (Admin) gỡ tin đăng "Nhà 3 tầng hẻm xe hơi" theo báo cáo #204',
          meta: 'ADMIN-02 · IP 10.0.4.31',
          time: '16:30, 17/09',
          typeClass: 'type-reject'
        },
        {
          id: 4,
          category: 'account',
          content: 'Ngô Thuỳ Trang (Admin) khoá tài khoản "levan.hung@gmail.com" · lý do: spam tin đăng',
          meta: 'ADMIN-02 · IP 10.0.4.31',
          time: '14:02, 17/09',
          typeClass: 'type-reject'
        },
        {
          id: 5,
          category: 'ai',
          content: 'Trần Minh Đức (Admin) cập nhật ngưỡng cảnh báo trùng ảnh: 90% → 92%',
          meta: 'ADMIN-04 · Cấu hình AI',
          time: '11:20, 16/09',
          typeClass: 'type-ai'
        },
        {
          id: 6,
          category: 'system',
          content: 'Hệ thống (Tự động) ẩn 3 tin đăng đã quá hạn hiển thị 90 ngày',
          meta: 'SYSTEM-JOB · scheduled',
          time: '09:00, 16/09',
          typeClass: 'type-system'
        },
        {
          id: 7,
          category: 'post',
          content: 'Ngô Thuỳ Trang (Admin) bỏ qua báo cáo #198 — không phát hiện vi phạm',
          meta: 'ADMIN-02 · IP 10.0.4.31',
          time: '17:45, 15/09',
          typeClass: 'type-approve'
        },
        {
          id: 8,
          category: 'post',
          content: 'Trần Minh Đức (Admin) duyệt tin đăng "Đất nền Hoà Xuân" · Cẩm Lệ',
          meta: 'ADMIN-04 · IP 10.0.4.12',
          time: '10:10, 15/09',
          typeClass: 'type-approve'
        },
        {
          id: 9,
          category: 'account',
          content: 'Trần Minh Đức (Admin) mở khoá tài khoản "phamthu.ha@gmail.com"',
          meta: 'ADMIN-04 · IP 10.0.4.12',
          time: '15:33, 14/09',
          typeClass: 'type-approve'
        },
        {
          id: 10,
          category: 'system',
          content: 'Hệ thống (Tự động) cập nhật mô hình định giá XGBoost lên phiên bản v2.3',
          meta: 'SYSTEM-JOB · model-deploy',
          time: '08:47, 14/09',
          typeClass: 'type-system'
        }
      ]
    }
  },
  computed: {
    filteredLogs() {
      if (this.currentTab === 'all') {
        return this.logsList;
      }
      return this.logsList.filter(log => log.category === this.currentTab);
    }
  },
  methods: {
    handlePostAction() {
      alert('Chức năng đăng tin nhanh');
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
  padding-bottom: 30px;
}

/* Phần đầu trang */
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

/* Thẻ thống kê */
.stats-container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.stat-card {
  background: #ffffff;
  padding: 20px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-label {
  font-size: var(--text-sm);
  color: #6b7280;
  font-weight: 500;
}

.stat-value {
  font-size: var(--text-2xl);
  font-weight: bold;
  color: #1e325a;
}

/* Thanh lọc tab */
.filter-tabs {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.tab-btn {
  background: #ffffff;
  border: 1px solid #d1d5db;
  color: #4b5563;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: #f3f4f6;
}

.tab-btn.active {
  background: #1e325a;
  color: #ffffff;
  border-color: #1e325a;
}

/* Danh sách nhật ký */
.logs-section {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.logs-header {
  font-size: var(--text-base);
  font-weight: bold;
  color: #1e325a;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 12px;
}

.logs-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px;
  border-radius: 8px;
  background: #f9fafb;
  border: 1px solid #f3f4f6;
}

.log-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.type-approve { background: #10b981; }
.type-reject { background: #ef4444; }
.type-ai { background: #8b5cf6; }
.type-system { background: #3b82f6; }

.log-content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.log-text {
  font-size: var(--text-sm);
  color: #1f2937;
  font-weight: 500;
}

.log-meta {
  font-size: var(--text-xs);
  color: #6b7280;
}

.log-time {
  font-size: 14px;
  color: #4b5563;
  font-weight: 500;
  white-space: nowrap;
}
</style>