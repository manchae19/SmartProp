<script setup>
import {ref,onMounted,onBeforeUnmount} from 'vue'
import {api} from '../../src/services/api.js'
import {applicationStatuses,applicationActions,reviewActions,brokerErrorText} from '../../src/services/brokerApplication.js'
const items=ref([]),status=ref('PENDING'),page=ref(0),totalPages=ref(0),total=ref(0),busy=ref(false),error=ref(''),message=ref(''),selected=ref(null),reason=ref('')
let sequence=0
async function load(reset=false){
  if(reset)page.value=0
  const run=++sequence;busy.value=true;error.value='';selected.value=null
  try{const q=new URLSearchParams({page:String(page.value),size:'10'});if(status.value)q.set('status',status.value);const result=await api('/admin/broker-applications?'+q);if(run!==sequence)return;items.value=result.items;total.value=result.totalElements;totalPages.value=result.totalPages}
  catch(e){if(run===sequence)error.value=brokerErrorText(e)}finally{if(run===sequence)busy.value=false}
}
function select(item){selected.value=item;reason.value='';message.value=''}
async function review(action){
  if(busy.value||!selected.value||!reason.value.trim())return
  const application=selected.value;busy.value=true;error.value='';message.value=''
  try{await api('/admin/broker-applications/'+encodeURIComponent(application.id)+'/review',{method:'POST',body:{action,expectedVersion:application.contentVersion,reason:reason.value.trim()}});message.value='Đã xử lý hồ sơ. Khi thay đổi quyền, người dùng cần đăng nhập lại.';reason.value='';await load()}
  catch(e){error.value=brokerErrorText(e);if(e.status===409){selected.value=null;error.value+=' Tải lại danh sách và kiểm tra hồ sơ trước khi thao tác lại.'}}
  finally{busy.value=false}
}
async function move(delta){page.value+=delta;await load()}
onMounted(()=>load());onBeforeUnmount(()=>{sequence++})
</script>
<template>
  <section class="rounded-panel bg-white p-5 text-brand-navy sm:p-7">
    <h1 class="text-2xl font-semibold">Duyệt quyền đăng tin</h1><p class="mt-2 text-sm leading-6 text-brand-muted">Xét duyệt người đăng, độc lập với duyệt từng tin. Không cấp quyền ADMIN từ màn hình này.</p>
    <div class="my-5 flex flex-wrap items-end gap-3"><label class="sp-field">Trạng thái<select v-model="status" class="sp-input" :disabled="busy" @change="load(true)"><option value="">Tất cả</option><option v-for="(label,key) in applicationStatuses" v-show="key!=='NOT_REQUESTED'" :key="key" :value="key">{{label}}</option></select></label><button class="sp-button sp-button-secondary" type="button" :disabled="busy" @click="load()">Tải lại danh sách</button><p class="text-sm">{{total}} hồ sơ</p></div>
    <p v-if="busy" role="status">Đang xử lý…</p><p v-if="error" role="alert" class="my-4 whitespace-pre-wrap rounded-control bg-red-50 p-4 text-sm text-red-800">{{error}}</p><p v-if="message" role="status" class="my-4 text-sm text-emerald-800">{{message}}</p>
    <p v-if="!busy&&!error&&!items.length" class="py-8 text-center text-brand-muted">Chưa có hồ sơ ở trạng thái này.</p>
    <div class="grid gap-4"><article v-for="item in items" :key="item.id" class="rounded-panel border p-4" :class="selected?.id===item.id?'border-brand-gold bg-brand-cream':'border-brand-line'">
      <div class="flex flex-wrap items-start justify-between gap-3"><div><h2 class="font-semibold">{{item.displayName}}</h2><p class="mt-1 text-sm">{{item.applicantType==='OWNER'?'Chủ nhà':'Môi giới'}} · {{item.operatingArea}}</p><p class="mt-1 text-xs text-brand-muted">Tài khoản #{{item.userId}} · {{applicationStatuses[item.status]}} · phiên bản {{item.contentVersion}}</p></div><button class="sp-button sp-button-secondary" type="button" :disabled="busy" @click="select(item)">Xem hồ sơ</button></div>
      <div v-if="selected?.id===item.id" class="mt-5 grid gap-4 text-sm">
        <p>Điện thoại đã cung cấp: {{item.contactPhone}}</p><p class="whitespace-pre-wrap leading-6">{{item.requestMessage}}</p><p>Xác nhận trách nhiệm: {{item.responsibilityAccepted?'Đã xác nhận':'Chưa xác nhận'}}</p><p v-if="item.reviewReason" class="whitespace-pre-wrap">Phản hồi trước: {{item.reviewReason}}</p>
        <label v-if="reviewActions(item.status).length" class="sp-field">Lý do / phản hồi<textarea v-model="reason" class="sp-input min-h-24" required maxlength="2000" :disabled="busy"/></label>
        <div class="flex flex-wrap gap-3"><button v-for="action in reviewActions(item.status)" :key="action" class="sp-button" :class="action==='APPROVE'?'sp-button-primary':'sp-button-secondary'" type="button" :disabled="busy||!reason.trim()" @click="review(action)">{{applicationActions[action]}}</button></div>
      </div>
    </article></div>
    <nav v-if="totalPages>1" aria-label="Phân trang hồ sơ" class="mt-5 flex items-center gap-4"><button class="sp-button sp-button-secondary" :disabled="busy||page===0" @click="move(-1)">Trước</button><span>{{page+1}} / {{totalPages}}</span><button class="sp-button sp-button-secondary" :disabled="busy||page+1>=totalPages" @click="move(1)">Sau</button></nav>
  </section>
</template>
