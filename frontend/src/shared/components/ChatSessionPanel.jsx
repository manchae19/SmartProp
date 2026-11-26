import React, {useEffect, useSyncExternalStore} from 'react';
import {chatHistory, chatSession} from '../../features/prediction/chatRuntime.js';
import {session} from '../../features/auth/api.js';
import {SiteLink} from '../../app/navigation.jsx';
import './ChatSessionPanel.css';

export const CHAT_STARTER_PROMPTS = [
  'Tìm lô đất Hòa Xuân khoảng 2 tỷ.',
  'Xem đất tại Đảo Triệu Phú.',
  'Tìm tin đăng bất động sản dưới 10 tỷ tại Đà Nẵng.',
  'Những khu vực nào ở Hòa Xuân có nguy cơ ngập?',
  'Ở Hải Châu có những bệnh viện nào?',
];

export default function ChatSessionPanel({preview,locked,onChoose,onCurrent,onNew}) {
  const history=useSyncExternalStore(chatHistory.subscribe,chatHistory.getSnapshot);
  const active=useSyncExternalStore(chatSession.subscribe,chatSession.getSnapshot).state.sessionId;
  const account=useSyncExternalStore(session.subscribe,session.getSnapshot).user;
  useEffect(()=>{if(account)chatHistory.refresh();},[account?.id]);

  return <div className="session-panel" data-sp-57e2adde="">
    <p className="panel-eyebrow" data-sp-57e2adde="">{account?'10 HỘI THOẠI GẦN NHẤT':'HỘI THOẠI TRONG TAB'}</p>
    {!account && <p className="history-note">Đăng nhập để lưu và tiếp tục hội thoại trên các thiết bị.</p>}
    <button className="history-item history-new" type="button" aria-current={!active?'true':undefined} disabled={locked || history.selecting} onClick={()=>onNew?.()}>
      <strong>＋ Hội thoại mới</strong><small>Bắt đầu câu hỏi khác · Giữ lịch sử đã lưu</small>
    </button>
    {history.loading && <p role="status" className="history-note">Đang tải lịch sử…</p>}
    {history.selecting && <p role="status" className="history-note">Đang mở hội thoại…</p>}
    {history.error && <div role="alert" className="history-note">{history.error}<button type="button" disabled={locked} onClick={()=>chatHistory.refresh(true)}>Thử tải lại</button></div>}
    {account && history.loaded && !history.items.length && <p className="history-note">Chưa có hội thoại đã lưu. Hãy gửi câu hỏi đầu tiên.</p>}
    <nav aria-label="Lịch sử hội thoại" className="chat-history-list">
      {history.items.map(item=><div key={item.id} className="history-row"><button className="history-item" type="button" disabled={locked || history.selecting}
        aria-current={active===item.id?'true':undefined} onClick={async()=>{if(await chatHistory.select(item.id))onCurrent?.();}}>
        <strong>{item.title}</strong><small>{item.updatedAt ? new Date(item.updatedAt).toLocaleString('vi-VN'):''}</small>
      </button><button type="button" className="history-delete" aria-label={'Xóa hội thoại '+item.title} title="Xóa hội thoại" disabled={locked || history.selecting} onClick={()=>{if(window.confirm('Xóa hội thoại này? Không thể khôi phục sau khi xóa.'))chatHistory.remove(item.id);}}>×</button></div>)}
    </nav>
    <div className="panel-prompts" data-sp-57e2adde=""><h2 data-sp-57e2adde="">Gợi ý bắt đầu</h2>
      {CHAT_STARTER_PROMPTS.map(text=><button key={text} type="button" disabled={locked} onClick={()=>onChoose?.(text)} data-sp-57e2adde="">{text}</button>)}
    </div>
    <SiteLink to="/advisor" className="filter-link" data-sp-57e2adde="">Tìm bằng bộ lọc →</SiteLink>
  </div>;
}
