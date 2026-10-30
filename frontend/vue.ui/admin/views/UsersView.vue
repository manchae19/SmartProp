<template>
  <div class="main">
<LegacyState :state="state" />
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
<section v-if="target" class="bg-white rounded-2xl p-6"><h3>{{target.fullName}}</h3><label class="block text-xs mt-3">Lý do<textarea v-model="reason" maxlength="4000" class="block w-full border rounded-xl p-3 my-3"/></label><button @click="saveStatus" class="bg-[#1E325A] text-white rounded-full px-5 py-2 text-xs">Xác nhận</button></section><LegacyPager :state="state" /></template>
<script setup>
import {ref,computed,watch,onMounted,onBeforeUnmount} from 'vue'
import {useRouter,useRoute} from 'vue-router'
import {api,session,errorText} from '../../src/services/api.js'
import {useList,adapt,money,LegacyState,LegacyPager,PrivateImage,types,states,reasons as reasonLabels,date,mapUrl} from '../../src/services/legacy.js'


const state=useList('/admin/users'),target=ref(null),reason=ref(''),usersList=computed(()=>state.items.map(u=>({...u,name:u.fullName,avatarLetter:u.fullName.slice(0,1),roleText:u.role,roleClass:u.role==='ADMIN'?'role-admin':'role-user',postsCount:'—',statusText:states[u.status],statusClass:u.status==='LOCKED'?'status-locked':'status-active',joinedDate:date(u.createdAt),isLocked:u.status==='LOCKED'})));
function toggleLockUser(id){target.value=state.items.find(u=>u.id===id);reason.value=''}
async function saveStatus(){if(!reason.value.trim()){state.error='Nhập lý do thay đổi trạng thái.';return}await state.run(async()=>{await api('/admin/users/'+target.value.id+'/status',{method:'PATCH',body:{status:target.value.status==='LOCKED'?'ACTIVE':'LOCKED',reason:reason.value}});target.value=null;await state.load(state.page)})}

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
  font-size: var(--text-base);
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
  font-size: 16px;
  font-weight: bold;
  color: #1e325a;
}

.user-email {
  font-size: 14px;
  color: #6b7280;
}

/* Vai trò (Role) */
.user-role {
  flex: 1;
  font-size: 14px;
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
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

/* Trạng thái hoạt động */
.user-status {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: var(--text-xs);
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
  font-size: 14px;
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
  font-size: 14px;
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
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-unlock:hover {
  opacity: 0.9;
}
</style>