import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useImperativeHandle, useEffect } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { session, errorText } from "../auth/api.js";
import { createHistoryClient } from "./history.js";
import { formatPrice, locationLabel } from "./valuation.js";
function useValuationHistoryState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const props = {
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [client] = useState(() => createHistoryClient());
  const [items] = useState(() => createStateStore([])),
    [busy] = useState(() => createStateStore(false)),
    [error] = useState(() => createStateStore("")),
    [page] = useState(() => createStateStore(0)),
    [pages] = useState(() => createStateStore(0));
  useSyncExternalStore(pages.subscribe, pages.getSnapshot);
  useSyncExternalStore(page.subscribe, page.getSnapshot);
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  useSyncExternalStore(items.subscribe, items.getSnapshot);
  const [removing] = useState(() => createStateStore("")),
    [labels] = useState(() => createStateStore({}));
  useSyncExternalStore(labels.subscribe, labels.getSnapshot);
  useSyncExternalStore(removing.subscribe, removing.getSnapshot);
  const _revisionRef = useRef(0);
  async function load() {
    const current = ++_revisionRef.current;
    items.set([]);
    error.set("");
    busy.set(false);
    if (!session.getSnapshot().token) return;
    busy.set(true);
    try {
      const result = await client.list(page.getSnapshot());
      if (current !== _revisionRef.current) return;
      items.set(result.items);
      pages.set(result.totalPages);
    } catch (failure) {
      if (current === _revisionRef.current) error.set(failure.code === "HISTORY_UNAVAILABLE" ? "Lịch sử định giá hiện chưa khả dụng. Bạn vẫn có thể thực hiện ước tính mới." : errorText(failure));
    } finally {
      if (current === _revisionRef.current) busy.set(false);
    }
  }
  async function remove(id) {
    if (removing.getSnapshot()) return;
    const current = _revisionRef.current;
    removing.set(id);
    error.set("");
    try {
      await client.remove(id);
      if (current !== _revisionRef.current) return;
      page.set(0);
      await load();
    } catch (failure) {
      if (current === _revisionRef.current) error.set(errorText(failure));
    } finally {
      removing.set("");
    }
  }
  function setLabels(value) {
    labels.set(value);
  }
  useImperativeHandle(forwardedRef, () => ({
    setLabels
  }), []);
  const _watched = (() => session.getSnapshot().token)();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    _initialized.current = true;
    const result = (() => {
      page.set(0);
      load();
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  const _watched2 = (() => _props.current.refreshKey)();
  const _previous2 = useRef(_watched2),
    _initialized2 = useRef(false);
  useEffect(() => {
    const previousValue = _previous2.current;
    _previous2.current = _watched2;
    let dispose;
    if (!_initialized2.current) {
      _initialized2.current = true;
      return;
    }
    const result = (() => {
      page.set(0);
      load();
    })(_watched2, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched2)]);
  useEffect(() => () => (() => {
    _revisionRef.current++;
  })(), []);
  return {
    ...inputProps,
    session: session.getSnapshot(),
    formatPrice,
    locationLabel,
    items: items.getSnapshot(),
    busy: busy.getSnapshot(),
    error: error.getSnapshot(),
    page: page.getSnapshot(),
    pages: pages.getSnapshot(),
    removing: removing.getSnapshot(),
    labels: labels.getSnapshot(),
    load,
    remove,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["refreshKey", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updatePageValue: page.set
  };
}
export default React.forwardRef(function ValuationHistory(props, ref) {
  const view = useValuationHistoryState(props, ref);
  return <><section aria-labelledby="history-heading" {...view.rootAttributes} className={classNames(["mt-8 rounded-3xl border border-[var(--ui-border)]/20 bg-brand-card p-6 sm:p-8", view.rootAttributes.className])}>
      <div className="flex flex-wrap justify-between gap-3">
        <h2 id="history-heading" className="text-xl font-semibold sm:text-2xl">
          {"Lịch sử định giá"}
        </h2>
        <SiteLink to="/valuation" className="text-sm underline">
          {"Ước tính giá rao mới ↗"}
        </SiteLink>
      </div>
      {!view.session.token ? <p className="mt-3 text-sm leading-6">
          <SiteLink to="/login?next=/valuation" className="underline">
            {"Đăng nhập"}
          </SiteLink>
          {" để lưu và xem lại kết quả của bạn. "}
        </p> : <React.Fragment>
          <p className="mt-2 text-sm text-[var(--ui-accent)]">
            {"Kết quả đã lưu của "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.session.user?.fullName || "tài khoản hiện tại")}
            {". Giá được giữ theo thời điểm ước tính."}
          </p>
          {view.busy ? <p role="status" className="mt-4">
              {"Đang tải lịch sử…"}
            </p> : null}
          {view.error ? <div role="alert" className="mt-4 rounded-xl bg-[var(--ui-surface)] p-3 text-sm">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}{" "}
              <button className="underline ml-2" onClick={$event => {
            return view.load?.($event);
          }}>
                {"Tải lại lịch sử"}
              </button>
            </div> : null}
          {!view.busy && !view.error && !view.items.length ? <div className="mt-5 rounded-2xl border border-dashed border-brand-line bg-brand-cream p-6 text-center">
              <h3 className="text-base font-semibold">
                {"Chưa có phân tích đã lưu"}
              </h3>
              <p className="mx-auto mt-2 max-w-md text-sm leading-7 text-brand-muted">
                {"Khi bạn lưu một kết quả ước tính, kết quả đó sẽ xuất hiện tại đây."}
              </p>
              <SiteLink to="/valuation" className="sp-button sp-button-secondary mt-4">
                {"Thực hiện đánh giá mới ↗"}
              </SiteLink>
            </div> : null}
          <ol className="mt-4 space-y-3">
            {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.items, item => <li key={item.id} className="rounded-xl bg-[var(--ui-surface)]/60 p-4" data-testid="history-item">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.formatPrice(item.prediction.predicted_asking_price_vnd))}
                    </p>
                    <p className="text-sm mt-1">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.input.category)}
                      {" · "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.input.area_sqm)}
                      {" m² · "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.locationLabel(item.input.location_feature, view.labels))}
                    </p>
                    <p className="text-xs mt-2 text-[var(--ui-accent)]">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(new Intl.DateTimeFormat("vi-VN", {
                    dateStyle: "short",
                    timeStyle: "short"
                  }).format(new Date(item.createdAt)))}
                      {" · Giá rao tham khảo"}
                    </p>
                  </div>
                  <button type="button" disabled={!!view.removing} className="text-sm underline disabled:opacity-50" aria-label={`Xóa kết quả ${view.formatPrice(item.prediction.predicted_asking_price_vnd)}`} onClick={$event => {
                view.remove(item.id);
              }}>
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.removing === item.id ? "Đang xóa…" : "Xóa")}
                  </button>
                </div>
              </li>)}
          </ol>
          {view.pages > 1 ? <nav className="mt-4 flex items-center gap-4 text-sm" aria-label="Trang lịch sử">
              <button disabled={view.busy || view.page === 0} className="underline disabled:opacity-40" onClick={$event => {
            view.updatePageValue(view.page - 1);
            view.load();
          }}>
                {"Trang trước"}
              </button>
              <span>
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.page + 1)}
                {" / "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.pages)}
              </span>
              <button disabled={view.busy || view.page + 1 >= view.pages} className="underline disabled:opacity-40" onClick={$event => {
            view.updatePageValue(view.page + 1);
            view.load();
          }}>
                {"Trang sau"}
              </button>
            </nav> : null}
        </React.Fragment>}
    </section></>;
});
