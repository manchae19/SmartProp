<script setup>
import { nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'
const props = defineProps({ open: Boolean, title: { type: String, default: 'Khám phá SmartProp' } })
const emit = defineEmits(['update:open', 'closed'])
const panel = ref(null), closeButton = ref(null), titleId = useId()
let previousOverflow, locked = false, pendingCloses = 0
function unlock() { if (locked) { document.body.style.overflow = previousOverflow; locked = false } }
function close() { emit('update:open', false) }
function closePanel() { if (panel.value?.open) { pendingCloses++; panel.value.close() } unlock() }
function closed() {
  if (pendingCloses) { pendingCloses--; if (!props.open && !panel.value?.open) emit('closed'); return }
  if (panel.value?.open) return
  unlock(); emit('update:open', false); emit('closed')
}
function backdrop(event) {
  if (event.target !== panel.value) return
  const box = panel.value.getBoundingClientRect()
  if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) close()
}
function trapTab(event) {
  if (event.key !== 'Tab' || !panel.value?.open) return
  const items = [...panel.value.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])')].filter(element => element.getClientRects().length && !element.closest('[inert]'))
  const first = items[0], last = items.at(-1)
  if (!first) { event.preventDefault(); panel.value.focus(); return }
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
}
watch(() => props.open, async value => {
  await nextTick()
  if (!panel.value || props.open !== value) return
  if (value) {
    if (!panel.value.open) panel.value.showModal()
    if (!locked) { previousOverflow = document.body.style.overflow; locked = true; document.body.style.overflow = 'hidden' }
    closeButton.value?.focus()
  } else closePanel()
})
onBeforeUnmount(closePanel)
defineExpose({ id: titleId })
</script>
<template>
  <dialog ref="panel" :aria-labelledby="titleId" class="mobile-drawer fixed inset-y-0 right-0 left-auto m-0 h-dvh max-h-none w-[min(25rem,calc(100vw-1.25rem))] max-w-none border-0 bg-white p-0 text-brand-navy shadow-2xl" @cancel.prevent="close" @close="closed" @click="backdrop" @keydown="trapTab">
    <div class="flex h-full flex-col">
      <div class="flex shrink-0 items-center justify-between gap-4 border-b border-brand-line px-5 py-5"><h2 :id="titleId" class="text-lg font-semibold">{{ title }}</h2><button ref="closeButton" type="button" class="sp-icon-button" aria-label="Đóng menu" @click="close"><svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6" /></svg></button></div>
      <div v-if="open" class="min-h-0 flex-1 overflow-y-auto overscroll-contain p-5"><slot /></div>
    </div>
  </dialog>
</template>
<style scoped>
.mobile-drawer::backdrop{background:#07162bb3;backdrop-filter:blur(4px)}
</style>
