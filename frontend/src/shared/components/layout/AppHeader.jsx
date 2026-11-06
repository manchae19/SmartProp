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
import { computed, nextTick, ref, useId, watch } from "../../state/store.js";
import { useRoute, useRouter } from "../../routing/router.jsx";
import { session, logout, errorText } from "../../../features/auth/api.js";
import {
  canPublish,
  canAccessAdmin,
  scrollHomeSection,
} from "../../lib/siteNavigation.js";
import {
  normalizeFilters,
  listingLink,
} from "../../../features/property/listingFilters.js";
import { useComparison } from "../../hooks/useComparison.js";
import AppNavigation from "./AppNavigation.jsx";
import MobileDrawer from "./MobileDrawer.jsx";
import AccountNavigation from "./AccountNavigation.jsx";
import UserAvatar from "../UserAvatar.jsx";
import AppIcon from "../AppIcon.jsx";
function setup(__props) {
  const route = useRoute(),
    router = useRouter(),
    compare = useComparison();
  const open = ref(false),
    busy = ref(false),
    error = ref(""),
    trigger = ref(null);
  const drawerId = "app-navigation-" + useId();
  const homeLink = computed(() =>
    listingLink("/home", normalizeFilters(route.query)),
  );
  const restoreFocus = ref(true);
  watch(
    () => route.fullPath,
    async () => {
      if (open.value) {
        restoreFocus.value = false;
        open.value = false;
        await nextTick();
        document.getElementById("page-content")?.focus({
          preventScroll: true,
        });
      }
    },
  );
  async function signOut() {
    if (busy.value) return;
    busy.value = true;
    error.value = "";
    try {
      await logout();
      compare.clear();
      open.value = false;
      await router.replace("/login");
    } catch (failure) {
      error.value = errorText(failure);
    } finally {
      busy.value = false;
    }
  }
  function toggle() {
    error.value = "";
    restoreFocus.value = true;
    open.value = !open.value;
  }
  function show() {
    restoreFocus.value = true;
    open.value = true;
  }
  async function drawerChanged(value) {
    if (!value && restoreFocus.value) {
      await nextTick();
      trigger.value?.focus({
        preventScroll: true,
      });
    }
  }
  async function navigate() {
    restoreFocus.value = false;
    open.value = false;
    await nextTick();
    document.getElementById("page-content")?.focus({
      preventScroll: true,
    });
  }
  return {
    computed,
    nextTick,
    ref,
    useId,
    watch,
    useRoute,
    useRouter,
    session,
    logout,
    errorText,
    canPublish,
    canAccessAdmin,
    scrollHomeSection,
    normalizeFilters,
    listingLink,
    useComparison,
    AppNavigation,
    MobileDrawer,
    AccountNavigation,
    UserAvatar,
    AppIcon,
    route,
    router,
    compare,
    open,
    busy,
    error,
    trigger,
    drawerId,
    homeLink,
    restoreFocus,
    signOut,
    toggle,
    show,
    drawerChanged,
    navigate,
  };
}
export default React.forwardRef(function AppHeader(props, ref) {
  const ctx = useSetup(setup, props, ref);
  const [scrolled, setScrolled] = React.useState(() => window.scrollY > 24);
  React.useEffect(() => {
    const update = () => setScrolled(window.scrollY > 24);
    update();
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);
  return rootProps(ctx, [
    <header
      {...mergeProps({
        className:
          "app-header sticky top-0 z-50 h-[var(--sp-header-height)] border-b border-brand-line bg-brand-cream/95 text-brand-navy backdrop-blur-xl",
        "data-scrolled": scrolled ? "true" : undefined,
      })}
    >
      <div
        {...mergeProps({
          className:
            "sp-container flex h-full items-center justify-between gap-4",
        })}
      >
        <RouterLink
          {...mergeProps({
            to: ctx.homeLink,
            className:
              "inline-flex shrink-0 items-center gap-2.5 text-xl font-bold tracking-tight focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand-gold",
            "aria-label": "SmartProp — Trang chủ",
            onClick: ($event) => {
              ctx.route.path === "/home" && ctx.scrollHomeSection("home");
            },
          })}
        >
          <span
            {...mergeProps({
              className:
                "grid size-9 place-items-center rounded-control bg-brand-raised text-lg text-brand-navy",
            })}
          >
            {"S"}
          </span>
          <span {...mergeProps({})}>
            {"SmartProp"}
            <span
              {...mergeProps({
                className: "text-brand-accent",
              })}
            >
              {"."}
            </span>
            <span
              {...mergeProps({
                className:
                  "mt-0.5 hidden text-[13px] font-normal tracking-normal text-brand-muted 2xl:block",
              })}
            >
              {"Không gian sống · Dữ liệu thông minh"}
            </span>
          </span>
        </RouterLink>
        <nav
          {...mergeProps({
            "aria-label": "Điều hướng chính",
            className: "hidden lg:flex items-center gap-1 xl:gap-2",
          })}
        >
          <RouterLink
            {...mergeProps({
              to: ctx.listingLink(
                "/listings",
                ctx.normalizeFilters(ctx.route.query),
              ),
              className: ["rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold", ctx.route.path === "/listings" ||
                ctx.route.path.startsWith("/listing/")
                  ? "bg-brand-raised text-brand-navy shadow-sm"
                  : "text-brand-navy hover:bg-brand-surface"],
              
            })}
          >
            {"Bất động sản"}
          </RouterLink>
          <RouterLink
            {...mergeProps({
              to: "/projects",
              className: ["rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold", ctx.route.path.startsWith("/projects")
                ? "bg-brand-raised text-brand-navy shadow-sm"
                : "text-brand-navy hover:bg-brand-surface"],
              
            })}
          >
            {"Dự án"}
          </RouterLink>
          <RouterLink
            {...mergeProps({
              to: ctx.listingLink(
                "/map",
                ctx.normalizeFilters(ctx.route.query),
              ),
              className: ["rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold", ctx.route.path === "/map"
                  ? "bg-brand-raised text-brand-navy shadow-sm"
                  : "text-brand-navy hover:bg-brand-surface"],
              
            })}
          >
            {"Bản đồ GIS"}
          </RouterLink>
          <RouterLink
            {...mergeProps({
              to: "/market",
              className: ["inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold", ctx.route.path.startsWith("/market")
                ? "bg-brand-raised text-brand-navy shadow-sm"
                : "text-brand-navy hover:bg-brand-surface"],
              
              "data-market-header": true,
            })}
          >
            <span {...mergeProps({})}>{"Thị trường BĐS"}</span>
            <span
              {...mergeProps({
                className: ["rounded-full px-1.5 py-0.5 text-[10px] font-bold border transition-colors", ctx.route.path.startsWith("/market")
                  ? "bg-[var(--ui-soft)] text-[var(--ui-accent)] border-[var(--ui-border)]"
                  : "bg-brand-gold/20 text-[var(--ui-warning-text)] border-brand-gold/40"],
                
              })}
            >
              {"Mới"}
            </span>
          </RouterLink>
          <RouterLink
            {...mergeProps({
              to: "/valuation",
              className: ["rounded-lg px-2.5 py-1.5 text-[13px] xl:text-sm font-semibold transition focus-visible:outline-brand-gold", ctx.route.path === "/valuation"
                  ? "bg-brand-raised text-brand-navy shadow-sm"
                  : "text-brand-navy hover:bg-brand-surface"],
              
            })}
          >
            {"Định giá"}
          </RouterLink>
        </nav>
        <div
          {...mergeProps({
            className: "flex shrink-0 items-center gap-2 sm:gap-3",
          })}
        >
          <RouterLink
            {...mergeProps({
              to: "/advisor",
              className: "sp-button sp-button-secondary hidden lg:inline-flex",
              "aria-current":
                ctx.route.path === "/advisor" ||
                ctx.route.path.startsWith("/advisor/")
                  ? "page"
                  : undefined,
              "data-advisor-header": true,
            })}
          >
            {"Tư vấn BĐS"}
          </RouterLink>
          {ctx.session.token && ctx.canAccessAdmin(ctx.session.user) ? (
            <RouterLink
              {...mergeProps({
                to: "/admin/dashboard",
                className: ["sp-button sp-button-secondary gap-2 px-3 sm:px-4", ctx.route.path.startsWith("/admin")
                  ? "!bg-brand-raised !text-brand-navy"
                  : ""],
                
                "aria-current": ctx.route.path.startsWith("/admin")
                  ? "location"
                  : undefined,
                "aria-label": "Trang quản trị",
                "data-admin-entry": true,
              })}
            >
              <AppIcon
                {...mergeProps({
                  name: "shield",
                  className: "!size-4",
                })}
              />
              <span
                {...mergeProps({
                  className: "hidden sm:inline",
                })}
              >
                {"Quản trị"}
              </span>
            </RouterLink>
          ) : null}
          {ctx.session.token && ctx.canPublish(ctx.session.user) ? (
            <RouterLink
              {...mergeProps({
                to: "/post",
                className:
                  "sp-button hidden border-brand-gold bg-brand-highlight text-brand-navy sm:inline-flex",
              })}
            >
              {"Đăng tin ↗"}
            </RouterLink>
          ) : !ctx.session.token ? (
            <RouterLink
              {...mergeProps({
                to: "/login",
                className:
                  "hidden text-xs font-semibold text-brand-navy sm:block",
              })}
            >
              {"Đăng nhập"}
            </RouterLink>
          ) : null}
          <button
            {...mergeProps({
              ref: bindRef(ctx, "trigger"),
              type: "button",
              "aria-expanded": ctx.open,
              "aria-controls": ctx.drawerId,
              "aria-haspopup": "dialog",
              "aria-label": ctx.session.token
                ? "Mở menu tài khoản và điều hướng"
                : "Mở menu điều hướng",
              className: "sp-button sp-button-secondary gap-2 px-3",
              "data-app-menu-trigger": "",
              onClick: ($event) => {
                return ctx.toggle?.($event);
              },
              onKeyDown: ($event) => {
                if ($event.key !== "ArrowDown") return;
                $event.preventDefault();
                return ctx.show?.($event);
              },
            })}
          >
            {ctx.session.token ? (
              <UserAvatar
                {...mergeProps({
                  name: ctx.session.user?.fullName,
                  size: 32,
                })}
              />
            ) : null}
            <svg
              {...mergeProps({
                className: "size-5",
                viewBox: "0 0 24 24",
                fill: "none",
                stroke: "currentColor",
                strokeWidth: "1.7",
                strokeLinecap: "round",
                "aria-hidden": "true",
              })}
            >
              <path
                {...mergeProps({
                  d: "M4 6h16M4 12h16M4 18h16",
                })}
              />
            </svg>
            <span
              {...mergeProps({
                className: "hidden text-sm sm:inline",
              })}
            >
              {display(ctx.session.token ? "Tài khoản" : "Menu")}
            </span>
          </button>
        </div>
      </div>
      <MobileDrawer
        {...mergeProps(
          {
            id: ctx.drawerId,
            onUpdateOpen: ($event) => {
              return ctx.drawerChanged?.($event);
            },
            onClosed: ($event) => {
              ctx.drawerChanged(false);
            },
          },
          {
            open: ctx.open,
            onUpdateOpen: ($value) => {
              ctx.open = $value;
            },
          },
        )}
      >
        <RouterLink className="drawer-profile" to={ctx.session.token ? "/account" : "/login"} onClick={() => ctx.navigate()}>
          <UserAvatar name={ctx.session.user?.fullName || "SmartProp"} size={44} />
          <span className="drawer-profile-copy"><strong>{ctx.session.user?.fullName || "Chào mừng đến SmartProp"}</strong><small>{ctx.session.token ? ({ BUYER: "Người mua / người thuê", BROKER: "Chủ nhà / môi giới", ADMIN: "Quản trị viên" }[ctx.session.user?.role] || "Thành viên") : "Đăng nhập để quản lý tài khoản"}</small></span>
        </RouterLink>
        <div
          {...mergeProps({
            className: "drawer-explore mb-5",
          })}
        >
          <p
            {...mergeProps({
              className:
                "mb-2 text-xs font-semibold tracking-[.2em] text-brand-accent",
            })}
          >
            {"KHÁM PHÁ"}
          </p>
          <AppNavigation
            {...mergeProps({
              vertical: true,
              onNavigate: ($event) => {
                return ctx.navigate?.($event);
              },
            })}
          />
        </div>
        <AccountNavigation
          {...mergeProps({
            busy: ctx.busy,
            error: ctx.error,
            onNavigate: ($event) => {
              return ctx.navigate?.($event);
            },
            onLogout: ($event) => {
              return ctx.signOut?.($event);
            },
          })}
        />
      </MobileDrawer>
    </header>,
  ]);
});
