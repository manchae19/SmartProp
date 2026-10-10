<template>
  <div class="main">
    <!-- Các khối thống kê tổng quan -->
    <div class="stats">
      <div class="stat">
        <div class="tin-ang-hi-n-th">Tin đang hiển thị</div>
        <div class="_2-417">2.417</div>
      </div>
      <div class="stat">
        <div class="ch-duy-t">Chờ duyệt</div>
        <div class="_182">18</div>
      </div>
      <div class="stat2">
        <div class="c-nh-b-o-nh-tr-ng">Cảnh báo ảnh trùng</div>
        <div class="_9">9</div>
      </div>
      <div class="stat">
        <div class="ng-i-d-ng-ho-t-ng">Người dùng hoạt động</div>
        <div class="_1-043">1.043</div>
      </div>
    </div>

    <!-- Hàng thứ 2: Biểu đồ và Tình trạng AI -->
    <div class="row-2">
      <div class="chart">
        <div class="tin-ng-m-i-theo-tu">Tin đăng mới theo tuần</div>
        <div class="bars">
          <div class="col" v-for="(item, index) in chartData" :key="index">
            <div class="bar-fill" :class="{ active: index === 5 }" :style="{ height: item.height }"></div>
            <div class="label-day">{{ item.day }}</div>
          </div>
        </div>
      </div>

      <div class="ai">
        <div class="t-nh-tr-ng-d-ch-v-a">Tình trạng dịch vụ AI</div>
        
        <div class="row">
          <div class="ellipse green"></div>
          <div class="nh-gi-xg-boost">Định giá XGBoost</div>
          <div class="_82-ms-q-0">82ms · q:0</div>
        </div>

        <div class="row">
          <div class="ellipse green"></div>
          <div class="nh-n-di-n-nh-tr-ng">Nhận diện ảnh trùng</div>
          <div class="_340-ms-q-2">340ms · q:2</div>
        </div>

        <div class="row">
          <div class="ellipse red"></div>
          <div class="g-i-ti-n-ch-t">Gợi ý tiện ích tự động</div>
          <div class="l-i-q-5">lỗi · q:5</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DashboardView',
  data() {
    return {
      chartData: [
        { day: 'T27', height: '40px' },
        { day: 'T28', height: '60px' },
        { day: 'T29', height: '35px' },
        { day: 'T30', height: '80px' },
        { day: 'T31', height: '55px' },
        { day: 'T32', height: '110px' },
        { day: 'T33', height: '70px' }
      ]
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
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: left;
}

/* Thẻ "Cảnh báo ảnh trùng" dùng chính xác màu #1E325A */
.stat2 {
  background: #1e325a;
  color: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: left;
}

.stat2 div:first-child {
  font-size: 13px;
  color: #9ca3af;
  text-align: left;
}

.stat2 ._9 {
  color: white;
  font-size: 24px;
  font-weight: bold;
  text-align: left;
}

.stat div:first-child {
  font-size: 13px;
  color: #6b7280;
  text-align: left;
}

.stat div:last-child {
  font-size: 24px;
  font-weight: bold;
  color: #1e325a;
  text-align: left;
}

.row-2 {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}

.chart, .ai {
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  text-align: left;
}

.tin-ng-m-i-theo-tu, .t-nh-tr-ng-d-ch-v-a {
  font-weight: bold;
  font-size: 15px;
  margin-bottom: 20px;
  color: #1e325a;
  text-align: left;
}

.bars {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 160px;
  padding-top: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.bar-fill {
  width: 24px;
  background: #cbd5e1;
  border-radius: 4px 4px 0 0;
}

/* Cột biểu đồ nổi bật dùng đúng mã màu #1E325A */
.bar-fill.active {
  background: #1e325a;
}

.label-day {
  font-size: 12px;
  color: #6b7280;
}

.ai {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  padding: 10px 0;
  border-bottom: 1px solid #f3f4f6;
  text-align: left;
}

.ellipse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.green { background: #10b981; }
.red { background: #ef4444; }

.row div:nth-child(2) {
  flex: 1;
  margin-left: 10px;
  color: #374151;
  text-align: left;
}

._82-ms-q-0, ._340-ms-q-2, .l-i-q-5 {
  font-size: 12px;
  color: #6b7280;
}
.l-i-q-5 {
  color: #ef4444;
  font-weight: bold;
}
</style>