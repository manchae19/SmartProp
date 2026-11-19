import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import { useAppNavigation } from "../../app/navigation.jsx";
import { api } from "../auth/api.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import Pagination from "../../shared/components/Pagination.jsx";
import PrivateImage from "../../shared/components/PrivateImage.jsx";
import { collectionReport } from "../home/collection.js";
import ReportDetails from "./ReportDetails.jsx";
import { useCollection } from "../../shared/hooks/useCollection.js";
import "./MyReportsView.css";
function useMyReportsViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const router = useAppNavigation();

  // SMARTPROP MY REPORTS 2.0
  // Data is loaded from the existing backend.
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  const [activeFilter] = useState(() => createStateStore("all"));
  useSyncExternalStore(activeFilter.subscribe, activeFilter.getSnapshot);
  const [searchText] = useState(() => createStateStore(""));
  useSyncExternalStore(searchText.subscribe, searchText.getSnapshot);
  const [selectedReport] = useState(() => createStateStore(null));
  useSyncExternalStore(selectedReport.subscribe, selectedReport.getSnapshot);
  const reportStatuses = {
    open: "OPEN",
    processing: "PROCESSING",
    resolved: "RESOLVED",
    rejected: "REJECTED"
  };
  const state = useCollection("/users/me/reports", "/reports/summary", () => ({
    keyword: searchText.getSnapshot().trim(),
    status: reportStatuses[activeFilter.getSnapshot()],
    sort: "newest"
  }));
  const _stateLatest = useRef(state);
  _stateLatest.current = state;
  const getReports = () => _stateLatest.current.items.map(collectionReport),
    filteredReports = getReports();
  const count = key => _stateLatest.current.summary?.byStatus?.[reportStatuses[key]] ?? "—";
  const getProcessingCount = () => count("processing"),
    getResolvedCount = () => count("resolved"),
    getRejectedCount = () => count("rejected");
  const getFilters = () => [{
    key: "all",
    label: "Tất cả",
    count: _stateLatest.current.summary?.totalReports ?? "—"
  }, ...Object.entries({
    open: "Mới gửi",
    processing: "Đang xử lý",
    resolved: "Đã xử lý",
    rejected: "Từ chối"
  }).map(([key, label]) => ({
    key,
    label,
    count: count(key)
  }))];
  function statusClass(status) {
    if (status === "processing") {
      return "bg-[#FFF1D9] text-[#A36A19]";
    }
    if (status === "resolved") {
      return "bg-[#E5F4EB] text-[#287B56]";
    }
    return "bg-[#FCE8E3] text-[#BD5D48]";
  }
  function statusDot(status) {
    if (status === "processing") return "bg-[#D69C44]";
    if (status === "resolved") return "bg-[#4DAD80]";
    return "bg-[#D17760]";
  }
  async function openReport(report) {
    await _stateLatest.current.run(async () => {
      selectedReport.set(collectionReport(await api("/reports/" + report.id)));
    });
  }
  async function reportUpdated(report) {
    selectedReport.set(collectionReport(report));
    await _stateLatest.current.reload();
  }
  function closeReport() {
    selectedReport.set(null);
  }
  function resetFilters() {
    activeFilter.set("all");
    searchText.set("");
  }
  function goHome() {
    _routerLatest.current.push("/home");
  }
  function goAccount() {
    _routerLatest.current.push("/account");
  }
  function goPost() {
    _routerLatest.current.push("/post");
  }
  function goMap() {
    _routerLatest.current.push("/map");
  }
  return {
    ...inputProps,
    activeFilter: activeFilter.getSnapshot(),
    searchText: searchText.getSnapshot(),
    selectedReport: selectedReport.getSnapshot(),
    state,
    filteredReports,
    processingCount: getProcessingCount(),
    resolvedCount: getResolvedCount(),
    rejectedCount: getRejectedCount(),
    filters: getFilters(),
    statusClass,
    statusDot,
    openReport,
    reportUpdated,
    closeReport,
    resetFilters,
    goMap,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateSearchTextValue: searchText.set,
    updateActiveFilterValue: activeFilter.set
  };
}
export default React.forwardRef(function MyReportsView(props, ref) {
  const view = useMyReportsViewState(props, ref);
  return <><div data-ui-view="MyReportsView" data-sp-ef737f62="" {...view.rootAttributes} className={classNames(["sp-my-reports min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)]", view.rootAttributes.className])}>
      <section className="relative overflow-hidden border-b border-[var(--ui-border)]" data-sp-ef737f62="">
        <div className="pointer-events-none absolute -right-28 -top-32 h-[420px] w-[420px] rounded-full border border-[var(--ui-border)]/20" data-sp-ef737f62="" />
        <div className="pointer-events-none absolute -right-10 -top-12 h-[280px] w-[280px] rounded-full border border-[var(--ui-border)]/20" data-sp-ef737f62="" />
        <div className="relative mx-auto max-w-[1440px] px-5 py-12 md:px-10 md:py-16" data-sp-ef737f62="">
          <div className="flex flex-wrap items-end justify-between gap-8" data-sp-ef737f62="">
            <div data-sp-ef737f62="">
              <div className="flex items-center gap-3" data-sp-ef737f62="">
                <span className="h-px w-9 bg-[var(--ui-soft)]" data-sp-ef737f62="" />
                <p className="text-xs font-bold uppercase tracking-[0.22em] text-[var(--ui-muted)]" data-sp-ef737f62="">
                  {" SMARTPROP / TRUST & TRANSPARENCY "}
                </p>
              </div>
              <h1 className="mt-6 text-[39px] font-medium leading-tight tracking-tight sm:text-[56px]" data-sp-ef737f62="">
                {" Theo dõi "}
                <span className="block italic text-[var(--ui-muted)]" data-sp-ef737f62="">
                  {"báo cáo của bạn."}
                </span>
              </h1>
              <p className="mt-5 max-w-2xl text-sm leading-7 text-[var(--ui-muted)]" data-sp-ef737f62="">
                {" Quản lý các báo cáo đã gửi, theo dõi tiến độ xem xét và xem kết quả xử lý trong một không gian trực quan, minh bạch và dễ sử dụng. "}
              </p>
              <span className="mt-5 inline-flex rounded-full border border-[var(--ui-border)] bg-[var(--ui-surface)] px-4 py-2 text-xs font-bold uppercase tracking-widest text-[var(--ui-muted)]" data-sp-ef737f62="">
                {" Dữ liệu từ hệ thống "}
              </span>
            </div>
            <button type="button" onClick={$event => {
              return view.goMap?.($event);
            }} className="rounded-full border border-[var(--ui-border)] bg-brand-card px-7 py-4 text-xs font-bold transition hover:border-[var(--ui-border)]" data-sp-ef737f62="">
              {" Khám phá GIS Explorer ↗ "}
            </button>
          </div>
        </div>
      </section>
      <section className="mx-auto max-w-[1440px] px-5 pt-10 md:px-10" data-sp-ef737f62="">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-5" data-sp-ef737f62="">
          <div className="rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7" data-sp-ef737f62="">
            <p className="text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]" data-sp-ef737f62="">
              {" Tổng báo cáo "}
            </p>
            <div className="mt-4 flex items-end justify-between" data-sp-ef737f62="">
              <span className="text-4xl font-semibold" data-sp-ef737f62="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.summary?.totalReports ?? "—")}
              </span>
              <span className="text-xl text-[var(--ui-ink)]" data-sp-ef737f62="">
                {"▤"}
              </span>
            </div>
            <p className="mt-3 text-xs text-[var(--ui-ink)]" data-sp-ef737f62="">
              {" Báo cáo đã gửi "}
            </p>
          </div>
          <div className="rounded-[20px] bg-[var(--ui-soft)] p-5 text-brand-navy sm:p-7" data-sp-ef737f62="">
            <p className="text-xs font-bold uppercase tracking-widest text-brand-navy/60" data-sp-ef737f62="">
              {" Đang xử lý "}
            </p>
            <div className="mt-4 flex items-end justify-between" data-sp-ef737f62="">
              <span className="text-4xl font-semibold" data-sp-ef737f62="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.processingCount)}
              </span>
              <span className="h-3 w-3 rounded-full bg-[var(--ui-soft)]" data-sp-ef737f62="" />
            </div>
            <p className="mt-3 text-xs text-brand-navy/55" data-sp-ef737f62="">
              {" Đang chờ kết quả "}
            </p>
          </div>
          <div className="rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7" data-sp-ef737f62="">
            <p className="text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]" data-sp-ef737f62="">
              {" Đã xử lý "}
            </p>
            <div className="mt-4 flex items-end justify-between" data-sp-ef737f62="">
              <span className="text-4xl font-semibold" data-sp-ef737f62="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.resolvedCount)}
              </span>
              <span className="text-xl text-[var(--ui-accent)]" data-sp-ef737f62="">
                {"✓"}
              </span>
            </div>
            <p className="mt-3 text-xs text-[var(--ui-ink)]" data-sp-ef737f62="">
              {" Đã có kết quả xem xét "}
            </p>
          </div>
          <div className="rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7" data-sp-ef737f62="">
            <p className="text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]" data-sp-ef737f62="">
              {" Bị từ chối "}
            </p>
            <div className="mt-4 flex items-end justify-between" data-sp-ef737f62="">
              <span className="text-4xl font-semibold" data-sp-ef737f62="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.rejectedCount)}
              </span>
              <span className="text-xl text-[var(--ui-ink)]" data-sp-ef737f62="">
                {"!"}
              </span>
            </div>
            <p className="mt-3 text-xs text-[var(--ui-ink)]" data-sp-ef737f62="">
              {" Báo cáo không được chấp nhận "}
            </p>
          </div>
        </div>
      </section>
      <div className="mx-auto max-w-[1440px] px-5 pb-20 pt-12 md:px-10" data-sp-ef737f62="">
        <ResourceState state={view.state} data-sp-ef737f62="" />
        {view.state.summaryError ? <p role="alert" data-sp-ef737f62="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.summaryError)}{" "}
            <button onClick={$event => {
            return view.state.loadSummary?.($event);
          }} data-sp-ef737f62="">
              {"Tải lại thống kê"}
            </button>
          </p> : null}
        <p className="mb-4 text-xs text-[var(--ui-ink)]" data-sp-ef737f62="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.totalElements)}
          {" kết quả · kết quả đã lọc trên toàn bộ báo cáo."}
        </p>
        <div className="flex flex-wrap items-end justify-between gap-5" data-sp-ef737f62="">
          <div data-sp-ef737f62="">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-muted)]" data-sp-ef737f62="">
              {" REPORT CENTER / 01 "}
            </p>
            <h2 className="mt-3 text-3xl font-medium tracking-tight sm:text-4xl" data-sp-ef737f62="">
              {" Lịch sử "}
              <span className="italic text-[var(--ui-muted)]" data-sp-ef737f62="">
                {"báo cáo."}
              </span>
            </h2>
            <p className="mt-3 text-xs text-[var(--ui-ink)]" data-sp-ef737f62="">
              {" Theo dõi tiến độ và kết quả xử lý của từng báo cáo. "}
            </p>
          </div>
          <div className="flex w-full items-center gap-3 rounded-xl border border-[var(--ui-border)] bg-brand-card px-4 sm:w-[320px]" data-sp-ef737f62="">
            <span className="text-xl text-[var(--ui-muted)]" data-sp-ef737f62="">
              {"⌕"}
            </span>
            <input type="search" aria-label="Tìm kiếm báo cáo" placeholder="Tìm nội dung, mã tin hoặc lý do..." className="h-12 min-w-0 w-full bg-transparent text-xs outline-none" data-sp-ef737f62="" value={view.searchText ?? ""} onChange={event => ($value => {
              view.updateSearchTextValue($value);
            })(event.target.value)} />
          </div>
        </div>
        <div className="mt-8 flex flex-wrap gap-2" data-sp-ef737f62="">
          {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.filters, filter => <button key={filter.key} type="button" onClick={$event => {
            view.updateActiveFilterValue(filter.key);
          }} className={classNames(["rounded-full border px-4 py-2.5 text-xs font-semibold transition sm:px-5", view.activeFilter === filter.key ? "border-[var(--ui-border)] bg-[var(--ui-soft)] text-brand-navy" : "border-[var(--ui-border)] bg-brand-card text-[var(--ui-accent)] hover:border-[var(--ui-border)]"])} data-sp-ef737f62="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(filter.label)}{" "}
              <span className="ml-1 opacity-65" data-sp-ef737f62="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(filter.count)}
              </span>
            </button>)}
        </div>
        <div className="mb-5 mt-7 flex items-center justify-between gap-4" data-sp-ef737f62="">
          <p className="text-xs text-[var(--ui-ink)]" data-sp-ef737f62="">
            {" Hiển thị "}
            <strong className="text-[var(--ui-accent)]" data-sp-ef737f62="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.filteredReports.length)}
            </strong>
            {" báo cáo "}
          </p>
          <span className="text-xs uppercase tracking-widest text-[var(--ui-muted)]" data-sp-ef737f62="">
            {" REPORT HISTORY "}
          </span>
        </div>
        {view.filteredReports.length ? <div className="space-y-5" data-sp-ef737f62="">
            {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.filteredReports, report => <article key={report.id} className="group grid min-w-0 overflow-hidden rounded-[22px] border border-[var(--ui-border)] bg-brand-card transition duration-300 hover:border-[var(--ui-border)] hover:shadow-[0_16px_45px_rgba(20,43,79,0.08)] lg:grid-cols-[245px_minmax(0,1fr)_225px]" data-sp-ef737f62="">
                <div className="relative h-[225px] overflow-hidden bg-[var(--ui-surface)] lg:h-full lg:min-h-[230px]" data-sp-ef737f62="">
                  <PrivateImage src={report.image} alt={`${report.title}`} loading="lazy" className="h-full w-full object-cover transition duration-700 group-hover:scale-105" data-sp-ef737f62="" />
                  <div className="absolute inset-0 bg-gradient-to-t from-[var(--ui-soft)]/55 to-transparent" data-sp-ef737f62="" />
                  <span className="absolute bottom-4 left-4 text-xs font-bold uppercase tracking-[0.12em] text-brand-navy" data-sp-ef737f62="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(report.location)}
                  </span>
                </div>
                <div className="flex min-w-0 flex-col justify-center p-5 sm:p-7" data-sp-ef737f62="">
                  <div className="flex flex-wrap items-center gap-3" data-sp-ef737f62="">
                    <span className={classNames(["inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold", view.statusClass(report.status)])} data-sp-ef737f62="">
                      <span className={classNames(["h-1.5 w-1.5 rounded-full", view.statusDot(report.status)])} data-sp-ef737f62="" />{" "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(report.statusLabel)}
                    </span>
                    <span className="text-xs font-semibold text-[var(--ui-muted)]" data-sp-ef737f62="">
                      {" REPORT #"}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(String(report.id).padStart(3, "0"))}
                    </span>
                  </div>
                  <h3 className="mt-4 text-lg font-semibold leading-7 sm:text-xl" data-sp-ef737f62="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(report.title)}
                  </h3>
                  <p className="mt-2 text-xs text-[var(--ui-ink)]" data-sp-ef737f62="">
                    {" ⌖ "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(report.location)}
                  </p>
                  <div className="mt-4" data-sp-ef737f62="">
                    <span className="inline-flex max-w-full rounded-full bg-[var(--ui-surface)] px-3 py-2 text-xs font-bold tracking-wide text-[var(--ui-muted)]" data-sp-ef737f62="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(report.reason)}
                    </span>
                  </div>
                  <p className="mt-4 text-xs text-[var(--ui-ink)]" data-sp-ef737f62="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(report.sentAt)}
                  </p>
                  {report.result ? <p className="mt-4 border-l-2 border-[var(--ui-border)] pl-3 text-xs leading-6 text-[var(--ui-accent)]" data-sp-ef737f62="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(report.result)}
                    </p> : null}
                </div>
                <div className="flex flex-col justify-between gap-6 border-t border-[var(--ui-border)] p-5 sm:p-7 lg:border-l lg:border-t-0" data-sp-ef737f62="">
                  <div className="lg:text-right" data-sp-ef737f62="">
                    <p className="text-xs uppercase tracking-widest text-[var(--ui-ink)]" data-sp-ef737f62="">
                      {" Trạng thái hiện tại "}
                    </p>
                    <p className="mt-3 text-base font-semibold" data-sp-ef737f62="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(report.statusLabel)}
                    </p>
                    <p className="mt-2 text-xs leading-5 text-[var(--ui-ink)]" data-sp-ef737f62="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(report.update)}
                    </p>
                  </div>
                  <button type="button" onClick={$event => {
                view.openReport(report);
              }} className="self-start rounded-full border border-[var(--ui-border)] bg-brand-card px-5 py-3 text-xs font-semibold transition hover:border-[var(--ui-border)] hover:bg-[var(--ui-soft)] hover:text-brand-navy lg:self-end" data-sp-ef737f62="">
                    {" Xem báo cáo ↗ "}
                  </button>
                </div>
              </article>)}
          </div> : <div className="rounded-[24px] border border-[var(--ui-border)] bg-brand-card px-6 py-20 text-center" data-sp-ef737f62="">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[var(--ui-surface)] text-3xl text-[var(--ui-muted)]" data-sp-ef737f62="">
              {" ⚑ "}
            </div>
            <h3 className="mt-6 text-xl font-semibold" data-sp-ef737f62="">
              {" Không tìm thấy báo cáo "}
            </h3>
            <p className="mt-3 text-sm text-[var(--ui-ink)]" data-sp-ef737f62="">
              {" Hãy thử thay đổi trạng thái hoặc từ khóa tìm kiếm. "}
            </p>
            <button type="button" onClick={$event => {
            return view.resetFilters?.($event);
          }} className="mt-6 rounded-full bg-[var(--ui-soft)] px-6 py-3 text-xs font-semibold text-brand-navy" data-sp-ef737f62="">
              {" Xem tất cả báo cáo "}
            </button>
          </div>}
        <section className="mt-10 rounded-[22px] border border-[var(--ui-border)] bg-brand-card px-6 py-6 sm:px-8" data-sp-ef737f62="">
          <div className="flex items-start gap-4" data-sp-ef737f62="">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[var(--ui-surface)] text-lg font-semibold text-[var(--ui-muted)]" data-sp-ef737f62="">
              {" i "}
            </div>
            <div data-sp-ef737f62="">
              <h3 className="text-sm font-semibold" data-sp-ef737f62="">
                {" Thông tin về quá trình xử lý "}
              </h3>
              <p className="mt-2 max-w-3xl text-xs leading-6 text-[var(--ui-ink)]" data-sp-ef737f62="">
                {" Bạn có thể theo dõi trạng thái xử lý và bổ sung bằng chứng trong chi tiết báo cáo. "}
              </p>
            </div>
          </div>
        </section>
        <section className="relative mt-12 overflow-hidden rounded-[25px] bg-[var(--ui-soft)] px-7 py-10 text-brand-navy sm:px-10" data-sp-ef737f62="">
          <div className="pointer-events-none absolute -right-12 -top-24 h-72 w-72 rounded-full border border-[var(--ui-border)]/20" data-sp-ef737f62="" />
          <div className="relative flex flex-wrap items-center justify-between gap-7" data-sp-ef737f62="">
            <div data-sp-ef737f62="">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-accent)]" data-sp-ef737f62="">
                {" SMARTPROP / TRUST & SAFETY "}
              </p>
              <h2 className="mt-4 text-3xl font-medium" data-sp-ef737f62="">
                {" Minh bạch hơn. "}
                <span className="italic text-[var(--ui-ink)]" data-sp-ef737f62="">
                  {" An tâm hơn."}
                </span>
              </h2>
              <p className="mt-4 max-w-xl text-sm leading-7 text-brand-navy/60" data-sp-ef737f62="">
                {" Khám phá bất động sản và các thông tin tham khảo trên nền tảng SmartProp. "}
              </p>
            </div>
            <button type="button" onClick={$event => {
              return view.goMap?.($event);
            }} className="rounded-full bg-[var(--ui-soft)] px-7 py-4 text-xs font-bold text-[var(--ui-accent)] transition hover:bg-[var(--ui-soft)]" data-sp-ef737f62="">
              {" Khám phá bản đồ GIS ↗ "}
            </button>
          </div>
        </section>
        <p className="mt-7 text-center text-xs leading-6 text-[var(--ui-ink)]" data-sp-ef737f62="">
          {" Báo cáo và kết quả xử lý được tải từ tài khoản của bạn. "}
        </p>
        <Pagination state={view.state} data-sp-ef737f62="" />
      </div>
      {view.selectedReport ? <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--ui-soft)]/70 p-4" onClick={$event => {
        if ($event.target !== $event.currentTarget) return;
        return view.closeReport?.($event);
      }} data-sp-ef737f62="">
          <div role="dialog" aria-modal="true" aria-labelledby="report-dialog-title" className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-[24px] bg-brand-card shadow-2xl" data-sp-ef737f62="">
            <div className="relative h-[210px]" data-sp-ef737f62="">
              <PrivateImage src={view.selectedReport.image} alt={view.selectedReport.title} className="h-full w-full object-cover" data-sp-ef737f62="" />
              <button type="button" onClick={$event => {
              return view.closeReport?.($event);
            }} aria-label="Đóng chi tiết báo cáo" className="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full bg-brand-card text-[var(--ui-accent)]" data-sp-ef737f62="">
                {" ✕ "}
              </button>
            </div>
            <div className="p-6 sm:p-8" data-sp-ef737f62="">
              <div className="flex flex-wrap items-center gap-3" data-sp-ef737f62="">
                <span className={classNames(["rounded-full px-3 py-1.5 text-xs font-semibold", view.statusClass(view.selectedReport.status)])} data-sp-ef737f62="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedReport.statusLabel)}
                </span>
                <span className="text-xs text-[var(--ui-muted)]" data-sp-ef737f62="">
                  {" REPORT #"}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(String(view.selectedReport.id).padStart(3, "0"))}
                </span>
              </div>
              <h2 id="report-dialog-title" className="mt-5 text-2xl font-semibold" data-sp-ef737f62="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedReport.title)}
              </h2>
              <p className="mt-3 text-sm text-[var(--ui-ink)]" data-sp-ef737f62="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedReport.location)}
              </p>
              <div className="mt-6 space-y-4 border-y border-[var(--ui-border)] py-5" data-sp-ef737f62="">
                <div data-sp-ef737f62="">
                  <p className="text-xs uppercase tracking-widest text-[var(--ui-ink)]" data-sp-ef737f62="">
                    {" Lý do báo cáo "}
                  </p>
                  <p className="mt-2 text-sm font-semibold" data-sp-ef737f62="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedReport.reason)}
                  </p>
                </div>
                <div data-sp-ef737f62="">
                  <p className="text-xs uppercase tracking-widest text-[var(--ui-ink)]" data-sp-ef737f62="">
                    {" Thời gian gửi "}
                  </p>
                  <p className="mt-2 text-sm" data-sp-ef737f62="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedReport.sentAt)}
                  </p>
                </div>
                <div data-sp-ef737f62="">
                  <p className="text-xs uppercase tracking-widest text-[var(--ui-ink)]" data-sp-ef737f62="">
                    {" Cập nhật "}
                  </p>
                  <p className="mt-2 text-sm" data-sp-ef737f62="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedReport.update)}
                  </p>
                </div>
                <div data-sp-ef737f62="">
                  <p className="text-xs uppercase tracking-widest text-[var(--ui-ink)]" data-sp-ef737f62="">
                    {" Kết quả "}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-[var(--ui-accent)]" data-sp-ef737f62="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedReport.result || "Báo cáo đang được xử lý, chưa có kết quả.")}
                  </p>
                </div>
              </div>
              <ReportDetails report={view.selectedReport.raw} onUpdated={$event => {
              return view.reportUpdated?.($event);
            }} data-sp-ef737f62="" />
              <button type="button" onClick={$event => {
              return view.closeReport?.($event);
            }} className="mt-6 rounded-full bg-[var(--ui-soft)] px-7 py-3 text-xs font-semibold text-brand-navy" data-sp-ef737f62="">
                {" Đóng chi tiết "}
              </button>
            </div>
          </div>
        </div> : null}
    </div></>;
});
