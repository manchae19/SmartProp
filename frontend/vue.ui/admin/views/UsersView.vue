<template>
  <div class="main">
    <!-- Tiêu đề danh sách người dùng -->
    <div class="section-title">
      <div class="danh-s-ch-ng-i-d-ng">Danh sách người dùng</div>
    </div>

    <!-- Danh sách người dùng -->
    <div class="users-list">
      <div class="user-card" v-for="user in usersList" :key="user.id">
        <!-- Avatar viết tắt tên -->
        <div class="user-avatar">
          <div class="avatar-letter">{{ user.avatarLetter }}</div>
        </div>

        <!-- Thông tin cá nhân (Tên & Email) -->
        <div class="user-info">
          <div class="user-name">{{ user.name }}</div>
          <div class="user-email">{{ user.email }}</div>
        </div>

        <!-- Vai trò (Role) -->
        <div :class="['user-role', user.roleClass]">
          <div class="role-text">{{ user.roleText }}</div>
        </div>

        <!-- Thống kê số tin -->
        <div class="user-posts-count">
          <div class="posts-text">{{ user.postsCount }}</div>
        </div>

        <!-- Trạng thái hoạt động -->
        <div :class="['user-status', user.statusClass]">
          <div class="status-text">{{ user.statusText }}</div>
        </div>

        <!-- Ngày tham gia -->
        <div class="user-joined-date">
          <div class="joined-text">Tham gia {{ user.joinedDate }}</div>
        </div>

        <!-- Nút thao tác (Khóa / Mở khóa) -->
        <div class="user-actions">
          <button 
            :class="user.isLocked ? 'btn-unlock' : 'btn-lock'" 
            @click="toggleLockUser(user.id)"
          >
            {{ user.isLocked ? 'Mở khóa' : 'Khóa tài khoản' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'UsersView',
  data() {
    return {
      usersList: [
        {
          id: 1,
          avatarLetter: 'A',
          name: 'Nguyễn Văn A',
          email: 'nguyenvana@gmail.com',
          roleText: 'Người dùng',
          roleClass: 'role-user',
          postsCount: '12 tin',
          statusText: 'Hoạt động',
          statusClass: 'status-active',
          joinedDate: '12/03/2024',
          isLocked: false
        },
        {
          id: 2,
          avatarLetter: 'B',
          name: 'Trần Thị Bích',
          email: 'tranthib@gmail.com',
          roleText: 'Người dùng',
          roleClass: 'role-user',
          postsCount: '34 tin',
          statusText: 'Hoạt động',
          statusClass: 'status-active',
          joinedDate: '28/06/2023',
          isLocked: false
        },
        {
          id: 3,
          avatarLetter: 'N',
          name: 'Lê Hoàng Nam',
          email: 'lehoangnam@gmail.com',
          roleText: 'Quản trị viên',
          roleClass: 'role-admin',
          postsCount: '3 tin',
          statusText: 'Đã khóa',
          statusClass: 'status-locked',
          joinedDate: '04/01/2025',
          isLocked: true
        }
      ]
    }
  },
  methods: {
    toggleLockUser(id) {
      const user = this.usersList.find(u => u.id === id);
      if (user) {
        user.isLocked = !user.isLocked;
        user.statusText = user.isLocked ? 'Đã khóa' : 'Hoạt động';
        user.statusClass = user.isLocked ? 'status-locked' : 'status-active';
      }
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
  font-size: 16px;
  font-weight: bold;
  color: #1e325a;
  margin-bottom: 4px;
}

.users-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Thẻ thông tin người dùng */
.user-card {
  background: #ffffff;
  padding: 16px 20px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border: 1px solid #e5e7eb;
}

/* Avatar chữ cái */
.user-avatar {
  width: 44px;
  height: 44px;
  background: #e2e8f0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-letter {
  font-size: 16px;
  font-weight: bold;
  color: #1e325a;
}

.user-info {
  flex: 1.5;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-name {
  font-size: 15px;
  font-weight: bold;
  color: #1e325a;
}

.user-email {
  font-size: 13px;
  color: #6b7280;
}

/* Vai trò (Role) */
.user-role {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
}

.role-user {
  color: #4b5563;
}

.role-admin {
  color: #7c3aed;
  font-weight: bold;
}

/* Số lượng tin */
.user-posts-count {
  flex: 0.8;
  font-size: 13px;
  color: #374151;
  font-weight: 500;
}

/* Trạng thái hoạt động */
.user-status {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  text-align: center;
}

.status-active {
  background: #d1fae5;
  color: #059669;
}

.status-locked {
  background: #fee2e2;
  color: #dc2626;
}

/* Ngày tham gia */
.user-joined-date {
  flex: 1.2;
  font-size: 13px;
  color: #6b7280;
  text-align: right;
}

/* Khu vực nút bấm */
.user-actions {
  flex-shrink: 0;
}

.btn-lock {
  background: #ffffff;
  color: #dc2626;
  border: 1px solid #fecaca;
  padding: 7px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-lock:hover {
  background: #fef2f2;
}

.btn-unlock {
  background: #1e325a;
  color: #ffffff;
  border: none;
  padding: 7px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-unlock:hover {
  opacity: 0.9;
}
</style>