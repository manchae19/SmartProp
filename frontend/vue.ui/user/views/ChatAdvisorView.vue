<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { chatSession } from '../../src/services/chatRuntime.js'
import { isNearChatBottom } from '../../src/services/chatPresentation.js'
import ChatAnswer from '../../src/components/ChatAnswer.vue'
import ChatSessionPanel from '../../src/components/ChatSessionPanel.vue'
import MobileDrawer from '../../src/components/layout/MobileDrawer.vue'
import AppIcon from '../../src/components/AppIcon.vue'
const { state } = chatSession
const draft = ref(''), input = ref(null), thread = ref(null), clock = ref(Date.now()), viewportHeight = ref(null)
const sidebar = ref(true), drawer = ref(false), smallScreen = ref(false), menuButton = ref(null)
const follow = ref(true), unread = ref(false)
let focusAfterDrawer = 'menu'
let timer, media
const elapsed = computed(() => Math.max(0, Math.floor((clock.value - state.startedAt) / 1000)))
const waitSeconds = computed(() => Math.max(0, Math.ceil((state.retryAt - clock.value) / 1000)))
const locked = computed(() => state.busy || waitSeconds.value > 0)
const preview = computed(() => state.messages.findLast(m => m.role === 'user')?.text || '')

function resizeInput() {
  if (!input.value) return
  input.value.style.height = 'auto'
  input.value.style.height = Math.min(128, input.value.scrollHeight) + 'px'
  input.value.style.overflowY = input.value.scrollHeight > 128 ? 'auto' : 'hidden'
}
function scrollLatest() {
  follow.value = true; unread.value = false
  if (thread.value) thread.value.scrollTop = thread.value.scrollHeight
}
function onScroll() { follow.value = isNearChatBottom(thread.value); if (follow.value) unread.value = false }
function reading() { follow.value = false }
function answerResized() { if (follow.value) nextTick(scrollLatest); else unread.value = true }
function questionFor(messageId) {
  const index = state.messages.findIndex(m => m.id === messageId)
  return state.messages.slice(0, index).findLast(m => m.role === 'user')?.text || ''
}
function syncViewport() {
  if (typeof window === 'undefined') return
  const view = window.visualViewport
  const top = document.querySelector('.app-header')?.getBoundingClientRect().bottom || 0
  // visualViewport follows the mobile keyboard; composer stays inside the visible frame.
  viewportHeight.value = Math.max(180, (view?.height || window.innerHeight) - Math.max(0, top - (view?.offsetTop || 0)))
  if (follow.value) nextTick(scrollLatest)
}
function screenChanged() { smallScreen.value = media.matches; if (!media.matches) drawer.value = false; syncViewport() }
function togglePanel() { if (smallScreen.value) { focusAfterDrawer = 'menu'; drawer.value = true } else sidebar.value = !sidebar.value }
async function drawerClosed() { await nextTick(); (focusAfterDrawer === 'input' ? input.value : menuButton.value)?.focus({ preventScroll: true }) }
async function choose(question) { if (locked.value) return; draft.value = question; focusAfterDrawer = 'input'; drawer.value = false; await nextTick(); resizeInput(); input.value?.focus() }
function currentConversation() { focusAfterDrawer = 'input'; drawer.value = false; nextTick(() => input.value?.focus()) }
function newConversation() {
  if (locked.value) return
  chatSession.clear(); draft.value = ''; scrollLatest(); nextTick(() => { resizeInput(); input.value?.focus() })
}
async function submit() {
  if (locked.value || !draft.value.trim()) return
  follow.value = true
  const pending = chatSession.submit(draft.value)
  if (state.busy) draft.value = ''
  await nextTick(); resizeInput(); scrollLatest()
  await pending
}
function retry() { if (locked.value) return; follow.value = true; chatSession.retry() }
function keydown(event) { if (!event.shiftKey && !event.isComposing) { event.preventDefault(); submit() } }
watch(draft, () => nextTick(resizeInput))
watch(() => [state.messages.length, state.busy, state.error], async () => {
  const shouldFollow = follow.value
  await nextTick()
  if (shouldFollow) scrollLatest()
  else unread.value = true
})
onMounted(() => {
  timer = setInterval(() => { clock.value = Date.now() }, 1000)
  media = window.matchMedia('(max-width: 760px)'); screenChanged(); media.addEventListener('change', screenChanged)
  window.addEventListener('resize', syncViewport); window.visualViewport?.addEventListener('resize', syncViewport); window.visualViewport?.addEventListener('scroll', syncViewport)
  nextTick(() => { resizeInput(); scrollLatest() })
})
onBeforeUnmount(() => {
  clearInterval(timer); media?.removeEventListener('change', screenChanged)
  window.removeEventListener('resize', syncViewport); window.visualViewport?.removeEventListener('resize', syncViewport); window.visualViewport?.removeEventListener('scroll', syncViewport)
})
</script>

