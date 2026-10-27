<script setup>
import {ref,reactive,onMounted,computed} from 'vue'
import {api,loadProfile,session} from '../../src/services/api.js'
import {canPublish} from '../../src/services/siteNavigation.js'
import {applicationStatuses,canApply,applicationPayload,brokerErrorText,canRequestBroker} from '../../src/services/brokerApplication.js'
const state=ref(null),busy=ref(false),error=ref(''),message=ref(''),form=reactive({applicantType:'OWNER',displayName:'',contactPhone:'',operatingArea:'',requestMessage:'',responsibilityAccepted:false})
const needsReload=ref(false),ready=ref(false)
const editable=computed(()=>ready.value&&!needsReload.value&&canApply(state.value,session.user))
async function load(){
  busy.value=true;error.value='';ready.value=false;state.value=null;message.value='';needsReload.value=false
  try{await loadProfile();if(!canRequestBroker(session.user))return;state.value=await api('/users/me/broker-application');const a=state.value.application
    ready.value=true
    if(a)Object.assign(form,{applicantType:a.applicantType,displayName:a.displayName,contactPhone:a.contactPhone,operatingArea:a.operatingArea,requestMessage:a.requestMessage,responsibilityAccepted:false})
    else Object.assign(form,{displayName:session.user.fullName||'',contactPhone:session.user.phone||'',operatingArea:session.user.district||''})
  }catch(e){error.value=brokerErrorText(e)}finally{busy.value=false}
}
async function submit(){
  if(busy.value||!editable.value)return
  busy.value=true;error.value='';message.value=''
  try{state.value=await api('/users/me/broker-application',{method:'POST',body:applicationPayload(form,state.value,session.user)});message.value='Đã gửi hồ sơ. Vui lòng chờ quản trị viên xét duyệt. Khi được cấp quyền, hãy đăng nhập lại.'}
  catch(e){error.value=brokerErrorText(e);if(e.status===409)needsReload.value=true}finally{busy.value=false}
}
onMounted(load)
</script>
<template>
  <div class="sp-container max-w-4xl py-8 sm:py-12">
    <RouterLink to="/account" class="text-sm underline">← Tài khoản</RouterLink>
    <h1 class="mt-5 text-3xl font-semibold">Đăng ký quyền đăng tin</h1>
    <p class="mt-3 text-sm leading-6 text-brand-muted">Đăng ký miễn phí bằng hồ sơ liên hệ. Không gửi căn cước hoặc giấy tờ nhạy cảm trong nội dung yêu cầu. Hồ sơ này chỉ bạn và quản trị viên được phép xem.</p>
    <p v-if="busy" role="status" class="mt-5">Đang xử lý…</p>
    <p v-if="error" role="alert" class="mt-5 rounded-panel bg-red-50 p-4 text-sm text-red-800">{{error}}</p>
    <p v-if="message" role="status" class="mt-5 rounded-panel bg-emerald-50 p-4 text-sm text-emerald-900">{{message}}</p>
    <button class="sp-button sp-button-secondary mt-5" type="button" :disabled="busy" @click="load">Tải lại trạng thái</button>
    <section v-if="state" class="mt-6 rounded-panel border border-brand-line bg-white p-5 sm:p-7">
      <h2 class="text-lg font-semibold">{{applicationStatuses[state.status]||state.status}}</h2>
      <p v-if="state.legacyPublisher" class="mt-2 text-sm text-brand-muted">Quyền hiện có của tài khoản được giữ nguyên.</p>
      <p v-if="state.application?.reviewReason" class="mt-3 whitespace-pre-wrap rounded-control bg-brand-surface p-4 text-sm leading-6">Phản hồi của quản trị viên: {{state.application.reviewReason}}</p>
      <p v-if="state.status==='PENDING'" class="mt-3 text-sm leading-6">Bạn chưa có quyền tạo tin. Có thể quay lại kiểm tra sau; không cần gửi lại yêu cầu.</p>
      <p v-if="state.status==='SUSPENDED'" class="mt-3 text-sm leading-6">Quyền đăng tin đang tạm ngưng. Liên hệ quản trị viên để xem xét khôi phục, không gửi yêu cầu mới.</p>
      <div v-if="canPublish(session.user)" class="mt-5 flex flex-wrap gap-3"><RouterLink to="/post" class="sp-button sp-button-primary">Đăng tin mới</RouterLink><RouterLink to="/my-listing" class="sp-button sp-button-secondary">Quản lý tin đăng</RouterLink></div>
      <form v-if="editable" class="mt-6 grid gap-5" @submit.prevent="submit">
        <fieldset :disabled="busy" class="grid gap-5 sm:grid-cols-2">
          <label class="sp-field">Loại người đăng<select v-model="form.applicantType" name="applicantType" class="sp-input" required><option value="OWNER">Chủ nhà</option><option value="AGENT">Môi giới</option></select></label>
          <label class="sp-field">Họ tên / tên đơn vị<input v-model="form.displayName" name="displayName" class="sp-input" required maxlength="150" autocomplete="name"/></label>
          <label class="sp-field">Số điện thoại liên hệ<input v-model="form.contactPhone" name="contactPhone" class="sp-input" required minlength="8" maxlength="30" type="tel" autocomplete="tel" pattern="\+?[0-9][0-9 \(\)\-]{6,28}[0-9]"/></label>
          <label class="sp-field">Khu vực hoạt động<input v-model="form.operatingArea" name="operatingArea" class="sp-input" required maxlength="200" placeholder="Ví dụ: Hải Châu, Đà Nẵng"/></label>
          <label class="sp-field sm:col-span-2">Nội dung yêu cầu<textarea v-model="form.requestMessage" name="requestMessage" class="sp-input min-h-32" required maxlength="2000" rows="4"/></label>
          <label class="flex items-start gap-3 text-sm leading-6 sm:col-span-2"><input v-model="form.responsibilityAccepted" name="responsibilityAccepted" required type="checkbox" class="mt-1"/>Tôi chịu trách nhiệm về tính chính xác và quyền sử dụng thông tin, hình ảnh trong các tin đăng.</label>
        </fieldset>
        <button class="sp-button sp-button-primary justify-self-start" type="submit" :disabled="busy">{{state.status==='NOT_REQUESTED'?'Gửi yêu cầu':'Gửi lại hồ sơ'}}</button>
      </form>
      <dl v-else-if="state.application" class="mt-5 grid gap-3 text-sm"><div><dt class="text-brand-muted">Người đăng</dt><dd>{{state.application.displayName}} · {{state.application.applicantType==='OWNER'?'Chủ nhà':'Môi giới'}}</dd></div><div><dt class="text-brand-muted">Liên hệ / khu vực</dt><dd>{{state.application.contactPhone}} · {{state.application.operatingArea}}</dd></div><div><dt class="text-brand-muted">Nội dung</dt><dd class="whitespace-pre-wrap">{{state.application.requestMessage}}</dd></div></dl>
    </section>
  </div>
</template>
