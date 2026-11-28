import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useEffect, useRef } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { useAppNavigation } from "../../app/navigation.jsx";
import { api, loadProfile, logout as revokeSession, clearSession, session, errorText, getGoogleLinkScope, assertGoogleLinkScope, googleLinkStatus, startGoogleLink, refreshEnabled } from "../auth/api.js";
import BrokerApplicationCard from "../broker/BrokerApplicationCard.jsx";
import ValuationHistory from "../prediction/ValuationHistory.jsx";
import UserAvatar from "../../shared/components/UserAvatar.jsx";
import AvatarEditor from "./AvatarEditor.jsx";
import AppIcon from "../../shared/components/AppIcon.jsx";
import "./AccountView.css";
import LifestyleFields, { emptyLifestyle } from "./LifestyleFields.jsx";
function useAccountViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const auth = useSyncExternalStore(session.subscribe, session.getSnapshot);
  const linkScope = getGoogleLinkScope(auth);
  const router = useAppNavigation(),
    [form] = useState(() => createStateStore({
      fullName: "",
      email: "",
      phone: "",
      district: "",
      address: ""
    }));
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  useSyncExternalStore(form.subscribe, form.getSnapshot);
  const [prefs] = useState(() => createStateStore({
      matchingListings: false,
      brokerMessages: false,
      statusUpdates: false
    })),
    [securityTab] = useState(() => createStateStore("password"));
  useSyncExternalStore(securityTab.subscribe, securityTab.getSnapshot);
  useSyncExternalStore(prefs.subscribe, prefs.getSnapshot);
  const [currentPassword] = useState(() => createStateStore("")),
    [googleLinkPassword] = useState(() => createStateStore("")),
    [googleLinked] = useState(() => createStateStore(null)),
    [googleLinkAvailable] = useState(() => createStateStore(false)),
    [googleLinkBusy] = useState(() => createStateStore(false)),
    [googleLinkError] = useState(() => createStateStore("")),
    [newPassword] = useState(() => createStateStore("")),
    [confirmPassword] = useState(() => createStateStore("")),
    [showPassword] = useState(() => createStateStore(false));
  useSyncExternalStore(showPassword.subscribe, showPassword.getSnapshot);
  useSyncExternalStore(confirmPassword.subscribe, confirmPassword.getSnapshot);
  useSyncExternalStore(newPassword.subscribe, newPassword.getSnapshot);
  useSyncExternalStore(currentPassword.subscribe, currentPassword.getSnapshot);
  useSyncExternalStore(googleLinkPassword.subscribe, googleLinkPassword.getSnapshot);
  useSyncExternalStore(googleLinked.subscribe, googleLinked.getSnapshot);
  useSyncExternalStore(googleLinkAvailable.subscribe, googleLinkAvailable.getSnapshot);
  useSyncExternalStore(googleLinkBusy.subscribe, googleLinkBusy.getSnapshot);
  useSyncExternalStore(googleLinkError.subscribe, googleLinkError.getSnapshot);
  const [busy] = useState(() => createStateStore(false)),
    [loading] = useState(() => createStateStore(true)),
    [loaded] = useState(() => createStateStore(false)),
    [preferencesLoaded] = useState(() => createStateStore(false)),
    [message] = useState(() => createStateStore("")),
    [error] = useState(() => createStateStore("")),
    [prefsError] = useState(() => createStateStore("")),
    [nameInput] = useState(() => createStateStore(null));
  useSyncExternalStore(nameInput.subscribe, nameInput.getSnapshot);
  useSyncExternalStore(prefsError.subscribe, prefsError.getSnapshot);
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(message.subscribe, message.getSnapshot);
  useSyncExternalStore(preferencesLoaded.subscribe, preferencesLoaded.getSnapshot);
  useSyncExternalStore(loaded.subscribe, loaded.getSnapshot);
  useSyncExternalStore(loading.subscribe, loading.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  const getRoleLabel = () => ({
    BUYER: "Người mua / người thuê",
    BROKER: "Chủ nhà / môi giới",
    ADMIN: "Quản trị viên"
  })[session.getSnapshot().user?.role] || "Thành viên";
  const getStatusLabel = () => ({
    ACTIVE: "Đang hoạt động",
    LOCKED: "Đã khóa"
  })[session.getSnapshot().user?.status] || "Đang kiểm tra";
  const getJoined = () => session.getSnapshot().user?.createdAt ? new Date(session.getSnapshot().user.createdAt).toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "long",
    year: "numeric"
  }) : "Chưa có thông tin";
  const tools = [{
    to: "/favorites",
    icon: "heart",
    title: "Tin đã lưu",
    text: "Những không gian bạn quan tâm"
  }, {
    to: "/account/reports",
    icon: "report",
    title: "Báo cáo của tôi",
    text: "Theo dõi phản hồi và xử lý"
  }, {
    to: "/account/notifications",
    icon: "bell",
    title: "Thông báo",
    text: "Cập nhật hoạt động tài khoản"
  }, {
    to: "/account/messages",
    icon: "messages",
    title: "Tin nhắn",
    text: "Tiếp tục những cuộc trò chuyện"
  }];
  const preferenceLabels = [{
    key: "matchingListings",
    title: "Tin phù hợp với bạn",
    text: "Lưu tùy chọn nhận thông báo tin đăng phù hợp."
  }, {
    key: "brokerMessages",
    title: "Tin nhắn liên quan",
    text: "Lưu tùy chọn thông báo khi có trao đổi."
  }, {
    key: "statusUpdates",
    title: "Trạng thái tin và báo cáo",
    text: "Lưu tùy chọn cập nhật xử lý từ hệ thống."
  }];
  function fill(user) {
    form.set({
      fullName: user.fullName,
      email: user.email,
      phone: user.phone || "",
      district: user.district || "",
      address: user.address || "",
      advisorPreferences: {
        ...emptyLifestyle(),
        ...user.advisorPreferences
      }
    });
  }
  async function load() {
    loading.set(true);
    error.set("");
    try {
      const user = await loadProfile();
      fill(user);
      loaded.set(true);
      await loadPreferences();
    } catch (e) {
      error.set(errorText(e));
    } finally {
      loading.set(false);
    }
  }
  async function loadPreferences() {
    prefsError.set("");
    try {
      prefs.set(await api("/users/me/notification-preferences"));
      preferencesLoaded.set(true);
    } catch (e) {
      preferencesLoaded.set(false);
      prefsError.set(errorText(e));
    }
  }
  async function saveProfile() {
    if (busy.getSnapshot() || !loaded.getSnapshot()) return;
    busy.set(true);
    message.set(error.set(""));
    try {
      const {
        email,
        ...body
      } = form.getSnapshot();
      const user = await api("/users/me", {
        method: "PATCH",
        body
      });
      session.edit(draftValue => draftValue["user"] = user);
      fill(user);
      message.set("Thông tin cá nhân đã được cập nhật.");
    } catch (e) {
      error.set(errorText(e));
    } finally {
      busy.set(false);
    }
  }
  function resetProfile() {
    if (session.getSnapshot().user) fill(session.getSnapshot().user);
    message.set(error.set(""));
  }
  async function savePreferences() {
    if (busy.getSnapshot() || !preferencesLoaded.getSnapshot()) return;
    busy.set(true);
    prefsError.set("");
    message.set("");
    try {
      await api("/users/me/notification-preferences", {
        method: "PATCH",
        body: prefs.getSnapshot()
      });
      message.set("Đã lưu tùy chọn thông báo.");
    } catch (e) {
      prefsError.set(errorText(e));
    } finally {
      busy.set(false);
    }
  }
  async function changePassword() {
    if (busy.getSnapshot()) return;
    message.set(error.set(""));
    if (newPassword.getSnapshot() !== confirmPassword.getSnapshot()) {
      error.set("Mật khẩu xác nhận không khớp.");
      return;
    }
    if (new TextEncoder().encode(newPassword.getSnapshot()).length > 72) {
      error.set("Mật khẩu tối đa 72 byte UTF-8. Vui lòng dùng mật khẩu ngắn hơn.");
      return;
    }
    busy.set(true);
    try {
      await api("/users/me/password", {
        method: "PUT",
        body: {
          currentPassword: currentPassword.getSnapshot(),
          newPassword: newPassword.getSnapshot()
        }
      });
      currentPassword.set(newPassword.set(confirmPassword.set("")));
      clearSession();
      await _routerLatest.current.replace({
        path: "/login",
        query: {
          reason: "password-changed"
        }
      });
    } catch (e) {
      error.set(errorText(e));
    } finally {
      busy.set(false);
    }
  }
  async function linkGoogle() {
    if (linkScope == null || busy.getSnapshot() || googleLinkBusy.getSnapshot() || googleLinked.getSnapshot() === true || !googleLinkAvailable.getSnapshot()) return;
    googleLinkError.set("");
    if (!googleLinkPassword.getSnapshot()) {
      googleLinkError.set("Vui lòng nhập mật khẩu hiện tại để xác nhận liên kết.");
      return;
    }
    googleLinkBusy.set(true);
    const password = googleLinkPassword.getSnapshot();
    googleLinkPassword.set("");
    try {
      const result = await startGoogleLink(password, linkScope);
      assertGoogleLinkScope(linkScope);
      if (result?.authorizationPath !== "/auth/oauth2/link/authorize/google") {
        throw Error("Không thể mở bước xác thực Google.");
      }
      const base = (import.meta.env?.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");
      window.location.assign(base + result.authorizationPath);
    } catch (linkError) {
      if (linkScope !== getGoogleLinkScope()) return;
      googleLinkError.set(errorText(linkError));
      googleLinkBusy.set(false);
    }
  }
  function editProfile() {
    document.getElementById("personal-information")?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",
      block: "start"
    });
    nameInput.getSnapshot()?.focus({
      preventScroll: true
    });
  }
  async function signOut() {
    if (busy.getSnapshot()) return;
    busy.set(true);
    try {
      await revokeSession();
      await _routerLatest.current.replace("/login");
    } catch (e) {
      error.set(errorText(e));
    } finally {
      busy.set(false);
    }
  }
  useEffect(() => {
    if (linkScope == null) return;
    let active = true;
    googleLinkStatus(linkScope).then(status => {
      if (!active || linkScope !== getGoogleLinkScope()) return;
      googleLinked.set(status.linked === true);
      googleLinkAvailable.set(status.available === true && refreshEnabled);
    }).catch(statusError => {
      if (!active || linkScope !== getGoogleLinkScope()) return;
      googleLinkError.set(errorText(statusError));
    });
    return () => { active = false; };
  }, [linkScope]);
  useEffect(() => {
    const result = load();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  return {
    ...inputProps,
    session: session.getSnapshot(),
    form: form.getSnapshot(),
    prefs: prefs.getSnapshot(),
    securityTab: securityTab.getSnapshot(),
    currentPassword: currentPassword.getSnapshot(),
    googleLinkPassword: googleLinkPassword.getSnapshot(),
    googleLinked: googleLinked.getSnapshot(),
    googleLinkAvailable: googleLinkAvailable.getSnapshot(),
    googleLinkBusy: googleLinkBusy.getSnapshot(),
    googleLinkError: googleLinkError.getSnapshot(),
    newPassword: newPassword.getSnapshot(),
    confirmPassword: confirmPassword.getSnapshot(),
    showPassword: showPassword.getSnapshot(),
    busy: busy.getSnapshot(),
    loading: loading.getSnapshot(),
    loaded: loaded.getSnapshot(),
    preferencesLoaded: preferencesLoaded.getSnapshot(),
    message: message.getSnapshot(),
    error: error.getSnapshot(),
    prefsError: prefsError.getSnapshot(),
    roleLabel: getRoleLabel(),
    statusLabel: getStatusLabel(),
    joined: getJoined(),
    tools,
    preferenceLabels,
    load,
    loadPreferences,
    saveProfile,
    resetProfile,
    savePreferences,
    changePassword,
    linkGoogle,
    editProfile,
    signOut,
    updateNameInputValue: nameInput.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateForm: form.edit,
    updateSecurityTabValue: securityTab.set,
    updateCurrentPasswordValue: currentPassword.set,
    updateGoogleLinkPasswordValue: googleLinkPassword.set,
    updateNewPasswordValue: newPassword.set,
    updateConfirmPasswordValue: confirmPassword.set,
    updateShowPasswordValue: showPassword.set,
    updatePrefs: prefs.edit
  };
}
export default React.forwardRef(function AccountView(props, ref) {
  const auth = useSyncExternalStore(session.subscribe, session.getSnapshot);
  return <AccountContent key={getGoogleLinkScope(auth) ?? 'no-session'} {...props} ref={ref} />;
});

const AccountContent = React.forwardRef(function AccountContent(props, ref) {
  const view = useAccountViewState(props, ref);
  return <><div data-ui-view="AccountView" aria-busy={view.loading} data-sp-c8811dc0="" {...view.rootAttributes} className={classNames(["account-page sp-container py-8 sm:py-12", view.rootAttributes.className])}>
      <div className="page-intro-banner mb-7" data-sp-c8811dc0="">
        <p className="account-eyebrow" data-sp-c8811dc0="">
          {"KHÔNG GIAN CỦA BẠN"}
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl" data-sp-c8811dc0="">
          {"Hồ sơ cá nhân"}
        </h1>
        <p className="mt-3 text-[15px] leading-7 text-brand-muted" data-sp-c8811dc0="">
          {"Quản lý thông tin, bảo mật và những điều bạn quan tâm."}
        </p>
      </div>
      {view.loading ? <p role="status" className="account-notice mb-5" data-sp-c8811dc0="">
          {"Đang tải thông tin tài khoản…"}
        </p> : null}
      {view.error ? <div role="alert" className="account-notice account-error mb-5" data-sp-c8811dc0="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}{" "}
          {!view.loaded ? <button type="button" className="underline" onClick={$event => {
          return view.load?.($event);
        }} data-sp-c8811dc0="">
              {"Thử lại"}
            </button> : null}
        </div> : null}
      {view.message ? <p role="status" className="account-notice account-success mb-5" data-sp-c8811dc0="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.message)}
        </p> : null}
      <section data-profile-overview="" className="profile-overview account-card mb-6" aria-labelledby="profile-name" data-sp-c8811dc0="">
        <div className="flex min-w-0 flex-wrap items-center gap-6" data-sp-c8811dc0="">
          <div className="relative" data-sp-c8811dc0="">
            <UserAvatar name={view.session.user?.fullName} size={96} data-sp-c8811dc0="" />
          </div>
          <div className="min-w-0 flex-1" data-sp-c8811dc0="">
            <p className="account-eyebrow" data-sp-c8811dc0="">
              {"SMARTPROP · TÀI KHOẢN CÁ NHÂN"}
            </p>
            <h2 id="profile-name" className="mt-2 break-words text-2xl font-semibold" data-sp-c8811dc0="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.session.user?.fullName || "Tài khoản SmartProp")}
            </h2>
            <p className="mt-2 break-all text-[15px] text-brand-muted" data-sp-c8811dc0="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.session.user?.email)}
            </p>
            <div className="mt-4 flex flex-wrap gap-2" data-sp-c8811dc0="">
              <span className="account-chip" data-sp-c8811dc0="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.roleLabel)}
              </span>
              <span className={classNames(["account-chip", view.session.user?.status === "ACTIVE" ? "text-[var(--ui-success-text)]" : "text-[var(--ui-error-text)]"])} data-sp-c8811dc0="">
                {"● "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.statusLabel)}
              </span>
            </div>
            <p className="mt-3 text-[13px] text-brand-muted" data-sp-c8811dc0="">
              {"Tham gia từ "}
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.joined)}
            </p>
          </div>
        </div>
        <div className="profile-actions" data-sp-c8811dc0="">
          <button type="button" className="sp-button sp-button-primary" disabled={!view.loaded || view.busy} onClick={$event => {
            return view.editProfile?.($event);
          }} data-sp-c8811dc0="">
            <AppIcon name="edit" data-sp-c8811dc0="" />
            {"Chỉnh sửa hồ sơ"}
          </button>
          <AvatarEditor data-sp-c8811dc0="" />
        </div>
      </section>
      <section id="personal-information" className="account-card mb-6" aria-labelledby="personal-heading" data-sp-c8811dc0="">
        <div className="account-section-heading" data-sp-c8811dc0="">
          <span className="account-section-icon" data-sp-c8811dc0="">
            <AppIcon name="user" data-sp-c8811dc0="" />
          </span>
          <div data-sp-c8811dc0="">
            <h2 id="personal-heading" data-sp-c8811dc0="">
              {"Thông tin cá nhân"}
            </h2>
            <p data-sp-c8811dc0="">
              {"Giữ thông tin liên hệ của bạn luôn chính xác."}
            </p>
          </div>
        </div>
        <form className="grid gap-5 sm:grid-cols-2" onSubmit={$event => {
          $event.preventDefault();
          return view.saveProfile?.($event);
        }} data-sp-c8811dc0="">
          <label className="account-field" data-sp-c8811dc0="">
            {"Họ và tên"}
            <input ref={view.updateNameInputValue} required={true} maxLength="100" autoComplete="name" className="sp-input" disabled={!view.loaded || view.busy} data-sp-c8811dc0="" value={view.form.fullName ?? ""} onChange={event => ($value => {
              view.updateForm(draftValue => draftValue.fullName = $value);
            })(event.target.value)} />
          </label>
          <label className="account-field" data-sp-c8811dc0="">
            {"Email"}
            <input type="email" readOnly={true} autoComplete="email" className="sp-input bg-brand-surface" data-sp-c8811dc0="" value={view.form.email ?? ""} onChange={event => ($value => {
              view.updateForm(draftValue => draftValue.email = $value);
            })(event.target.value)} />
            <small data-sp-c8811dc0="">
              {"Email dùng để đăng nhập và xác thực tài khoản."}
            </small>
          </label>
          <label className="account-field" data-sp-c8811dc0="">
            {"Số điện thoại"}
            <input type="tel" maxLength="30" autoComplete="tel" className="sp-input" disabled={!view.loaded || view.busy} data-sp-c8811dc0="" value={view.form.phone ?? ""} onChange={event => ($value => {
              view.updateForm(draftValue => draftValue.phone = $value);
            })(event.target.value)} />
          </label>
          <label className="account-field" data-sp-c8811dc0="">
            {"Khu vực quan tâm"}
            <input maxLength="100" className="sp-input" disabled={!view.loaded || view.busy} placeholder="Ví dụ: Hải Châu, Đà Nẵng" data-sp-c8811dc0="" value={view.form.district ?? ""} onChange={event => ($value => {
              view.updateForm(draftValue => draftValue.district = $value);
            })(event.target.value)} />
          </label>
          <label className="account-field sm:col-span-2" data-sp-c8811dc0="">
            {"Địa chỉ liên hệ"}
            <input maxLength="255" autoComplete="street-address" className="sp-input" disabled={!view.loaded || view.busy} data-sp-c8811dc0="" value={view.form.address ?? ""} onChange={event => ($value => {
              view.updateForm(draftValue => draftValue.address = $value);
            })(event.target.value)} />
          </label>
          <LifestyleFields value={view.form.advisorPreferences} disabled={!view.loaded || view.busy} onChange={value => {
            view.updateForm(draftValue => draftValue.advisorPreferences = value);
          }} />
          <div className="flex flex-wrap gap-3 sm:col-span-2" data-sp-c8811dc0="">
            <button className="sp-button sp-button-primary" disabled={!view.loaded || view.busy} data-sp-c8811dc0="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.busy ? "Đang lưu…" : "Lưu thay đổi")}
            </button>
            <button type="button" className="sp-button sp-button-secondary" disabled={view.busy} onClick={$event => {
              return view.resetProfile?.($event);
            }} data-sp-c8811dc0="">
              {"Hủy thay đổi"}
            </button>
          </div>
        </form>
      </section>
      <section id="security-settings" className="account-card mb-6" aria-labelledby="security-heading" data-sp-c8811dc0="">
        <div className="account-section-heading" data-sp-c8811dc0="">
          <span className="account-section-icon" data-sp-c8811dc0="">
            <AppIcon name="shield" data-sp-c8811dc0="" />
          </span>
          <div data-sp-c8811dc0="">
            <h2 id="security-heading" data-sp-c8811dc0="">
              {"Bảo mật & cài đặt"}
            </h2>
            <p data-sp-c8811dc0="">
              {"Chủ động bảo vệ tài khoản và quản lý cách nhận thông tin."}
            </p>
          </div>
        </div>
        <div className="account-tabs mb-6" role="group" aria-label="Cài đặt tài khoản" data-sp-c8811dc0="">
          {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))([{
            id: "password",
            label: "Mật khẩu"
          }, {
            id: "notifications",
            label: "Thông báo"
          }], tab => <button key={tab.id} type="button" aria-pressed={view.securityTab === tab.id} onClick={$event => {
            view.updateSecurityTabValue(tab.id);
          }} data-sp-c8811dc0="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(tab.label)}
              </button>)}
          <SiteLink to="/account/sessions" data-sp-c8811dc0="">
            {"Phiên đăng nhập ↗"}
          </SiteLink>
        </div>
        {view.securityTab === "password" ? <form className="grid gap-5 sm:grid-cols-2" onSubmit={$event => {
          $event.preventDefault();
          return view.changePassword?.($event);
        }} data-sp-c8811dc0="">
            <label className="account-field sm:col-span-2" data-sp-c8811dc0="">
              {"Mật khẩu hiện tại"}
              <input type={view.showPassword ? "text" : "password"} required={true} maxLength="72" autoComplete="current-password" className="sp-input" data-sp-c8811dc0="" value={view.currentPassword ?? ""} onChange={event => ($value => {
              view.updateCurrentPasswordValue($value);
            })(event.target.value)} />
            </label>
            <label className="account-field" data-sp-c8811dc0="">
              {"Mật khẩu mới"}
              <input type={view.showPassword ? "text" : "password"} required={true} minLength="8" maxLength="72" autoComplete="new-password" className="sp-input" data-sp-c8811dc0="" value={view.newPassword ?? ""} onChange={event => ($value => {
              view.updateNewPasswordValue($value);
            })(event.target.value)} />
              <small data-sp-c8811dc0="">
                {"Từ 8 ký tự, tối đa 72 byte UTF-8."}
              </small>
            </label>
            <label className="account-field" data-sp-c8811dc0="">
              {"Xác nhận mật khẩu mới"}
              <input type={view.showPassword ? "text" : "password"} required={true} minLength="8" maxLength="72" autoComplete="new-password" className="sp-input" data-sp-c8811dc0="" value={view.confirmPassword ?? ""} onChange={event => ($value => {
              view.updateConfirmPasswordValue($value);
            })(event.target.value)} />
            </label>
            <div className="flex flex-wrap items-center justify-between gap-4 sm:col-span-2" data-sp-c8811dc0="">
              <button type="button" className="text-sm font-medium underline" aria-pressed={view.showPassword} onClick={$event => {
              view.updateShowPasswordValue(!view.showPassword);
            }} data-sp-c8811dc0="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu")}
              </button>
              <button className="sp-button sp-button-primary" disabled={view.busy || !view.loaded} data-sp-c8811dc0="">
                {"Đổi mật khẩu"}
              </button>
            </div>
          </form> : <div data-sp-c8811dc0="">
            {view.prefsError ? <div role="alert" className="account-notice account-error mb-4" data-sp-c8811dc0="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.prefsError)}{" "}
                <button type="button" className="underline" onClick={$event => {
              return view.loadPreferences?.($event);
            }} data-sp-c8811dc0="">
                  {"Thử lại"}
                </button>
              </div> : null}
            {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.preferenceLabels, item => <label key={item.key} className="flex cursor-pointer items-center justify-between gap-6 border-b border-brand-line py-4" data-sp-c8811dc0="">
                <span data-sp-c8811dc0="">
                  <strong className="block text-[15px] font-semibold" data-sp-c8811dc0="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.title)}
                  </strong>
                  <span className="mt-1 block text-sm leading-6 text-brand-muted" data-sp-c8811dc0="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.text)}
                  </span>
                </span>
                <input type="checkbox" className="size-5 shrink-0 accent-brand-navy" disabled={!view.preferencesLoaded || view.busy} data-sp-c8811dc0="" checked={Array.isArray(view.prefs[item.key]) ? view.prefs[item.key].includes("on") : !!view.prefs[item.key]} onChange={event => ($value => {
              view.updatePrefs(draftValue => draftValue[item.key] = $value);
            })(Array.isArray(view.prefs[item.key]) ? event.target.checked ? [...view.prefs[item.key], "on"] : view.prefs[item.key].filter(item => item !== "on") : event.target.checked)} />
              </label>)}
            <button type="button" className="sp-button sp-button-primary mt-5" disabled={!view.preferencesLoaded || view.busy} onClick={$event => {
            return view.savePreferences?.($event);
          }} data-sp-c8811dc0="">
              {"Lưu tùy chọn"}
            </button>
          </div>}
        <div className="mt-8 border-t border-brand-line pt-6" aria-labelledby="google-link-heading" data-sp-c8811dc0="">
          <h3 id="google-link-heading" className="text-lg font-semibold">{"Liên kết tài khoản Google"}</h3>
          <p className="mt-2 text-sm leading-6 text-brand-muted">{"Dùng Google để đăng nhập vào chính tài khoản SmartProp này. Việc liên kết yêu cầu mật khẩu hiện tại và không thay đổi email hoặc quyền tài khoản."}</p>
          {view.googleLinkError ? <p role="alert" className="account-notice account-error mt-4" data-sp-c8811dc0="">{view.googleLinkError}</p> : null}
          {view.googleLinked === true ? <p role="status" className="account-notice account-success mt-4" data-sp-c8811dc0="">{"Đã liên kết Google với tài khoản SmartProp này."}</p> : view.googleLinked === false && !view.googleLinkAvailable ? <p role="status" className="mt-4 text-sm text-brand-muted">Liên kết Google hiện chưa khả dụng.</p> : view.googleLinked === false ? <><p role="status" className="mt-4 text-sm text-brand-muted">{"Chưa liên kết Google với tài khoản SmartProp này."}</p><form className="mt-4 grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end" onSubmit={$event => {
            $event.preventDefault();
            return view.linkGoogle?.($event);
          }} data-sp-c8811dc0="">
              <label className="account-field" data-sp-c8811dc0="">
                {"Mật khẩu SmartProp hiện tại"}
                <input type="password" required={true} maxLength="72" autoComplete="current-password" className="sp-input" disabled={view.googleLinkBusy || view.busy} value={view.googleLinkPassword ?? ""} onChange={event => view.updateGoogleLinkPasswordValue(event.target.value)} />
              </label>
              {!refreshEnabled ? <p className="text-sm text-[var(--ui-error-text)] sm:col-span-2">{"Cần bật VITE_ENABLE_REFRESH=true để giữ phiên SmartProp qua bước xác thực Google."}</p> : null}
              <button type="submit" className="sp-button sp-button-primary" disabled={!view.loaded || !refreshEnabled || view.googleLinkBusy || view.busy} data-sp-c8811dc0="">
                {view.googleLinkBusy ? "Đang chuyển tới Google…" : "Liên kết Google"}
              </button>
            </form></> : <div role="status" className="mt-4 text-sm text-brand-muted">{"Chưa xác nhận được trạng thái liên kết Google."} <button type="button" className="font-semibold underline" onClick={$event => view.load?.($event)}>{"Thử lại"}</button></div>}
        </div>
        <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-brand-line pt-5 text-sm" data-sp-c8811dc0="">
          <span data-sp-c8811dc0="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.session.user?.emailVerifiedAt ? "Email của bạn đã được xác minh." : "Hoàn tất xác minh để bảo vệ tài khoản.")}
          </span>
          {!view.session.user?.emailVerifiedAt ? <SiteLink to="/account/verify-email" className="font-semibold underline" data-sp-c8811dc0="">
              {"Xác minh email ↗"}
            </SiteLink> : null}
        </div>
      </section>
      <section id="property-management" className="mb-6" aria-label="Quản lý bất động sản" data-sp-c8811dc0="">
        <BrokerApplicationCard data-sp-c8811dc0="" />
      </section>
      <section id="valuation-history" className="mb-6" aria-label="Lịch sử định giá" data-sp-c8811dc0="">
        <ValuationHistory data-sp-c8811dc0="" />
      </section>
      <section id="account-tools" className="account-card" aria-labelledby="account-tools-heading" data-sp-c8811dc0="">
        <div className="account-section-heading" data-sp-c8811dc0="">
          <span className="account-section-icon" data-sp-c8811dc0="">
            <AppIcon name="briefcase" data-sp-c8811dc0="" />
          </span>
          <div data-sp-c8811dc0="">
            <h2 id="account-tools-heading" data-sp-c8811dc0="">
              {"Tiện ích của bạn"}
            </h2>
            <p data-sp-c8811dc0="">
              {"Tiếp tục từ những nội dung và trao đổi đã lưu."}
            </p>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2" data-sp-c8811dc0="">
          {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.tools, tool => <SiteLink key={tool.to} to={tool.to} className="account-tool" data-sp-c8811dc0="">
              <AppIcon name={tool.icon} data-sp-c8811dc0="" />
              <span className="min-w-0 flex-1" data-sp-c8811dc0="">
                <strong data-sp-c8811dc0="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(tool.title)}
                </strong>
                <small data-sp-c8811dc0="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(tool.text)}
                </small>
              </span>
              <AppIcon name="arrow" data-sp-c8811dc0="" />
            </SiteLink>)}
        </div>
        <button type="button" className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-brand-muted underline" disabled={view.busy} onClick={$event => {
          return view.signOut?.($event);
        }} data-sp-c8811dc0="">
          <AppIcon name="logout" data-sp-c8811dc0="" />
          {"Đăng xuất tài khoản"}
        </button>
      </section>
    </div></>;
});
