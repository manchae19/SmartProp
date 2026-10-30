<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { api, errorText } from '../../src/services/api.js'
import { googlePointUrl } from '../../src/services/googleMapsLocation.js'
const route = useRoute(), project = ref(null), busy = ref(false), error = ref('')
let sequence = 0
async function load() {
  const run = ++sequence; busy.value = true; error.value = ''; project.value = null
  try { const result = await api('/projects/' + encodeURIComponent(String(route.params.id)), { authenticated: false }); if (run === sequence) project.value = result }
  catch (failure) { if (run === sequence) error.value = failure.status === 404 ? 'Dự án không tồn tại hoặc chưa được công bố.' : errorText(failure) }
  finally { if (run === sequence) busy.value = false }
}
watch(() => route.params.id, load, { immediate: true })
onBeforeUnmount(() => sequence++)
const mapLink = computed(() => project.value ? googlePointUrl(project.value.latitude, project.value.longitude) : '')
</script>
<template>
  <div class="sp-container py-10 sm:py-14" data-project-detail><RouterLink to="/projects" class="text-sm font-semibold text-brand-accent">← Danh sách dự án</RouterLink><p v-if="busy" role="status" class="mt-8 text-sm text-brand-muted">Đang tải dự án…</p><div v-else-if="error" role="alert" class="mt-8 rounded-panel border border-rose-200 bg-rose-50 p-6 text-sm text-rose-800">{{ error }}<button type="button" class="ml-3 font-semibold underline" @click="load">Thử lại</button></div><article v-else-if="project" class="mt-8"><p class="text-xs font-semibold tracking-[.2em] text-brand-accent">DỮ LIỆU TỪ SMARTPROP</p><h1 class="mt-3 max-w-4xl break-words text-3xl font-semibold tracking-tight sm:text-5xl">{{ project.name }}</h1><p class="mt-4 text-sm leading-7 text-brand-muted">Thông tin được cung cấp trong hồ sơ dự án. Chưa có ảnh dự án trong API này.</p><dl class="mt-8 grid gap-5 rounded-panel border border-brand-line bg-white p-6 sm:grid-cols-2 sm:p-8"><div v-for="(label, key) in { developer: 'Chủ đầu tư', address: 'Địa chỉ', scale: 'Quy mô', handoverYear: 'Năm bàn giao' }" :key="key" class="min-w-0"><dt class="text-xs text-brand-muted">{{ label }}</dt><dd class="mt-2 break-words text-base font-medium">{{ project[key] || 'Chưa cung cấp' }}</dd></div><div class="sm:col-span-2"><dt class="text-xs text-brand-muted">Tiện ích theo hồ sơ dự án</dt><dd class="mt-2 text-sm leading-7">{{ project.amenities?.join(', ') || 'Chưa cung cấp' }}</dd></div></dl><a v-if="mapLink" :href="mapLink" target="_blank" rel="noopener noreferrer" class="sp-button sp-button-secondary mt-6">Mở tọa độ dự án trên Google Maps ↗</a></article></div>
</template>
