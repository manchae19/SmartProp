<script setup>
import { ref, computed, onMounted, onBeforeUnmount, defineAsyncComponent } from 'vue'
const PropertyExplorer = defineAsyncComponent(() => import('./PropertyExplorer.vue'))
const props = defineProps({ items: { type: Array, default: () => [] }, selectedId: String, total: Number, mapLink: Object, busy: Boolean, error: String })
const emit = defineEmits(['update:selectedId', 'retry'])
const host = ref(null), activated = ref(false)
const exploreLink = computed(() => ({ ...(props.mapLink || {path:'/map'}), query: { ...(props.mapLink?.query || {}), ...(props.selectedId ? {propertyId:props.selectedId} : {}) } }))
let observer
onMounted(() => {
  if (!('IntersectionObserver' in window)) { activated.value = true; return }
  observer = new IntersectionObserver(entries => { if(entries.some(e=>e.isIntersecting)){activated.value=true;observer.disconnect()} }, {rootMargin:'160px'})
  observer.observe(host.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>
<template>
  <div ref="host" class="home-gis">
    <p v-if="error" role="alert" class="home-gis-message">{{error}} <button type="button" @click="emit('retry')">Thử lại</button></p>
    <p v-if="busy" role="status" class="home-gis-message">Đang tải tin trên bản đồ…</p>
    <PropertyExplorer v-if="activated" :items="items" :selected-id="selectedId" :explore-link="exploreLink" preview @select="emit('update:selectedId',$event)" />
    <button v-else class="home-gis-activate" type="button" @click="activated=true">⌖ Khám phá vị trí trên bản đồ</button>
  </div>
</template>
<style scoped>
.home-gis{min-width:0}.home-gis-message{padding:12px 16px;font-size:13px;color:#536178}.home-gis-message button{text-decoration:underline}.home-gis-activate{width:100%;min-height:500px;border-radius:24px;background:linear-gradient(135deg,#e3ede9,#edf0e7);border:1px solid #d6e3dc;font-size:17px;color:#183b4c}
</style>
