<script setup>
import { computed } from 'vue'
import { poiSvgPath } from '../services/nearbyPlaces.js'

const props = defineProps({
  category: {
    type: String,
    default: ''
  }
})

const path = computed(() => poiSvgPath(props.category))
</script>

<template>
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    class="shrink-0"
    aria-hidden="true"
  >
    <path :d="path" />
  </svg>
</template>
