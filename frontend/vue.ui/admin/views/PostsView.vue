<template>
  <div class="main">
    <!-- Tiêu đề danh sách tin chờ duyệt -->
    <div class="section-title">
      <div class="_18-tin-ang-ch-duy-t">{{ pendingPosts.length }} tin đang chờ duyệt</div>
    </div>

    <!-- Danh sách các tin chờ duyệt -->
    <div class="posts-list">
      <div class="post-card" v-for="post in pendingPosts" :key="post.id">
        <!-- Ảnh thu nhỏ của tin đăng -->
        <div class="post-thumb"></div>

        <!-- Thông tin chi tiết tin đăng -->
        <div class="post-info">
          <div class="post-title">{{ post.title }}</div>
          <div class="post-meta">{{ post.location }} · {{ post.price }} · gửi {{ post.time }}</div>
        </div>

        <!-- Nhãn trạng thái (Badge) -->
        <div :class="['post-badge', post.badgeClass]">
          <div class="badge-text">{{ post.badgeText }}</div>
        </div>

        <!-- Khu vực nút thao tác -->
        <div class="post-actions">
          <button class="btn-approve" @click="handleApprove(post.id)">Duyệt</button>
          <button class="btn-reject" @click="handleReject(post.id)">Từ chối</button>
          <button class="btn-detail" @click="handleViewDetail(post.id)">Xem chi tiết ›</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PostsView',
  data() {
    return {
      pendingPosts: [
        {
          id: 1,
          title: 'Nhà 3 tầng hẻm xe hơi, gần cầu Rồng',
          location: '123 Nguyễn Văn Linh, Hải Châu',
          price: '4,8 tỷ',
          time: '2 giờ trước',
          badgeText: 'Ảnh trùng x2',
          badgeClass: 'badge-warning' // Màu cảnh báo
        },
        {
          id: 2,
          title: 'Căn hộ 2PN view sông Hàn, nội thất đầy đủ',
          location: '45 Trần Hưng Đạo, Sơn Trà',
          price: '2,1 tỷ',
          time: '5 giờ trước',
          badgeText: 'Chờ đối chiếu',
          badgeClass: 'badge-info' // Màu chờ xử lý
        },
        {
          id: 3,
          title: 'Đất nền mặt tiền đường Nguyễn Tất Thành',
          location: 'Lô 12 Nguyễn Tất Thành, Thanh Khê',
          price: '6,3 tỷ',
          time: 'hôm qua',
          badgeText: 'Sẵn sàng duyệt',
          badgeClass: 'badge-success' // Màu sẵn sàng
        }
      ]
    }
  },
  methods: {
    handleApprove(id) {
      // Logic xử lý duyệt tin
      this.pendingPosts = this.pendingPosts.filter(p => p.id !== id);
    },
    handleReject(id) {
      // Logic xử lý từ chối tin
      this.pendingPosts = this.pendingPosts.filter(p => p.id !== id);
    },
    handleViewDetail(id) {
      // Logic xem chi tiết tin đăng
      console.log('Xem chi tiết tin:', id);
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

.posts-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Thẻ item tin đăng */
.post-card {
  background: #ffffff;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border: 1px solid #e5e7eb;
}

.post-thumb {
  width: 64px;
  height: 64px;
  background: #e2e8f0;
  border-radius: 8px;
  flex-shrink: 0;
}

.post-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.post-title {
  font-size: 16px;
  font-weight: bold;
  color: #1e325a;
}

.post-meta {
  font-size: 14px;
  color: #6b7280;
}

/* Kiểu dáng các nhãn trạng thái (Badge) */
.post-badge {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: var(--text-xs);
  font-weight: 500;
  text-align: center;
  white-space: nowrap;
}

.badge-warning {
  background: #fef3c7;
  color: #d97706;
}

.badge-info {
  background: #e0f2fe;
  color: #0284c7;
}

.badge-success {
  background: #d1fae5;
  color: #059669;
}

/* Cụm nút bấm thao tác */
.post-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-approve {
  background: #1e325a;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-approve:hover {
  opacity: 0.9;
}

.btn-reject {
  background: #ffffff;
  color: #ef4444;
  border: 1px solid #fecaca;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-reject:hover {
  background: #fef2f2;
}

.btn-detail {
  background: transparent;
  color: #4b5563;
  border: none;
  padding: 8px 12px;
  font-size: 14px;
  cursor: pointer;
  font-weight: 500;
}

.btn-detail:hover {
  color: #1e325a;
}
</style>