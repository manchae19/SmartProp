import React from "react";
import {
  useSetup,
  propsForSetup,
  emitForProps,
  exposeForSetup,
} from "../../state/store.js";
import {
  mergeProps,
  bindRef,
  renderList,
  display,
  modelProps,
  rootProps,
  Teleport,
} from "../rendering.js";
import { RouterLink, RouterView } from "../../routing/router.jsx";
import { computed } from "../../state/store.js";
import { useRoute } from "../../routing/router.jsx";
import { session } from "../../../features/auth/api.js";
import { canRequestBroker } from "../../../features/broker/brokerApplication.js";
import { canPublish, canAccessAdmin } from "../../lib/siteNavigation.js";
import NotificationBadge from "../../../features/notification/NotificationBadge.jsx";
import AppIcon from "../AppIcon.jsx";
function setup(__props) {
  propsForSetup(__props, {
    busy: Boolean,
    error: String,
  });
  const emit = emitForProps(__props, ["navigate", "logout"]);
  const route = useRoute();
  const links = computed(() => {
    if (!session.token)
      return [
        {
          label: "Đăng nhập",
          to: "/login",
        },
        {
          label: "Tạo tài khoản",
          to: "/register",
        },
      ];
    return [
      {
        label: "Hồ sơ cá nhân",
        to: "/account",
      },
      {
        label: "Tin đã lưu",
        to: "/favorites",
      },
      {
        label: "Tin nhắn",
        to: "/account/messages",
      },
      {
        label: "Phiên đăng nhập",
        to: "/account/sessions",
      },
      {
        label: "Xác minh email",
        to: "/account/verify-email",
      },
      {
        label: "Báo cáo của tôi",
        to: "/account/reports",
      },
      ...(canRequestBroker(session.user)
        ? [
            {
              label: "Quyền đăng tin",
              to: "/account/broker-application",
            },
          ]
        : []),
      ...(canPublish(session.user)
        ? [
            {
              label: "Đăng tin",
              to: "/post",
            },
            {
              label: "Quản lý tin đăng",
              to: "/my-listing",
            },
          ]
        : []),
    ];
  });
  return {
    computed,
    useRoute,
    session,
    canRequestBroker,
    canPublish,
    canAccessAdmin,
    NotificationBadge,
    AppIcon,
    emit,
    route,
    links,
  };
}
export default React.forwardRef(function AccountNavigation(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section
      {...mergeProps({
        "aria-label": "Tài khoản",
        className: "account-navigation border-t border-brand-line pt-5",
      })}
    >
      {ctx.session.token && ctx.canAccessAdmin(ctx.session.user) ? (
        <div
          {...mergeProps({
            className:
              "mb-5 rounded-panel border border-brand-line bg-brand-cream p-3",
            "data-admin-menu-group": "",
          })}
        >
          <p
            {...mergeProps({
              className:
                "px-3 pt-1 text-xs font-semibold tracking-[.16em] text-brand-accent",
            })}
          >
            {"KHÔNG GIAN QUẢN TRỊ"}
          </p>
          <RouterLink
            {...mergeProps({
              to: "/admin/dashboard",
              className: ["mt-2 flex min-h-12 items-center gap-3 rounded-control px-3 py-3 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-brand-gold", ctx.route.path.startsWith("/admin")
                ? "bg-brand-raised text-brand-navy"
                : "text-brand-navy hover:bg-brand-card"],
              
              "aria-current": ctx.route.path.startsWith("/admin")
                ? "location"
                : undefined,
              onClick: ($event) => {
                ctx.emit("navigate");
              },
            })}
          >
            <AppIcon
              {...mergeProps({
                name: "shield",
              })}
            />
            <span {...mergeProps({})}>{"Quản trị hệ thống"}</span>
            <AppIcon
              {...mergeProps({
                name: "arrow",
                className: "ml-auto !size-4",
              })}
            />
          </RouterLink>
        </div>
      ) : null}
      <p
        {...mergeProps({
          className:
            "mb-2 text-xs font-semibold tracking-[.2em] text-brand-accent",
        })}
      >
        {"TÀI KHOẢN CỦA BẠN"}
      </p>
      <nav
        {...mergeProps({
          "aria-label": "Chức năng tài khoản",
          className: "grid gap-1",
        })}
      >
        {renderList(ctx.links, (link) => (
          <RouterLink
            key={link.to}
            {...mergeProps({
              to: link.to,
              className: ["flex min-h-12 items-center gap-3 rounded-control px-3 py-3 text-sm font-medium transition-colors hover:bg-brand-surface focus-visible:outline-2 focus-visible:outline-brand-gold", ctx.route.path === link.to
                  ? "bg-brand-surface text-brand-accent"
                  : "text-brand-navy"],
              
              "aria-current": ctx.route.path === link.to ? "page" : undefined,
              onClick: ($event) => {
                ctx.emit("navigate");
              },
            })}
          >
            <AppIcon
              {...mergeProps({
                name:
                  {
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
                    "/register": "shield",
                  }[link.to] || "user",
              })}
            />
            <span {...mergeProps({})}>{display(link.label)}</span>
            <span className="drawer-chevron" aria-hidden="true">›</span>
          </RouterLink>
        ))}
        {ctx.session.token ? (
          <div
            {...mergeProps({
              className:
                "flex min-h-12 items-center gap-3 rounded-control px-3 py-3 text-sm font-medium hover:bg-brand-surface",
              onClick: ($event) => {
                ctx.emit("navigate");
              },
            })}
          >
            <AppIcon
              {...mergeProps({
                name: "bell",
              })}
            />
            <NotificationBadge {...mergeProps({})} />
          </div>
        ) : null}
      </nav>
      {ctx.error ? (
        <p
          {...mergeProps({
            role: "alert",
            className:
              "mt-4 rounded-control bg-[var(--ui-error-bg)] p-3 text-sm leading-6 text-[var(--ui-error-text)]",
          })}
        >
          {display(ctx.error)}
        </p>
      ) : null}
      {ctx.session.token ? (
        <button
          {...mergeProps({
            type: "button",
            disabled: ctx.busy,
            className: "sp-button sp-button-secondary mt-5 w-full",
            onClick: ($event) => {
              ctx.emit("logout");
            },
          })}
        >
          {display(ctx.busy ? "Đang đăng xuất…" : "Đăng xuất")}
        </button>
      ) : null}
    </section>,
  ]);
});
