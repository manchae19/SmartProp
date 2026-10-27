<script setup>
import {ref,computed,watch,onBeforeUnmount} from 'vue'
import {api,session} from '../services/api.js'
import {canPublish} from '../services/siteNavigation.js'
import {applicationStatuses,canRequestBroker,brokerErrorText} from '../services/brokerApplication.js'
const state=ref(null),busy=ref(false),error=ref('')
const buyer=computed(()=>canRequestBroker(session.user)),admin=computed(()=>session.user?.role==='ADMIN'&&session.user?.status==='ACTIVE')
let sequence=0
async function load(){
  const run=++sequence;state.value=null;error.value='';busy.value=false
  if(!buyer.value)return
  busy.value=true
  try{const result=await api('/users/me/broker-application');if(run===sequence)state.value=result}
  catch(e){if(run===sequence)error.value=brokerErrorText(e)}finally{if(run===sequence)busy.value=false}
}
watch(()=>[session.user?.id,session.user?.role,session.user?.status],load,{immediate:true})
onBeforeUnmount(()=>sequence++)
</script>
<template>
  <section aria-labelledby="broker-card-title" class="rounded-panel border border-brand-line bg-white p-5 sm:p-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div><p class="text-xs font-semibold tracking-widest text-brand-accent">QUYỀN ĐĂNG TIN</p><h2 id="broker-card-title" class="mt-2 text-xl font-semibold">{{admin?'Quản trị người đăng':canPublish(session.user)?'Quản lý bất động sản của bạn':'Đăng ký quyền đăng tin'}}</h2><p class="mt-2 text-sm leading-6 text-brand-muted">Hồ sơ người đăng và từng tin bất động sản được xét duyệt riêng. Chỉ tin đã duyệt mới xuất hiện công khai.</p></div>
      <span v-if="buyer&&state" class="rounded-full bg-brand-surface px-3 py-2 text-sm font-semibold">{{applicationStatuses[state.status]||state.status}}</span>
    </div>
    <template v-if="buyer">
      <p v-if="busy" role="status" class="mt-3 text-sm">Đang tải trạng thái…</p>
      <p v-if="error" role="alert" class="mt-3 text-sm leading-6 text-red-800">{{error}} <button type="button" class="underline" :disabled="busy" @click="load">Thử lại</button></p>
      <p v-if="state?.application?.reviewReason" class="mt-3 whitespace-pre-wrap text-sm leading-6">Phản hồi: {{state.application.reviewReason}}</p>
      <p v-if="state?.status==='PENDING'" class="mt-3 text-sm leading-6">Yêu cầu đang chờ xét duyệt. Bạn chưa có quyền đăng tin và không cần gửi yêu cầu trùng.</p>
      <p v-if="state?.status==='SUSPENDED'" class="mt-3 text-sm leading-6">Quyền đăng tin đang tạm ngưng. Vui lòng liên hệ quản trị viên.</p>
      <RouterLink v-if="state" class="sp-button sp-button-primary mt-4" to="/account/broker-application">{{state.status==='NOT_REQUESTED'?'Đăng ký quyền đăng tin':['REJECTED','NEEDS_INFORMATION'].includes(state.status)?'Bổ sung và gửi lại hồ sơ':'Xem trạng thái hồ sơ'}}</RouterLink>
    </template>
    <div v-if="canPublish(session.user)" class="mt-4 flex flex-wrap gap-3">
      <RouterLink v-if="admin" class="sp-button sp-button-primary" to="/admin/broker-applications">Duyệt quyền đăng tin</RouterLink>
      <RouterLink v-if="admin" class="sp-button sp-button-secondary" to="/admin/posts">Duyệt tin bất động sản</RouterLink>
      <RouterLink class="sp-button sp-button-secondary" to="/post">Đăng tin mới</RouterLink><RouterLink class="sp-button sp-button-secondary" to="/my-listing">Quản lý tin đăng</RouterLink>
    </div>
  </section>
</template>
