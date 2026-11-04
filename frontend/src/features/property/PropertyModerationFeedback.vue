<script setup>
import {ref} from 'vue'
import {api,errorText} from '../auth/api.js'
const props=defineProps({id:{type:String,required:true}})
const items=ref(null),error=ref(''),busy=ref(false),open=ref(false)
async function toggle(){open.value=!open.value;if(!open.value||busy.value)return;busy.value=true;error.value='';try{items.value=await api('/users/me/properties/'+encodeURIComponent(props.id)+'/moderation')}catch(e){error.value=errorText(e)}finally{busy.value=false}}
</script>
<template>
  <div class="mt-4 border-t border-brand-line pt-3 text-sm"><button type="button" class="font-semibold underline" :aria-expanded="open" :disabled="busy" @click="toggle">{{open?'Thu gọn phản hồi':'Xem phản hồi kiểm duyệt'}}</button><div v-if="open" class="mt-3 grid gap-3"><p v-if="busy" role="status">Đang tải…</p><p v-if="error" role="alert" class="text-red-800">{{error}}</p><p v-if="items&&!items.length">Chưa có phản hồi kiểm duyệt.</p><article v-for="(item,index) in items" :key="index" class="rounded-control bg-brand-surface p-3"><p class="text-xs text-brand-muted">{{item.newStatus}} · {{new Date(item.createdAt).toLocaleString('vi-VN')}}</p><p class="mt-1 whitespace-pre-wrap leading-6">{{item.reason}}</p></article></div></div>
</template>
