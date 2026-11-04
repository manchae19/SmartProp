<script setup>
import { ref,watch,onBeforeUnmount } from 'vue'
import { api,session } from '../features/auth/api.js'
const props=defineProps({src:String,alt:{type:String,default:''}})
const url=ref(''), failed=ref(false);let serial=0
function release(){if(url.value)URL.revokeObjectURL(url.value);url.value=''}
watch(()=>[props.src,session.token],async()=>{const run=++serial;release();failed.value=false;if(!props.src)return;try{const blob=await api(props.src.replace(/^\/api\/v1/,''),{responseType:'blob',authenticated:!!session.token});if(run===serial)url.value=URL.createObjectURL(blob)}catch{if(run===serial)failed.value=true}},{immediate:true})
onBeforeUnmount(()=>{serial++;release()})
</script>
<template><img v-if="url" :src="url" :alt="alt" loading="lazy" @error="release();failed=true"><div v-else class="sp-placeholder" role="img" :aria-label="alt">{{failed?'Không tải được ảnh':src?'Đang tải ảnh…':'Chưa có ảnh'}}</div></template>
<style scoped>.sp-placeholder{display:flex;align-items:center;justify-content:center;background:#dedbd3;color:#536178;font-size:13px;min-height:100px;width:100%;height:100%}</style>