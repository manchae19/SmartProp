import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { useAppNavigation } from "../../app/navigation.jsx";
import { api } from "../auth/api.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import Pagination from "../../shared/components/Pagination.jsx";
import PrivateImage from "../../shared/components/PrivateImage.jsx";
import { collectionProperty } from "../home/collection.js";
import { useCollection } from "../../shared/hooks/useCollection.js";
import { typeCode } from "../property/listingPresentation.js";
import "./FavoriteView.css";
function useFavoriteViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const router = useAppNavigation();

  // SMARTPROP FAVORITES 2.0
  // Data is loaded from the existing backend.
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  const [activeFilter] = useState(() => createStateStore("Tất cả"));
  useSyncExternalStore(activeFilter.subscribe, activeFilter.getSnapshot);
  const [sortType] = useState(() => createStateStore("Mới lưu"));
  useSyncExternalStore(sortType.subscribe, sortType.getSnapshot);
  const [searchText] = useState(() => createStateStore(""));
  useSyncExternalStore(searchText.subscribe, searchText.getSnapshot);
  const [removedItem] = useState(() => createStateStore(null));
  useSyncExternalStore(removedItem.subscribe, removedItem.getSnapshot);
  const filters = ["Tất cả", "Nhà phố", "Căn hộ", "Đất nền"];
  const state = useCollection("/users/me/saved-properties", "/users/me/saved-properties/summary", () => ({
    keyword: searchText.getSnapshot().trim(),
    propertyType: typeCode[activeFilter.getSnapshot()],
    sort: {
      "Mới lưu": "newest",
      "Cũ nhất": "oldest",
      "Giá thấp": "priceAsc",
      "Giá cao": "priceDesc"
    }[sortType.getSnapshot()]
  }));
  const _stateLatest = useRef(state);
  _stateLatest.current = state;
  const getListings = () => _stateLatest.current.items.map(collectionProperty);
  const filteredListings = getListings();
  const getPropertyTypeCount = () => _stateLatest.current.summary ? Object.keys(_stateLatest.current.summary.byPropertyType || {}).length : "—";
  const getPriceGroups = () => _stateLatest.current.summary?.priceGroups || [];
  const filterCount = label => _stateLatest.current.summary ? label === "Tất cả" ? _stateLatest.current.summary.totalVisible : _stateLatest.current.summary.byPropertyType?.[typeCode[label]] || 0 : "—";
  function formatPrice(price) {
    return price.toLocaleString("vi-VN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  }
  async function removeFavorite(id) {
    const item = getListings().find(x => x.id === id);
    if (!item || _stateLatest.current.busy) return;
    await _stateLatest.current.run(async () => {
      await api("/users/me/saved-properties/" + id, {
        method: "DELETE"
      });
      removedItem.set(item);
      await _stateLatest.current.reload();
    });
  }
  async function undoRemove() {
    if (!removedItem.getSnapshot() || _stateLatest.current.busy) return;
    await _stateLatest.current.run(async () => {
      await api("/users/me/saved-properties/" + removedItem.getSnapshot().id, {
        method: "PUT"
      });
      removedItem.set(null);
      await _stateLatest.current.reload();
    });
  }
  function openListing(id) {
    _routerLatest.current.push("/listing/" + id);
  }
  function resetFilters() {
    activeFilter.set("Tất cả");
    searchText.set("");
    sortType.set("Mới lưu");
  }
  return {
    ...inputProps,
    activeFilter: activeFilter.getSnapshot(),
    sortType: sortType.getSnapshot(),
    searchText: searchText.getSnapshot(),
    removedItem: removedItem.getSnapshot(),
    filters,
    state,
    filteredListings,
    propertyTypeCount: getPropertyTypeCount(),
    priceGroups: getPriceGroups(),
    filterCount,
    removeFavorite,
    undoRemove,
    openListing,
    resetFilters,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateSearchTextValue: searchText.set,
    updateSortTypeValue: sortType.set,
    updateActiveFilterValue: activeFilter.set
  };
}
export default React.forwardRef(function FavoriteView(props, ref) {
  const view = useFavoriteViewState(props, ref);
  return <><div data-ui-view="FavoriteView" data-sp-928bf8cf="" {...view.rootAttributes} className={classNames(["sp-favorites min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)]", view.rootAttributes.className])}>
      <section className="relative overflow-hidden border-b border-[var(--ui-border)]" data-sp-928bf8cf="">
        <div className="pointer-events-none absolute -right-28 -top-32 h-[420px] w-[420px] rounded-full border border-[var(--ui-border)]/20" data-sp-928bf8cf="" />
        <div className="pointer-events-none absolute -right-10 -top-12 h-[280px] w-[280px] rounded-full border border-[var(--ui-border)]/20" data-sp-928bf8cf="" />
        <div className="relative mx-auto max-w-[1440px] px-5 py-12 md:px-10 md:py-16" data-sp-928bf8cf="">
          <div className="flex flex-wrap items-end justify-between gap-8" data-sp-928bf8cf="">
            <div data-sp-928bf8cf="">
              <div className="flex items-center gap-3" data-sp-928bf8cf="">
                <span className="h-px w-9 bg-[var(--ui-soft)]" data-sp-928bf8cf="" />
                <p className="text-xs font-bold uppercase tracking-[0.22em] text-[var(--ui-muted)]" data-sp-928bf8cf="">
                  {" SMARTPROP / SAVED COLLECTION "}
                </p>
              </div>
              <h1 className="mt-6 text-[39px] font-medium leading-tight tracking-tight sm:text-[56px]" data-sp-928bf8cf="">
                {" Những lựa chọn "}
                <span className="block italic text-[var(--ui-muted)]" data-sp-928bf8cf="">
                  {"bạn yêu thích."}
                </span>
              </h1>
              <p className="mt-5 max-w-2xl text-sm leading-7 text-[var(--ui-muted)]" data-sp-928bf8cf="">
                {" Lưu giữ những bất động sản đáng quan tâm, so sánh mức giá và dễ dàng quay lại khám phá những không gian sống phù hợp. "}
              </p>
              <span className="mt-5 inline-flex rounded-full border border-[var(--ui-border)] bg-[var(--ui-surface)] px-4 py-2 text-xs font-bold uppercase tracking-widest text-[var(--ui-muted)]" data-sp-928bf8cf="">
                {" Dữ liệu từ hệ thống "}
              </span>
            </div>
            <SiteLink to="/listings" className="rounded-full bg-[var(--ui-soft)] px-7 py-4 text-xs font-bold text-brand-navy transition hover:bg-[var(--ui-soft)]" data-sp-928bf8cf="">
              {" Khám phá thêm bất động sản ↗ "}
            </SiteLink>
          </div>
        </div>
      </section>
      <section className="mx-auto max-w-[1440px] px-5 pt-10 md:px-10" data-sp-928bf8cf="">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 lg:gap-5" data-sp-928bf8cf="">
          <div className="rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7" data-sp-928bf8cf="">
            <p className="text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]" data-sp-928bf8cf="">
              {" Đã yêu thích "}
            </p>
            <div className="mt-4 flex items-end justify-between" data-sp-928bf8cf="">
              <span className="text-4xl font-semibold" data-sp-928bf8cf="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.summary?.totalVisible ?? "—")}
              </span>
              <span className="text-xl text-[var(--ui-ink)]" data-sp-928bf8cf="">
                {"♥"}
              </span>
            </div>
            <p className="mt-3 text-xs text-[var(--ui-ink)]" data-sp-928bf8cf="">
              {"Bất động sản đã lưu"}
            </p>
          </div>
          <div className="rounded-[20px] bg-[var(--ui-soft)] p-5 text-brand-navy sm:p-7" data-sp-928bf8cf="">
            <p className="text-xs font-bold uppercase tracking-widest text-brand-navy/60" data-sp-928bf8cf="">
              {" Loại hình quan tâm "}
            </p>
            <div className="mt-4 flex items-end justify-between" data-sp-928bf8cf="">
              <span className="text-4xl font-semibold" data-sp-928bf8cf="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.propertyTypeCount)}
              </span>
              <span className="text-xl text-[var(--ui-ink)]" data-sp-928bf8cf="">
                {"⌂"}
              </span>
            </div>
            <p className="mt-3 text-xs text-brand-navy/55" data-sp-928bf8cf="">
              {"Nhà phố · Căn hộ · Đất nền"}
            </p>
          </div>
          <div className="col-span-2 rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7 lg:col-span-1" data-sp-928bf8cf="">
            <p className="text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]" data-sp-928bf8cf="">
              {" Tổng giá trị tham khảo "}
            </p>
            <div className="mt-4 flex items-end justify-between" data-sp-928bf8cf="">
              <span className="text-3xl font-semibold sm:text-4xl" data-sp-928bf8cf="">
                {!view.priceGroups.length ? <span data-sp-928bf8cf="">
                    {"—"}
                  </span> : null}
                {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.priceGroups, g => <span key={g.transactionType + g.currency + g.priceUnit} className="block text-sm" data-sp-928bf8cf="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(Number(g.amounts.totalAskingPrice).toLocaleString("vi-VN"))}{" "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(g.currency)}
                    {" · "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(g.transactionType === "SALE" ? "Bán" : "Thuê")}
                    {" / "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(g.priceUnit)}
                  </span>)}
              </span>
              <span className="text-xl text-[var(--ui-ink)]" data-sp-928bf8cf="">
                {"↗"}
              </span>
            </div>
            <p className="mt-3 text-xs text-[var(--ui-ink)]" data-sp-928bf8cf="">
              {"Giá chào toàn bộ tin còn hiển thị, tách theo giao dịch/đơn vị"}
            </p>
          </div>
        </div>
      </section>
      <div className="mx-auto max-w-[1440px] px-5 pb-20 pt-12 md:px-10" data-sp-928bf8cf="">
        <ResourceState state={view.state} data-sp-928bf8cf="" />
        {view.state.summaryError ? <p role="alert" data-sp-928bf8cf="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.summaryError)}{" "}
            <button onClick={$event => {
            return view.state.loadSummary?.($event);
          }} data-sp-928bf8cf="">
              {"Tải lại thống kê"}
            </button>
          </p> : null}
        <p className="mb-4 text-xs text-[var(--ui-ink)]" data-sp-928bf8cf="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.totalElements)}
          {" kết quả · kết quả đã lọc toàn bộ danh mục."}
        </p>
        <div className="flex flex-wrap items-end justify-between gap-5" data-sp-928bf8cf="">
          <div data-sp-928bf8cf="">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-muted)]" data-sp-928bf8cf="">
              {" YOUR FAVORITES / 01 "}
            </p>
            <h2 className="mt-3 text-3xl font-medium tracking-tight sm:text-4xl" data-sp-928bf8cf="">
              {" Bộ sưu tập "}
              <span className="italic text-[var(--ui-muted)]" data-sp-928bf8cf="">
                {"của bạn."}
              </span>
            </h2>
            <p className="mt-3 text-xs text-[var(--ui-ink)]" data-sp-928bf8cf="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.totalElements)}
              {" bất động sản phù hợp với bộ lọc. "}
            </p>
          </div>
          <div className="flex w-full flex-wrap gap-3 sm:w-auto" data-sp-928bf8cf="">
            <div className="flex min-w-0 flex-1 items-center gap-2 rounded-xl border border-[var(--ui-border)] bg-brand-card px-4 sm:w-[260px]" data-sp-928bf8cf="">
              <span className="text-lg text-[var(--ui-muted)]" data-sp-928bf8cf="">
                {"⌕"}
              </span>
              <input type="search" aria-label="Tìm kiếm tin đã lưu" placeholder="Tìm tin đăng, khu vực..." className="h-12 min-w-0 w-full bg-transparent text-xs outline-none" data-sp-928bf8cf="" value={view.searchText ?? ""} onChange={event => ($value => {
                view.updateSearchTextValue($value);
              })(event.target.value)} />
            </div>
            <select aria-label="Sắp xếp tin yêu thích" className="h-12 rounded-xl border border-[var(--ui-border)] bg-brand-card px-4 text-xs outline-none" data-sp-928bf8cf="" value={view.sortType ?? ""} onChange={event => ($value => {
              view.updateSortTypeValue($value);
            })(event.target.value)}>
              <option data-sp-928bf8cf="">
                {"Mới lưu"}
              </option>
              <option data-sp-928bf8cf="">
                {"Cũ nhất"}
              </option>
              <option data-sp-928bf8cf="">
                {"Giá thấp"}
              </option>
              <option data-sp-928bf8cf="">
                {"Giá cao"}
              </option>
            </select>
          </div>
        </div>
        <div className="mt-8 flex flex-wrap gap-2" data-sp-928bf8cf="">
          {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.filters, filter => <button key={filter} type="button" onClick={$event => {
            view.updateActiveFilterValue(filter);
          }} className={classNames(["rounded-full border px-4 py-2.5 text-xs font-semibold transition sm:px-5", view.activeFilter === filter ? "border-[var(--ui-border)] bg-[var(--ui-soft)] text-brand-navy" : "border-[var(--ui-border)] bg-brand-card text-[var(--ui-accent)] hover:border-[var(--ui-border)]"])} data-sp-928bf8cf="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(filter)}{" "}
              <span className="ml-1 opacity-65" data-sp-928bf8cf="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.filterCount(filter))}
              </span>
            </button>)}
        </div>
        {view.removedItem ? <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-[var(--ui-border)] bg-[var(--ui-surface)] px-5 py-4" data-sp-928bf8cf="">
            <p className="text-xs text-[var(--ui-muted)]" data-sp-928bf8cf="">
              {" Đã bỏ yêu thích: "}
              <strong data-sp-928bf8cf="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.removedItem.title)}
              </strong>
            </p>
            <button type="button" onClick={$event => {
            return view.undoRemove?.($event);
          }} className="text-xs font-bold text-[var(--ui-accent)] underline underline-offset-4" data-sp-928bf8cf="">
              {" Hoàn tác "}
            </button>
          </div> : null}
        {view.filteredListings.length ? <div className="mt-8 grid min-w-0 grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3" data-sp-928bf8cf="">
            {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.filteredListings, item => <article key={item.id} className="group min-w-0 overflow-hidden rounded-[22px] border border-[var(--ui-border)] bg-brand-card transition duration-300 hover:-translate-y-1 hover:border-[var(--ui-border)] hover:shadow-[0_18px_50px_rgba(20,43,79,.10)]" data-sp-928bf8cf="">
                <div className="relative h-[260px] overflow-hidden bg-[var(--ui-surface)]" data-sp-928bf8cf="">
                  <PrivateImage src={item.image} alt={`${item.title}`} loading="lazy" className="h-full w-full object-cover transition duration-700 group-hover:scale-105" data-sp-928bf8cf="" />
                  <div className="absolute inset-0 bg-gradient-to-t from-[var(--ui-soft)]/50 via-transparent to-transparent" data-sp-928bf8cf="" />
                  <span className={classNames(["absolute left-4 top-4 rounded-full px-3 py-2 text-xs font-bold shadow-sm", item.badgeColor === "green" ? "bg-[var(--ui-surface)] text-[var(--ui-accent)]" : "bg-[var(--ui-surface)] text-[var(--ui-muted)]"])} data-sp-928bf8cf="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.badge)}
                  </span>
                  <button type="button" onClick={$event => {
                view.removeFavorite(item.id);
              }} aria-label={`Bỏ yêu thích ${item.title}`} title="Bỏ yêu thích" className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-full bg-[var(--ui-soft)] text-lg text-brand-navy transition hover:scale-110 hover:bg-[var(--ui-soft)]" data-sp-928bf8cf="">
                    {" ♥ "}
                  </button>
                  <span className="absolute bottom-5 left-5 text-xs font-bold uppercase tracking-[0.15em] text-brand-navy" data-sp-928bf8cf="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.type)}
                    {" / Đà Nẵng "}
                  </span>
                </div>
                <div className="p-6 sm:p-7" data-sp-928bf8cf="">
                  <p className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--ui-muted)]" data-sp-928bf8cf="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.type)}
                  </p>
                  <h3 className="mt-3 min-h-[56px] text-xl font-semibold leading-7" data-sp-928bf8cf="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.title)}
                  </h3>
                  <p className="mt-3 text-xs text-[var(--ui-ink)]" data-sp-928bf8cf="">
                    {" ⌖ "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.location)}
                  </p>
                  <div className="mt-6 border-y border-[var(--ui-border)] py-4" data-sp-928bf8cf="">
                    <p className="text-xs text-[var(--ui-accent)]" data-sp-928bf8cf="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.info)}
                    </p>
                  </div>
                  <div className="mt-5 flex items-end justify-between gap-4" data-sp-928bf8cf="">
                    <div data-sp-928bf8cf="">
                      <p className="text-xs uppercase tracking-widest text-[var(--ui-ink)]" data-sp-928bf8cf="">
                        {" Giá tham khảo "}
                      </p>
                      <p className="mt-2 text-[27px] font-semibold tracking-tight" data-sp-928bf8cf="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.priceText)}{" "}
                        <span className="text-base text-[var(--ui-muted)]" data-sp-928bf8cf="" />
                      </p>
                    </div>
                    <button type="button" onClick={$event => {
                  view.openListing(item.id);
                }} aria-label={`Xem chi tiết ${item.title}`} className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-[var(--ui-border)] text-lg transition group-hover:border-[var(--ui-border)] group-hover:bg-[var(--ui-soft)] group-hover:text-brand-navy" data-sp-928bf8cf="">
                      {" ↗ "}
                    </button>
                  </div>
                  <div className="mt-5 flex items-center justify-between border-t border-[var(--ui-border)] pt-4" data-sp-928bf8cf="">
                    <span className="text-xs text-[var(--ui-ink)]" data-sp-928bf8cf="">
                      {" ♡ "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.saved)}
                    </span>
                    <button type="button" onClick={$event => {
                  view.openListing(item.id);
                }} className="text-xs font-bold text-[var(--ui-accent)] hover:text-[var(--ui-muted)]" data-sp-928bf8cf="">
                      {" Xem chi tiết → "}
                    </button>
                  </div>
                </div>
              </article>)}
          </div> : <div className="mt-8 rounded-[24px] border border-[var(--ui-border)] bg-brand-card px-6 py-20 text-center" data-sp-928bf8cf="">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[var(--ui-surface)] text-3xl text-[var(--ui-muted)]" data-sp-928bf8cf="">
              {" ♡ "}
            </div>
            <h3 className="mt-6 text-xl font-semibold" data-sp-928bf8cf="">
              {" Chưa có bất động sản phù hợp "}
            </h3>
            <p className="mt-3 text-sm text-[var(--ui-ink)]" data-sp-928bf8cf="">
              {" Hãy thay đổi bộ lọc hoặc khám phá thêm tin đăng. "}
            </p>
            <button type="button" onClick={$event => {
            return view.resetFilters?.($event);
          }} className="mt-6 rounded-full bg-[var(--ui-soft)] px-6 py-3 text-xs font-semibold text-brand-navy" data-sp-928bf8cf="">
              {" Xem tất cả tin yêu thích "}
            </button>
          </div>}
        <section className="relative mt-14 overflow-hidden rounded-[25px] bg-[var(--ui-soft)] px-7 py-10 text-brand-navy sm:px-10" data-sp-928bf8cf="">
          <div className="pointer-events-none absolute -right-12 -top-24 h-72 w-72 rounded-full border border-[var(--ui-border)]/20" data-sp-928bf8cf="" />
          <div className="relative flex flex-wrap items-center justify-between gap-7" data-sp-928bf8cf="">
            <div data-sp-928bf8cf="">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-accent)]" data-sp-928bf8cf="">
                {" SMARTPROP / DISCOVER MORE "}
              </p>
              <h2 className="mt-4 text-3xl font-medium" data-sp-928bf8cf="">
                {" Lựa chọn tiếp theo "}
                <span className="italic text-[var(--ui-ink)]" data-sp-928bf8cf="">
                  {" đang chờ bạn."}
                </span>
              </h2>
              <p className="mt-4 max-w-xl text-sm leading-7 text-brand-navy/60" data-sp-928bf8cf="">
                {" Tiếp tục khám phá các bất động sản, tìm kiếm theo nhu cầu và mở rộng bộ sưu tập yêu thích của bạn. "}
              </p>
            </div>
            <SiteLink to="/listings" className="rounded-full bg-[var(--ui-soft)] px-7 py-4 text-xs font-bold text-[var(--ui-accent)] transition hover:bg-[var(--ui-soft)]" data-sp-928bf8cf="">
              {" Khám phá bất động sản ↗ "}
            </SiteLink>
          </div>
        </section>
        <p className="mt-7 text-center text-xs leading-6 text-[var(--ui-ink)]" data-sp-928bf8cf="">
          {" Tin đăng và trạng thái được tải từ hệ thống. Danh sách yêu thích được lưu theo tài khoản của bạn. "}
        </p>
        <Pagination state={view.state} data-sp-928bf8cf="" />
      </div>
    </div></>;
});
