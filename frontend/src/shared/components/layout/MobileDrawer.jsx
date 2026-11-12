import { afterPaint, classNames } from "../../lib/ui.js";
import { createStateStore, stateKey } from "../../state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useId, useEffect, useImperativeHandle } from "react";
import "./MobileDrawer.css";
function useMobileDrawerState(inputProps, forwardedRef) {
  inputProps = {
    title: "Khám phá SmartProp",
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    title: "Khám phá SmartProp",
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [panel] = useState(() => createStateStore(null)),
    [closeButton] = useState(() => createStateStore(null)),
    titleId = useId();
  useSyncExternalStore(closeButton.subscribe, closeButton.getSnapshot);
  useSyncExternalStore(panel.subscribe, panel.getSnapshot);
  const _previousOverflowRef = useRef(undefined),
    _lockedRef = useRef(false),
    _pendingClosesRef = useRef(0);
  function unlock() {
    if (_lockedRef.current) {
      document.body.style.overflow = _previousOverflowRef.current;
      _lockedRef.current = false;
    }
  }
  function close() {
    _propsLatest.current.onUpdateOpen?.(false);
  }
  function closePanel() {
    if (panel.getSnapshot()?.open) {
      _pendingClosesRef.current++;
      panel.getSnapshot().close();
    }
    unlock();
  }
  function closed() {
    if (_pendingClosesRef.current) {
      _pendingClosesRef.current--;
      if (!_props.current.open && !panel.getSnapshot()?.open) _propsLatest.current.onClosed?.();
      return;
    }
    if (panel.getSnapshot()?.open) return;
    unlock();
    _propsLatest.current.onUpdateOpen?.(false);
    _propsLatest.current.onClosed?.();
  }
  function backdrop(event) {
    if (event.target !== panel.getSnapshot()) return;
    const box = panel.getSnapshot().getBoundingClientRect();
    if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) close();
  }
  function trapTab(event) {
    if (event.key !== "Tab" || !panel.getSnapshot()?.open) return;
    const items = [...panel.getSnapshot().querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])')].filter(element => element.getClientRects().length && !element.closest("[inert]"));
    const first = items[0],
      last = items.at(-1);
    if (!first) {
      event.preventDefault();
      panel.getSnapshot().focus();
      return;
    }
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
  const _watched = (() => _props.current.open)();
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
    const result = (async value => {
      await afterPaint();
      if (!panel.getSnapshot() || _props.current.open !== value) return;
      if (value) {
        if (!panel.getSnapshot().open) panel.getSnapshot().showModal();
        if (!_lockedRef.current) {
          _previousOverflowRef.current = document.body.style.overflow;
          _lockedRef.current = true;
          document.body.style.overflow = "hidden";
        }
        closeButton.getSnapshot()?.focus();
      } else closePanel();
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  useEffect(() => () => closePanel(), []);
  useImperativeHandle(forwardedRef, () => ({
    id: titleId
  }), []);
  return {
    ...inputProps,
    titleId,
    close,
    closed,
    backdrop,
    trapTab,
    updatePanelValue: panel.set,
    updateCloseButtonValue: closeButton.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["open", "title", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function MobileDrawer(props, ref) {
  const view = useMobileDrawerState(props, ref);
  return <><dialog ref={view.updatePanelValue} aria-labelledby={view.titleId} onCancel={$event => {
      $event.preventDefault();
      return view.close?.($event);
    }} onClose={$event => {
      return view.closed?.($event);
    }} onClick={$event => {
      return view.backdrop?.($event);
    }} onKeyDown={$event => {
      return view.trapTab?.($event);
    }} data-sp-16c95175="" {...view.rootAttributes} className={classNames(["mobile-drawer fixed inset-y-0 right-0 left-auto m-0 h-dvh max-h-none w-[min(25rem,calc(100vw-1.25rem))] max-w-none border-0 bg-brand-card p-0 text-brand-navy shadow-2xl", view.rootAttributes.className])}>
      <div className="flex h-full flex-col" data-sp-16c95175="">
        <div className="drawer-heading flex shrink-0 items-center justify-between gap-4 px-5 py-5" data-sp-16c95175="">
          <div>
            <p className="drawer-eyebrow">SMARTPROP · ĐÀ NẴNG</p>
          <h2 id={view.titleId} className="text-lg font-semibold" data-sp-16c95175="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.title)}
          </h2>
          </div>
          <button ref={view.updateCloseButtonValue} type="button" className="sp-icon-button" aria-label="Đóng menu" onClick={$event => {
            return view.close?.($event);
          }} data-sp-16c95175="">
            <svg className="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true" data-sp-16c95175="">
              <path d="m6 6 12 12M6 18 18 6" data-sp-16c95175="" />
            </svg>
          </button>
        </div>
        {view.open ? <div className="drawer-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain p-5" data-sp-16c95175="">
            {view.children ?? null}
          </div> : null}
      </div>
    </dialog></>;
});
