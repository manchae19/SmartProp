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
import {
  listingLink,
  normalizeFilters,
} from "../../../features/property/listingFilters.js";
import { session } from "../../../features/auth/api.js";
function setup(__props) {
  const route = useRoute(),
    filters = computed(() => normalizeFilters(route.query));
  return {
    computed,
    useRoute,
    listingLink,
    normalizeFilters,
    session,
    route,
    filters,
  };
}
export default React.forwardRef(function AppFooter(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <footer
      {...mergeProps({
        id: "account",
        className: "app-footer mt-auto bg-brand-raised py-10 pb-36 text-brand-navy",
      })}
    >
      <div
        {...mergeProps({
          className: "sp-container grid gap-8 md:grid-cols-[1.4fr_1fr_1fr]",
        })}
      >
        <div {...mergeProps({})}>
          <RouterLink
            {...mergeProps({
              to: ctx.listingLink("/home", ctx.filters),
              className: "text-2xl font-bold tracking-tight",
            })}
          >
            {"SmartProp"}
            <span
              {...mergeProps({
                className: "text-brand-highlight",
              })}
            >
              {"."}
            </span>
          </RouterLink>
          <p
            {...mergeProps({
              className: "mt-3 max-w-sm text-sm leading-7 text-brand-navy",
            })}
          >
            {"Khám phá bất động sản và không gian sống tại Đà Nẵng."}
          </p>
        </div>
        <nav
          {...mergeProps({
            "aria-label": "Khám phá cuối trang",
            className: "grid content-start gap-3 text-sm text-brand-navy",
          })}
        >
          <RouterLink
            {...mergeProps({
              to: ctx.listingLink("/listings", ctx.filters),
            })}
          >
            {"Bất động sản"}
          </RouterLink>
          <RouterLink
            {...mergeProps({
              to: "/projects",
            })}
          >
            {"Dự án"}
          </RouterLink>
          <RouterLink
            {...mergeProps({
              to: ctx.listingLink("/map", ctx.filters),
            })}
          >
            {"Bản đồ GIS"}
          </RouterLink>
        </nav>
        <nav
          {...mergeProps({
            "aria-label": "Tiện ích cuối trang",
            className: "grid content-start gap-3 text-sm text-brand-navy",
          })}
        >
          <RouterLink
            {...mergeProps({
              to: "/market",
            })}
          >
            {"Dữ liệu thị trường"}
          </RouterLink>
          <RouterLink
            {...mergeProps({
              to: {
                ...ctx.listingLink("/home", ctx.filters),
                hash: "#finance",
              },
            })}
          >
            {"Công cụ tài chính"}
          </RouterLink>
          <RouterLink
            {...mergeProps({
              to: ctx.session.token ? "/account" : "/login",
            })}
          >
            {display(
              ctx.session.token ? "Hồ sơ cá nhân" : "Đăng nhập / Tạo tài khoản",
            )}
          </RouterLink>
        </nav>
      </div>
    </footer>,
  ]);
});
