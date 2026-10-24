<template>
  <div class="main">
<LegacyState :state="state" />
    <!-- Tiêu đề danh sách tin chờ duyệt -->
    <div class="section-title">
      <div class="_18-tin-ang-ch-duy-t">{{ state.totalElements }} tin đăng</div>
    </div>

    <!-- Danh sách các tin chờ duyệt -->
    <select v-model="statusFilter" @change="selected=null;state.load(0)" class="bg-white border rounded-lg p-2 text-sm"><option v-for="key in ['PENDING','PUBLISHED','HIDDEN','REJECTED','DRAFT','EXPIRED','CLOSED']" :key="key" :value="key">{{states[key]}}</option></select><div class="posts-list">
      <div class="post-card" v-for="post in pendingPosts" :key="post.id">
        <!-- Ảnh thu nhỏ của tin đăng -->
        <PrivateImage :src="post.image" alt="Ảnh tin đăng" class="post-thumb object-cover"/>

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
          <button v-if="post.raw.status==='PENDING'" class="btn-approve" @click="handleApprove(post.id)">Duyệt</button>
          <button v-if="post.raw.status==='PENDING'" class="btn-reject" @click="handleReject(post.id)">Từ chối</button>
          <button v-if="post.raw.status==='PUBLISHED'" class="btn-reject" @click="moderate(post.id,'HIDE')">Ẩn tin</button><button v-if="post.raw.status==='HIDDEN'" class="btn-approve" @click="moderate(post.id,'RESTORE')">Khôi phục</button><button class="btn-detail" @click="handleViewDetail(post.id)">Xem chi tiết ›</button>
        </div>
      </div>
    </div>
  </div>
<section v-if="selected" class="bg-white rounded-2xl p-6"><h3 class="font-semibold">{{selected.property.title}}</h3><p class="text-xs py-3 whitespace-pre-wrap">{{selected.property.description}}</p><div class="grid grid-cols-3 gap-3"><PrivateImage v-for="image in selected.property.images" :key="image.id" :src="image.url" alt="Ảnh tin chờ duyệt" class="h-32 w-full object-cover rounded-xl"/></div><label class="block text-xs mt-4">Lý do<textarea v-model="reason" class="w-full mt-2 p-3 border rounded-xl" maxlength="4000"/></label><button v-if="selected.property.status==='PENDING'" class="px-4 py-2 rounded-full bg-[#1E325A] text-white text-xs" @click="handleApprove(selected.property.id)">Duyệt tin</button><button v-if="selected.property.status==='PENDING'" class="px-4 py-2 rounded-full border ml-2 text-xs" @click="handleReject(selected.property.id)">Từ chối</button><button v-if="selected.property.status==='PUBLISHED'" class="px-4 py-2 rounded-full border text-xs" @click="moderate(selected.property.id,'HIDE')">Ẩn tin</button><button v-if="selected.property.status==='HIDDEN'" class="px-4 py-2 rounded-full border text-xs" @click="moderate(selected.property.id,'RESTORE')">Khôi phục</button></section><LegacyPager :state="state" /></template>
<script setup>
import {ref,computed,watch,onMounted,onBeforeUnmount} from 'vue'
import {useRouter,useRoute} from 'vue-router'
import {api,session,errorText} from '../../src/services/api.js'
import {useList,adapt,money,LegacyState,LegacyPager,PrivateImage,types,states,reasons as reasonLabels,date,mapUrl} from '../../src/services/legacy.js'


const statusFilter=ref('PENDING');
const router=useRouter(),state=useList('/admin/properties',()=>({status:statusFilter.value})),selected=ref(null),reason=ref(''),pendingPosts=computed(()=>state.items.map(m=>({...adapt(m),location:adapt(m).location,time:date(m.property.createdAt),badgeText:states[m.property.status],badgeClass:'badge-info'})));
const handleViewDetail=id=>{selected.value=state.items.find(m=>m.property.id===id);reason.value=''};
async function moderate(id,action){if(!selected.value||selected.value.property.id!==id){handleViewDetail(id);return}if(!reason.value.trim()){state.error='Nhập lý do trước khi xử lý.';return}await state.run(async()=>{await api('/admin/properties/'+id+'/moderation',{method:'POST',body:{action,expectedVersion:selected.value.property.contentVersion,reason:reason.value}});selected.value=null;await state.load(state.page)})}
const handleApprove=id=>moderate(id,'APPROVE'),handleReject=id=>moderate(id,'REJECT');

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
  font-size: 15px;
  font-weight: bold;
  color: #1e325a;
}

.post-meta {
  font-size: 13px;
  color: #6b7280;
}

/* Kiểu dáng các nhãn trạng thái (Badge) */
.post-badge {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
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
  font-size: 13px;
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
  font-size: 13px;
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
  font-size: 13px;
  cursor: pointer;
  font-weight: 500;
}

.btn-detail:hover {
  color: #1e325a;
}
</style>