<script setup>
import AppIcon from './AppIcon.vue'
defineProps({ preview: String, locked: Boolean })
const emit = defineEmits(['choose', 'current'])
const prompts = [
  { label: 'Tìm nhà theo ngân sách', text: 'Tôi có 10 tỷ, gợi ý bất động sản phù hợp và giải thích điểm đề xuất.' },
  { label: 'Khám phá tiện ích khu vực', text: 'Hải Châu có bằng chứng bệnh viện nào?' },
  { label: 'Kiểm tra lựa chọn dưới 2 tỷ', text: 'Tôi có 2 tỷ, có bất động sản công khai phù hợp không?' },
]
</script>
<template>
  <div class="session-panel">
    <p class="panel-eyebrow">TRONG TAB NÀY</p>
    <button class="current-conversation" type="button" aria-current="true" @click="emit('current')"><span class="session-avatar" aria-hidden="true">S</span><span><strong>SmartProp AI Advisor</strong><small>{{ preview || 'Bắt đầu từ nhu cầu của bạn' }}</small></span></button>
    <div class="panel-prompts"><h2>Gợi ý bắt đầu</h2><button v-for="prompt in prompts" :key="prompt.label" type="button" :disabled="locked" @click="emit('choose', prompt.text)"><AppIcon name="messages" /><span>{{ prompt.label }}</span><AppIcon name="arrow" /></button></div>
    <div class="session-scope"><AppIcon name="shield" /><div><strong>Chỉ dùng dữ liệu công khai</strong><p>Giá rao để tham khảo. Không dùng dữ liệu nghiên cứu để lấp kết quả rỗng.</p></div></div>
    <p class="session-privacy">Lịch sử chỉ ở tab hiện tại, không lưu vào tài khoản và mất khi tải lại. Mỗi câu hỏi được xử lý độc lập; hãy nhắc lại ngân sách và khu vực.</p>
    <RouterLink to="/advisor" class="filter-link">Tìm bằng bộ lọc <AppIcon name="arrow" /></RouterLink>
  </div>
</template>
<style scoped>
.session-panel{padding:24px 15px;color:var(--color-brand-navy);min-width:0}.panel-eyebrow{font-size:.61rem;font-weight:750;letter-spacing:.13em;color:var(--color-brand-muted);padding:0 10px;margin-bottom:10px}.current-conversation{display:flex;align-items:center;gap:10px;background:#e6ebf2;border-radius:15px;width:100%;text-align:left;padding:13px 11px;min-width:0}.session-avatar{display:grid;place-items:center;width:38px;height:38px;border-radius:13px;background:var(--color-brand-navy);color:var(--color-brand-highlight);font-size:1.1rem;font-weight:700;flex-shrink:0}.current-conversation>span:last-child{min-width:0}.current-conversation strong{display:block;font-size:.78rem}.current-conversation small{display:block;font-size:.69rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:170px;color:var(--color-brand-muted);margin-top:3px}.panel-prompts{margin-top:32px;padding:0 6px}.panel-prompts h2{font-size:.7rem;font-weight:700;color:var(--color-brand-muted);margin:0 4px 10px}.panel-prompts button{display:flex;align-items:center;gap:8px;min-height:48px;text-align:left;font-size:.72rem;line-height:1.5;width:100%;padding:8px 5px;border-radius:9px}.panel-prompts button:hover:not(:disabled){background:#e8edf3}.panel-prompts button:disabled{opacity:.5;cursor:wait}.panel-prompts svg{width:16px;height:16px;flex-shrink:0}.panel-prompts svg:last-child{margin-left:auto;width:14px}.session-scope{display:flex;gap:8px;border-top:1px solid #dde2e9;margin:25px 10px 0;padding-top:22px}.session-scope svg{width:17px;height:17px;flex-shrink:0;margin-top:2px}.session-scope strong{font-size:.7rem;font-weight:650}.session-scope p,.session-privacy{font-size:.68rem;line-height:1.8;color:var(--color-brand-muted);margin-top:6px}.session-privacy{padding:0 10px;margin-top:18px}.filter-link{display:flex;align-items:center;gap:7px;margin:16px 10px 0;min-height:44px;font-size:.72rem;font-weight:650;color:var(--color-brand-accent)}.filter-link svg{width:14px;height:14px}:focus-visible{outline:3px solid var(--color-brand-accent);outline-offset:3px}
</style>