<template>
  <section class="messenger-page" aria-labelledby="chat-title" :style="viewportHeight ? { height: viewportHeight + 'px' } : undefined">
    <div class="messenger-shell" :class="{ 'sidebar-collapsed': !sidebar }">
      <aside v-if="sidebar" class="desktop-chat-panel" aria-label="Hội thoại trong tab"><div class="panel-title"><h2>Tin nhắn</h2><span>SmartProp</span></div><ChatSessionPanel :preview="preview" :locked="locked" @choose="choose" @current="currentConversation" /></aside>
      <div class="conversation">
        <header class="conversation-header">
          <button ref="menuButton" type="button" class="chat-icon-button panel-toggle" :aria-label="smallScreen ? 'Mở hội thoại và gợi ý' : sidebar ? 'Thu gọn danh sách hội thoại' : 'Mở danh sách hội thoại'" :aria-expanded="smallScreen ? drawer : sidebar" @click="togglePanel"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9 4v16"/></svg></button>
          <span class="conversation-avatar" aria-hidden="true">S<span>AI</span></span>
          <div class="conversation-name"><h1 id="chat-title">SmartProp AI Advisor</h1><p>Trợ lý tư vấn bất động sản</p></div>
          <button type="button" class="chat-icon-button new-chat" :disabled="locked || !state.messages.length" aria-label="Tạo hội thoại mới" title="Bắt đầu lại sẽ xóa hội thoại hiện tại trong tab" @click="newConversation"><AppIcon name="edit" /><span>Hội thoại mới</span></button>
        </header>

        <div class="thread-host">
          <div ref="thread" class="chat-thread" role="log" aria-labelledby="chat-title" aria-live="polite" aria-relevant="additions" :aria-busy="state.busy" tabindex="0" @scroll.passive="onScroll">
            <div class="thread-date"><span>Hội thoại trong tab này</span></div>
            <div v-if="!state.messages.length" class="chat-welcome">
              <span class="welcome-avatar" aria-hidden="true">S</span><h2>Chào bạn, mình là SmartProp.</h2><p>Bạn đang tìm một nơi để ở hay muốn khám phá khu vực? Hãy bắt đầu từ ngân sách và nhu cầu của bạn.</p>
              <div class="welcome-prompts"><button type="button" :disabled="locked" @click="choose('Tôi có 10 tỷ, gợi ý bất động sản phù hợp.')">Tìm BĐS theo ngân sách<AppIcon name="arrow" /></button><button type="button" :disabled="locked" @click="choose('Hải Châu có bằng chứng bệnh viện nào?')">Hỏi tiện ích khu vực<AppIcon name="arrow" /></button></div>
              <p class="welcome-note">Chỉ dùng dữ liệu công khai. Mỗi câu hỏi được xử lý độc lập.</p>
            </div>
            <p v-if="state.trimmed" class="trimmed-note">Đang hiển thị 24 tin nhắn gần nhất trong tab.</p>
            <article v-for="message in state.messages" :key="message.id" :class="message.role === 'user' ? 'user-message' : 'assistant-message'" :data-chat-message="message.role">
              <template v-if="message.role === 'user'"><span class="sr-only">Bạn:</span><p class="user-bubble">{{ message.text }}</p></template>
              <template v-else><span class="message-avatar" aria-hidden="true">S</span><ChatAnswer :result="message.response" :message-id="message.id" :question="questionFor(message.id)" @reading="reading" @resized="answerResized" /></template>
            </article>
            <div v-if="state.busy" class="assistant-message typing-message" role="status" data-chat-loading>
              <span class="message-avatar" aria-hidden="true">S</span><div><div class="typing-bubble" aria-hidden="true"><i/><i/><i/></div><p class="typing-label">{{ elapsed >= 30 ? 'SmartProp vẫn đang xử lý. Bạn không cần gửi lại.' : 'SmartProp đang tìm kiếm và phân tích…' }}</p><span class="sr-only">Câu trả lời sẽ xuất hiện khi xử lý hoàn tất.</span></div>
            </div>
            <div v-if="state.error" class="assistant-message" role="alert" data-chat-error><span class="message-avatar" aria-hidden="true">S</span><div class="error-bubble"><p>{{ state.error.text }}</p><button v-if="state.error.retry" type="button" :disabled="locked" @click="retry">{{ waitSeconds ? 'Chờ ' + waitSeconds + ' giây' : 'Thử lại' }}<AppIcon name="arrow" /></button></div></div>
            <div class="thread-bottom" aria-hidden="true" />
          </div>
          <button v-if="unread" type="button" class="new-message-button" @click="scrollLatest">Tin nhắn mới <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M12 4v16m-6-6 6 6 6-6"/></svg></button>
        </div>

        <footer class="composer-dock">
          <form class="chat-composer" :aria-busy="state.busy" @submit.prevent="submit">
            <label class="sr-only" for="chat-question">Câu hỏi của bạn</label>
            <div class="composer-field"><textarea id="chat-question" ref="input" v-model="draft" :disabled="locked" rows="1" maxlength="2000" required placeholder="Nhắn tin cho SmartProp AI..." aria-describedby="chat-input-hint" @keydown.enter="keydown" /><span v-if="draft.length > 1700" class="input-count" aria-hidden="true">{{ draft.length }}/2.000</span></div>
            <button type="submit" class="send-button" :disabled="locked || !draft.trim()" :aria-label="state.busy ? 'Đang xử lý câu hỏi' : 'Gửi câu hỏi'" :title="state.busy ? 'Đang xử lý câu hỏi' : 'Gửi câu hỏi'"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 14-8-4 16-4-6-6-2Zm6 2 8-10"/></svg></button>
          </form>
          <p id="chat-input-hint" class="composer-note"><span>Enter để gửi · Shift + Enter xuống dòng.</span><span>Thông tin tham khảo · không thay thế kiểm tra thực tế.</span></p>
        </footer>
      </div>
    </div>
    <MobileDrawer v-model:open="drawer" title="Hội thoại và gợi ý" @closed="drawerClosed"><ChatSessionPanel :preview="preview" :locked="locked" @choose="choose" @current="currentConversation" /></MobileDrawer>
  </section>
