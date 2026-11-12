import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useEffect, useRef } from "react";
import { api, refreshEnabled } from "./api.js";
function useGoogleLoginButtonState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const [ready] = useState(() => createStateStore(false)),
    [loading] = useState(() => createStateStore(true)),
    [starting] = useState(() => createStateStore(false));
  useSyncExternalStore(starting.subscribe, starting.getSnapshot);
  useSyncExternalStore(loading.subscribe, loading.getSnapshot);
  useSyncExternalStore(ready.subscribe, ready.getSnapshot);
  const base = (import.meta.env?.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");
  async function load() {
    loading.set(true);
    try {
      const config = await api("/auth/google/config", {
        authenticated: false
      });
      ready.set(refreshEnabled && config.available === true && config.authorizationPath === "/auth/oauth2/authorize/google");
    } catch {
      ready.set(false);
    } finally {
      loading.set(false);
    }
  }
  function start() {
    if (!ready.getSnapshot() || starting.getSnapshot()) return;
    starting.set(true);
    window.location.assign(base + "/auth/oauth2/authorize/google");
  }
  useEffect(() => {
    const result = load();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  return {
    ...inputProps,
    ready: ready.getSnapshot(),
    loading: loading.getSnapshot(),
    starting: starting.getSnapshot(),
    start,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["disabled", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function GoogleLoginButton(props, ref) {
  const view = useGoogleLoginButtonState(props, ref);
  return <><div {...view.rootAttributes} className={classNames(["w-full mt-5", view.rootAttributes.className])}>
      <div className="relative flex items-center justify-center my-4">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-brand-line" />
        </div>
        <span className="relative bg-brand-card px-3 text-[11px] font-semibold text-brand-muted uppercase tracking-wider">
          {" Hoặc tiếp tục với "}
        </span>
      </div>
      <button type="button" className="w-full min-h-[46px] py-2.5 px-4 rounded-xl border border-brand-line bg-brand-card hover:bg-brand-card hover:border-[var(--ui-border)]/60 text-[var(--ui-accent)] font-bold text-xs flex items-center justify-center gap-3 transition-all duration-150 active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed shadow-2xs cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ui-border)]" disabled={view.disabled || view.loading || !view.ready || view.starting} onClick={$event => {
        return view.start?.($event);
      }}>
        <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
          <path fill="#4285F4" d="M21.6 12.23c0-.71-.06-1.39-.18-2.05H12v3.88h5.38a4.6 4.6 0 0 1-2 3.02v2.51h3.24c1.9-1.75 2.98-4.33 2.98-7.36Z" />
          <path fill="#34A853" d="M12 22c2.7 0 4.96-.9 6.62-2.41l-3.24-2.51c-.9.6-2.05.96-3.38.96-2.6 0-4.81-1.76-5.6-4.12H3.05v2.59A10 10 0 0 0 12 22Z" />
          <path fill="#FBBC05" d="M6.4 13.92a6 6 0 0 1 0-3.84V7.49H3.05a10 10 0 0 0 0 9.02l3.35-2.59Z" />
          <path fill="#EA4335" d="M12 5.96c1.47 0 2.79.51 3.83 1.51l2.87-2.87A9.6 9.6 0 0 0 12 2a10 10 0 0 0-8.95 5.49l3.35 2.59C7.19 7.72 9.4 5.96 12 5.96Z" />
        </svg>
        <span>
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.starting ? "Đang kết nối Google…" : "Tiếp tục với Google")}
        </span>
      </button>
      {view.loading ? <p className="text-[11px] text-brand-muted text-center mt-2" role="status">
          {" Đang kiểm tra phương thức đăng nhập… "}
        </p> : !view.ready ? <p className="text-[11px] text-brand-muted text-center mt-2">
          {" Đăng nhập nhanh an toàn bằng tài khoản SmartProp "}
        </p> : null}
    </div></>;
});
