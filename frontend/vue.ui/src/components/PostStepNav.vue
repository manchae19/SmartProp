<script setup>
import {useRoute} from 'vue-router'
import {postSteps} from '../services/postForm.js'
defineProps({current:Number,busy:Boolean})
const route=useRoute()
</script>
<template>
  <nav aria-label="Các bước đăng tin" class="grid grid-cols-3 gap-3 py-6">
    <RouterLink v-for="item in postSteps" :key="item.step" :to="{path:item.path,query:route.query}" :aria-current="current===item.step?'step':undefined" :aria-disabled="busy||undefined" @click="busy&&$event.preventDefault()" class="border-t-2 pt-2 text-xs leading-relaxed transition hover:text-[#1E325A] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#1E325A]" :class="[item.step<=current?'border-[#1E325A] text-[#1E325A]':'border-[#cfd2d4] text-gray-500',busy?'pointer-events-none opacity-60':'']">Bước {{item.step}} · {{item.label}}</RouterLink>
  </nav>
</template>