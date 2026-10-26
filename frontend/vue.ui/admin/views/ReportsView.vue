<template>
  <div class="main">
    <!-- Tiêu đề phần báo cáo -->
    <div class="section-title">
      <div class="title-text">3 báo cáo cần xử lý</div>
    </div>

    <!-- Danh sách các báo cáo vi phạm -->
    <div class="reports-list">
      <div class="report-card" v-for="report in reportsList" :key="report.id">
        <!-- Thông tin chi tiết báo cáo -->
        <div class="report-info">
          <div class="report-title">{{ report.title }}</div>
          <div class="report-reason-badge">
            <span class="reason-text">{{ report.reason }}</span>
          </div>
          <div class="report-meta">
            Báo cáo bởi {{ report.reporter }} · {{ report.time }}
          </div>
        </div>

        <!-- Các nút thao tác xử lý -->
        <div class="report-actions">
          <button class="btn-view" @click="viewPost(report.id)">
            Xem tin &rsaquo;
          </button>
          <button class="btn-remove" @click="removePost(report.id)">
            Gỡ tin
          </button>
          <button class="btn-skip" @click="skipReport(report.id)">
            Bỏ qua
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ReportsView',
  data() {
    return {
      reportsList: [
        {
          id: 1,
          title: 'Villa sân vườn Điện Ngọc, sổ hồng riêng',
          reason: 'Có dấu hiệu lừa đảo',
          reporter: 'Phạm Thu Hà',
          time: '2 giờ trước'
        },
        {
          id: 2,
          title: 'Nhà phố 2 mặt tiền gần chợ Cồn',
          reason: 'Nghi ngờ ảnh giả mạo',
          reporter: 'Đỗ Minh Khoa',
          time: 'hôm qua'
        },
        {
          id: 3,
          title: 'Đất thổ cư Hòa Xuân, pháp lý đầy đủ',
          reason: 'Sai lệch giá bán so với thực tế',
          reporter: 'Vũ Thị Lan',
          time: '3 ngày trước'
        }
      ]
    }
  },
  methods: {
    viewPost(id) {
      alert(`Xem chi tiết tin đăng có ID báo cáo: ${id}`);
    },
    removePost(id) {
      this.reportsList = this.reportsList.filter(item => item.id !== id);
      alert('Đã gỡ tin đăng vi phạm thành công!');
    },
    skipReport(id) {
      this.reportsList = this.reportsList.filter(item => item.id !== id);
      alert('Đã bỏ qua báo cáo này.');
    }
  }
}
</script>

<style scoped>
.main {
  display: flex;
  flex-direction: column;
  gap: 20px;
  text-align: left;
}

.section-title {
  font-size: var(--text-base);
  font-weight: bold;
  color: #1e325a;
  margin-bottom: 4px;
}

.reports-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Thẻ báo cáo */
.report-card {
  background: #ffffff;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid #e5e7eb;
  gap: 20px;
}

.report-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.report-title {
  font-size: 16px;
  font-weight: bold;
  color: #1e325a;
}

/* Nhãn lý do vi phạm */
.report-reason-badge {
  display: inline-flex;
  align-self: flex-start;
  background: #fee2e2;
  padding: 2px 8px;
  border-radius: 6px;
}

.reason-text {
  font-size: var(--text-xs);
  font-weight: 500;
  color: #dc2626;
}

.report-meta {
  font-size: 14px;
  color: #6b7280;
}

/* Khu vực nút bấm thao tác */
.report-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.btn-view {
  background: transparent;
  color: #1e325a;
  border: none;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  padding: 6px 10px;
}

.btn-view:hover {
  text-decoration: underline;
}

.btn-remove {
  background: #dc2626;
  color: #ffffff;
  border: none;
  padding: 7px 14px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-remove:hover {
  opacity: 0.9;
}

.btn-skip {
  background: #ffffff;
  color: #4b5563;
  border: 1px solid #d1d5db;
  padding: 7px 14px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-skip:hover {
  background: #f9fafb;
}
</style>