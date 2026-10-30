<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const video = ref(null)
const playing = ref(false)
const failed = ref(false)
const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
const reduced = ref(motion.matches)

async function play() {
  if (!video.value) return
  video.value.muted = true
  try { await video.value.play() } catch { playing.value = false }
}
function toggle() {
  if (playing.value) video.value?.pause()
  else play()
}
function motionChanged(event) {
  reduced.value = event.matches
  if (event.matches) video.value?.pause()
  else play()
}
onMounted(() => {
  motion.addEventListener('change', motionChanged)
  if (!reduced.value) play()
})
onBeforeUnmount(() => motion.removeEventListener('change', motionChanged))
</script>

<template>
  <div class="absolute inset-0">
    <video ref="video" :autoplay="!reduced" muted loop playsinline preload="metadata" poster="/media/home/hero-poster.jpg" aria-label="Video nền trang chủ SmartProp" class="absolute inset-0 h-full w-full object-cover" @playing="playing = true" @pause="playing = false" @error="failed = true">
      <source src="/background.mp4" type="video/mp4" />
    </video>
    <button v-if="!failed" type="button" :aria-label="playing ? 'Tạm dừng video nền' : 'Phát video nền'" class="absolute right-4 top-4 z-20 flex cursor-pointer items-center gap-2 rounded-full border border-white/30 bg-[#091728]/35 px-3 py-2 text-xs font-medium text-white/90 backdrop-blur-md transition hover:bg-[#091728]/65 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#D8B887] md:right-10" @click="toggle">
      <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path v-if="playing" d="M4 2h3v12H4zm5 0h3v12H9z" /><path v-else d="M4 2v12l10-6z" /></svg>
      {{ playing ? 'Tạm dừng video' : 'Phát video nền' }}
    </button>
  </div>
</template>
