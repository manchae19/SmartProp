import { lazy, Suspense, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { createPortal } from 'react-dom';
import { useLocation } from 'react-router-dom';
import { SiteLink } from '../../app/navigation.jsx';
import { session } from '../auth/api.js';
import { chatSession } from './chatRuntime.js';
import { isNearChatBottom } from './chatPresentation.js';
import DiscoveryIcon from '../../shared/components/DiscoveryIcon.jsx';
import AppIcon from '../../shared/components/AppIcon.jsx';
import './FloatingAdvisor.css';
const ChatAnswer = lazy(() => import('../../shared/components/ChatAnswer.jsx'));
export default function FloatingAdvisor() {
  const route = useLocation();
  const model = useSyncExternalStore(chatSession.subscribe, chatSession.getSnapshot);
  const auth = useSyncExternalStore(session.subscribe, session.getSnapshot);
  const state = model.state;
  const [open, setOpen] = useState(false), [draft, setDraft] = useState(''), [clock, setClock] = useState(Date.now());
  const launcher = useRef(null), input = useRef(null), thread = useRef(null), follow = useRef(true);
  const identity = auth.user?.id ?? 'guest';
  const [viewport, setViewport] = useState(null);
  const fullChat = route.pathname.replace(/\/$/, '') === '/advisor/chat';
  const wait = Math.max(0, Math.ceil((state.retryAt - clock) / 1000));
  const locked = state.busy || wait > 0;
  useEffect(() => { setDraft(''); }, [identity]);
  useEffect(() => {const openChat = () => {follow.current=true;setOpen(true);};window.addEventListener('smartprop:advisor-open',openChat);return () => window.removeEventListener('smartprop:advisor-open',openChat);}, []);
  useEffect(() => {
    if (!open || fullChat) return;
    input.current?.focus();
    const escape = event => { if (event.key === 'Escape') {setOpen(false); launcher.current?.focus();} };
    window.addEventListener('keydown', escape);
    return () => window.removeEventListener('keydown', escape);
  }, [open, fullChat]);
  useEffect(() => {
    if (open && !fullChat && follow.current) thread.current?.scrollTo({top: thread.current.scrollHeight});
  }, [open, fullChat, state.messages.length, state.busy]);
  useEffect(() => {
    if (!open) return;
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [open]);
  useEffect(() => {
    if (!open || !window.visualViewport) return;
    const resize = () => setViewport({height: window.visualViewport.height, offset: Math.max(0, window.innerHeight - window.visualViewport.height - window.visualViewport.offsetTop)});
    resize(); window.visualViewport.addEventListener('resize', resize);
    return () => {window.visualViewport.removeEventListener('resize', resize); setViewport(null);};
  }, [open]);
  const submit = async event => {
    event.preventDefault();
    if (!draft.trim() || locked) return;
    const question = draft.trim(); setDraft(''); follow.current = true;
    await model.submit(question);
  };
  const close = () => {setOpen(false); launcher.current?.focus();};
  if (fullChat) return null;
  return createPortal(<div className="floating-advisor" style={{'--chat-keyboard-offset': `${viewport?.offset || 0}px`}}>
    {open && <section className="floating-advisor-panel" style={viewport ? {maxHeight: Math.max(180, viewport.height - 135)} : undefined} role="dialog" aria-modal="false" aria-labelledby="floating-advisor-title">
      <header><DiscoveryIcon /><div><h2 id="floating-advisor-title">SmartProp AI</h2><p>Tư vấn bất động sản</p></div>
        <SiteLink to="/advisor/chat" onClick={() => setOpen(false)} className="floating-advisor-tool" aria-label="Mở trang tư vấn đầy đủ" title="Mở trang tư vấn đầy đủ"><AppIcon name="arrow" /></SiteLink>
        <button className="floating-advisor-tool" onClick={close} aria-label="Đóng chat">×</button>
      </header>
      <div className="floating-advisor-thread" ref={thread} onScroll={() => {follow.current = isNearChatBottom(thread.current);}}>
        {state.propertyContext && <p className="floating-advisor-context">Đang hỏi về: {state.propertyContext.label}<button onClick={() => model.reset()}>Bỏ chọn</button></p>}
        {!state.messages.length && state.propertyContext && <button onClick={() => model.submit('Tóm tắt thông tin căn này')}>Tóm tắt căn này</button>}
        {!state.messages.length && <div className="floating-advisor-welcome"><DiscoveryIcon /><h3>Bạn đang tìm không gian sống nào?</h3><p>Hỏi về nhà, giá thị trường hoặc tiện ích tại Đà Nẵng.</p><div>{['Giá căn hộ ở Sơn Trà?', 'Ở Hải Châu có bệnh viện nào?'].map(question => <button key={question} disabled={locked} onClick={() => {follow.current = true; model.submit(question);}}>{question}<span aria-hidden="true">↗</span></button>)}</div></div>}
        {state.messages.map((message, index) => message.role === 'user' ? <p key={message.id} className="floating-advisor-user">{message.text}</p> : <div key={message.id} className="floating-advisor-answer"><Suspense fallback={<p role="status">Đang hiển thị câu trả lời…</p>}><ChatAnswer result={message.response} messageId={message.id} question={state.messages.slice(0,index).findLast(m => m.role === 'user')?.text || ''} onReading={() => {follow.current = false;}} /></Suspense></div>)}
        {state.busy && <p className="floating-advisor-loading" role="status">SmartProp đang kiểm tra dữ liệu<span aria-hidden="true">…</span></p>}
        {state.error && <div className="floating-advisor-error" role="alert"><p>{state.error.message || state.error.text || 'Chưa nhận được phản hồi. Vui lòng thử lại.'}</p>{state.error.retry && <button disabled={locked} onClick={() => {follow.current = true; model.retry();}}>{wait ? `Thử lại sau ${wait}s` : 'Thử lại'}</button>}</div>}
      </div>
      <footer><form onSubmit={submit}><textarea ref={input} rows="1" aria-label="Câu hỏi cho SmartProp AI" placeholder="Bạn cần tìm nhà hoặc hỏi điều gì?" maxLength={2000} value={draft} onChange={e => setDraft(e.target.value)} onKeyDown={e => {if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {e.preventDefault();submit(e);}}} /><button type="submit" aria-label="Gửi câu hỏi" disabled={locked || !draft.trim()}><AppIcon name="arrow" /></button></form><div><small>Thông tin tham khảo · Kiểm tra nguồn trước khi quyết định.</small><button disabled={locked || !state.messages.length} onClick={() => {model.clear(); setDraft(''); input.current?.focus();}}>Hội thoại mới</button></div></footer>
    </section>}
    <button ref={launcher} className="floating-advisor-launcher" aria-label={open ? 'Thu gọn tư vấn AI' : 'Mở tư vấn AI SmartProp'} aria-expanded={open} onClick={() => {follow.current = true; setOpen(value => !value);}}><DiscoveryIcon /><span>AI tư vấn<strong>SmartProp</strong></span></button>
  </div>, document.body);
}
