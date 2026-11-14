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
import { normalizeFilters } from "../../../features/property/listingFilters.js";
import {
  activeNavigation,
  siteNavigation,
  scrollHomeSection,
} from "../../lib/siteNavigation.js";
import AppIcon from "../AppIcon.jsx";
function setup(__props) {
  propsForSetup(__props, {
    vertical: Boolean,
  });
  const emit = emitForProps(__props, ["navigate"]),
    route = useRoute();
  const items = computed(() => siteNavigation(normalizeFilters(route.query)));
  function navigate(item) {
    if (item.key === "home" && route.path === "/home")
      scrollHomeSection("home");
    emit("navigate");
  }
  return {
    computed,
    useRoute,
    normalizeFilters,
    activeNavigation,
    siteNavigation,
    scrollHomeSection,
    AppIcon,
    emit,
    route,
    items,
    navigate,
  };
}
export default React.forwardRef(function AppNavigation(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <nav
      {...mergeProps({
        "aria-label": ctx.vertical
          ? "Điều hướng website trong menu"
          : "Điều hướng website",
        className: ctx.vertical ? "grid gap-1.5" : "flex items-center gap-1",
      })}
    >
      {renderList(ctx.items, (item) => (
        <RouterLink
          key={item.key}
          {...mergeProps({
            to: item.to,
            "aria-current": ctx.activeNavigation(item.key, ctx.route)
              ? "page"
              : undefined,
            className: ["flex min-h-12 items-center gap-3 rounded-xl px-4 py-3 text-[15px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-gold", ctx.activeNavigation(item.key, ctx.route)
              ? "bg-brand-raised text-brand-navy"
              : "text-brand-navy hover:bg-brand-surface"],
            
            onClick: ($event) => {
              ctx.navigate(item);
            },
          })}
        >
          <AppIcon
            {...mergeProps({
              name:
                item.key === "home"
                  ? "home"
                  : item.key === "advisor"
                    ? "tools"
                    : item.key === "image-check"
                      ? "camera"
                      : item.key === "image-analysis"
                        ? "camera"
                        : item.key,
            })}
          />
          <span {...mergeProps({})}>{display(item.label)}</span>
          {ctx.vertical && <span className="drawer-chevron" aria-hidden="true">›</span>}
        </RouterLink>
      ))}
    </nav>,
  ]);
});
