import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import { useRouteState, useAppNavigation } from "../../app/navigation.jsx";
import { initializeAuth, session } from "./api.js";
function useSessionRecoveryState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const router = useAppNavigation(),
    route = useRouteState(),
    [busy] = useState(() => createStateStore(false));
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  async function retry() {
    if (busy.getSnapshot()) return;
    busy.set(true);
    try {
      await initializeAuth({
        force: true
      });
      if (session.getSnapshot().status !== "UNAVAILABLE") {
        const target = typeof _routeLatest.current.query.returnTo === "string" && _routeLatest.current.query.returnTo.startsWith("/") && !_routeLatest.current.query.returnTo.startsWith("//") ? _routeLatest.current.query.returnTo : _routeLatest.current.path === "/session-recovery" ? "/home" : _routeLatest.current.fullPath;
        await _routerLatest.current.replace(target);
      }
    } finally {
      busy.set(false);
    }
  }
  return {
    ...inputProps,
    session: session.getSnapshot(),
    busy: busy.getSnapshot(),
    retry,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function SessionRecovery(props, ref) {
  const view = useSessionRecoveryState(props, ref);
  return <><main data-ui-view="SessionRecovery" {...view.rootAttributes} className={classNames(["grid min-h-screen place-items-center bg-brand-cream p-6 text-brand-navy", view.rootAttributes.className])}>
      <section className="w-full max-w-lg rounded-panel border border-brand-line bg-brand-card p-7">
        <h1 className="text-2xl font-semibold">
          {"Chưa thể kiểm tra phiên đăng nhập"}
        </h1>
        <p className="mt-4 text-sm leading-6">
          {"Kết nối đang gián đoạn. Bạn có thể thử lại khi máy chủ hoặc mạng hoạt động trở lại."}
        </p>
        {view.session.error ? <p role="alert" className="mt-3 text-sm leading-6 text-brand-muted">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.session.error)}
          </p> : null}
        <button className="sp-button sp-button-primary mt-5" disabled={view.busy} onClick={$event => {
          return view.retry?.($event);
        }}>
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.busy ? "Đang kiểm tra…" : "Thử lại kết nối")}
        </button>
      </section>
    </main></>;
});
