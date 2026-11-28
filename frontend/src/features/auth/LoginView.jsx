import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef, useEffect } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { useAppNavigation, useRouteState } from "../../app/navigation.jsx";
import { api, login, register, errorText } from "./api.js";
import { safeLoginDestination } from "./authNavigation.js";
import GoogleLoginButton from "./GoogleLoginButton.jsx";
function useLoginViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
      ...inputProps
    },
    router = useAppNavigation(),
    route = useRouteState();
  const _props = useRef(props);
  _props.current = props;
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  const getIsRegister = () => _props.current.initialRegister || _routeLatest.current.path === "/register",
    [forgot] = useState(() => createStateStore(false));
  useSyncExternalStore(forgot.subscribe, forgot.getSnapshot);
  const [fullName] = useState(() => createStateStore("")),
    [email] = useState(() => createStateStore("")),
    [password] = useState(() => createStateStore("")),
    [confirmPassword] = useState(() => createStateStore("")),
    [showPassword] = useState(() => createStateStore(false)),
    [showConfirm] = useState(() => createStateStore(false));
  useSyncExternalStore(showConfirm.subscribe, showConfirm.getSnapshot);
  useSyncExternalStore(showPassword.subscribe, showPassword.getSnapshot);
  useSyncExternalStore(confirmPassword.subscribe, confirmPassword.getSnapshot);
  useSyncExternalStore(password.subscribe, password.getSnapshot);
  useSyncExternalStore(email.subscribe, email.getSnapshot);
  useSyncExternalStore(fullName.subscribe, fullName.getSnapshot);
  const [busy] = useState(() => createStateStore(false)),
    [message] = useState(() => createStateStore("")),
    [error] = useState(() => createStateStore("")),
    [video] = useState(() => createStateStore(null)),
    [playing] = useState(() => createStateStore(false));
  useSyncExternalStore(playing.subscribe, playing.getSnapshot);
  useSyncExternalStore(video.subscribe, video.getSnapshot);
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(message.subscribe, message.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  const reasons = {
    "password-changed": "Đổi mật khẩu thành công. Vui lòng đăng nhập bằng mật khẩu mới.",
    "session-expired": "Phiên đã hết hạn hoặc bị thu hồi. Vui lòng đăng nhập lại.",
    "session-unavailable": "Vui lòng đăng nhập lại để tiếp tục.",
    "login-required": "Đăng nhập để sử dụng chức năng này.",
    "google-failed": "Chưa hoàn tất đăng nhập Google. Vui lòng thử lại hoặc đăng nhập bằng email."
  };
  const _watched = (() => _routeLatest.current.fullPath)();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    _initialized.current = true;
    const result = (() => {
      message.set(_routeLatest.current.query.registered === "1" ? "Tạo tài khoản thành công. Bạn có thể đăng nhập ngay." : reasons[_routeLatest.current.query.reason] || "");
      error.set("");
      forgot.set(false);
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  const getHeading = () => forgot.getSnapshot() ? "Khôi phục mật khẩu" : getIsRegister() ? "Bắt đầu cùng SmartProp" : "Chào mừng bạn trở lại";
  function switchTab(path) {
    if (!busy.getSnapshot()) _routerLatest.current.push(path);
  }
  async function toggleVideo() {
    if (!video.getSnapshot()) return;
    if (playing.getSnapshot()) {
      video.getSnapshot().pause();
      playing.set(false);
    } else {
      try {
        await video.getSnapshot().play();
        playing.set(true);
      } catch {
        playing.set(false);
      }
    }
  }
  useEffect(() => {
    const result = (() => {
      if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) toggleVideo();
    })();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  async function submit() {
    if (busy.getSnapshot()) return;
    error.set(message.set(""));
    if (!forgot.getSnapshot() && new TextEncoder().encode(password.getSnapshot()).length > 72) {
      error.set("Mật khẩu tối đa 72 byte UTF-8. Vui lòng kiểm tra lại.");
      return;
    }
    if (getIsRegister() && !forgot.getSnapshot() && password.getSnapshot() !== confirmPassword.getSnapshot()) {
      error.set("Mật khẩu xác nhận không khớp.");
      return;
    }
    busy.set(true);
    try {
      if (forgot.getSnapshot()) {
        await api("/auth/password/forgot", {
          method: "POST",
          body: {
            email: email.getSnapshot().trim()
          },
          authenticated: false
        });
        message.set("Nếu tài khoản đủ điều kiện, liên kết đặt lại mật khẩu sẽ được gửi đến email của bạn.");
      } else if (getIsRegister()) {
        await register({
          fullName: fullName.getSnapshot().trim(),
          email: email.getSnapshot(),
          password: password.getSnapshot(),
          role: "BUYER"
        });
        password.set(confirmPassword.set(""));
        await _routerLatest.current.replace({
          path: "/login",
          query: {
            registered: "1"
          }
        });
      } else {
        const user = await login(email.getSnapshot(), password.getSnapshot(), false);
        password.set("");
        await _routerLatest.current.replace(safeLoginDestination(_routeLatest.current.query.next, user.role));
      }
    } catch (e) {
      error.set(errorText(e));
    } finally {
      busy.set(false);
    }
  }
  return {
    ...inputProps,
    isRegister: getIsRegister(),
    forgot: forgot.getSnapshot(),
    fullName: fullName.getSnapshot(),
    email: email.getSnapshot(),
    password: password.getSnapshot(),
    confirmPassword: confirmPassword.getSnapshot(),
    showPassword: showPassword.getSnapshot(),
    showConfirm: showConfirm.getSnapshot(),
    busy: busy.getSnapshot(),
    message: message.getSnapshot(),
    error: error.getSnapshot(),
    playing: playing.getSnapshot(),
    heading: getHeading(),
    switchTab,
    toggleVideo,
    submit,
    updateVideoValue: video.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["initialRegister", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateForgotValue: forgot.set,
    updateErrorValue: error.set,
    updateMessageValue: message.set,
    updateFullNameValue: fullName.set,
    updateEmailValue: email.set,
    updatePasswordValue: password.set,
    updateShowPasswordValue: showPassword.set,
    updateConfirmPasswordValue: confirmPassword.set,
    updateShowConfirmValue: showConfirm.set
  };
}
export default React.forwardRef(function LoginView(props, ref) {
  const view = useLoginViewState(props, ref);
  return <><main data-ui-view="LoginView" {...view.rootAttributes} className={classNames(["min-h-screen relative isolation-auto bg-[var(--ui-soft)] flex items-center justify-center p-4 sm:p-6 lg:p-10 font-sans selection:bg-[var(--ui-soft)] selection:text-brand-navy", view.rootAttributes.className])}>
      <video ref={view.updateVideoValue} className="absolute inset-0 w-full h-full object-cover z-0 pointer-events-none opacity-50" src="/background.mp4" preload="metadata" loop={true} muted={true} playsInline={true} aria-hidden="true" />
      <div className="absolute inset-0 bg-gradient-to-tr from-[var(--ui-soft)]/95 via-[var(--ui-soft)]/80 to-[var(--ui-soft)]/95 z-0 pointer-events-none" />
      <div className="relative z-10 w-full max-w-[1200px] mx-auto grid grid-cols-1 lg:grid-cols-[1.1fr_480px] gap-8 lg:gap-14 items-center">
        <section className="hidden lg:flex flex-col justify-between min-h-[600px] text-brand-navy py-4 pr-6" aria-label="SmartProp">
          <div>
            <SiteLink to="/home" className="inline-flex items-center gap-3 group">
              <span className="w-11 h-11 rounded-xl bg-brand-card text-[var(--ui-accent)] font-black text-2xl flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform duration-200">
                {" S "}
              </span>
              <span className="text-2xl font-bold tracking-tight text-brand-navy block">
                {"SmartProp."}
              </span>
            </SiteLink>
          </div>
          <div className="space-y-5 my-auto max-w-[500px]">
            <p className="text-xs font-semibold tracking-[0.18em] text-[var(--ui-ink)] uppercase">
              {" ĐÀ NẴNG · SMARTPROP "}
            </p>
            <h1 className="text-4xl xl:text-5xl font-medium tracking-tight text-brand-navy leading-[1.25]">
              {" Không gian sống."}
              <br />
              <em className="[font-family:inherit] not-italic text-[var(--ui-ink)]">
                {"Khởi đầu của bạn."}
              </em>
            </h1>
            <p className="text-brand-navy text-sm xl:text-base leading-relaxed">
              {" Khám phá bất động sản, lưu những lựa chọn yêu thích và tìm hiểu giá trị từ dữ liệu. "}
            </p>
          </div>
          <div className="pt-4">
            <button type="button" className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-brand-line/40 hover:border-brand-line text-xs text-brand-navy transition-all cursor-pointer backdrop-blur-sm" aria-pressed={view.playing} onClick={$event => {
              return view.toggleVideo?.($event);
            }}>
              <span>
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.playing ? "Ⅱ" : "▷")}
              </span>
              <span>
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.playing ? "Tạm dừng nền" : "Phát video nền")}
              </span>
            </button>
          </div>
        </section>
        <section className="bg-brand-card/95 backdrop-blur-xl rounded-3xl p-6 sm:p-9 shadow-2xl border border-brand-line/60 relative" aria-busy={view.busy} aria-labelledby="auth-heading">
          <div className="mb-5">
            <SiteLink to="/home" className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--ui-accent)] hover:text-[var(--ui-accent)] transition-all cursor-pointer">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="19" y1="12" x2="5" y2="12" />
                <polyline points="12 19 5 12 12 5" />
              </svg>
              <span>{"Trang chủ SmartProp"}</span>
            </SiteLink>
          </div>
          {!view.forgot ? <div className="bg-brand-card p-1.5 rounded-2xl flex border border-brand-line/80 mb-6" role="tablist" aria-label="Đăng nhập hoặc đăng ký">
              <button type="button" role="tab" aria-selected={!view.isRegister} disabled={view.busy} className={classNames(["w-1/2 py-2.5 px-4 rounded-xl text-xs font-bold transition-all duration-150 cursor-pointer text-center", !view.isRegister ? "bg-brand-card text-[var(--ui-accent)] shadow-xs" : "text-brand-muted hover:text-[var(--ui-accent)]"])} onClick={$event => {
              view.switchTab("/login");
            }}>
                {" Đăng nhập "}
              </button>
              <button type="button" role="tab" aria-selected={view.isRegister} disabled={view.busy} className={classNames(["w-1/2 py-2.5 px-4 rounded-xl text-xs font-bold transition-all duration-150 cursor-pointer text-center", view.isRegister ? "bg-brand-card text-[var(--ui-accent)] shadow-xs" : "text-brand-muted hover:text-[var(--ui-accent)]"])} onClick={$event => {
              view.switchTab("/register");
            }}>
                {" Đăng ký "}
              </button>
            </div> : <button type="button" className="inline-flex items-center gap-1.5 text-xs font-bold text-[var(--ui-accent)] hover:text-[var(--ui-accent)] transition mb-5 cursor-pointer" onClick={$event => {
            view.updateForgotValue(false);
            view.updateMessageValue(view.updateErrorValue(""));
          }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="19" y1="12" x2="5" y2="12" />
                <polyline points="12 19 5 12 12 5" />
              </svg>
              <span>{"Quay lại đăng nhập"}</span>
            </button>}
          <div className="mb-5">
            <h2 id="auth-heading" className="text-2xl sm:text-3xl font-extrabold text-[var(--ui-accent)] tracking-tight">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.heading)}
            </h2>
            <p className="text-xs sm:text-sm text-[var(--ui-accent)] mt-1.5 leading-relaxed">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.forgot ? "Nhập email để nhận liên kết đặt lại mật khẩu." : view.isRegister ? "Một tài khoản cho mọi trải nghiệm của bạn." : "Đăng nhập để tiếp tục từ những điều bạn quan tâm.")}
            </p>
          </div>
          {view.message ? <div role="status" className="p-3.5 rounded-xl bg-[var(--ui-surface)] border border-[var(--ui-success-border)] text-xs font-semibold text-[var(--ui-accent)] flex items-center gap-2 mb-4">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="shrink-0 text-[var(--ui-accent)]">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span>{(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.message)}</span>
            </div> : null}
          {view.error ? <div role="alert" className="p-3.5 rounded-xl bg-[var(--ui-surface)] border border-[var(--ui-error-border)] text-xs font-semibold text-[var(--ui-muted)] flex items-center gap-2 mb-4">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="shrink-0 text-[var(--ui-muted)]">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}</span>
            </div> : null}
          <form className="space-y-4" onSubmit={$event => {
            $event.preventDefault();
            return view.submit?.($event);
          }}>
            {view.isRegister && !view.forgot ? <div className="space-y-1.5">
                <label className="block text-xs font-bold text-[var(--ui-accent)]" htmlFor="name-input">
                  {" Họ và tên "}
                </label>
                <div className="relative flex items-center">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="absolute left-3.5 text-brand-muted pointer-events-none">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                  <input id="name-input" type="text" autoComplete="name" required={true} maxLength="100" placeholder="Họ và tên của bạn" disabled={view.busy} className="w-full pl-10 pr-4 py-2.5 sm:py-3 rounded-xl border border-brand-line bg-brand-card text-[var(--ui-accent)] text-xs sm:text-sm font-normal placeholder:text-brand-muted focus:outline-none focus:border-[var(--ui-border)] focus:ring-4 focus:ring-[var(--ui-border)]/15 transition-all duration-150 disabled:bg-brand-card shadow-2xs" value={view.fullName ?? ""} onChange={event => ($value => {
                  view.updateFullNameValue($value);
                })(event.target.value)} />
                </div>
              </div> : null}
            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-[var(--ui-accent)]" htmlFor="email-input">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(!view.isRegister && !view.forgot ? "Email / tên quản trị" : "Email")}
              </label>
              <div className="relative flex items-center">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="absolute left-3.5 text-brand-muted pointer-events-none">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                  <polyline points="22,6 12,13 2,6" />
                </svg>
                <input id="email-input" type={!view.isRegister && !view.forgot ? "text" : "email"} autoComplete={!view.isRegister && !view.forgot ? "username" : "email"} maxLength="254" required={true} placeholder={!view.isRegister && !view.forgot ? "Email hoặc Admin" : "ban@email.com"} disabled={view.busy} className="w-full pl-10 pr-4 py-2.5 sm:py-3 rounded-xl border border-brand-line bg-brand-card text-[var(--ui-accent)] text-xs sm:text-sm font-normal placeholder:text-brand-muted focus:outline-none focus:border-[var(--ui-border)] focus:ring-4 focus:ring-[var(--ui-border)]/15 transition-all duration-150 disabled:bg-brand-card shadow-2xs" value={view.email ?? ""} onChange={event => ($value => {
                  view.updateEmailValue($value);
                })(event.target.value)} />
              </div>
            </div>
            {!view.forgot ? <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-bold text-[var(--ui-accent)]" htmlFor="password-input">
                    {" Mật khẩu "}
                  </label>
                  {!view.isRegister && !view.forgot ? <button type="button" className="text-xs text-[var(--ui-accent)] hover:text-[var(--ui-accent)] hover:underline cursor-pointer" onClick={$event => {
                  view.updateForgotValue(true);
                  view.updateErrorValue(view.updateMessageValue(""));
                }}>
                      {" Quên mật khẩu? "}
                    </button> : null}
                </div>
                <div className="relative flex items-center">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="absolute left-3.5 text-brand-muted pointer-events-none">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                  <input id="password-input" type={view.showPassword ? "text" : "password"} autoComplete={view.isRegister ? "new-password" : "current-password"} minLength={view.isRegister ? 8 : undefined} maxLength="72" required={true} placeholder={view.isRegister ? "Tối thiểu 8 ký tự" : "Nhập mật khẩu"} disabled={view.busy} className="w-full pl-10 pr-11 py-2.5 sm:py-3 rounded-xl border border-brand-line bg-brand-card text-[var(--ui-accent)] text-xs sm:text-sm font-normal placeholder:text-brand-muted focus:outline-none focus:border-[var(--ui-border)] focus:ring-4 focus:ring-[var(--ui-border)]/15 transition-all duration-150 disabled:bg-brand-card shadow-2xs" value={view.password ?? ""} onChange={event => ($value => {
                  view.updatePasswordValue($value);
                })(event.target.value)} />
                  <button type="button" className="absolute right-2.5 p-1.5 text-brand-muted hover:text-[var(--ui-accent)] transition cursor-pointer" aria-label={view.showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"} onClick={$event => {
                  view.updateShowPasswordValue(!view.showPassword);
                }}>
                    {view.showPassword ? <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                      </svg> : <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>}
                  </button>
                </div>
                {view.isRegister ? <p className="text-[11px] text-[var(--ui-accent)]">
                    {" Từ 8 ký tự, tối đa 72 byte UTF-8. "}
                  </p> : null}
              </div> : null}
            {view.isRegister && !view.forgot ? <div className="space-y-1.5">
                <label className="block text-xs font-bold text-[var(--ui-accent)]" htmlFor="confirm-password-input">
                  {" Xác nhận mật khẩu "}
                </label>
                <div className="relative flex items-center">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="absolute left-3.5 text-brand-muted pointer-events-none">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                  <input id="confirm-password-input" type={view.showConfirm ? "text" : "password"} autoComplete="new-password" minLength="8" maxLength="72" required={true} placeholder="Nhập lại mật khẩu" disabled={view.busy} className="w-full pl-10 pr-11 py-2.5 sm:py-3 rounded-xl border border-brand-line bg-brand-card text-[var(--ui-accent)] text-xs sm:text-sm font-normal placeholder:text-brand-muted focus:outline-none focus:border-[var(--ui-border)] focus:ring-4 focus:ring-[var(--ui-border)]/15 transition-all duration-150 disabled:bg-brand-card shadow-2xs" value={view.confirmPassword ?? ""} onChange={event => ($value => {
                  view.updateConfirmPasswordValue($value);
                })(event.target.value)} />
                  <button type="button" className="absolute right-2.5 p-1.5 text-brand-muted hover:text-[var(--ui-accent)] transition cursor-pointer" aria-label={view.showConfirm ? "Ẩn mật khẩu xác nhận" : "Hiện mật khẩu xác nhận"} onClick={$event => {
                  view.updateShowConfirmValue(!view.showConfirm);
                }}>
                    {view.showConfirm ? <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                      </svg> : <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>}
                  </button>
                </div>
              </div> : null}
            <button type="submit" className="w-full min-h-[48px] py-3.5 px-6 rounded-xl bg-[var(--ui-soft)] hover:bg-[var(--ui-soft)] active:bg-[var(--ui-soft)] text-brand-navy font-bold text-sm tracking-wide shadow-md flex items-center justify-center gap-2 transition-all duration-150 active:scale-[0.99] disabled:opacity-60 disabled:cursor-wait cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ui-border)]" disabled={view.busy}>
              {view.busy ? <svg className="animate-spin w-4 h-4 text-brand-navy" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg> : null}
              <span>
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.busy ? "Đang xử lý…" : view.forgot ? "Gửi liên kết đặt lại" : view.isRegister ? "Tạo tài khoản" : "Đăng nhập")}
              </span>
            </button>
          </form>
          {!view.forgot ? <GoogleLoginButton disabled={view.busy} /> : null}
          <p className="text-xs text-[var(--ui-accent)] text-center mt-6">
            {" Tiếp tục khám phá không gian sống cùng SmartProp. "}
          </p>
        </section>
      </div>
    </main></>;
});
