import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { api, session } from "../auth/api.js";
import { canPublish } from "../../shared/lib/siteNavigation.js";
import { applicationStatuses, canRequestBroker, brokerErrorText } from "./brokerApplication.js";
function useBrokerApplicationCardState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const [state] = useState(() => createStateStore(null)),
    [busy] = useState(() => createStateStore(false)),
    [error] = useState(() => createStateStore(""));
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  useSyncExternalStore(state.subscribe, state.getSnapshot);
  const getBuyer = () => canRequestBroker(session.getSnapshot().user),
    getAdmin = () => session.getSnapshot().user?.role === "ADMIN" && session.getSnapshot().user?.status === "ACTIVE";
  const _sequenceRef = useRef(0);
  async function load() {
    const run = ++_sequenceRef.current;
    state.set(null);
    error.set("");
    busy.set(false);
    if (!getBuyer()) return;
    busy.set(true);
    try {
      const result = await api("/users/me/broker-application");
      if (run === _sequenceRef.current) state.set(result);
    } catch (e) {
      if (run === _sequenceRef.current) error.set(brokerErrorText(e));
    } finally {
      if (run === _sequenceRef.current) busy.set(false);
    }
  }
  const _watched = (() => [session.getSnapshot().user?.id, session.getSnapshot().user?.role, session.getSnapshot().user?.status])();
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
  useEffect(() => () => (() => _sequenceRef.current++)(), []);
  return {
    ...inputProps,
    session: session.getSnapshot(),
    canPublish,
    applicationStatuses,
    state: state.getSnapshot(),
    busy: busy.getSnapshot(),
    error: error.getSnapshot(),
    buyer: getBuyer(),
    admin: getAdmin(),
    load,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function BrokerApplicationCard(props, ref) {
  const view = useBrokerApplicationCardState(props, ref);
  return <><section aria-labelledby="broker-card-title" {...view.rootAttributes} className={classNames(["rounded-panel border border-brand-line bg-brand-card p-5 sm:p-6", view.rootAttributes.className])}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold tracking-widest text-brand-accent">
            {"QUYỀN ĐĂNG TIN"}
          </p>
          <h2 id="broker-card-title" className="mt-2 text-xl font-semibold">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.admin ? "Quản trị người đăng" : view.canPublish(view.session.user) ? "Quản lý bất động sản của bạn" : "Đăng ký quyền đăng tin")}
          </h2>
          <p className="mt-2 text-sm leading-6 text-brand-muted">
            {"Hồ sơ người đăng và từng tin bất động sản được xét duyệt riêng. Chỉ tin đã duyệt mới xuất hiện công khai."}
          </p>
        </div>
        {view.buyer && view.state ? <span className="rounded-full bg-brand-surface px-3 py-2 text-sm font-semibold">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.applicationStatuses[view.state.status] || view.state.status)}
          </span> : null}
      </div>
      {view.buyer ? <React.Fragment>
          {view.busy ? <p role="status" className="mt-3 text-sm">
              {"Đang tải trạng thái…"}
            </p> : null}
          {view.error ? <p role="alert" className="mt-3 text-sm leading-6 text-[var(--ui-error-text)]">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}{" "}
              <button type="button" className="underline" disabled={view.busy} onClick={$event => {
            return view.load?.($event);
          }}>
                {"Thử lại"}
              </button>
            </p> : null}
          {view.state?.application?.reviewReason ? <p className="mt-3 whitespace-pre-wrap text-sm leading-6">
              {"Phản hồi: "}
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.application.reviewReason)}
            </p> : null}
          {view.state?.status === "PENDING" ? <p className="mt-3 text-sm leading-6">
              {"Yêu cầu đang chờ xét duyệt. Bạn chưa có quyền đăng tin và không cần gửi yêu cầu trùng."}
            </p> : null}
          {view.state?.status === "SUSPENDED" ? <p className="mt-3 text-sm leading-6">
              {"Quyền đăng tin đang tạm ngưng. Vui lòng liên hệ quản trị viên."}
            </p> : null}
          {view.state ? <SiteLink className="sp-button sp-button-primary mt-4" to="/account/broker-application">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.status === "NOT_REQUESTED" ? "Đăng ký quyền đăng tin" : ["REJECTED", "NEEDS_INFORMATION"].includes(view.state.status) ? "Bổ sung và gửi lại hồ sơ" : "Xem trạng thái hồ sơ")}
            </SiteLink> : null}
        </React.Fragment> : null}
      {view.canPublish(view.session.user) ? <div className="mt-4 flex flex-wrap gap-3">
          {view.admin ? <SiteLink className="sp-button sp-button-primary" to="/admin/broker-applications">
              {"Duyệt quyền đăng tin"}
            </SiteLink> : null}
          {view.admin ? <SiteLink className="sp-button sp-button-secondary" to="/admin/posts">
              {"Duyệt tin bất động sản"}
            </SiteLink> : null}
          <SiteLink className="sp-button sp-button-secondary" to="/post">
            {"Đăng tin mới"}
          </SiteLink>
          <SiteLink className="sp-button sp-button-secondary" to="/my-listing">
            {"Quản lý tin đăng"}
          </SiteLink>
        </div> : null}
    </section></>;
});
