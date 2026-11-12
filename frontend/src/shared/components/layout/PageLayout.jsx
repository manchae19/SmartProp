import { afterPaint, classNames } from "../../lib/ui.js";
import { stateKey } from "../../state/createStateStore.js";
import React, { useRef, useEffect } from "react";
import { useRouteState } from "../../../app/navigation.jsx";
import AppHeader from "./AppHeader.jsx";
import AppFooter from "./AppFooter.jsx";
import "./PageLayout.css";
function usePageLayoutState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const route = useRouteState();
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  const getMessengerPage = () => _routeLatest.current.path === "/advisor/chat";
  const _watched = (() => _routeLatest.current.path)();
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
    const result = (async () => {
      await afterPaint();
      document.getElementById("page-content")?.focus({
        preventScroll: true
      });
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  return {
    ...inputProps,
    messengerPage: getMessengerPage(),
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function PageLayout(props, ref) {
  const view = usePageLayoutState(props, ref);
  return <><div data-sp-292ae0bf="" {...view.rootAttributes} className={classNames([classNames(["page-layout flex min-h-dvh flex-col bg-brand-cream text-brand-navy", {
      "messenger-layout": view.messengerPage
    }]), view.rootAttributes.className])}>
      <a href="#page-content" className="fixed -top-20 left-4 z-[100] rounded-control bg-brand-card px-5 py-3 text-sm font-semibold shadow-lg focus:top-3" data-sp-292ae0bf="">
        {"Đến nội dung chính"}
      </a>
      <AppHeader data-sp-292ae0bf="" />
      <main id="page-content" tabIndex="-1" className={classNames(["min-w-0 flex-1 outline-none", {
        "messenger-main": view.messengerPage
      }])} data-sp-292ae0bf="">
        {view.children ?? null}
      </main>
      {!view.messengerPage ? <AppFooter data-sp-292ae0bf="" /> : null}
    </div></>;
});
