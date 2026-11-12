import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useEffect, useRef } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { api, loadProfile, session } from "../auth/api.js";
import { canPublish } from "../../shared/lib/siteNavigation.js";
import { applicationStatuses, canApply, applicationPayload, brokerErrorText, canRequestBroker } from "./brokerApplication.js";
function useBrokerApplicationViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const [state] = useState(() => createStateStore(null)),
    [busy] = useState(() => createStateStore(false)),
    [error] = useState(() => createStateStore("")),
    [message] = useState(() => createStateStore("")),
    [form] = useState(() => createStateStore({
      applicantType: "OWNER",
      displayName: "",
      contactPhone: "",
      operatingArea: "",
      requestMessage: "",
      responsibilityAccepted: false
    }));
  useSyncExternalStore(form.subscribe, form.getSnapshot);
  useSyncExternalStore(message.subscribe, message.getSnapshot);
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  useSyncExternalStore(state.subscribe, state.getSnapshot);
  const [needsReload] = useState(() => createStateStore(false)),
    [ready] = useState(() => createStateStore(false));
  useSyncExternalStore(ready.subscribe, ready.getSnapshot);
  useSyncExternalStore(needsReload.subscribe, needsReload.getSnapshot);
  const getEditable = () => ready.getSnapshot() && !needsReload.getSnapshot() && canApply(state.getSnapshot(), session.getSnapshot().user);
  async function load() {
    busy.set(true);
    error.set("");
    ready.set(false);
    state.set(null);
    message.set("");
    needsReload.set(false);
    try {
      await loadProfile();
      if (!canRequestBroker(session.getSnapshot().user)) return;
      state.set(await api("/users/me/broker-application"));
      const a = state.getSnapshot().application;
      ready.set(true);
      if (a) form.edit(draftValue => Object.assign(draftValue, {
        applicantType: a.applicantType,
        displayName: a.displayName,
        contactPhone: a.contactPhone,
        operatingArea: a.operatingArea,
        requestMessage: a.requestMessage,
        responsibilityAccepted: false
      }));else form.edit(draftValue => Object.assign(draftValue, {
        displayName: session.getSnapshot().user.fullName || "",
        contactPhone: session.getSnapshot().user.phone || "",
        operatingArea: session.getSnapshot().user.district || ""
      }));
    } catch (e) {
      error.set(brokerErrorText(e));
    } finally {
      busy.set(false);
    }
  }
  async function submit() {
    if (busy.getSnapshot() || !getEditable()) return;
    busy.set(true);
    error.set("");
    message.set("");
    try {
      state.set(await api("/users/me/broker-application", {
        method: "POST",
        body: applicationPayload(form.getSnapshot(), state.getSnapshot(), session.getSnapshot().user)
      }));
      message.set("Đã gửi hồ sơ. Vui lòng chờ quản trị viên xét duyệt. Khi được cấp quyền, hãy đăng nhập lại.");
    } catch (e) {
      error.set(brokerErrorText(e));
      if (e.status === 409) needsReload.set(true);
    } finally {
      busy.set(false);
    }
  }
  useEffect(() => {
    const result = load();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  return {
    ...inputProps,
    session: session.getSnapshot(),
    canPublish,
    applicationStatuses,
    state: state.getSnapshot(),
    busy: busy.getSnapshot(),
    error: error.getSnapshot(),
    message: message.getSnapshot(),
    form: form.getSnapshot(),
    editable: getEditable(),
    load,
    submit,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateForm: form.edit
  };
}
export default React.forwardRef(function BrokerApplicationView(props, ref) {
  const view = useBrokerApplicationViewState(props, ref);
  return <><div data-ui-view="BrokerApplicationView" {...view.rootAttributes} className={classNames(["sp-container max-w-4xl py-8 sm:py-12", view.rootAttributes.className])}>
      <SiteLink to="/account" className="text-sm underline">
        {"← Tài khoản"}
      </SiteLink>
      <h1 className="mt-5 text-3xl font-semibold">
        {"Đăng ký quyền đăng tin"}
      </h1>
      <p className="mt-3 text-sm leading-6 text-brand-muted">
        {"Đăng ký miễn phí bằng hồ sơ liên hệ. Không gửi căn cước hoặc giấy tờ nhạy cảm trong nội dung yêu cầu. Hồ sơ này chỉ bạn và quản trị viên được phép xem."}
      </p>
      {view.busy ? <p role="status" className="mt-5">
          {"Đang xử lý…"}
        </p> : null}
      {view.error ? <p role="alert" className="mt-5 rounded-panel bg-[var(--ui-error-bg)] p-4 text-sm text-[var(--ui-error-text)]">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}
        </p> : null}
      {view.message ? <p role="status" className="mt-5 rounded-panel bg-[var(--ui-success-bg)] p-4 text-sm text-[var(--ui-success-text)]">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.message)}
        </p> : null}
      <button className="sp-button sp-button-secondary mt-5" type="button" disabled={view.busy} onClick={$event => {
        return view.load?.($event);
      }}>
        {"Tải lại trạng thái"}
      </button>
      {view.state ? <section className="mt-6 rounded-panel border border-brand-line bg-brand-card p-5 sm:p-7">
          <h2 className="text-lg font-semibold">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.applicationStatuses[view.state.status] || view.state.status)}
          </h2>
          {view.state.legacyPublisher ? <p className="mt-2 text-sm text-brand-muted">
              {"Quyền hiện có của tài khoản được giữ nguyên."}
            </p> : null}
          {view.state.application?.reviewReason ? <p className="mt-3 whitespace-pre-wrap rounded-control bg-brand-surface p-4 text-sm leading-6">
              {"Phản hồi của quản trị viên: "}
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.application.reviewReason)}
            </p> : null}
          {view.state.status === "PENDING" ? <p className="mt-3 text-sm leading-6">
              {"Bạn chưa có quyền tạo tin. Có thể quay lại kiểm tra sau; không cần gửi lại yêu cầu."}
            </p> : null}
          {view.state.status === "SUSPENDED" ? <p className="mt-3 text-sm leading-6">
              {"Quyền đăng tin đang tạm ngưng. Liên hệ quản trị viên để xem xét khôi phục, không gửi yêu cầu mới."}
            </p> : null}
          {view.canPublish(view.session.user) ? <div className="mt-5 flex flex-wrap gap-3">
              <SiteLink to="/post" className="sp-button sp-button-primary">
                {"Đăng tin mới"}
              </SiteLink>
              <SiteLink to="/my-listing" className="sp-button sp-button-secondary">
                {"Quản lý tin đăng"}
              </SiteLink>
            </div> : null}
          {view.editable ? <form className="mt-6 grid gap-5" onSubmit={$event => {
          $event.preventDefault();
          return view.submit?.($event);
        }}>
              <fieldset disabled={view.busy} className="grid gap-5 sm:grid-cols-2">
                <label className="sp-field">
                  {"Loại người đăng"}
                  <select name="applicantType" className="sp-input" required={true} value={view.form.applicantType ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.applicantType = $value);
              })(event.target.value)}>
                    <option value="OWNER">
                      {"Chủ nhà"}
                    </option>
                    <option value="AGENT">
                      {"Môi giới"}
                    </option>
                  </select>
                </label>
                <label className="sp-field">
                  {"Họ tên / tên đơn vị"}
                  <input name="displayName" className="sp-input" required={true} maxLength="150" autoComplete="name" value={view.form.displayName ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.displayName = $value);
              })(event.target.value)} />
                </label>
                <label className="sp-field">
                  {"Số điện thoại liên hệ"}
                  <input name="contactPhone" className="sp-input" required={true} minLength="8" maxLength="30" type="tel" autoComplete="tel" pattern="\\+?[0-9][0-9 \\(\\)\\-]{6,28}[0-9]" value={view.form.contactPhone ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.contactPhone = $value);
              })(event.target.value)} />
                </label>
                <label className="sp-field">
                  {"Khu vực hoạt động"}
                  <input name="operatingArea" className="sp-input" required={true} maxLength="200" placeholder="Ví dụ: Hải Châu, Đà Nẵng" value={view.form.operatingArea ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.operatingArea = $value);
              })(event.target.value)} />
                </label>
                <label className="sp-field sm:col-span-2">
                  {"Nội dung yêu cầu"}
                  <textarea name="requestMessage" className="sp-input min-h-32" required={true} maxLength="2000" rows="4" value={view.form.requestMessage ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.requestMessage = $value);
              })(event.target.value)} />
                </label>
                <label className="flex items-start gap-3 text-sm leading-6 sm:col-span-2">
                  <input name="responsibilityAccepted" required={true} type="checkbox" className="mt-1" checked={Array.isArray(view.form.responsibilityAccepted) ? view.form.responsibilityAccepted.includes("on") : !!view.form.responsibilityAccepted} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.responsibilityAccepted = $value);
              })(Array.isArray(view.form.responsibilityAccepted) ? event.target.checked ? [...view.form.responsibilityAccepted, "on"] : view.form.responsibilityAccepted.filter(item => item !== "on") : event.target.checked)} />
                  {"Tôi chịu trách nhiệm về tính chính xác và quyền sử dụng thông tin, hình ảnh trong các tin đăng."}
                </label>
              </fieldset>
              <button className="sp-button sp-button-primary justify-self-start" type="submit" disabled={view.busy}>
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.status === "NOT_REQUESTED" ? "Gửi yêu cầu" : "Gửi lại hồ sơ")}
              </button>
            </form> : view.state.application ? <dl className="mt-5 grid gap-3 text-sm">
              <div>
                <dt className="text-brand-muted">
                  {"Người đăng"}
                </dt>
                <dd>
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.application.displayName)}
                  {" · "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.application.applicantType === "OWNER" ? "Chủ nhà" : "Môi giới")}
                </dd>
              </div>
              <div>
                <dt className="text-brand-muted">
                  {"Liên hệ / khu vực"}
                </dt>
                <dd>
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.application.contactPhone)}
                  {" · "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.application.operatingArea)}
                </dd>
              </div>
              <div>
                <dt className="text-brand-muted">
                  {"Nội dung"}
                </dt>
                <dd className="whitespace-pre-wrap">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.application.requestMessage)}
                </dd>
              </div>
            </dl> : null}
        </section> : null}
    </div></>;
});
