import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { useRouteState } from "../../app/navigation.jsx";
import { api, session, errorText } from "../auth/api.js";
import BusinessPage from "../../shared/components/BusinessPage.jsx";
import LegalDocuments from "./LegalDocuments.jsx";
function useLegalDocumentsViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const route = useRouteState(),
    [managed] = useState(() => createStateStore(null)),
    [error] = useState(() => createStateStore("")),
    [busy] = useState(() => createStateStore(false));
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(managed.subscribe, managed.getSnapshot);
  const _sequenceRef = useRef(0);
  async function load() {
    const run = ++_sequenceRef.current;
    managed.set(null);
    error.set("");
    busy.set(true);
    try {
      const result = await api((session.getSnapshot().user?.role === "ADMIN" ? "/admin/properties/" : "/users/me/properties/") + _routeLatest.current.params.id);
      if (run === _sequenceRef.current) managed.set(result);
    } catch (e) {
      if (run === _sequenceRef.current) error.set(errorText(e));
    } finally {
      if (run === _sequenceRef.current) busy.set(false);
    }
  }
  const _watched = (() => [_routeLatest.current.params.id, session.getSnapshot().user?.id])();
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
    managed: managed.getSnapshot(),
    error: error.getSnapshot(),
    busy: busy.getSnapshot(),
    load,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function LegalDocumentsView(props, ref) {
  const view = useLegalDocumentsViewState(props, ref);
  return <><BusinessPage data-ui-view="LegalDocumentsView" title="Quản lý hồ sơ pháp lý" {...view.rootAttributes}>
      {view.busy ? <p role="status">
          {"Đang tải quyền quản lý tin…"}
        </p> : null}
      {view.error ? <p role="alert">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}{" "}
          <button onClick={$event => {
          return view.load?.($event);
        }}>
            {"Thử lại"}
          </button>
        </p> : null}
      {view.managed ? <React.Fragment>
          <h2>{(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.managed.property.title)}</h2>
          <LegalDocuments key={view.managed.property.id} propertyId={view.managed.property.id} ownerId={view.managed.ownerId} />
        </React.Fragment> : null}
    </BusinessPage></>;
});
