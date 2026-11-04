<template>
  <div class="main">
<LegacyState :state="state" />
    
    <div class="section-title">
      <div class="title-text">{{ state.totalElements }} báo cáo</div>
    </div>

    
    <select v-model="statusFilter" @change="selected=null;state.load(0)" class="bg-white border rounded-lg p-2 text-sm"><option value="OPEN">Mới tiếp nhận</option><option value="PROCESSING">Đang xử lý</option><option value="RESOLVED">Đã giải quyết</option><option value="REJECTED">Đã từ chối</option><option value="">Tất cả</option></select><div class="reports-list">
      <div class="report-card" v-for="report in reportsList" :key="report.id" :data-report-id="report.id">
        
        <div class="report-info">
          <div class="report-title">{{ report.title }}</div>
          <div class="report-reason-badge">
            <span class="reason-text">{{ report.reason }}</span>
          </div>
          <div class="report-meta">
            Báo cáo bởi {{ report.reporter }} · {{ report.time }}
          </div>
        </div>

        
        <div class="report-actions">
          <button class="btn-view" @click="viewPost(report.id)">
            Xem báo cáo &rsaquo;
          </button>
          <button v-if="!['RESOLVED','REJECTED'].includes(report.status)" class="btn-remove" @click="removePost(report.id)">
            Giải quyết
          </button>
          <button v-if="!['RESOLVED','REJECTED'].includes(report.status)" class="btn-skip" @click="skipReport(report.id)">
            Bỏ qua
          </button>
        </div>
      </div>
    </div>
  </div>
<section v-if="selected" class="rounded-2xl bg-white p-6"><ReportDetails :report="selected" admin/><label class="block text-xs">Ghi chú xử lý<textarea v-model="note" maxlength="4000" class="w-full border rounded-xl p-3 my-3"/></label><button v-if="!['RESOLVED','REJECTED'].includes(selected.status)" @click="removePost(selected.id)" class="bg-[#1E325A] text-white rounded-full px-5 py-2 text-xs">Giải quyết</button><button v-if="!['RESOLVED','REJECTED'].includes(selected.status)" @click="skipReport(selected.id)" class="border rounded-full px-5 py-2 text-xs ml-2">Từ chối</button></section><LegacyPager :state="state" /></template>
<script setup>
import {ref,computed,watch,onMounted,onBeforeUnmount} from 'vue'
import {useRouter,useRoute} from 'vue-router'
import {api,session,errorText} from '../auth/api.js'
import {useList,adapt,money,LegacyState,LegacyPager,PrivateImage,types,states,reasons as reasonLabels,date,mapUrl} from '../../lib/legacy.js'


import ReportDetails from '../report/ReportDetails.vue'
const statusFilter=ref('OPEN');
const router=useRouter(),state=useList('/admin/reports',()=>({status:statusFilter.value||undefined})),selected=ref(null),note=ref(''),reportsList=computed(()=>state.items.map(r=>({...r,title:'Tin '+r.propertyId,reason:reasonLabels[r.reasonCode]||r.reasonCode,reporter:'Người dùng #'+r.reporterId,time:date(r.createdAt)})));
const viewPost=id=>{selected.value=state.items.find(r=>r.id===id);note.value=''};
async function resolve(id,status){if(!selected.value||selected.value.id!==id){viewPost(id);return}if(!note.value.trim()){state.error='Nhập ghi chú xử lý.';return}await state.run(async()=>{await api('/admin/reports/'+id+'/status',{method:'PATCH',body:{status,note:note.value}});selected.value=null;await state.load(state.page)})}
const removePost=id=>resolve(id,'RESOLVED'),skipReport=id=>resolve(id,'REJECTED');

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