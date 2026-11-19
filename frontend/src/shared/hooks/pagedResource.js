import { createStateStore } from "../state/createStateStore.js";
export function createPagedResource(request, endpoint, filters = () => ({}), summaryEndpoint = null, {
  size = 20
} = {}) {
  let sequence = 0,
    summarySequence = 0,
    disposed = false;
  const s = createStateStore({
    items: [],
    busy: false,
    error: "",
    notice: "",
    page: 0,
    totalElements: 0,
    totalPages: 0,
    summary: null,
    summaryError: "",
    summaryBusy: false
  });
  s.edit(draftValue => draftValue["invalidate"] = () => {
    sequence++;
    s.edit(draftValue => draftValue["busy"] = false);
    s.edit(draftValue => draftValue["items"] = []);
    s.edit(draftValue => draftValue["totalElements"] = 0);
    s.edit(draftValue => draftValue["totalPages"] = 0);
    s.edit(draftValue => draftValue["page"] = 0);
  });
  s.edit((resolvedValue => draftValue => draftValue["loadSummary"] = resolvedValue)(async () => {
    if (!summaryEndpoint) return;
    const run = ++summarySequence;
    s.edit(draftValue => draftValue["summaryBusy"] = true);
    s.edit(draftValue => draftValue["summaryError"] = "");
    try {
      const result = await request(summaryEndpoint);
      if (!disposed && run === summarySequence) s.edit(draftValue => draftValue["summary"] = result);
    } catch (e) {
      if (!disposed && run === summarySequence) {
        s.edit(draftValue => draftValue["summary"] = null);
        s.edit(draftValue => draftValue["summaryError"] = "Chưa tải được thống kê toàn bộ. Vui lòng thử lại.");
      }
    } finally {
      if (!disposed && run === summarySequence) s.edit(draftValue => draftValue["summaryBusy"] = false);
    }
  }));
  s.edit((resolvedValue => draftValue => draftValue["load"] = resolvedValue)(async (page = 0) => {
    const run = ++sequence;
    s.edit(draftValue => draftValue["busy"] = true);
    s.edit(draftValue => draftValue["error"] = "");
    s.edit(draftValue => draftValue["items"] = []);
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries({
      ...filters(),
      page,
      size
    })) if (v !== null && v !== undefined && v !== "") q.set(k, v);
    try {
      let r = await request(endpoint + "?" + q);
      if (disposed || run !== sequence) return;
      if (page > 0 && !r.items?.length && r.totalElements > 0) {
        const lastPage = Math.max(0, (r.totalPages || 1) - 1);
        if (lastPage === page) throw Error("Danh sách đã thay đổi. Hãy tải lại.");
        return await s.getSnapshot().load(lastPage);
      }
      s.edit(draftValue => Object.assign(draftValue, {
        items: r.items || [],
        page: r.page,
        totalElements: r.totalElements,
        totalPages: r.totalPages
      }));
    } catch (e) {
      if (!disposed && run === sequence) {
        s.edit(draftValue => draftValue["error"] = e.message || "Không tải được dữ liệu.");
        s.edit(draftValue => draftValue["totalElements"] = 0);
        s.edit(draftValue => draftValue["totalPages"] = 0);
      }
    } finally {
      if (!disposed && run === sequence) s.edit(draftValue => draftValue["busy"] = false);
    }
  }));
  s.edit((resolvedValue => draftValue => draftValue["run"] = resolvedValue)(async fn => {
    if (s.getSnapshot().busy) return;
    s.edit(draftValue => draftValue["busy"] = true);
    s.edit(draftValue => draftValue["error"] = "");
    try {
      return await fn();
    } catch (e) {
      s.edit(draftValue => draftValue["error"] = e.status === 409 ? "Dữ liệu đã thay đổi. Hãy tải lại trước khi thao tác." : e.message);
      return null;
    } finally {
      s.edit(draftValue => draftValue["busy"] = false);
    }
  }));
  s.edit(draftValue => draftValue["reload"] = () => Promise.all([s.getSnapshot().load(s.getSnapshot().page), s.getSnapshot().loadSummary()]));
  s.edit(draftValue => draftValue["dispose"] = () => {
    disposed = true;
    sequence++;
    summarySequence++;
  });
  return s;
}
