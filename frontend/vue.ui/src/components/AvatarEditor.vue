<script setup>
import {ref,onBeforeUnmount} from 'vue'
import {avatar,uploadAvatar,removeAvatar,validateAvatar,loadAvatar} from '../services/avatar.js'
import {errorText} from '../services/api.js'
import AppIcon from './AppIcon.vue'
const picker=ref(null),selected=ref(null),preview=ref(''),busy=ref(false),error=ref(''),message=ref('')
let revision=0
function reset(){revision++;selected.value=null;if(preview.value)URL.revokeObjectURL(preview.value);preview.value='';if(picker.value)picker.value.value=''}
async function choose(event){const file=event.target.files?.[0];reset();error.value=message.value='';if(!file)return;const run=revision;try{await validateAvatar(file);if(run!==revision)return;selected.value=file;preview.value=URL.createObjectURL(file)}catch(e){error.value=e.message}}
async function save(){if(!selected.value||busy.value)return;busy.value=true;error.value='';try{await uploadAvatar(selected.value);reset();message.value='Đã cập nhật ảnh đại diện.'}catch(e){error.value=errorText(e)}finally{busy.value=false}}
async function remove(){if(busy.value)return;busy.value=true;error.value='';try{await removeAvatar();reset();message.value='Đã trở về ảnh đại diện mặc định.'}catch(e){error.value=errorText(e)}finally{busy.value=false}}
onBeforeUnmount(reset)
</script>
<template><div class="avatar-editor"><input ref="picker" type="file" accept="image/jpeg,image/png,image/webp" class="sr-only" aria-label="Chọn ảnh đại diện" :disabled="!avatar.enabled||busy" @change="choose"/><button type="button" class="sp-button sp-button-secondary w-full" :disabled="!avatar.enabled||busy||avatar.loading" @click="picker?.click()"><AppIcon name="camera"/>Đổi ảnh đại diện</button>
 <p v-if="avatar.loading" class="mt-2 text-[13px] text-brand-muted" role="status">Đang tải ảnh…</p><p v-else-if="!avatar.enabled" class="mt-2 max-w-64 text-[13px] leading-5 text-brand-muted">Ảnh đại diện chưa được bật trên hệ thống. <button v-if="avatar.error" type="button" class="underline" @click="loadAvatar">Thử lại</button></p><p v-else class="mt-2 max-w-64 text-[13px] leading-5 text-brand-muted">JPG, PNG hoặc WebP · tối đa 5 MB.</p>
 <div v-if="preview" class="mt-4 rounded-2xl border border-brand-line bg-brand-surface p-4"><img :src="preview" alt="Xem trước ảnh đại diện mới" class="mx-auto size-28 rounded-full object-cover"/><p class="mt-3 text-center text-[13px]">Xem trước · ảnh được cắt vuông ở giữa.</p><div class="mt-3 flex flex-wrap justify-center gap-2"><button type="button" class="sp-button sp-button-primary" :disabled="busy" @click="save">{{busy?'Đang lưu…':'Lưu ảnh'}}</button><button type="button" class="sp-button sp-button-secondary" :disabled="busy" @click="reset">Hủy</button></div></div>
 <button v-if="avatar.available&&!preview" type="button" class="mt-3 text-[13px] text-brand-muted underline" :disabled="busy" @click="remove">Xóa ảnh đại diện</button><p v-if="error" role="alert" class="mt-3 max-w-72 text-sm leading-6 text-red-800">{{error}}</p><p v-if="message" role="status" class="mt-3 max-w-72 text-sm leading-6 text-emerald-800">{{message}}</p>
</div></template>
