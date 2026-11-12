import { classNames } from "../../lib/ui.js";
import React, { useSyncExternalStore, useRef } from "react";
import { SiteLink } from "../../../app/navigation.jsx";
import { useRouteState } from "../../../app/navigation.jsx";
import { session } from "../../../features/auth/api.js";
import { canRequestBroker } from "../../../features/broker/brokerApplication.js";
import { canPublish, canAccessAdmin } from "../../lib/siteNavigation.js";
import NotificationBadge from "../../../features/notification/NotificationBadge.jsx";
import AppIcon from "../AppIcon.jsx";
function useAccountNavigationState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const route = useRouteState();
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  const getLinks = () => {
    if (!session.getSnapshot().token) return [{
      label: "Đăng nhập",
      to: "/login"
    }, {
      label: "Tạo tài khoản",
      to: "/register"
    }];
    return [{
      label: "Hồ sơ cá nhân",
      to: "/account"
    }, {
      label: "Tin đã lưu",
      to: "/favorites"
    }, {
      label: "Tin nhắn",
      to: "/account/messages"
    }, {
      label: "Phiên đăng nhập",
      to: "/account/sessions"
    }, {
      label: "Xác minh email",
      to: "/account/verify-email"
    }, {
      label: "Báo cáo của tôi",
      to: "/account/reports"
    }, ...(canRequestBroker(session.getSnapshot().user) ? [{
      label: "Quyền đăng tin",
      to: "/account/broker-application"
    }] : []), ...(canPublish(session.getSnapshot().user) ? [{
      label: "Đăng tin",
      to: "/post"
    }, {
      label: "Quản lý tin đăng",
      to: "/my-listing"
    }] : [])];
  };
  return {
    ...inputProps,
    session: session.getSnapshot(),
    canAccessAdmin,
    route,
    links: getLinks(),
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["busy", "error", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function AccountNavigation(props, ref) {
  const view = useAccountNavigationState(props, ref);
  return <><section aria-label="Tài khoản" {...view.rootAttributes} className={classNames(["account-navigation border-t border-brand-line pt-5", view.rootAttributes.className])}>
      {view.session.token && view.canAccessAdmin(view.session.user) ? <div className="mb-5 rounded-panel border border-brand-line bg-brand-cream p-3" data-admin-menu-group="">
          <p className="px-3 pt-1 text-xs font-semibold tracking-[.16em] text-brand-accent">
            {"KHÔNG GIAN QUẢN TRỊ"}
          </p>
          <SiteLink to="/admin/dashboard" className={classNames(["mt-2 flex min-h-12 items-center gap-3 rounded-control px-3 py-3 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-brand-gold", view.route.path.startsWith("/admin") ? "bg-brand-raised text-brand-navy" : "text-brand-navy hover:bg-brand-card"])} aria-current={view.route.path.startsWith("/admin") ? "location" : undefined} onClick={$event => {
          view.onNavigate?.();
        }}>
            <AppIcon name="shield" />
            <span>{"Quản trị hệ thống"}</span>
            <AppIcon name="arrow" className="ml-auto !size-4" />
          </SiteLink>
        </div> : null}
      <p className="mb-2 text-xs font-semibold tracking-[.2em] text-brand-accent">
        {"TÀI KHOẢN CỦA BẠN"}
      </p>
      <nav aria-label="Chức năng tài khoản" className="grid gap-1">
        {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.links, link => <SiteLink key={link.to} to={link.to} className={classNames(["flex min-h-12 items-center gap-3 rounded-control px-3 py-3 text-sm font-medium transition-colors hover:bg-brand-surface focus-visible:outline-2 focus-visible:outline-brand-gold", view.route.path === link.to ? "bg-brand-surface text-brand-accent" : "text-brand-navy"])} aria-current={view.route.path === link.to ? "page" : undefined} onClick={$event => {
          view.onNavigate?.();
        }}>
            <AppIcon name={{
            "/account": "user",
            "/favorites": "heart",
            "/account/messages": "messages",
            "/account/sessions": "clock",
            "/account/verify-email": "email",
            "/account/reports": "report",
            "/account/broker-application": "briefcase",
            "/post": "edit",
            "/my-listing": "properties",
            "/admin": "shield",
            "/login": "user",
            "/register": "shield"
          }[link.to] || "user"} />
            <span>{(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(link.label)}</span>
            <span className="drawer-chevron" aria-hidden="true">›</span>
          </SiteLink>)}
        {view.session.token ? <div className="flex min-h-12 items-center gap-3 rounded-control px-3 py-3 text-sm font-medium hover:bg-brand-surface" onClick={$event => {
          view.onNavigate?.();
        }}>
            <AppIcon name="bell" />
            <NotificationBadge />
          </div> : null}
      </nav>
      {view.error ? <p role="alert" className="mt-4 rounded-control bg-[var(--ui-error-bg)] p-3 text-sm leading-6 text-[var(--ui-error-text)]">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}
        </p> : null}
      {view.session.token ? <button type="button" disabled={view.busy} className="sp-button sp-button-secondary mt-5 w-full" onClick={$event => {
        view.onLogout?.();
      }}>
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.busy ? "Đang đăng xuất…" : "Đăng xuất")}
        </button> : null}
    </section></>;
});