</template>

<style scoped>
.messenger-page{height:calc(100dvh - var(--sp-header-height));min-height:0;overflow:hidden;color:var(--color-brand-navy);padding:16px 28px 20px;background:#eef1f5}.messenger-shell{display:grid;grid-template-columns:270px minmax(0,1fr);height:100%;min-height:0;max-width:1360px;margin:0 auto;border:1px solid #dbe1e9;border-radius:22px;background:white;overflow:hidden;box-shadow:0 8px 34px #10233f05}.messenger-shell.sidebar-collapsed{grid-template-columns:minmax(0,1fr)}.desktop-chat-panel{background:#f5f7fa;border-right:1px solid #e0e5eb;overflow-y:auto;min-height:0}.panel-title{display:flex;align-items:center;justify-content:space-between;padding:24px 25px 0}.panel-title h2{font-size:1.25rem;letter-spacing:-.03em;font-weight:750}.panel-title>span{font-size:.65rem;color:var(--color-brand-muted);border:1px solid #d9e0e9;border-radius:20px;padding:3px 9px}.conversation{display:flex;flex-direction:column;min-width:0;min-height:0;overflow:hidden}.conversation-header{display:flex;align-items:center;gap:12px;flex-shrink:0;min-height:86px;padding:14px 24px;border-bottom:1px solid #e5e9ee;background:white;z-index:1}.conversation-avatar{position:relative;display:grid;place-items:center;width:44px;height:44px;flex-shrink:0;border-radius:16px;background:var(--color-brand-navy);color:var(--color-brand-highlight);font-size:1.4rem;font-weight:700}.conversation-avatar>span{position:absolute;right:-5px;bottom:-2px;background:#f3dfbc;color:#59421e;font-size:.52rem;line-height:16px;font-weight:800;min-width:20px;text-align:center;border:2px solid white;border-radius:7px}.conversation-name{min-width:0}.conversation-name h1{font-size:1rem;font-weight:750;line-height:1.45;letter-spacing:-.02em}.conversation-name p{color:var(--color-brand-muted);font-size:.73rem;margin-top:3px}.chat-icon-button{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-width:42px;min-height:42px;border-radius:13px;color:var(--color-brand-muted);flex-shrink:0}.chat-icon-button:hover:not(:disabled){background:#eef2f7;color:var(--color-brand-navy)}.chat-icon-button:disabled{opacity:.4;cursor:not-allowed}.chat-icon-button svg{width:20px;height:20px}.new-chat{margin-left:auto;padding:0 10px;background:#f3f5f8}.new-chat span{font-size:.7rem;font-weight:650}.thread-host{position:relative;flex:1;min-height:0;overflow:hidden}.chat-thread{height:100%;overflow-y:auto;overscroll-behavior:contain;padding:20px 28px 0;scrollbar-gutter:stable;overflow-anchor:none;scroll-padding:16px;outline-offset:-3px}.thread-date{text-align:center;font-size:.62rem;color:#6a7584;margin:0 0 22px}.thread-date span{border-radius:20px;padding:4px 12px;background:#f3f5f7}.chat-welcome{max-width:430px;margin:clamp(18px,5vh,65px) auto 30px;text-align:center}.welcome-avatar{display:grid;place-items:center;width:64px;height:64px;margin:0 auto 18px;border-radius:24px;background:#edf1f7;color:var(--color-brand-navy);font-size:2rem;font-weight:700;box-shadow:inset 0 0 0 1px #dce4ef}.chat-welcome h2{font-weight:700;font-size:1.28rem;letter-spacing:-.025em}.chat-welcome>p{font-size:.83rem;line-height:1.8;color:var(--color-brand-muted);margin:10px auto;max-width:350px}.welcome-prompts{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin-top:24px}.welcome-prompts button{display:flex;align-items:center;gap:7px;min-height:42px;padding:9px 13px;border:1px solid #d6dfeb;border-radius:20px;background:#fff;font-size:.72rem;color:var(--color-brand-navy)}.welcome-prompts button:hover{background:#f0f4f9}.welcome-prompts svg{width:14px;height:14px}.chat-welcome .welcome-note{font-size:.65rem;max-width:320px;margin-top:17px}.user-message{display:flex;justify-content:flex-end;margin:0 0 22px;min-width:0}.user-bubble{max-width:min(76%,550px);white-space:pre-wrap;overflow-wrap:anywhere;border-radius:21px 21px 5px 21px;background:var(--color-brand-navy);color:white;padding:12px 17px;font-size:.9rem;line-height:1.75}.assistant-message{display:flex;align-items:start;gap:10px;margin:0 0 26px;min-width:0;padding-right:24px}.assistant-message>.chat-answer{flex:1;min-width:0}.message-avatar{display:grid;place-items:center;width:29px;height:29px;flex-shrink:0;margin-top:3px;border-radius:11px;background:var(--color-brand-navy);color:var(--color-brand-highlight);font-size:.85rem;font-weight:700}.thread-bottom{height:10px}.typing-message{margin-bottom:18px}.typing-bubble{display:flex;align-items:center;gap:5px;background:#edf0f4;border-radius:5px 20px 20px 20px;width:69px;height:43px;padding:0 18px}.typing-bubble i{width:6px;height:6px;border-radius:50%;background:#728198;animation:typing 1.4s ease-in-out infinite}.typing-bubble i:nth-child(2){animation-delay:.16s}.typing-bubble i:nth-child(3){animation-delay:.32s}.typing-label{font-size:.65rem;color:var(--color-brand-muted);line-height:1.6;margin:6px 0 0 3px}.error-bubble{max-width:520px;background:#fff4e6;border:1px solid #ecd3af;border-radius:6px 20px 20px 20px;padding:13px 16px;font-size:.83rem;line-height:1.8;color:#704e22}.error-bubble button{display:flex;align-items:center;gap:7px;min-height:42px;margin-top:5px;font-size:.77rem;font-weight:700}.error-bubble button:disabled{opacity:.55;cursor:wait}.error-bubble svg{width:15px;height:15px}.new-message-button{position:absolute;bottom:12px;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:7px;white-space:nowrap;min-height:42px;padding:8px 16px;border:1px solid #d0d9e5;border-radius:24px;background:white;box-shadow:0 4px 15px #10233f1a;color:var(--color-brand-navy);font-size:.75rem;font-weight:650}.new-message-button svg{width:16px;height:16px}.composer-dock{flex-shrink:0;padding:13px 26px 12px;border-top:1px solid #e8edf2;background:white}.chat-composer{display:flex;align-items:flex-end;gap:10px;min-width:0}.composer-field{position:relative;flex:1;min-width:0;border:1px solid transparent;border-radius:24px;background:#eff2f6;padding:3px 7px}.composer-field:focus-within{border-color:#aab8cc;box-shadow:0 0 0 2px #e8edf5}.composer-field textarea{display:block;width:100%;min-height:42px;max-height:128px;height:42px;border:0;outline:none;background:transparent;color:var(--color-brand-navy);padding:9px 11px;font-size:.9rem;line-height:1.6;resize:none;overflow-y:hidden}.composer-field textarea:disabled{color:var(--color-brand-muted);cursor:wait}.input-count{display:block;font-size:.6rem;text-align:right;padding:0 12px 4px;color:var(--color-brand-muted)}.send-button{display:grid;place-items:center;width:46px;height:46px;flex-shrink:0;border-radius:50%;background:var(--color-brand-navy);color:white}.send-button svg{width:22px;height:22px}.send-button:hover:not(:disabled){background:#29476d}.send-button:disabled{background:#e8edf3;color:#8c98aa;cursor:not-allowed}.composer-note{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;font-size:.59rem;line-height:1.65;color:#66758b;margin:7px 7px 0}.trimmed-note{text-align:center;font-size:.65rem;color:var(--color-brand-muted);padding:8px 0 16px}:focus-visible{outline:3px solid var(--color-brand-accent);outline-offset:3px}.composer-field textarea:focus-visible{outline:none}@keyframes typing{0%,60%,100%{opacity:.4;transform:translateY(0)}30%{opacity:1;transform:translateY(-3px)}}@media(min-width:761px) and (max-width:1100px){.messenger-shell{grid-template-columns:235px minmax(0,1fr)}.messenger-page{padding:12px}.conversation-header{padding:12px 16px}.chat-thread{padding:16px 16px 0}.assistant-message{padding-right:0}.composer-dock{padding:12px 18px}}@media(max-width:760px){.messenger-page{padding:0;background:white}.messenger-shell,.messenger-shell.sidebar-collapsed{border:0;border-radius:0;grid-template-columns:minmax(0,1fr)}.desktop-chat-panel{display:none}.conversation-header{gap:9px;min-height:73px;padding:10px 12px}.conversation-avatar{width:37px;height:37px;border-radius:14px;font-size:1.2rem}.conversation-name h1{font-size:.88rem}.conversation-name p{font-size:.65rem}.chat-icon-button{min-width:38px;min-height:42px}.new-chat{padding:0;background:transparent}.new-chat span{display:none}.chat-thread{padding:16px 12px 0;scrollbar-gutter:auto}.assistant-message{gap:7px;padding-right:0;margin-bottom:22px}.message-avatar{width:25px;height:25px;font-size:.75rem;border-radius:9px}.user-bubble{max-width:88%;padding:10px 14px;font-size:.88rem}.chat-welcome{margin:30px auto 24px}.chat-welcome h2{font-size:1.13rem}.chat-welcome>p{font-size:.8rem;max-width:280px}.welcome-prompts{gap:7px}.welcome-prompts button{min-height:44px;font-size:.7rem}.composer-dock{padding:10px 12px max(8px,env(safe-area-inset-bottom))}.chat-composer{gap:8px}.composer-field textarea{font-size:16px;padding:8px 9px;line-height:1.6}.send-button{width:44px;height:44px}.composer-note{font-size:.56rem;margin-top:5px}.composer-note>span:first-child{display:none}.thread-date{margin-bottom:18px}.conversation-header>.panel-toggle{margin-left:-5px}.typing-label{font-size:.62rem}.error-bubble{padding:11px 13px}}@media(max-height:500px){.chat-welcome{margin:12px auto}.welcome-avatar{display:none}.welcome-prompts{margin-top:12px}.conversation-header{min-height:62px;padding-top:8px;padding-bottom:8px}.composer-note{display:none}}@media(prefers-reduced-motion:reduce){.typing-bubble i{animation:none;opacity:.7}}
</style>
