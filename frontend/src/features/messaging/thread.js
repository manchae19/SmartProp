import { createStateStore, combineStateStores } from "../../shared/state/createStateStore.js";
export function createThread(request, uuid = () => crypto.randomUUID()) {
  let generation = 0,
    id = null;
  const s = createStateStore({
    items: [],
    cursor: 0,
    hasMore: false,
    busy: false,
    sendBusy: false,
    error: '',
    pending: null
  });
  function reset(next) {
    generation++;
    id = next;
    s.edit(draftValue => Object.assign(draftValue, {
      items: [],
      cursor: 0,
      hasMore: false,
      busy: false,
      sendBusy: false,
      error: '',
      pending: null
    }));
  }
  function merge(items) {
    const rows = new Map(s.getSnapshot().items.map(m => [m.id, m]));
    for (const m of items) rows.set(m.id, m);
    s.edit(draftValue => draftValue["items"] = [...rows.values()].sort((a, b) => a.cursor - b.cursor));
  }
  async function load() {
    if (!id || s.getSnapshot().busy) return;
    const selected = id,
      run = generation;
    s.edit(draftValue => draftValue["busy"] = true);
    s.edit(draftValue => draftValue["error"] = '');
    try {
      const result = await request('/conversations/' + selected + '/messages?after=' + s.getSnapshot().cursor + '&limit=50');
      if (run !== generation) return;
      merge(result.items || []);
      s.edit(draftValue => draftValue["cursor"] = result.nextCursor);
      s.edit(draftValue => draftValue["hasMore"] = result.hasMore);
    } catch (e) {
      if (run === generation) s.edit(draftValue => draftValue["error"] = e.status === 429 ? 'Đã đạt giới hạn. Vui lòng chờ rồi thử lại.' : e.message);
    } finally {
      if (run === generation) s.edit(draftValue => draftValue["busy"] = false);
    }
  }
  async function send(body) {
    if (!id || s.getSnapshot().sendBusy) return;
    const text = body.trim();
    if (!text || text.length > 4000) {
      s.edit(draftValue => draftValue["error"] = 'Tin nhắn cần 1–4000 ký tự.');
      return false;
    }
    if (s.getSnapshot().pending && s.getSnapshot().pending.body !== text) {
      s.edit(draftValue => draftValue["error"] = 'Tin trước chưa được xác nhận. Hãy thử lại đúng nội dung trước khi gửi tin mới.');
      return false;
    }
    const run = generation,
      selected = id;
    s.edit(draftValue => draftValue["pending"] = s.getSnapshot().pending || {
      clientMessageId: uuid(),
      body: text
    });
    s.edit(draftValue => draftValue["sendBusy"] = true);
    s.edit(draftValue => draftValue["error"] = '');
    try {
      const row = await request('/conversations/' + selected + '/messages', {
        method: 'POST',
        body: {
          ...s.getSnapshot().pending
        }
      });
      if (run !== generation) return false;
      merge([row]);
      s.edit(draftValue => draftValue["pending"] = null);
      return true;
    } catch (e) {
      if (run === generation) s.edit(draftValue => draftValue["error"] = e.status === 409 ? 'Không thể gửi: tin đăng/phiên hội thoại đã thay đổi. Hãy tải lại.' : e.status === 429 ? 'Gửi quá nhanh. Hãy chờ rồi thử lại cùng nội dung.' : e.message);
      return false;
    } finally {
      if (run === generation) s.edit(draftValue => draftValue["sendBusy"] = false);
    }
  }
  async function markRead() {
    if (id && s.getSnapshot().cursor > 0) await request('/conversations/' + id + '/read', {
      method: 'PATCH',
      body: {
        cursor: s.getSnapshot().cursor
      }
    });
  }
  return combineStateStores([s], () => ({
    state: s.getSnapshot(),
    reset,
    load,
    send,
    markRead,
    dispose: () => {
      generation++;
      id = null;
    },
    updateState: s.edit,
    updateStateValue: s.set
  }));
}
