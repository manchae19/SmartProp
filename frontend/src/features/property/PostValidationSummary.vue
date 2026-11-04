<script setup>
import {useRoute} from 'vue-router'
import {postSteps} from './postForm.js'
defineProps({issues:{type:Array,default:()=>[]}})
const route=useRoute()
</script>
<template>
  <section v-if="issues.length" role="alert" aria-label="Thông tin cần sửa" class="my-4 rounded-xl bg-red-50 p-4 text-xs text-red-800">
    <p class="font-semibold">Vui lòng kiểm tra thông tin sau. Bấm vào lỗi để đến đúng bước cần sửa:</p>
    <ul class="mt-2 space-y-2"><li v-for="(issue,index) in issues" :key="issue.field+index"><RouterLink :to="{path:postSteps[issue.step-1].path,query:route.query,hash:'#post-'+issue.field}" class="underline underline-offset-2">Bước {{issue.step}} · {{issue.label}}: {{issue.message}}</RouterLink></li></ul>
  </section>
</template>