import { afterPaint, classNames, chainHandlers } from "../../lib/ui.js";
import { createStateStore, stateKey } from "../../state/createStateStore.js";
import React, { useState, useSyncExternalStore, useId, useRef, useEffect } from "react";
import { SiteLink } from "../../../app/navigation.jsx";
import { useRouteState, useAppNavigation } from "../../../app/navigation.jsx";
import { session, logout, errorText } from "../../../features/auth/api.js";
import { canPublish, canAccessAdmin, scrollHomeSection } from "../../lib/siteNavigation.js";
import { normalizeFilters, listingLink } from "../../../features/property/listingFilters.js";
import { useComparison } from "../../hooks/useComparison.js";
import AppNavigation from "./AppNavigation.jsx";
import MobileDrawer from "./MobileDrawer.jsx";
import AccountNavigation from "./AccountNavigation.jsx";
import UserAvatar from "../UserAvatar.jsx";
import AppIcon from "../AppIcon.jsx";
import './AppHeader.css';
function useAppHeaderState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const route = useRouteState(),
    router = useAppNavigation(),
    compare = useComparison();
  const _compareLatest = useRef(compare);
  _compareLatest.current = compare;
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  const [open] = useState(() => createStateStore(false)),
    [busy] = useState(() => createStateStore(false)),
    [error] = useState(() => createStateStore("")),
    [trigger] = useState(() => createStateStore(null));
  useSyncExternalStore(trigger.subscribe, trigger.getSnapshot);
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  useSyncExternalStore(open.subscribe, open.getSnapshot);
  const drawerId = "app-navigation-" + useId();
  const getHomeLink = () => listingLink("/home", normalizeFilters(_routeLatest.current.query));
  const [restoreFocus] = useState(() => createStateStore(true));
  useSyncExternalStore(restoreFocus.subscribe, restoreFocus.getSnapshot);
  const _watched = (() => _routeLatest.current.fullPath)();
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
      if (open.getSnapshot()) {
        restoreFocus.set(false);
        open.set(false);
        await afterPaint();
        document.getElementById("page-content")?.focus({
          preventScroll: true
        });
      }
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  async function signOut() {
    if (busy.getSnapshot()) return;
    busy.set(true);
    error.set("");
    try {
      await logout();
      _compareLatest.current.clear();
      open.set(false);
      await _routerLatest.current.replace("/login");
    } catch (failure) {
      error.set(errorText(failure));
    } finally {
      busy.set(false);
    }
  }
  function toggle() {
    error.set("");
    restoreFocus.set(true);
    open.set(!open.getSnapshot());
  }
  function show() {
    restoreFocus.set(true);
    open.set(true);
  }
  async function drawerChanged(value) {
    if (!value && restoreFocus.getSnapshot()) {
      await afterPaint();
      trigger.getSnapshot()?.focus({
        preventScroll: true
      });
    }
  }
  async function navigate() {
    restoreFocus.set(false);
    open.set(false);
    await afterPaint();
    document.getElementById("page-content")?.focus({
      preventScroll: true
    });
  }
  return {
    ...inputProps,
    session: session.getSnapshot(),
    canPublish,
    canAccessAdmin,
    scrollHomeSection,
    normalizeFilters,
    listingLink,
    route,
    open: open.getSnapshot(),
    busy: busy.getSnapshot(),
    error: error.getSnapshot(),
    drawerId,
    homeLink: getHomeLink(),
    signOut,
    toggle,
    show,
    drawerChanged,
    navigate,
    updateTriggerValue: trigger.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateOpenValue: open.set
  };
}
export default React.forwardRef(function AppHeader(props, ref) {
  const view = useAppHeaderState(props, ref);
  const [scrolled, setScrolled] = React.useState(() => window.scrollY > 24);
  React.useEffect(() => {
    const update = () => setScrolled(window.scrollY > 24);
    update();
    window.addEventListener("scroll", update, {
      passive: true
    });
    return () => window.removeEventListener("scroll", update);
  }, []);
  return <><header data-scrolled={scrolled ? "true" : undefined} {...view.rootAttributes} className={classNames(["app-header sticky top-0 z-50 h-[var(--sp-header-height)] border-b border-brand-line bg-brand-cream/95 text-brand-navy backdrop-blur-xl", view.rootAttributes.className])}>
      <div className="sp-container flex h-full items-center justify-between gap-4">
        <SiteLink to={view.homeLink} className="header-brand inline-flex shrink-0 items-center gap-2.5 text-xl font-bold tracking-tight focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand-gold" aria-label="SmartProp — Trang chủ" onClick={$event => {
          view.route.path === "/home" && view.scrollHomeSection("home");
        }}>
          <span className="grid size-9 place-items-center rounded-control bg-brand-raised text-lg text-brand-navy">
            {"S"}
          </span>
          <span>
            {"SmartProp"}
            <span className="text-brand-accent">
              {"."}
            </span>
            <span className="mt-0.5 hidden text-[13px] font-normal tracking-normal text-brand-muted 2xl:block">
              {"Không gian sống · Dữ liệu thông minh"}
            </span>
          </span>
        </SiteLink>
        <nav aria-label="Điều hướng chính" className="hidden lg:flex items-center gap-1 xl:gap-2">
          <SiteLink to={view.listingLink("/listings", view.normalizeFilters(view.route.query))} className={classNames(["rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold", view.route.path === "/listings" || view.route.path.startsWith("/listing/") ? "bg-brand-raised text-brand-navy shadow-sm" : "text-brand-navy hover:bg-brand-surface"])}>
            {"Bất động sản"}
          </SiteLink>
          <SiteLink to="/projects" className={classNames(["rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold", view.route.path.startsWith("/projects") ? "bg-brand-raised text-brand-navy shadow-sm" : "text-brand-navy hover:bg-brand-surface"])}>
            {"Dự án"}
          </SiteLink>
          <SiteLink to="/news" className={classNames(["rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold", view.route.path === "/news" || view.route.path.startsWith("/news/") ? "bg-brand-raised text-brand-navy shadow-sm" : "text-brand-navy hover:bg-brand-surface"])} data-news-header={true}>
            {"Tin tức"}
          </SiteLink>
          <SiteLink to={view.listingLink("/map", view.normalizeFilters(view.route.query))} className={classNames(["rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold", view.route.path === "/map" ? "bg-brand-raised text-brand-navy shadow-sm" : "text-brand-navy hover:bg-brand-surface"])}>
            {"Bản đồ GIS"}
          </SiteLink>
          <SiteLink to="/market" className={classNames(["inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold", view.route.path.startsWith("/market") ? "bg-brand-raised text-brand-navy shadow-sm" : "text-brand-navy hover:bg-brand-surface"])} data-market-header={true}>
            <span>{"Thị trường BĐS"}</span>
            <span className={classNames(["rounded-full px-1.5 py-0.5 text-[10px] font-bold border transition-colors", view.route.path.startsWith("/market") ? "bg-[var(--ui-soft)] text-[var(--ui-accent)] border-[var(--ui-border)]" : "bg-brand-gold/20 text-[var(--ui-warning-text)] border-brand-gold/40"])}>
              {"Mới"}
            </span>
          </SiteLink>
          <SiteLink to="/valuation" className={classNames(["rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold", view.route.path === "/valuation" ? "bg-brand-raised text-brand-navy shadow-sm" : "text-brand-navy hover:bg-brand-surface"])}>
            {"Định giá"}
          </SiteLink>
        </nav>
        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <SiteLink to="/advisor" className="sp-button sp-button-secondary hidden lg:inline-flex" aria-current={view.route.path === "/advisor" || view.route.path.startsWith("/advisor/") ? "page" : undefined} data-advisor-header={true}>
            {"Tư vấn BĐS"}
          </SiteLink>
          {view.session.token && view.canAccessAdmin(view.session.user) ? <SiteLink to="/admin/dashboard" className={classNames(["sp-button sp-button-secondary gap-2 px-3 sm:px-4", view.route.path.startsWith("/admin") ? "!bg-brand-raised !text-brand-navy" : ""])} aria-current={view.route.path.startsWith("/admin") ? "location" : undefined} aria-label="Trang quản trị" data-admin-entry={true}>
              <AppIcon name="shield" className="!size-4" />
              <span className="hidden sm:inline">
                {"Quản trị"}
              </span>
            </SiteLink> : null}
          {view.session.token && view.canPublish(view.session.user) ? <SiteLink to="/post" className="sp-button hidden border-brand-gold bg-brand-highlight text-brand-navy sm:inline-flex">
              {"Đăng tin ↗"}
            </SiteLink> : !view.session.token ? <SiteLink to="/login" className="hidden text-xs font-semibold text-brand-navy sm:block">
              {"Đăng nhập"}
            </SiteLink> : null}
          <button ref={view.updateTriggerValue} type="button" aria-expanded={view.open} aria-controls={view.drawerId} aria-haspopup="dialog" aria-label={view.session.token ? "Mở menu tài khoản và điều hướng" : "Mở menu điều hướng"} className="sp-button sp-button-secondary gap-2 px-3" data-app-menu-trigger="" onClick={$event => {
            return view.toggle?.($event);
          }} onKeyDown={$event => {
            if ($event.key !== "ArrowDown") return;
            $event.preventDefault();
            return view.show?.($event);
          }}>
            {view.session.token ? <UserAvatar name={view.session.user?.fullName} size={32} /> : null}
            <svg className="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" aria-hidden="true">
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            <span className="hidden text-sm sm:inline">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.session.token ? "Tài khoản" : "Menu")}
            </span>
          </button>
        </div>
      </div>
      <MobileDrawer id={view.drawerId} onClosed={$event => {
        view.drawerChanged(false);
      }} open={view.open} onUpdateOpen={chainHandlers($event => {
        return view.drawerChanged?.($event);
      }, $value => {
        view.updateOpenValue($value);
      })}>
        <SiteLink className="drawer-profile" to={view.session.token ? "/account" : "/login"} onClick={() => view.navigate()}>
          <UserAvatar name={view.session.user?.fullName || "SmartProp"} size={44} />
          <span className="drawer-profile-copy"><strong>{view.session.user?.fullName || "Chào mừng đến SmartProp"}</strong><small>{view.session.token ? {
                BUYER: "Người mua / người thuê",
                BROKER: "Chủ nhà / môi giới",
                ADMIN: "Quản trị viên"
              }[view.session.user?.role] || "Thành viên" : "Đăng nhập để quản lý tài khoản"}</small></span>
        </SiteLink>
        <div className="drawer-explore mb-5">
          <p className="mb-2 text-xs font-semibold tracking-[.2em] text-brand-accent">
            {"KHÁM PHÁ"}
          </p>
          <AppNavigation vertical={true} onNavigate={$event => {
            return view.navigate?.($event);
          }} />
        </div>
        <AccountNavigation busy={view.busy} error={view.error} onNavigate={$event => {
          return view.navigate?.($event);
        }} onLogout={$event => {
          return view.signOut?.($event);
        }} />
      </MobileDrawer>
    </header></>;
});
