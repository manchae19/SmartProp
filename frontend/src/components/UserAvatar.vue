<script setup>
import {computed} from 'vue'
import {avatar} from '../features/account/avatar.js'
import {session} from '../features/auth/api.js'
import PrivateImage from './PrivateImage.vue'
const props=defineProps({name:String,size:{type:Number,default:44}})
const initials=computed(()=>String(props.name||'').trim().split(/\s+/).filter(Boolean).slice(-2).map(word=>word[0]).join('').toUpperCase()||'S')
const image=computed(()=>avatar.available&&avatar.owner===session.user?.id?avatar.url:null)
</script>
<template><span class="user-avatar" :style="{width:size+'px',height:size+'px',fontSize:Math.max(14,Math.round(size*.3))+'px'}" role="img" :aria-label="name?'Ảnh đại diện của '+name:'SmartProp'"><PrivateImage v-if="image" :src="image" :alt="'Ảnh đại diện của '+name"/><span v-else>{{initials}}</span></span></template>
<style scoped>.user-avatar{display:inline-flex;flex-shrink:0;align-items:center;justify-content:center;overflow:hidden;border-radius:50%;background:#10233f;color:white;font-weight:650;letter-spacing:.02em;box-shadow:0 0 0 4px #f6f3ee}.user-avatar :deep(img){width:100%;height:100%;object-fit:cover}.user-avatar :deep(.sp-placeholder){min-height:0;font-size:13px;color:white;background:#10233f}</style>
