import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useEffect, useRef } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { useAppNavigation } from "../../app/navigation.jsx";
import { completeGoogleLogin, session, errorText } from "./api.js";
function useGoogleCompleteViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const router = useAppNavigation(),
    [error] = useState(() => createStateStore(""));
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useEffect(() => {
    const result = (async () => {
      try {
        await completeGoogleLogin();
        await _routerLatest.current.replace(session.getSnapshot().user?.role === "ADMIN" ? "/admin" : "/home");
      } catch (e) {
        error.set(errorText(e));
      }
    })();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  return {
    ...inputProps,
    error: error.getSnapshot(),
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function GoogleCompleteView(props, ref) {
  const view = useGoogleCompleteViewState(props, ref);
  return <><main data-ui-view="GoogleCompleteView" {...view.rootAttributes} className={classNames(["sp-container py-16", view.rootAttributes.className])}>
      <section className="mx-auto max-w-lg rounded-panel border border-brand-line bg-brand-card p-8">
        <p className="text-xs font-semibold tracking-widest text-brand-accent">
          {"SMARTPROP · GOOGLE"}
        </p>
        <h1 className="mt-3 text-2xl font-semibold">
          {"Hoàn tất đăng nhập"}
        </h1>
        {!view.error ? <p role="status" className="mt-4 text-sm leading-7 text-brand-muted">
            {"Đang xác minh tài khoản và khởi tạo phiên của bạn…"}
          </p> : <div role="alert" className="mt-4">
            <p className="text-sm leading-7 text-[var(--ui-error-text)]">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}
            </p>
            <SiteLink to="/login" className="sp-button sp-button-primary mt-6">
              {"Quay lại đăng nhập"}
            </SiteLink>
          </div>}
      </section>
    </main></>;
});
