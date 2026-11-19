import { stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useEffect, useSyncExternalStore } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { session } from "../auth/api.js";
import { notifications, refreshUnread } from "./notifications.js";
function useNotificationBadgeState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  useSyncExternalStore(notifications.subscribe, notifications.getSnapshot);
  const _timerRef = useRef(undefined);
  const refresh = () => {
    if (session.getSnapshot().token && !document.hidden) refreshUnread();
  };
  const _watched = (() => session.getSnapshot().user?.id)();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    if (!_initialized.current) {
      _initialized.current = true;
      return;
    }
    const result = refresh(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  useEffect(() => {
    const result = (() => {
      refresh();
      _timerRef.current = setInterval(refresh, 30000);
    })();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  useEffect(() => () => (() => clearInterval(_timerRef.current))(), []);
  return {
    ...inputProps,
    session: session.getSnapshot(),
    notifications: notifications.getSnapshot()
  };
}
export default React.forwardRef(function NotificationBadge(props, ref) {
  const view = useNotificationBadgeState(props, ref);
  return <>{view.session.token ? <SiteLink to="/account/notifications" aria-label={"Thông báo: " + (view.notifications.count ?? "chưa tải") + " chưa đọc"}>
        {"Thông báo"}
        {view.notifications.count !== null ? <span>
            {" ("}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.notifications.count)}
            {")"}
          </span> : null}
        {view.notifications.error ? <span>{" · chưa tải"}</span> : null}
      </SiteLink> : null}</>;
});
