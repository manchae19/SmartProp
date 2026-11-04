<script setup>
defineProps({page:Number,totalPages:Number,totalElements:Number,busy:Boolean});defineEmits(['change'])
</script>
<template><div class="sp-pager"><button :disabled="busy||page<=0" @click="$emit('change',page-1)">← Trước</button><span class="sp-muted">Trang {{totalPages?page+1:0}} / {{totalPages||0}} · {{totalElements||0}} kết quả</span><button :disabled="busy||page+1>=totalPages" @click="$emit('change',page+1)">Sau →</button></div></template>