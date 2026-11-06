export function createPagedResource(
  request,
  endpoint,
  filters = () => ({}),
  summaryEndpoint = null,
  observe = (x) => x,
  { size = 20 } = {},
) {
  let sequence = 0,
    summarySequence = 0,
    disposed = false;
  const s = observe({
    items: [],
    busy: false,
    error: "",
    notice: "",
    page: 0,
    totalElements: 0,
    totalPages: 0,
    summary: null,
    summaryError: "",
    summaryBusy: false,
  });
  s.invalidate = () => {
    sequence++;
    s.busy = false;
    s.items = [];
    s.totalElements = 0;
    s.totalPages = 0;
    s.page = 0;
  };
  s.loadSummary = async () => {
    if (!summaryEndpoint) return;
    const run = ++summarySequence;
    s.summaryBusy = true;
    s.summaryError = "";
    try {
      const result = await request(summaryEndpoint);
      if (!disposed && run === summarySequence) s.summary = result;
    } catch (e) {
      if (!disposed && run === summarySequence) {
        s.summary = null;
        s.summaryError = "Chưa tải được thống kê toàn bộ. Vui lòng thử lại.";
      }
    } finally {
      if (!disposed && run === summarySequence) s.summaryBusy = false;
    }
  };
  s.load = async (page = 0) => {
    const run = ++sequence;
    s.busy = true;
    s.error = "";
    s.items = [];
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries({ ...filters(), page, size }))
      if (v !== null && v !== undefined && v !== "") q.set(k, v);
    try {
      let r = await request(endpoint + "?" + q);
      if (disposed || run !== sequence) return;
      if (page > 0 && !r.items?.length && r.totalElements > 0) {
        const lastPage = Math.max(0, (r.totalPages || 1) - 1);
        if (lastPage === page)
          throw Error("Danh sách đã thay đổi. Hãy tải lại.");
        return await s.load(lastPage);
      }
      Object.assign(s, {
        items: r.items || [],
        page: r.page,
        totalElements: r.totalElements,
        totalPages: r.totalPages,
      });
    } catch (e) {
      if (!disposed && run === sequence) {
        s.error = e.message || "Không tải được dữ liệu.";
        s.totalElements = 0;
        s.totalPages = 0;
      }
    } finally {
      if (!disposed && run === sequence) s.busy = false;
    }
  };
  s.run = async (fn) => {
    if (s.busy) return;
    s.busy = true;
    s.error = "";
    try {
      return await fn();
    } catch (e) {
      s.error =
        e.status === 409
          ? "Dữ liệu đã thay đổi. Hãy tải lại trước khi thao tác."
          : e.message;
      return null;
    } finally {
      s.busy = false;
    }
  };
  s.reload = () => Promise.all([s.load(s.page), s.loadSummary()]);
  s.dispose = () => {
    disposed = true;
    sequence++;
    summarySequence++;
  };
  return s;
}
