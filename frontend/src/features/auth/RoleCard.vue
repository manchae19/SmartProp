<template>
  <div
    class="flex w-full items-start gap-3.5 overflow-hidden rounded-[20px] border border-white/28 bg-white/22 px-[18px] py-4 backdrop-blur-[9px]"
  >
    <span
      class="shrink-0 font-mono text-[12px] font-normal text-white/70"
    >
      {{ number }}
    </span>

    <div class="flex min-w-0 flex-col gap-[3px] overflow-hidden">
      <div class="font-sans text-[15.5px] font-medium text-white">
        {{ title }}
      </div>

      <div
        class="w-full max-w-[320px] font-sans text-[14px] font-normal leading-relaxed text-white/95"
      >
        {{ description }}
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  number: {
    type: String,
    required: true,
  },
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    required: true,
  },
})
</script>
