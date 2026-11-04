<script setup>
import ValuationPanel from './ValuationPanel.vue'
import ValuationHistory from './ValuationHistory.vue'
import { ref } from 'vue'
const history = ref(null), refreshKey = ref(0)
</script>

<template>
  <main class="min-h-screen bg-[#ebe9e2] text-[#1E325A] px-5 py-8 sm:py-12">
    <div class="max-w-3xl mx-auto">
      <nav class="flex flex-wrap justify-between gap-4 mb-8 text-sm">
        <RouterLink to="/home" class="font-semibold">SmartProp</RouterLink>
        <RouterLink to="/listings" class="underline underline-offset-4">Xem tin bất động sản</RouterLink>
      </nav>
      <h1 class="text-3xl sm:text-4xl font-semibold tracking-tight">Tham khảo giá trước khi quyết định</h1>
      <p class="mt-4 mb-8 text-sm leading-6 text-[#58657c]">Ước tính tổng giá rao nhà ở, đất nền và căn hộ tại các địa bàn Đà Nẵng mà mô hình hỗ trợ.</p>
      <ValuationPanel history-enabled @saved="refreshKey++" @options-loaded="history?.setLabels($event)" />
      <ValuationHistory ref="history" :refresh-key="refreshKey" />
    </div>
  </main>
</template>
