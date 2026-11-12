import { classNames, chainHandlers } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { api } from "../auth/api.js";
import { applicationStatuses, applicationActions, reviewActions, brokerErrorText } from "../broker/brokerApplication.js";
function useBrokerApplicationsViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const [items] = useState(() => createStateStore([])),
    [status] = useState(() => createStateStore("PENDING")),
    [page] = useState(() => createStateStore(0)),
    [totalPages] = useState(() => createStateStore(0)),
    [total] = useState(() => createStateStore(0)),
    [busy] = useState(() => createStateStore(false)),
    [error] = useState(() => createStateStore("")),
    [message] = useState(() => createStateStore("")),
    [selected] = useState(() => createStateStore(null)),
    [reason] = useState(() => createStateStore(""));
  useSyncExternalStore(reason.subscribe, reason.getSnapshot);
  useSyncExternalStore(selected.subscribe, selected.getSnapshot);
  useSyncExternalStore(message.subscribe, message.getSnapshot);
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  useSyncExternalStore(total.subscribe, total.getSnapshot);
  useSyncExternalStore(totalPages.subscribe, totalPages.getSnapshot);
  useSyncExternalStore(page.subscribe, page.getSnapshot);
  useSyncExternalStore(status.subscribe, status.getSnapshot);
  useSyncExternalStore(items.subscribe, items.getSnapshot);
  const _sequenceRef = useRef(0);
  async function load(reset = false) {
    if (reset) page.set(0);
    const run = ++_sequenceRef.current;
    busy.set(true);
    error.set("");
    selected.set(null);
    try {
      const q = new URLSearchParams({
        page: String(page.getSnapshot()),
        size: "10"
      });
      if (status.getSnapshot()) q.set("status", status.getSnapshot());
      const result = await api("/admin/broker-applications?" + q);
      if (run !== _sequenceRef.current) return;
      items.set(result.items);
      total.set(result.totalElements);
      totalPages.set(result.totalPages);
    } catch (e) {
      if (run === _sequenceRef.current) error.set(brokerErrorText(e));
    } finally {
      if (run === _sequenceRef.current) busy.set(false);
    }
  }
  function select(item) {
    selected.set(item);
    reason.set("");
    message.set("");
  }
  async function review(action) {
    if (busy.getSnapshot() || !selected.getSnapshot() || !reason.getSnapshot().trim()) return;
    const application = selected.getSnapshot();
    busy.set(true);
    error.set("");
    message.set("");
    try {
      await api("/admin/broker-applications/" + encodeURIComponent(application.id) + "/review", {
        method: "POST",
        body: {
          action,
          expectedVersion: application.contentVersion,
          reason: reason.getSnapshot().trim()
        }
      });
      message.set("Đã xử lý hồ sơ. Khi thay đổi quyền, người dùng cần đăng nhập lại.");
      reason.set("");
      await load();
    } catch (e) {
      error.set(brokerErrorText(e));
      if (e.status === 409) {
        selected.set(null);
        error.edit(draftValue => draftValue += " Tải lại danh sách và kiểm tra hồ sơ trước khi thao tác lại.");
      }
    } finally {
      busy.set(false);
    }
  }
  async function move(delta) {
    page.edit(draftValue => draftValue += delta);
    await load();
  }
  useEffect(() => {
    const result = (() => load())();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  useEffect(() => () => (() => {
    _sequenceRef.current++;
  })(), []);
  return {
    ...inputProps,
    applicationStatuses,
    applicationActions,
    reviewActions,
    items: items.getSnapshot(),
    status: status.getSnapshot(),
    page: page.getSnapshot(),
    totalPages: totalPages.getSnapshot(),
    total: total.getSnapshot(),
    busy: busy.getSnapshot(),
    error: error.getSnapshot(),
    message: message.getSnapshot(),
    selected: selected.getSnapshot(),
    reason: reason.getSnapshot(),
    load,
    select,
    review,
    move,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateStatusValue: status.set,
    updateReasonValue: reason.set
  };
}
export default React.forwardRef(function BrokerApplicationsView(props, ref) {
  const view = useBrokerApplicationsViewState(props, ref);
  return <><section data-ui-view="BrokerApplicationsView" {...view.rootAttributes} className={classNames(["rounded-panel bg-brand-card p-5 text-brand-navy sm:p-7", view.rootAttributes.className])}>
      <h1 className="text-2xl font-semibold">
        {"Duyệt quyền đăng tin"}
      </h1>
      <p className="mt-2 text-sm leading-6 text-brand-muted">
        {"Xét duyệt người đăng, độc lập với duyệt từng tin. Không cấp quyền ADMIN từ màn hình này."}
      </p>
      <div className="my-5 flex flex-wrap items-end gap-3">
        <label className="sp-field">
          {"Trạng thái"}
          <select className="sp-input" disabled={view.busy} value={view.status ?? ""} onChange={chainHandlers($event => {
            view.load(true);
          }, event => ($value => {
            view.updateStatusValue($value);
          })(event.target.value))}>
            <option value="">
              {"Tất cả"}
            </option>
            {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.applicationStatuses, (label, key) => <option key={key} value={key} style={{
              display: key !== "NOT_REQUESTED" ? undefined : "none"
            }}>
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(label)}
              </option>)}
          </select>
        </label>
        <button className="sp-button sp-button-secondary" type="button" disabled={view.busy} onClick={$event => {
          view.load();
        }}>
          {"Tải lại danh sách"}
        </button>
        <p className="text-sm">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.total)}
          {" hồ sơ"}
        </p>
      </div>
      {view.busy ? <p role="status">
          {"Đang xử lý…"}
        </p> : null}
      {view.error ? <p role="alert" className="my-4 whitespace-pre-wrap rounded-control bg-[var(--ui-error-bg)] p-4 text-sm text-[var(--ui-error-text)]">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}
        </p> : null}
      {view.message ? <p role="status" className="my-4 text-sm text-[var(--ui-success-text)]">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.message)}
        </p> : null}
      {!view.busy && !view.error && !view.items.length ? <p className="py-8 text-center text-brand-muted">
          {"Chưa có hồ sơ ở trạng thái này."}
        </p> : null}
      <div className="grid gap-4">
        {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.items, item => <article key={item.id} className={classNames(["rounded-panel border p-4", view.selected?.id === item.id ? "border-brand-gold bg-brand-cream" : "border-brand-line"])}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="font-semibold">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.displayName)}
                </h2>
                <p className="mt-1 text-sm">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.applicantType === "OWNER" ? "Chủ nhà" : "Môi giới")}
                  {" · "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.operatingArea)}
                </p>
                <p className="mt-1 text-xs text-brand-muted">
                  {"Tài khoản #"}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.userId)}
                  {" · "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.applicationStatuses[item.status])}
                  {" · phiên bản "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.contentVersion)}
                </p>
              </div>
              <button className="sp-button sp-button-secondary" type="button" disabled={view.busy} onClick={$event => {
              view.select(item);
            }}>
                {"Xem hồ sơ"}
              </button>
            </div>
            {view.selected?.id === item.id ? <div className="mt-5 grid gap-4 text-sm">
                <p>
                  {"Điện thoại đã cung cấp: "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.contactPhone)}
                </p>
                <p className="whitespace-pre-wrap leading-6">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.requestMessage)}
                </p>
                <p>
                  {"Xác nhận trách nhiệm: "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.responsibilityAccepted ? "Đã xác nhận" : "Chưa xác nhận")}
                </p>
                {item.reviewReason ? <p className="whitespace-pre-wrap">
                    {"Phản hồi trước: "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.reviewReason)}
                  </p> : null}
                {view.reviewActions(item.status).length ? <label className="sp-field">
                    {"Lý do / phản hồi"}
                    <textarea className="sp-input min-h-24" required={true} maxLength="2000" disabled={view.busy} value={view.reason ?? ""} onChange={event => ($value => {
                view.updateReasonValue($value);
              })(event.target.value)} />
                  </label> : null}
                <div className="flex flex-wrap gap-3">
                  {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.reviewActions(item.status), action => <button key={action} className={classNames(["sp-button", action === "APPROVE" ? "sp-button-primary" : "sp-button-secondary"])} type="button" disabled={view.busy || !view.reason.trim()} onClick={$event => {
                view.review(action);
              }}>
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.applicationActions[action])}
                    </button>)}
                </div>
              </div> : null}
          </article>)}
      </div>
      {view.totalPages > 1 ? <nav aria-label="Phân trang hồ sơ" className="mt-5 flex items-center gap-4">
          <button className="sp-button sp-button-secondary" disabled={view.busy || view.page === 0} onClick={$event => {
          view.move(-1);
        }}>
            {"Trước"}
          </button>
          <span>
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.page + 1)}
            {" / "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.totalPages)}
          </span>
          <button className="sp-button sp-button-secondary" disabled={view.busy || view.page + 1 >= view.totalPages} onClick={$event => {
          view.move(1);
        }}>
            {"Sau"}
          </button>
        </nav> : null}
    </section></>;
});
