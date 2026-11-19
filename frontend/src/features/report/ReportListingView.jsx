import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useEffect, useRef } from "react";
import { useAppNavigation, useRouteState } from "../../app/navigation.jsx";
import { api, session, errorText } from "../auth/api.js";
import { adapt } from "../property/listingPresentation.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import PrivateImage from "../../shared/components/PrivateImage.jsx";
function useReportListingViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const route = useRouteState(),
    router = useAppNavigation(),
    [state] = useState(() => createStateStore({
      busy: false,
      error: "",
      notice: ""
    })),
    [property] = useState(() => createStateStore(null)),
    getListing = () => adapt(property.getSnapshot()),
    reasons = ["Nghi ngờ ảnh giả mạo", "Thông tin sai lệch", "Nghi ngờ lừa đảo", "Tin đăng trùng lặp", "BĐS đã bán / đã cho thuê", "Lý do khác"],
    codes = ["FAKE_IMAGES", "INACCURATE_INFORMATION", "SUSPECTED_SCAM", "DUPLICATE", "UNAVAILABLE", "OTHER"],
    [selectedReason] = useState(() => createStateStore("")),
    [description] = useState(() => createStateStore("")),
    [email] = useState(() => createStateStore(session.getSnapshot().user?.email || "")),
    [confirmed] = useState(() => createStateStore(false)),
    [selectedFile] = useState(() => createStateStore(null)),
    [isSubmitted] = useState(() => createStateStore(false)),
    [created] = useState(() => createStateStore(null));
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  useSyncExternalStore(created.subscribe, created.getSnapshot);
  useSyncExternalStore(isSubmitted.subscribe, isSubmitted.getSnapshot);
  useSyncExternalStore(selectedFile.subscribe, selectedFile.getSnapshot);
  useSyncExternalStore(confirmed.subscribe, confirmed.getSnapshot);
  useSyncExternalStore(email.subscribe, email.getSnapshot);
  useSyncExternalStore(description.subscribe, description.getSnapshot);
  useSyncExternalStore(selectedReason.subscribe, selectedReason.getSnapshot);
  useSyncExternalStore(property.subscribe, property.getSnapshot);
  useSyncExternalStore(state.subscribe, state.getSnapshot);
  const selectReason = r => selectedReason.set(r),
    removeFile = () => selectedFile.set(null),
    goBack = () => _routerLatest.current.push("/listing/" + _routeLatest.current.params.id),
    goHome = () => _routerLatest.current.push("/home"),
    goAccount = () => _routerLatest.current.push("/account");
  useEffect(() => {
    const result = (async () => {
      try {
        property.set(await api("/properties/" + _routeLatest.current.params.id));
      } catch (e) {
        state.edit(draftValue => draftValue["error"] = errorText(e));
      }
    })();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  function handleFile(event) {
    selectedFile.set(event.target.files?.[0] || null);
  }
  async function submitReport() {
    if (state.getSnapshot().busy) return;
    state.edit(draftValue => draftValue["error"] = "");
    if (!selectedReason.getSnapshot() || !description.getSnapshot().trim() || !confirmed.getSnapshot()) {
      state.edit(draftValue => draftValue["error"] = "Vui lòng chọn lý do, mô tả và xác nhận thông tin.");
      return;
    }
    state.edit(draftValue => draftValue["busy"] = true);
    try {
      if (!created.getSnapshot()) created.set(await api("/properties/" + _routeLatest.current.params.id + "/reports", {
        method: "POST",
        body: {
          reasonCode: codes[reasons.indexOf(selectedReason.getSnapshot())],
          description: description.getSnapshot(),
          contactEmail: email.getSnapshot() || null
        }
      }));
      if (selectedFile.getSnapshot()) {
        const data = new FormData();
        data.append("file", selectedFile.getSnapshot());
        await api("/reports/" + created.getSnapshot().id + "/attachments", {
          method: "POST",
          body: data
        });
      }
      isSubmitted.set(true);
    } catch (e) {
      state.edit(draftValue => draftValue["error"] = errorText(e));
    } finally {
      state.edit(draftValue => draftValue["busy"] = false);
    }
  }
  return {
    ...inputProps,
    state: state.getSnapshot(),
    listing: getListing(),
    reasons,
    selectedReason: selectedReason.getSnapshot(),
    description: description.getSnapshot(),
    email: email.getSnapshot(),
    confirmed: confirmed.getSnapshot(),
    selectedFile: selectedFile.getSnapshot(),
    isSubmitted: isSubmitted.getSnapshot(),
    selectReason,
    removeFile,
    goBack,
    handleFile,
    submitReport,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateDescriptionValue: description.set,
    updateEmailValue: email.set,
    updateConfirmedValue: confirmed.set
  };
}
export default React.forwardRef(function ReportListingView(props, ref) {
  const view = useReportListingViewState(props, ref);
  return <><div data-ui-view="ReportListingView" {...view.rootAttributes} className={classNames(["min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)]", view.rootAttributes.className])}>
      <div className="max-w-[1180px] mx-auto px-6 md:px-10 py-10">
        <ResourceState state={view.state} />
        <button onClick={$event => {
          return view.goBack?.($event);
        }} className="sm:hidden text-xs text-brand-muted mb-6">
          {" ‹ Quay lại tin đăng "}
        </button>
        <section className="mb-8">
          <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-[var(--ui-accent)]">
            {" Báo cáo tin đăng "}
          </h1>
          <p className="text-sm text-brand-muted mt-2">
            {" Cho chúng tôi biết vấn đề bạn gặp phải với tin đăng này. "}
          </p>
        </section>
        {view.isSubmitted ? <section className="bg-brand-card rounded-[26px] p-8 md:p-12 shadow-sm text-center max-w-[720px] mx-auto">
            <div className="w-16 h-16 rounded-full bg-[var(--ui-surface)] text-[var(--ui-accent)] flex items-center justify-center text-2xl mx-auto">
              {" ✓ "}
            </div>
            <h2 className="text-2xl font-semibold mt-6">
              {" Báo cáo đã được gửi "}
            </h2>
            <p className="text-sm text-brand-muted mt-3 max-w-[500px] mx-auto leading-6">
              {" Cảm ơn bạn đã giúp SmartProp xây dựng môi trường bất động sản an toàn hơn. Đội ngũ quản trị sẽ xem xét báo cáo của bạn. "}
            </p>
            <div className="mt-7 bg-[var(--ui-surface)] rounded-2xl px-5 py-4 text-sm">
              {" Thời gian xem xét dự kiến: "}
              <strong>{"24–48 giờ"}</strong>
            </div>
            <button onClick={$event => {
            return view.goBack?.($event);
          }} className="mt-7 px-7 py-3 rounded-full bg-[var(--ui-soft)] text-brand-navy text-sm">
              {" Quay lại tin đăng "}
            </button>
          </section> : <div className="grid grid-cols-1 lg:grid-cols-[1fr_310px] gap-6 items-start">
            <div className="space-y-5">
              <section className="bg-brand-card rounded-[24px] p-6 md:p-7 shadow-sm">
                <h2 className="text-sm font-semibold mb-4">
                  {" Tin đăng được báo cáo "}
                </h2>
                <div className="flex items-center gap-4 bg-[var(--ui-surface)] rounded-[18px] p-3">
                  <div className="w-[105px] h-[78px] rounded-[14px] overflow-hidden bg-[var(--ui-soft)] shrink-0">
                    <PrivateImage src={view.listing.image} alt={view.listing.title} className="w-full h-full object-cover" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-[var(--ui-accent)] truncate">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.listing.title)}
                    </h3>
                    <p className="text-[12px] text-brand-muted mt-1">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.listing.location)}
                    </p>
                    <p className="text-sm font-semibold text-[var(--ui-accent)] mt-2">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.listing.price)}
                    </p>
                  </div>
                </div>
              </section>
              <section className="bg-brand-card rounded-[24px] p-6 md:p-7 shadow-sm">
                <h2 className="text-base font-semibold">
                  {" Lý do báo cáo "}
                </h2>
                <p className="text-xs text-brand-muted mt-1.5">
                  {" Chọn lý do phù hợp nhất với vấn đề bạn phát hiện. "}
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-5">
                  {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.reasons, reason => <button key={reason} type="button" onClick={$event => {
                  view.selectReason(reason);
                }} className={classNames(["relative text-left px-4 py-4 rounded-[16px] border text-xs font-medium transition", view.selectedReason === reason ? "border-[var(--ui-border)] bg-[var(--ui-surface)] text-[var(--ui-accent)] ring-1 ring-[var(--ui-border)]" : "border-brand-line bg-brand-card text-brand-muted hover:border-[var(--ui-border)]/40"])}>
                      <span className="inline-flex items-center gap-3">
                        <span className={classNames(["w-4 h-4 rounded-full border flex items-center justify-center", view.selectedReason === reason ? "border-[var(--ui-border)]" : "border-brand-line"])}>
                          {view.selectedReason === reason ? <span className="w-2 h-2 rounded-full bg-[var(--ui-soft)]" /> : null}
                        </span>{" "}
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(reason)}
                      </span>
                    </button>)}
                </div>
                <div className="mt-7">
                  <label className="block text-sm font-semibold mb-2">
                    {" Mô tả chi tiết "}
                  </label>
                  <textarea rows="6" maxLength="1000" placeholder="Mô tả vấn đề bạn phát hiện..." className="w-full resize-none rounded-[16px] border border-brand-line px-4 py-4 text-xs text-brand-muted leading-6 outline-none focus:border-[var(--ui-border)] focus:ring-1 focus:ring-[var(--ui-border)]" value={view.description ?? ""} onChange={event => ($value => {
                  view.updateDescriptionValue($value);
                })(event.target.value)} />
                  <div className="text-right text-xs text-brand-muted mt-1">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.description.length)}
                    {"/1000 "}
                  </div>
                </div>
                <div className="mt-5">
                  <label className="block text-sm font-semibold mb-2">
                    {" Đính kèm minh chứng "}
                    <span className="font-normal text-brand-muted">
                      {" (không bắt buộc) "}
                    </span>
                  </label>
                  <label className="relative flex flex-col items-center justify-center min-h-[135px] border border-dashed border-brand-line rounded-[16px] bg-[var(--ui-surface)] cursor-pointer hover:border-[var(--ui-border)]/50 transition">
                    <input type="file" accept=".jpg,.jpeg,.png,.pdf" className="hidden" onChange={$event => {
                    return view.handleFile?.($event);
                  }} />
                    {!view.selectedFile ? <React.Fragment>
                        <div className="text-xl">
                          {" 📎 "}
                        </div>
                        <p className="text-xs text-brand-muted text-center mt-2 px-5">
                          {" Kéo thả ảnh chụp màn hình hoặc tệp vào đây, hoặc bấm để chọn "}
                        </p>
                        <p className="text-xs text-brand-muted mt-1">
                          {" Hỗ trợ JPG, PNG, PDF · tối đa 10MB "}
                        </p>
                      </React.Fragment> : <React.Fragment>
                        <div className="w-10 h-10 rounded-full bg-[var(--ui-surface)] text-[var(--ui-accent)] flex items-center justify-center">
                          {" ✓ "}
                        </div>
                        <p className="text-xs font-medium text-[var(--ui-accent)] mt-2">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedFile.name)}
                        </p>
                        <p className="text-xs text-brand-muted mt-1">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))((view.selectedFile.size / 1024 / 1024).toFixed(2))}
                          {" MB "}
                        </p>
                      </React.Fragment>}
                  </label>
                  {view.selectedFile ? <button type="button" onClick={$event => {
                  return view.removeFile?.($event);
                }} className="text-xs text-[var(--ui-error-text)] mt-2 hover:underline">
                      {" Xoá tệp "}
                    </button> : null}
                </div>
                <div className="mt-6">
                  <label className="block text-sm font-semibold mb-2">
                    {" Email liên hệ "}
                  </label>
                  <input type="email" placeholder="example@gmail.com" className="w-full h-12 rounded-[14px] border border-brand-line px-4 text-xs outline-none focus:border-[var(--ui-border)] focus:ring-1 focus:ring-[var(--ui-border)]" value={view.email ?? ""} onChange={event => ($value => {
                  view.updateEmailValue($value);
                })(event.target.value)} />
                  <p className="text-xs text-brand-muted mt-2">
                    {" Chúng tôi sẽ gửi kết quả xử lý báo cáo tới email này. "}
                  </p>
                </div>
                <label className="flex items-start gap-3 mt-6 cursor-pointer">
                  <input type="checkbox" className="mt-0.5 w-4 h-4 accent-[#183e54]" checked={Array.isArray(view.confirmed) ? view.confirmed.includes("on") : !!view.confirmed} onChange={event => ($value => {
                  view.updateConfirmedValue($value);
                })(Array.isArray(view.confirmed) ? event.target.checked ? [...view.confirmed, "on"] : view.confirmed.filter(item => item !== "on") : event.target.checked)} />
                  <span className="text-[12px] text-brand-muted leading-5">
                    {" Tôi xác nhận thông tin báo cáo trên là đúng sự thật. Báo cáo sai sự thật có thể ảnh hưởng đến tài khoản của tôi. "}
                  </span>
                </label>
                <div className="flex flex-col-reverse sm:flex-row gap-3 mt-7">
                  <button type="button" onClick={$event => {
                  return view.submitReport?.($event);
                }} className="sm:flex-1 h-12 rounded-full bg-[var(--ui-soft)] text-brand-navy text-xs font-medium hover:opacity-90 transition">
                    {" Gửi báo cáo "}
                  </button>
                  <button type="button" onClick={$event => {
                  return view.goBack?.($event);
                }} className="sm:w-[130px] h-12 rounded-full bg-brand-card border border-brand-line text-brand-muted text-xs hover:bg-brand-card transition">
                    {" Huỷ "}
                  </button>
                </div>
              </section>
            </div>
            <aside className="space-y-4 lg:sticky lg:top-5">
              <section className="bg-[var(--ui-soft)] text-brand-navy rounded-[24px] p-6 shadow-sm">
                <p className="text-xs text-brand-navy/40 tracking-[0.18em] font-semibold">
                  {" SAU KHI BẠN GỬI BÁO CÁO "}
                </p>
                <h2 className="text-lg font-semibold mt-2">
                  {" Chuyện gì xảy ra tiếp theo? "}
                </h2>
                <div className="space-y-5 mt-6">
                  <div className="flex items-start gap-3">
                    <div className="w-7 h-7 rounded-full bg-brand-card/10 border border-brand-line/10 flex items-center justify-center text-xs shrink-0">
                      {" 1 "}
                    </div>
                    <p className="text-[12px] text-brand-navy/65 leading-5 pt-1">
                      {" Đội ngũ quản trị xem xét trong vòng 24–48 giờ. "}
                    </p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-7 h-7 rounded-full bg-brand-card/10 border border-brand-line/10 flex items-center justify-center text-xs shrink-0">
                      {" 2 "}
                    </div>
                    <p className="text-[12px] text-brand-navy/65 leading-5 pt-1">
                      {" Tin đăng có thể bị tạm ẩn nếu vi phạm rõ ràng. "}
                    </p>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-7 h-7 rounded-full bg-brand-card/10 border border-brand-line/10 flex items-center justify-center text-xs shrink-0">
                      {" 3 "}
                    </div>
                    <p className="text-[12px] text-brand-navy/65 leading-5 pt-1">
                      {' Bạn nhận kết quả qua email và tại trang "Báo cáo của tôi". '}
                    </p>
                  </div>
                </div>
              </section>
              <section className="bg-brand-card rounded-[24px] p-6 shadow-sm">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-[var(--ui-surface)] flex items-center justify-center">
                    {" 🔒 "}
                  </div>
                  <h3 className="text-sm font-semibold">
                    {" Quyền riêng tư "}
                  </h3>
                </div>
                <p className="text-[12px] text-brand-muted leading-5 mt-3">
                  {" Danh tính người báo cáo được giữ kín và không chia sẻ với người đăng tin. "}
                </p>
              </section>
            </aside>
          </div>}
      </div>
    </div></>;
});
