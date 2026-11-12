import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { useAppNavigation } from "../../app/navigation.jsx";
import { api, session } from "../auth/api.js";
import { createContact } from "./contact.js";
function useContactPanelState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const props = {
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const router = useAppNavigation();
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  const [contact] = useState(() => createContact(api));
  const [ui] = useState(() => createStateStore({
    busy: false,
    data: null,
    message: "",
    status: 0,
    retryAt: 0
  }));
  useSyncExternalStore(ui.subscribe, ui.getSnapshot);
  const _sequenceRef = useRef(0);
  const [clock] = useState(() => createStateStore(Date.now()));
  useSyncExternalStore(clock.subscribe, clock.getSnapshot);
  const timer = useRef(null);
  useEffect(() => {
    timer.current = setInterval(() => clock.set(Date.now()), 1000);
    return () => clearInterval(timer.current);
  }, []);
  const [copiedPhone] = useState(() => createStateStore(false));
  useSyncExternalStore(copiedPhone.subscribe, copiedPhone.getSnapshot);
  const [copiedEmail] = useState(() => createStateStore(false));
  useSyncExternalStore(copiedEmail.subscribe, copiedEmail.getSnapshot);
  function copyText(text, isEmail = false) {
    if (!text) return;
    try {
      navigator.clipboard.writeText(text);
      if (isEmail) {
        copiedEmail.set(true);
        setTimeout(() => copiedEmail.set(false), 2000);
      } else {
        copiedPhone.set(true);
        setTimeout(() => copiedPhone.set(false), 2000);
      }
    } catch (e) {
      // fallback
    }
  }
  const reset = () => {
    _sequenceRef.current++;
    contact.reset();
    ui.edit(draftValue => Object.assign(draftValue, contact.state));
    _propsLatest.current.onRevealed?.(null);
  };
  const _watched = (() => [_props.current.propertyId, session.getSnapshot().user?.id, session.getSnapshot().token])();
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
    const result = reset(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  useEffect(() => () => (() => {
    clearInterval(timer.current);
    reset();
  })(), []);
  async function reveal() {
    if (!session.getSnapshot().token) {
      return _routerLatest.current.push({
        path: "/login",
        query: {
          reason: "login-required"
        }
      });
    }
    const run = ++_sequenceRef.current;
    ui.edit(draftValue => draftValue["busy"] = true);
    await contact.reveal(_props.current.propertyId);
    if (run === _sequenceRef.current) {
      ui.edit(draftValue => Object.assign(draftValue, contact.state));
      if (ui.getSnapshot().data?.available) {
        _propsLatest.current.onRevealed?.(ui.getSnapshot().data);
      }
    }
  }
  const telephone = value => /^\+?[0-9 ().-]{5,30}$/.test(value || "") ? "tel:" + value.replace(/[ ().-]/g, "") : null;
  const email = value => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value || "") ? "mailto:" + value : null;
  const zaloUrl = value => {
    if (!value) return null;
    const clean = value.replace(/[^0-9]/g, "");
    return clean ? `https://zalo.me/${clean}` : null;
  };
  return {
    ...inputProps,
    ui: ui.getSnapshot(),
    clock: clock.getSnapshot(),
    copiedPhone: copiedPhone.getSnapshot(),
    copiedEmail: copiedEmail.getSnapshot(),
    copyText,
    reveal,
    telephone,
    email,
    zaloUrl,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["propertyId", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function ContactPanel(props, ref) {
  const view = useContactPanelState(props, ref);
  return <><div data-ui-view="ContactPanel" data-testid="contact-panel" aria-live="polite" {...view.rootAttributes} className={classNames(["space-y-3", view.rootAttributes.className])}>
      {!view.ui.data?.available ? <div>
          <button type="button" className="w-full py-3.5 px-4 rounded-2xl bg-[var(--ui-soft)] hover:bg-[var(--ui-soft)] text-brand-navy font-bold text-sm tracking-wide shadow-md flex items-center justify-center gap-2.5 transition-all duration-150 active:scale-[0.98] disabled:opacity-50 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ui-border)] focus-visible:ring-offset-2" disabled={view.ui.busy || view.clock < view.ui.retryAt} onClick={$event => {
          return view.reveal?.($event);
        }}>
            {view.ui.busy ? <svg className="animate-spin w-4 h-4 text-brand-navy" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg> : <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
              </svg>}
            <span>
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.ui.busy ? "Đang xác thực thông tin…" : "Xem số điện thoại & Liên hệ")}
            </span>
          </button>
          <div className="flex items-center justify-center gap-1.5 text-[11px] text-brand-muted mt-2">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-brand-muted">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <span>
              {"Thông tin liên hệ bảo mật chống spam"}
            </span>
          </div>
        </div> : null}
      {view.ui.message ? <p role={view.ui.status ? "alert" : "status"} className="text-xs text-[var(--ui-warning-text)] bg-[var(--ui-warning-bg)]/90 p-3 rounded-xl border border-[var(--ui-warning-border)]/80 flex items-center gap-2">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0 text-[var(--ui-warning-text)]">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.ui.message)}</span>
        </p> : null}
      {view.ui.data?.available ? <React.Fragment>
          {view.ui.data.contactPhone ? <div className="space-y-2">
              <div className="flex items-center gap-2">
                {view.telephone(view.ui.data.contactPhone) ? <a href={view.telephone(view.ui.data.contactPhone)} className="flex-1 py-3.5 px-4 rounded-2xl bg-[var(--ui-success-bg)] hover:bg-[var(--ui-success-bg)] text-brand-navy font-bold text-sm shadow-md flex items-center justify-center gap-2.5 transition-all duration-150 active:scale-[0.98] text-center cursor-pointer">
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                    </svg>
                    <span>
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.ui.data.contactPhone)}
                      {" · Gọi ngay"}
                    </span>
                  </a> : <div className="flex-1 py-3.5 px-4 rounded-2xl bg-[var(--ui-success-bg)] text-brand-navy font-bold text-sm flex items-center justify-center gap-2">
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                    </svg>
                    <span>
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.ui.data.contactPhone)}
                    </span>
                  </div>}
                <button type="button" className="px-3.5 py-3.5 rounded-2xl border border-brand-line hover:bg-brand-card/80 active:scale-95 text-xs font-semibold text-brand-muted transition-all duration-150 shrink-0 cursor-pointer shadow-2xs" title={view.copiedPhone ? "Đã sao chép!" : "Sao chép số điện thoại"} onClick={$event => {
              view.copyText(view.ui.data.contactPhone, false);
            }}>
                  {view.copiedPhone ? <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="text-[var(--ui-success-text)]">
                      <polyline points="20 6 9 17 4 12" />
                    </svg> : <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                    </svg>}
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2 pt-1">
                {view.zaloUrl(view.ui.data.contactPhone) ? <a href={view.zaloUrl(view.ui.data.contactPhone)} target="_blank" rel="noopener noreferrer" className="py-2.5 px-3 rounded-xl bg-brand-card hover:bg-brand-card border border-brand-line text-brand-muted font-bold text-xs flex items-center justify-center gap-1.5 transition-all duration-150 cursor-pointer">
                    <span className="w-4 h-4 rounded-full bg-brand-card text-brand-navy text-[9px] font-black flex items-center justify-center">
                      {"Z"}
                    </span>
                    <span>{"Chat Zalo"}</span>
                  </a> : null}
                <button type="button" className="py-2.5 px-3 rounded-xl bg-brand-card hover:bg-brand-card border border-brand-line text-brand-muted font-semibold text-xs flex items-center justify-center gap-1.5 transition-all duration-150 cursor-pointer" onClick={$event => {
              view.copyText(view.ui.data.contactPhone, false);
            }}>
                  <span className="text-[11px]">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.copiedPhone ? "✓ Đã chép" : "📋 Sao chép số")}
                  </span>
                </button>
              </div>
            </div> : null}
          {view.ui.data.contactEmail ? <div className="p-3 rounded-2xl bg-brand-card border border-brand-line flex items-center justify-between gap-2.5">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-xl bg-brand-card text-[var(--ui-accent)] flex items-center justify-center text-xs shrink-0 border border-brand-line">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                    <polyline points="22,6 12,13 2,6" />
                  </svg>
                </div>
                <div className="min-w-0">
                  <p className="text-[10px] text-brand-muted font-medium uppercase tracking-wider">
                    {"Email liên hệ"}
                  </p>
                  {view.email(view.ui.data.contactEmail) ? <a href={view.email(view.ui.data.contactEmail)} className="text-xs font-bold text-[var(--ui-accent)] hover:text-[var(--ui-accent)] hover:underline truncate block">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.ui.data.contactEmail)}
                    </a> : <span className="text-xs font-bold text-[var(--ui-accent)] truncate block">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.ui.data.contactEmail)}
                    </span>}
                </div>
              </div>
              <button type="button" className="p-2 rounded-xl text-brand-muted hover:text-brand-muted hover:bg-brand-card transition cursor-pointer" title={view.copiedEmail ? "Đã sao chép email!" : "Sao chép email"} onClick={$event => {
            view.copyText(view.ui.data.contactEmail, true);
          }}>
                {view.copiedEmail ? <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="text-[var(--ui-success-text)]">
                    <polyline points="20 6 9 17 4 12" />
                  </svg> : <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                  </svg>}
              </button>
            </div> : null}
        </React.Fragment> : null}
      {view.clock < view.ui.retryAt ? <p className="text-xs text-brand-muted text-center">
          {" Có thể thử lại sau "}
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(Math.ceil((view.ui.retryAt - view.clock) / 1000))}
          {" giây. "}
        </p> : null}
    </div></>;
});
