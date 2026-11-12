import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef, useEffect } from "react";
import PropertyModerationFeedback from "./PropertyModerationFeedback.jsx";
import { useAppNavigation } from "../../app/navigation.jsx";
import { api, session } from "../auth/api.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import Pagination from "../../shared/components/Pagination.jsx";
import PrivateImage from "../../shared/components/PrivateImage.jsx";
import { collectionProperty } from "../home/collection.js";
import { useCollection } from "../../shared/hooks/useCollection.js";
import { ownStatus } from "./listingPresentation.js";
import "./MyListingView.css";
function useMyListingViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const router = useAppNavigation();

  // SMARTPROP MY LISTINGS 2.0
  // Data is loaded from the existing backend.
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  const [activeFilter] = useState(() => createStateStore("all"));
  useSyncExternalStore(activeFilter.subscribe, activeFilter.getSnapshot);
  const [searchText] = useState(() => createStateStore(""));
  useSyncExternalStore(searchText.subscribe, searchText.getSnapshot);
  const [selectedListing] = useState(() => createStateStore(null));
  useSyncExternalStore(selectedListing.subscribe, selectedListing.getSnapshot);
  const [showEditNotice] = useState(() => createStateStore(false));
  useSyncExternalStore(showEditNotice.subscribe, showEditNotice.getSnapshot);
  const state = useCollection("/users/me/properties", "/users/me/properties/summary", () => ({
    keyword: searchText.getSnapshot().trim(),
    status: ownStatus[activeFilter.getSnapshot()]
  }));
  const _stateLatest = useRef(state);
  _stateLatest.current = state;
  const getListings = () => _stateLatest.current.items.map(collectionProperty);
  const count = id => _stateLatest.current.summary?.byStatus?.[ownStatus[id]] ?? "—";
  const getFilters = () => [{
    id: "all",
    label: "Tất cả",
    count: _stateLatest.current.summary?.totalListings ?? "—"
  }, ...Object.entries({
    draft: "Bản nháp",
    showing: "Đang hiển thị",
    pending: "Chờ duyệt",
    rejected: "Bị từ chối",
    hidden: "Đã ẩn",
    closed: "Đã đóng",
    expired: "Hết hạn"
  }).map(([id, label]) => ({
    id,
    label,
    count: count(id)
  }))];
  const filteredListings = getListings();
  const getTotalViews = () => _stateLatest.current.summary?.viewRecordingEnabled ? _stateLatest.current.summary.recordedViews : "—";
  const getTotalSaves = () => _stateLatest.current.summary?.savedRecords ?? "—";
  function statusClass(status) {
    if (status === "showing") {
      return "bg-[#E5F4EB] text-[#287B56]";
    }
    if (status === "pending") {
      return "bg-[#FFF1D9] text-[#A36A19]";
    }
    if (status === "rejected") {
      return "bg-[#FCE8E3] text-[#BD5D48]";
    }
    return "bg-[#EDF0F3] text-[#64748B]";
  }
  function openListing(item) {
    selectedListing.set(item);
  }
  function closeListing() {
    selectedListing.set(null);
  }
  function goToDetail(item) {
    _routerLatest.current.push({
      path: "/listing/" + item.id,
      query: {
        own: "1"
      }
    });
  }
  function editListing(item) {
    _routerLatest.current.push({
      path: "/post",
      query: {
        edit: item.id
      }
    });
  }
  function closeEditNotice() {
    showEditNotice.set(false);
    selectedListing.set(null);
  }
  function goHome() {
    _routerLatest.current.push("/home");
  }
  function goMap() {
    _routerLatest.current.push("/map");
  }
  function goPost() {
    if (!getCanPost()) {
      _stateLatest.current.updateState(draftValue => draftValue["notice"] = publishNotice);
      return;
    }
    _routerLatest.current.push("/post");
  }
  function goAccount() {
    _routerLatest.current.push("/account");
  }
  const getCanPost = () => ["BROKER", "ADMIN"].includes(session.getSnapshot().user?.role);
  const publishNotice = "Bạn đang dùng tài khoản Người mua / người thuê (BUYER). Để đăng tin, hãy đăng nhập bằng tài khoản Chủ nhà / môi giới (BROKER) hoặc ADMIN.";
  const _watched = (() => session.getSnapshot().user?.role)();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    _initialized.current = true;
    const result = (role => {
      if (role === "BUYER") _stateLatest.current.updateState(draftValue => draftValue["notice"] = publishNotice);else if (_stateLatest.current.notice === publishNotice) _stateLatest.current.updateState(draftValue => draftValue["notice"] = "");
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  async function act(p, action) {
    await _stateLatest.current.run(async () => {
      await api("/properties/" + p.id + (action === "delete" ? "?expectedVersion=" + p.raw.contentVersion : "/" + action), {
        method: action === "delete" ? "DELETE" : "POST",
        ...(action === "delete" ? {} : {
          body: {
            expectedVersion: p.raw.contentVersion
          }
        })
      });
      await _stateLatest.current.reload();
    });
  }
  return {
    ...inputProps,
    activeFilter: activeFilter.getSnapshot(),
    searchText: searchText.getSnapshot(),
    selectedListing: selectedListing.getSnapshot(),
    showEditNotice: showEditNotice.getSnapshot(),
    state,
    count,
    filters: getFilters(),
    filteredListings,
    totalViews: getTotalViews(),
    totalSaves: getTotalSaves(),
    statusClass,
    openListing,
    closeListing,
    goToDetail,
    editListing,
    closeEditNotice,
    goPost,
    act,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateSearchTextValue: searchText.set,
    updateActiveFilterValue: activeFilter.set
  };
}
export default React.forwardRef(function MyListingView(props, ref) {
  const view = useMyListingViewState(props, ref);
  return <><div data-ui-view="MyListingView" data-sp-51b40b91="" {...view.rootAttributes} className={classNames(["sp-my-listings min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)]", view.rootAttributes.className])}>
      <section className="relative overflow-hidden border-b border-[var(--ui-border)]" data-sp-51b40b91="">
        <div className="pointer-events-none absolute -right-28 -top-32 h-[420px] w-[420px] rounded-full border border-[var(--ui-border)]/20" data-sp-51b40b91="" />
        <div className="pointer-events-none absolute -right-10 -top-12 h-[280px] w-[280px] rounded-full border border-[var(--ui-border)]/20" data-sp-51b40b91="" />
        <div className="relative mx-auto max-w-[1440px] px-5 py-12 md:px-10 md:py-16" data-sp-51b40b91="">
          <div className="flex flex-wrap items-end justify-between gap-8" data-sp-51b40b91="">
            <div data-sp-51b40b91="">
              <div className="flex items-center gap-3" data-sp-51b40b91="">
                <span className="h-px w-9 bg-[var(--ui-soft)]" data-sp-51b40b91="" />
                <p className="text-xs font-bold uppercase tracking-[0.22em] text-[var(--ui-muted)]" data-sp-51b40b91="">
                  {" SMARTPROP / PROPERTY MANAGEMENT "}
                </p>
              </div>
              <h1 className="mt-6 text-[39px] font-medium leading-tight tracking-tight sm:text-[56px]" data-sp-51b40b91="">
                {" Quản lý "}
                <span className="block italic text-[var(--ui-muted)]" data-sp-51b40b91="">
                  {"bất động sản của bạn."}
                </span>
              </h1>
              <p className="mt-5 max-w-xl text-sm leading-7 text-[var(--ui-muted)]" data-sp-51b40b91="">
                {" Theo dõi trạng thái tin đăng, lượt quan tâm và quản lý danh mục bất động sản của bạn trong một không gian trực quan. "}
              </p>
              <span className="mt-5 inline-flex rounded-full border border-[var(--ui-border)] bg-[var(--ui-surface)] px-4 py-2 text-xs font-bold uppercase tracking-widest text-[var(--ui-muted)]" data-sp-51b40b91="">
                {" Dữ liệu từ hệ thống "}
              </span>
            </div>
            <button onClick={$event => {
              return view.goPost?.($event);
            }} className="rounded-full bg-[var(--ui-soft)] px-7 py-4 text-xs font-bold text-brand-navy shadow-lg transition hover:-translate-y-0.5 hover:bg-[var(--ui-soft)]" data-sp-51b40b91="">
              {" + Đăng bất động sản mới ↗ "}
            </button>
          </div>
        </div>
      </section>
      <section className="mx-auto max-w-[1440px] px-5 pt-10 md:px-10" data-sp-51b40b91="">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-5" data-sp-51b40b91="">
          <div className="rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7" data-sp-51b40b91="">
            <p className="text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]" data-sp-51b40b91="">
              {" Tổng tin đăng "}
            </p>
            <div className="mt-4 flex items-end justify-between" data-sp-51b40b91="">
              <span className="text-4xl font-semibold" data-sp-51b40b91="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.summary?.totalListings ?? "—")}
              </span>
              <span className="text-xl text-[var(--ui-ink)]" data-sp-51b40b91="">
                {"⌂"}
              </span>
            </div>
            <p className="mt-3 text-xs text-[var(--ui-ink)]" data-sp-51b40b91="">
              {"Danh mục của bạn"}
            </p>
          </div>
          <div className="rounded-[20px] bg-[var(--ui-soft)] p-5 text-brand-navy sm:p-7" data-sp-51b40b91="">
            <p className="text-xs font-bold uppercase tracking-widest text-brand-navy/60" data-sp-51b40b91="">
              {" Đang hiển thị "}
            </p>
            <div className="mt-4 flex items-end justify-between" data-sp-51b40b91="">
              <span className="text-4xl font-semibold" data-sp-51b40b91="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.count("showing"))}
              </span>
              <span className="h-3 w-3 rounded-full bg-[var(--ui-soft)]" data-sp-51b40b91="" />
            </div>
            <p className="mt-3 text-xs text-brand-navy/55" data-sp-51b40b91="">
              {"Tin đang hoạt động"}
            </p>
          </div>
          <div className="rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7" data-sp-51b40b91="">
            <p className="text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]" data-sp-51b40b91="">
              {" Tổng lượt xem "}
            </p>
            <div className="mt-4 flex items-end justify-between" data-sp-51b40b91="">
              <span className="text-4xl font-semibold" data-sp-51b40b91="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.totalViews)}
              </span>
              <span className="text-xl text-[var(--ui-ink)]" data-sp-51b40b91="">
                {"↗"}
              </span>
            </div>
            <p className="mt-3 text-xs text-[var(--ui-ink)]" data-sp-51b40b91="">
              {"Chưa có số liệu tương tác"}
            </p>
          </div>
          <div className="rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7" data-sp-51b40b91="">
            <p className="text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]" data-sp-51b40b91="">
              {" Lượt lưu tin "}
            </p>
            <div className="mt-4 flex items-end justify-between" data-sp-51b40b91="">
              <span className="text-4xl font-semibold" data-sp-51b40b91="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.totalSaves)}
              </span>
              <span className="text-xl text-[var(--ui-ink)]" data-sp-51b40b91="">
                {"♡"}
              </span>
            </div>
            <p className="mt-3 text-xs text-[var(--ui-ink)]" data-sp-51b40b91="">
              {"Người dùng quan tâm"}
            </p>
          </div>
        </div>
      </section>
      <div className="mx-auto max-w-[1440px] px-5 pb-20 pt-12 md:px-10" data-sp-51b40b91="">
        <ResourceState state={view.state} data-sp-51b40b91="" />
        {view.state.summaryError ? <p role="alert" data-sp-51b40b91="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.summaryError)}{" "}
            <button onClick={$event => {
            return view.state.loadSummary?.($event);
          }} data-sp-51b40b91="">
              {"Tải lại thống kê"}
            </button>
          </p> : null}
        <p className="mb-4 text-xs text-[var(--ui-ink)]" data-sp-51b40b91="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.totalElements)}
          {" kết quả · kết quả đã lọc trên toàn bộ dữ liệu. Số đếm trạng thái là tổng danh mục."}
        </p>
        <div className="flex flex-wrap items-end justify-between gap-5" data-sp-51b40b91="">
          <div data-sp-51b40b91="">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-muted)]" data-sp-51b40b91="">
              {" YOUR COLLECTION / 01 "}
            </p>
            <h2 className="mt-3 text-3xl font-medium tracking-tight sm:text-4xl" data-sp-51b40b91="">
              {" Danh sách "}
              <span className="italic text-[var(--ui-muted)]" data-sp-51b40b91="">
                {"tin đăng."}
              </span>
            </h2>
            <p className="mt-3 text-xs text-[var(--ui-ink)]" data-sp-51b40b91="">
              {" Quản lý và theo dõi các bất động sản đã đăng. "}
            </p>
          </div>
          <div className="flex w-full items-center gap-3 rounded-xl border border-[var(--ui-border)] bg-brand-card px-4 sm:w-[300px]" data-sp-51b40b91="">
            <span className="text-[var(--ui-muted)]" data-sp-51b40b91="">
              {"⌕"}
            </span>
            <input type="search" placeholder="Tìm tin đăng hoặc khu vực..." aria-label="Tìm tin đăng" className="h-12 min-w-0 w-full bg-transparent text-xs outline-none" data-sp-51b40b91="" value={view.searchText ?? ""} onChange={event => ($value => {
              view.updateSearchTextValue($value);
            })(event.target.value)} />
          </div>
        </div>
        <div className="mt-8 flex flex-wrap gap-2" data-sp-51b40b91="">
          {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.filters, filter => <button key={filter.id} onClick={$event => {
            view.updateActiveFilterValue(filter.id);
          }} className={classNames(["rounded-full border px-4 py-2.5 text-xs font-semibold transition sm:px-5", view.activeFilter === filter.id ? "border-[var(--ui-border)] bg-[var(--ui-soft)] text-brand-navy" : "border-[var(--ui-border)] bg-brand-card text-[var(--ui-accent)] hover:border-[var(--ui-border)]"])} data-sp-51b40b91="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(filter.label)}{" "}
              <span className="ml-1 opacity-65" data-sp-51b40b91="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(filter.count)}
              </span>
            </button>)}
        </div>
        <div className="mb-5 mt-7 flex items-center justify-between gap-4" data-sp-51b40b91="">
          <p className="text-xs text-[var(--ui-ink)]" data-sp-51b40b91="">
            {" Hiển thị "}
            <strong className="text-[var(--ui-accent)]" data-sp-51b40b91="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.filteredListings.length)}
            </strong>
            {" tin đăng "}
          </p>
          <span className="text-xs uppercase tracking-widest text-[var(--ui-muted)]" data-sp-51b40b91="">
            {" PROPERTY PORTFOLIO "}
          </span>
        </div>
        {view.filteredListings.length ? <div className="space-y-5" data-sp-51b40b91="">
            {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.filteredListings, listing => <article key={listing.id} className="group grid min-w-0 overflow-hidden rounded-[22px] border border-[var(--ui-border)] bg-brand-card transition duration-300 hover:border-[var(--ui-border)] hover:shadow-[0_16px_45px_rgba(20,43,79,0.08)] lg:grid-cols-[245px_minmax(0,1fr)_230px]" data-sp-51b40b91="">
                <div className="relative h-[230px] overflow-hidden bg-[var(--ui-surface)] lg:h-full lg:min-h-[220px]" data-sp-51b40b91="">
                  <PrivateImage src={listing.image} alt={`${listing.title}`} loading="lazy" className="h-full w-full object-cover transition duration-700 group-hover:scale-105" data-sp-51b40b91="" />
                  <div className="absolute inset-0 bg-gradient-to-t from-[var(--ui-soft)]/45 to-transparent" data-sp-51b40b91="" />
                  <span className="absolute bottom-4 left-4 text-xs font-bold uppercase tracking-[0.15em] text-brand-navy" data-sp-51b40b91="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(listing.location)}
                  </span>
                </div>
                <div className="flex min-w-0 flex-col justify-center p-5 sm:p-7" data-sp-51b40b91="">
                  <div className="flex flex-wrap items-center gap-3" data-sp-51b40b91="">
                    <span className={classNames(["rounded-full px-3 py-1.5 text-xs font-bold", view.statusClass(listing.status)])} data-sp-51b40b91="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(listing.statusText)}
                    </span>
                    {listing.statusSub ? <span className="text-xs text-[var(--ui-ink)]" data-sp-51b40b91="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(listing.statusSub)}
                      </span> : null}
                  </div>
                  <h3 className="mt-4 text-lg font-semibold leading-7 sm:text-xl" data-sp-51b40b91="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(listing.title)}
                  </h3>
                  <p className="mt-2 text-xs text-[var(--ui-ink)]" data-sp-51b40b91="">
                    {" ⌖ "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(listing.location)}
                  </p>
                  <p className="mt-3 text-xs leading-6 text-[var(--ui-accent)]" data-sp-51b40b91="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(listing.info)}
                  </p>
                  <div className="mt-5 flex flex-wrap gap-5 border-t border-[var(--ui-border)] pt-4" data-sp-51b40b91="">
                    {listing.views !== null ? <React.Fragment>
                        <span className="text-xs text-[var(--ui-ink)]" data-sp-51b40b91="">
                          <strong className="mr-1 text-sm text-[var(--ui-accent)]" data-sp-51b40b91="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(listing.views)}
                          </strong>
                          {" lượt xem "}
                        </span>
                        <span className="text-xs text-[var(--ui-ink)]" data-sp-51b40b91="">
                          <strong className="mr-1 text-sm text-[var(--ui-accent)]" data-sp-51b40b91="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(listing.saves)}
                          </strong>
                          {" lượt lưu "}
                        </span>
                      </React.Fragment> : <span className="text-xs text-[var(--ui-ink)]" data-sp-51b40b91="">
                        {" Chưa có thống kê tương tác "}
                      </span>}
                  </div>
                </div>
                <div className="flex flex-col justify-between gap-6 border-t border-[var(--ui-border)] p-5 sm:p-7 lg:border-l lg:border-t-0" data-sp-51b40b91="">
                  <div className="lg:text-right" data-sp-51b40b91="">
                    <p className="text-xs uppercase tracking-widest text-[var(--ui-ink)]" data-sp-51b40b91="">
                      {" Giá đăng "}
                    </p>
                    <p className="mt-2 text-[25px] font-semibold tracking-tight" data-sp-51b40b91="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(listing.priceText)}
                    </p>
                    <p className="mt-1 text-xs text-[var(--ui-muted)]" data-sp-51b40b91="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(listing.priceUnit)}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 lg:justify-end" data-sp-51b40b91="">
                    <button onClick={$event => {
                  view.openListing(listing);
                }} className="rounded-full border border-[var(--ui-border)] bg-brand-card px-5 py-3 text-xs font-semibold transition hover:border-[var(--ui-border)]" data-sp-51b40b91="">
                      {" Xem "}
                    </button>
                    <button onClick={$event => {
                  view.editListing(listing);
                }} className={classNames(["rounded-full px-5 py-3 text-xs font-semibold text-brand-navy transition hover:opacity-90", listing.status === "rejected" ? "bg-[var(--ui-soft)]" : "bg-[var(--ui-soft)]"])} data-sp-51b40b91="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(listing.status === "rejected" ? "Sửa & gửi lại" : "Sửa tin")}
                    </button>
                    {["draft", "rejected"].includes(listing.status) ? <button disabled={view.state.busy} onClick={$event => {
                  view.act(listing, "submit");
                }} className="rounded-full border px-4 py-2 text-xs" data-sp-51b40b91="">
                        {"Gửi duyệt"}
                      </button> : null}
                    {!["closed", "expired"].includes(listing.status) ? <button disabled={view.state.busy} onClick={$event => {
                  view.act(listing, "close");
                }} className="rounded-full border px-4 py-2 text-xs" data-sp-51b40b91="">
                        {"Đóng tin"}
                      </button> : null}
                    <button disabled={view.state.busy} onClick={$event => {
                  view.act(listing, "delete");
                }} className="rounded-full border px-4 py-2 text-xs" data-sp-51b40b91="">
                      {"Xóa tin"}
                    </button>
                  </div>
                </div>
                <PropertyModerationFeedback id={listing.id} data-sp-51b40b91="" />
              </article>)}
          </div> : <div className="rounded-[24px] border border-[var(--ui-border)] bg-brand-card px-6 py-20 text-center" data-sp-51b40b91="">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[var(--ui-surface)] text-3xl text-[var(--ui-muted)]" data-sp-51b40b91="">
              {" ⌕ "}
            </div>
            <h3 className="mt-6 text-xl font-semibold" data-sp-51b40b91="">
              {" Không tìm thấy tin đăng "}
            </h3>
            <p className="mt-3 text-sm text-[var(--ui-ink)]" data-sp-51b40b91="">
              {" Thử thay đổi trạng thái hoặc từ khóa tìm kiếm. "}
            </p>
            <button onClick={$event => {
            view.updateActiveFilterValue("all");
            view.updateSearchTextValue("");
          }} className="mt-6 rounded-full bg-[var(--ui-soft)] px-6 py-3 text-xs font-semibold text-brand-navy" data-sp-51b40b91="">
              {" Xem tất cả tin đăng "}
            </button>
          </div>}
        <section className="relative mt-14 overflow-hidden rounded-[25px] bg-[var(--ui-soft)] px-7 py-10 text-brand-navy sm:px-10" data-sp-51b40b91="">
          <div className="pointer-events-none absolute -right-12 -top-24 h-72 w-72 rounded-full border border-[var(--ui-border)]/20" data-sp-51b40b91="" />
          <div className="relative flex flex-wrap items-center justify-between gap-7" data-sp-51b40b91="">
            <div data-sp-51b40b91="">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-accent)]" data-sp-51b40b91="">
                {" SMARTPROP / YOUR NEXT LISTING "}
              </p>
              <h2 className="mt-4 text-3xl font-medium" data-sp-51b40b91="">
                {" Sẵn sàng cho "}
                <span className="italic text-[var(--ui-ink)]" data-sp-51b40b91="">
                  {"tin đăng tiếp theo?"}
                </span>
              </h2>
              <p className="mt-4 max-w-xl text-sm leading-7 text-brand-navy/60" data-sp-51b40b91="">
                {" Đăng tải bất động sản và tiếp tục xây dựng danh mục của bạn trên SmartProp. "}
              </p>
            </div>
            <button onClick={$event => {
              return view.goPost?.($event);
            }} className="rounded-full bg-[var(--ui-soft)] px-7 py-4 text-xs font-bold text-[var(--ui-accent)] transition hover:bg-[var(--ui-soft)]" data-sp-51b40b91="">
              {" + Tạo tin đăng mới ↗ "}
            </button>
          </div>
        </section>
        <p className="mt-7 text-center text-xs leading-6 text-[var(--ui-ink)]" data-sp-51b40b91="">
          {" Thông tin và trạng thái tin đăng được tải từ tài khoản của bạn. "}
        </p>
        <Pagination state={view.state} data-sp-51b40b91="" />
      </div>
      {view.selectedListing && !view.showEditNotice ? <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--ui-soft)]/70 p-4" onClick={$event => {
        if ($event.target !== $event.currentTarget) return;
        return view.closeListing?.($event);
      }} data-sp-51b40b91="">
          <div role="dialog" aria-modal="true" aria-labelledby="listing-dialog-title" className="w-full max-w-xl overflow-hidden rounded-[24px] bg-brand-card shadow-2xl" data-sp-51b40b91="">
            <div className="relative h-[220px]" data-sp-51b40b91="">
              <PrivateImage src={view.selectedListing.image} alt={view.selectedListing.title} className="h-full w-full object-cover" data-sp-51b40b91="" />
              <button onClick={$event => {
              return view.closeListing?.($event);
            }} aria-label="Đóng" className="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full bg-brand-card text-[var(--ui-accent)]" data-sp-51b40b91="">
                {" ✕ "}
              </button>
            </div>
            <div className="p-6 sm:p-8" data-sp-51b40b91="">
              <span className={classNames(["rounded-full px-3 py-1.5 text-xs font-semibold", view.statusClass(view.selectedListing.status)])} data-sp-51b40b91="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedListing.statusText)}
              </span>
              <h2 id="listing-dialog-title" className="mt-5 text-2xl font-semibold" data-sp-51b40b91="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedListing.title)}
              </h2>
              <p className="mt-3 text-sm text-[var(--ui-ink)]" data-sp-51b40b91="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedListing.location)}
              </p>
              <p className="mt-3 text-sm text-[var(--ui-accent)]" data-sp-51b40b91="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedListing.info)}
              </p>
              <p className="mt-6 text-2xl font-semibold" data-sp-51b40b91="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedListing.priceText)}
              </p>
              <div className="mt-7 flex flex-wrap gap-3" data-sp-51b40b91="">
                {view.selectedListing ? <button onClick={$event => {
                view.goToDetail(view.selectedListing);
              }} className="rounded-full bg-[var(--ui-soft)] px-6 py-3 text-xs font-semibold text-brand-navy" data-sp-51b40b91="">
                    {" Mở trang chi tiết ↗ "}
                  </button> : null}
                <button onClick={$event => {
                return view.closeListing?.($event);
              }} className="rounded-full border border-[var(--ui-border)] px-6 py-3 text-xs font-semibold" data-sp-51b40b91="">
                  {" Đóng "}
                </button>
              </div>
            </div>
          </div>
        </div> : null}
      {view.showEditNotice && view.selectedListing ? <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--ui-soft)]/70 p-4" onClick={$event => {
        if ($event.target !== $event.currentTarget) return;
        return view.closeEditNotice?.($event);
      }} data-sp-51b40b91="">
          <div role="dialog" aria-modal="true" aria-labelledby="edit-dialog-title" className="w-full max-w-md rounded-[24px] bg-brand-card p-7 text-center shadow-2xl sm:p-9" data-sp-51b40b91="">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[var(--ui-surface)] text-2xl text-[var(--ui-muted)]" data-sp-51b40b91="">
              {" ✎ "}
            </div>
            <h2 id="edit-dialog-title" className="mt-5 text-2xl font-semibold" data-sp-51b40b91="">
              {" Chỉnh sửa tin đăng "}
            </h2>
            <p className="mt-4 text-sm leading-7 text-[var(--ui-accent)]" data-sp-51b40b91="">
              {" Tin "}
              <strong data-sp-51b40b91="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedListing.title)}
              </strong>
              {" chưa có trang chỉnh sửa được kết nối. Chức năng này cần được xây dựng ở bước tiếp theo. "}
            </p>
            <button onClick={$event => {
            return view.closeEditNotice?.($event);
          }} className="mt-7 rounded-full bg-[var(--ui-soft)] px-8 py-3 text-xs font-semibold text-brand-navy" data-sp-51b40b91="">
              {" Đã hiểu "}
            </button>
          </div>
        </div> : null}
    </div></>;
});
