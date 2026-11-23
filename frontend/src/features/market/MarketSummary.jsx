import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { api } from "../auth/api.js";
import AppIcon from "../../shared/components/AppIcon.jsx";
import { types } from "../property/property.js";
function useMarketSummaryState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [summary] = useState(() => createStateStore(null));
  useSyncExternalStore(summary.subscribe, summary.getSnapshot);
  const [busy] = useState(() => createStateStore(false));
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  const [error] = useState(() => createStateStore(""));
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  const [type] = useState(() => createStateStore(""));
  useSyncExternalStore(type.subscribe, type.getSnapshot);
  const _sequenceRef = useRef(0);
  async function load() {
    const run = ++_sequenceRef.current;
    busy.set(true);
    error.set("");
    summary.set(null);
    try {
      const query = new URLSearchParams({
        transactionType: "SALE",
        priceUnit: "TOTAL"
      });
      if (_props.current.district) query.set("district", _props.current.district);
      if (type.getSnapshot()) query.set("propertyType", type.getSnapshot());
      const result = await api("/properties/market-summary?" + query, {
        authenticated: false
      });
      if (run === _sequenceRef.current) summary.set(result);
    } catch {
      if (run === _sequenceRef.current) error.set("Chưa tải được giá chào hiện tại. Vui lòng thử lại.");
    } finally {
      if (run === _sequenceRef.current) busy.set(false);
    }
  }
  const _watched = (() => [_props.current.district, type.getSnapshot()])();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    _initialized.current = true;
    const result = load(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  const price = value => value == null ? "—" : Number(value).toLocaleString("vi-VN", {
    maximumFractionDigits: 0
  });
  return {
    ...inputProps,
    types,
    summary: summary.getSnapshot(),
    busy: busy.getSnapshot(),
    error: error.getSnapshot(),
    type: type.getSnapshot(),
    load,
    price,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["district", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateTypeValue: type.set
  };
}
export default React.forwardRef(function MarketSummary(props, ref) {
  const view = useMarketSummaryState(props, ref);
  return <><section id="market-current" aria-labelledby="market-current-heading" {...view.rootAttributes} className={classNames(["bg-[var(--ui-surface)] pb-14 text-[var(--ui-accent)] md:pb-20", view.rootAttributes.className])}>
      <div className="mx-auto max-w-7xl px-5 lg:px-8">
        <div className="market-data-panel rounded-3xl border border-[var(--ui-border)] bg-brand-card p-5 md:p-7" aria-busy={view.busy}>
          <div className="market-panel-header flex flex-wrap items-start justify-between gap-5">
            <div className="max-w-2xl">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-accent)]">
                {"Dữ liệu từ SmartProp"}
              </p>
              <h2 id="market-current-heading" className="mt-2 text-xl font-semibold md:text-2xl">
                {"Giá chào hiện tại trên SmartProp"}
              </h2>
              <p className="mt-2 text-sm leading-6 text-[var(--ui-accent)]">
                {" Tin bán được duyệt còn hiệu lực"}
                {view.district ? <span>
                    {" tại "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.district)}
                  </span> : null}
                {" · VND / tổng giá. Đây là giá chào, chưa có dữ liệu lịch sử hoặc giá giao dịch. "}
              </p>
            </div>
            <label className="flex w-full flex-col gap-2 text-sm font-medium sm:w-auto">
              {" Loại bất động sản "}
              <select className="min-h-11 rounded-xl border border-[var(--ui-border)] bg-brand-card px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ui-border)]" value={view.type ?? ""} onChange={event => ($value => {
                view.updateTypeValue($value);
              })(event.target.value)}>
                <option value="">
                  {"Tất cả"}
                </option>
                {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.types, (label, key) => <option key={key} value={key}>
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(label)}
                  </option>)}
              </select>
            </label>
          </div>
          {view.busy ? <p role="status" className="mt-6 text-sm text-[var(--ui-accent)]">
              {"Đang tải thống kê…"}
            </p> : null}
          {view.error ? <p role="alert" className="mt-6 rounded-xl bg-[var(--ui-error-bg)] p-4 text-sm text-[var(--ui-error-text)]">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}{" "}
              <button type="button" onClick={$event => {
              return view.load?.($event);
            }} className="ml-2 cursor-pointer rounded font-semibold underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2">
                {"Thử lại"}
              </button>
            </p> : null}
          {view.summary ? <div className="market-kpis mt-6 grid gap-4 md:grid-cols-3">
              <div className="min-w-0 rounded-2xl bg-[var(--ui-surface)] p-5">
                <p className="text-sm text-[var(--ui-accent)]">
                  <AppIcon name="properties" className="market-kpi-icon hidden" />{"Tin phù hợp"}
                </p>
                <strong className="mt-2 block text-3xl font-bold">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.summary.overall.count)}
                </strong>
              </div>
              <div className="min-w-0 rounded-2xl bg-[var(--ui-surface)] p-5">
                <p className="text-sm text-[var(--ui-accent)]">
                  <AppIcon name="tools" className="market-kpi-icon hidden" />{"Giá chào trung bình"}
                </p>
                <strong className="mt-2 block text-xl font-semibold wrap-anywhere">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.price(view.summary.overall.averageAskingPrice))}{" "}
                  <span className="text-sm font-medium">
                    {"VND"}
                  </span>
                </strong>
              </div>
              <div className="min-w-0 rounded-2xl bg-[var(--ui-surface)] p-5">
                <p className="text-sm text-[var(--ui-accent)]">
                  <AppIcon name="gis" className="market-kpi-icon hidden" />{"Giá chào theo tổng diện tích"}
                </p>
                <strong className="mt-2 block text-xl font-semibold wrap-anywhere">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.price(view.summary.overall.weightedAskingPricePerSqm))}{" "}
                  <span className="text-sm font-medium">
                    {"VND/m²"}
                  </span>
                </strong>
              </div>
            </div> : null}
          {view.summary?.overall.count === 0 ? <p className="mt-5 text-sm text-[var(--ui-accent)]">
              {"Chưa có tin đủ điều kiện để thống kê."}
            </p> : null}
          {view.summary?.byDistrict?.length ? <ul className="market-area-grid mt-5 grid gap-3 md:grid-cols-3">
              {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.summary.byDistrict, group => <li key={group.key} className="rounded-xl border border-[var(--ui-border)] p-4 text-sm leading-6 text-[var(--ui-accent)]">
                  <strong className="block font-semibold text-[var(--ui-accent)]">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(group.key || "Chưa xác định khu vực")}
                  </strong>{" "}
                  <span className="market-area-count">{(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(group.amounts.count)}{" tin"}</span><span className="market-area-separator">{" · "}</span>
                  <span className="market-area-price">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.price(group.amounts.weightedAskingPricePerSqm))}
                  {" VND/m² "}
                  </span>
                </li>)}
            </ul> : null}
          {view.summary?.districtsTruncated ? <p className="mt-4 text-sm text-[var(--ui-accent)]">
              {"Danh sách thống kê khu vực đã được giới hạn bởi server."}
            </p> : null}
        </div>
      </div>
    </section></>;
});
