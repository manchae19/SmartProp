import { afterPaint, classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useId, useRef, useEffect, useImperativeHandle } from "react";
import { districts } from "../map/districts.js";
import { propertyTypes, normalizeFilters, filterError, sortOptions } from "./listingFilters.js";
function useListingFiltersState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [draft] = useState(() => createStateStore({})),
    [expanded] = useState(() => createStateStore(false)),
    [error] = useState(() => createStateStore("")),
    [errorNode] = useState(() => createStateStore(null)),
    panelId = useId();
  useSyncExternalStore(errorNode.subscribe, errorNode.getSnapshot);
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(expanded.subscribe, expanded.getSnapshot);
  useSyncExternalStore(draft.subscribe, draft.getSnapshot);
  const _watched = (() => _props.current.value)();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    _initialized.current = true;
    const result = (value => {
      draft.set({
        ...value
      });
      error.set("");
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  async function apply() {
    error.set(filterError(draft.getSnapshot()));
    if (error.getSnapshot()) {
      expanded.set(true);
      await afterPaint();
      errorNode.getSnapshot()?.focus();
      return;
    }
    _propsLatest.current.onChange?.(normalizeFilters(draft.getSnapshot()));
    _propsLatest.current.onSearch?.();
  }
  function transaction(value) {
    draft.edit(draftValue => draftValue["transactionType"] = value);
    apply();
  }
  function reset() {
    draft.set({});
    apply();
  }
  useImperativeHandle(forwardedRef, () => ({
    expand: () => {
      expanded.set(true);
    }
  }), []);
  return {
    ...inputProps,
    districts,
    propertyTypes,
    sortOptions,
    draft: draft.getSnapshot(),
    expanded: expanded.getSnapshot(),
    error: error.getSnapshot(),
    panelId,
    apply,
    transaction,
    reset,
    updateErrorNodeValue: errorNode.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["value", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateExpandedValue: expanded.set,
    updateDraft: draft.edit
  };
}
export default React.forwardRef(function ListingFilters(props, ref) {
  const view = useListingFiltersState(props, ref);
  return <><form aria-label="Tìm kiếm bất động sản" onSubmit={$event => {
      $event.preventDefault();
      return view.apply?.($event);
    }} {...view.rootAttributes} className={classNames(["listing-filters rounded-panel border border-brand-line bg-brand-card p-4 shadow-sm sm:p-6", view.rootAttributes.className])}>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="filter-tabs inline-flex flex-wrap gap-1 rounded-full bg-brand-surface p-1" role="group" aria-label="Hình thức giao dịch">
          {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))({
            "": "Tất cả",
            SALE: "Bán",
            RENT: "Cho thuê"
          }, (label, key) => <button key={key} type="button" aria-pressed={(view.draft.transactionType || "") === key} className={classNames(["min-h-11 rounded-full px-4 py-2 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-gold sm:px-6", (view.draft.transactionType || "") === key ? "bg-brand-raised text-brand-navy shadow-sm" : "text-brand-muted hover:bg-brand-card"])} onClick={$event => {
            view.transaction(key);
          }}>
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(label)}
              </button>)}
          {view.children ?? null}
        </div>
        <button type="button" className="advanced-toggle sp-button sp-button-secondary" aria-expanded={view.expanded} aria-controls={view.panelId} onClick={$event => {
          view.updateExpandedValue(!view.expanded);
        }}>
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.expanded ? "Thu gọn bộ lọc" : "Bộ lọc nâng cao")}
          <svg className={classNames(["size-4 transition-transform motion-reduce:transition-none", {
            "rotate-180": view.expanded
          }])} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
            <path d="m6 9 6 6 6-6" />
          </svg>
        </button>
      </div>
      <div className="quick-fields grid items-end gap-3 min-[360px]:grid-cols-2 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
        <label className="keyword sp-field min-[360px]:col-span-2 lg:col-span-1">
          {"Từ khóa"}
          <input name="keyword" className="sp-input" maxLength="200" placeholder="Tên tin, địa chỉ, khu vực…" type="search" value={view.draft.keyword ?? ""} onChange={event => ($value => {
            view.updateDraft(draftValue => draftValue.keyword = $value);
          })(event.target.value)} />
        </label>
        <label className="sp-field">
          {"Khu vực"}
          <select name="district" className="sp-input" value={view.draft.district ?? ""} onChange={event => ($value => {
            view.updateDraft(draftValue => draftValue.district = $value);
          })(event.target.value)}>
            <option value="">
              {"Tất cả khu vực"}
            </option>
            {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.districts.filter(d => d !== "Tất cả"), district => <option key={district}>
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(district)}
                </option>)}
          </select>
        </label>
        <label className="sp-field">
          {"Loại bất động sản"}
          <select name="propertyType" className="sp-input" value={view.draft.propertyType ?? ""} onChange={event => ($value => {
            view.updateDraft(draftValue => draftValue.propertyType = $value);
          })(event.target.value)}>
            <option value="">
              {"Tất cả loại hình"}
            </option>
            {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.propertyTypes, (label, key) => <option key={key} value={key}>
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(label)}
              </option>)}
          </select>
        </label>
        <button className="search-button sp-button sp-button-primary min-[360px]:col-span-2 lg:col-span-1" type="submit">
          <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
            <circle cx="10.5" cy="10.5" r="6.5" />
            <path d="m16 16 5 5" />
          </svg>
          {"Tìm kiếm"}
        </button>
      </div>
      <div id={view.panelId} className="advanced-fields mt-6 grid gap-4 border-t border-brand-line pt-5 sm:grid-cols-2 lg:grid-cols-3" style={{
        display: view.expanded ? undefined : "none"
      }}>
        <p className="filter-help text-xs leading-6 text-brand-muted sm:col-span-2 lg:col-span-3">
          {"Giá nhập bằng VND, theo đơn vị giá niêm yết của từng tin: tổng giá / tháng / năm / ngày. Bộ lọc áp dụng trên toàn bộ danh sách."}
        </p>
        <label className="sp-field">
          {"Giá tối thiểu (VND)"}
          <input name="minPrice" className="sp-input" type="text" inputMode="decimal" placeholder="Ví dụ: 2000000000" value={view.draft.minPrice ?? ""} onChange={event => ($value => {
            view.updateDraft(draftValue => draftValue.minPrice = $value);
          })(event.target.value)} />
        </label>
        <label className="sp-field">
          {"Giá tối đa (VND)"}
          <input name="maxPrice" className="sp-input" type="text" inputMode="decimal" placeholder="Không giới hạn" value={view.draft.maxPrice ?? ""} onChange={event => ($value => {
            view.updateDraft(draftValue => draftValue.maxPrice = $value);
          })(event.target.value)} />
        </label>
        <label className="sp-field">
          {"Diện tích tối thiểu (m²)"}
          <input name="minArea" className="sp-input" type="number" min="0" step="0.01" value={view.draft.minArea ?? ""} onChange={event => ($value => {
            view.updateDraft(draftValue => draftValue.minArea = $value);
          })(event.target.value)} />
        </label>
        <label className="sp-field">
          {"Diện tích tối đa (m²)"}
          <input name="maxArea" className="sp-input" type="number" min="0" step="0.01" value={view.draft.maxArea ?? ""} onChange={event => ($value => {
            view.updateDraft(draftValue => draftValue.maxArea = $value);
          })(event.target.value)} />
        </label>
        <label className="sp-field">
          {"Phòng ngủ tối thiểu"}
          <select name="bedrooms" className="sp-input" value={view.draft.bedrooms ?? ""} onChange={event => ($value => {
            view.updateDraft(draftValue => draftValue.bedrooms = $value);
          })(event.target.value)}>
            <option value="">
              {"Không giới hạn"}
            </option>
            {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(5, n => <option key={n} value={String(n)}>
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(n)}
                {"+"}
              </option>)}
          </select>
        </label>
        <label className="sp-field">
          {"Sắp xếp"}
          <select name="sort" className="sp-input" value={view.draft.sort ?? ""} onChange={event => ($value => {
            view.updateDraft(draftValue => draftValue.sort = $value);
          })(event.target.value)}>
            {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.sortOptions, (label, key) => <option key={key} value={key}>
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(label)}
              </option>)}
          </select>
        </label>
        {view.draft.city ? <label className="sp-field">
            {"Thành phố"}
            <input className="sp-input" name="city" maxLength="100" value={view.draft.city ?? ""} onChange={event => ($value => {
            view.updateDraft(draftValue => draftValue.city = $value);
          })(event.target.value)} />
          </label> : null}
        {view.draft.ward ? <label className="sp-field">
            {"Phường / xã"}
            <input className="sp-input" name="ward" maxLength="100" value={view.draft.ward ?? ""} onChange={event => ($value => {
            view.updateDraft(draftValue => draftValue.ward = $value);
          })(event.target.value)} />
          </label> : null}
        <div className="advanced-actions flex flex-wrap justify-end gap-3 sm:col-span-2 lg:col-span-3">
          <button type="submit" className="sp-button sp-button-primary">
            {"Áp dụng bộ lọc"}
          </button>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs leading-6 text-brand-muted">
          {"Có thể kết hợp hình thức, khu vực và loại hình."}
        </p>
        <button type="button" className="reset-filters min-h-11 rounded-control px-2 text-xs font-semibold text-brand-accent underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-brand-gold" onClick={$event => {
          return view.reset?.($event);
        }}>
          {"Xóa bộ lọc"}
        </button>
      </div>
      {view.error ? <p ref={view.updateErrorNodeValue} role="alert" tabIndex="-1" className="filter-error mt-4 rounded-control bg-[var(--ui-error-bg)] p-4 text-sm leading-6 text-[var(--ui-error-text)] focus-visible:outline-2 focus-visible:outline-red-700">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}
        </p> : null}
    </form></>;
});
