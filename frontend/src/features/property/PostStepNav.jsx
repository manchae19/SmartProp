import React from "react";
import {
  useSetup,
  propsForSetup,
  emitForProps,
  exposeForSetup,
} from "../../shared/state/store.js";
import {
  mergeProps,
  bindRef,
  renderList,
  display,
  modelProps,
  rootProps,
  Teleport,
} from "../../shared/components/rendering.js";
import { RouterLink, RouterView } from "../../shared/routing/router.jsx";
import { useRoute } from "../../shared/routing/router.jsx";
import { postSteps } from "./postForm.js";
function setup(__props) {
  propsForSetup(__props, {
    current: Number,
    busy: Boolean,
  });
  const route = useRoute();
  return {
    useRoute,
    postSteps,
    route,
  };
}
export default React.forwardRef(function PostStepNav(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <nav
      {...mergeProps({
        "aria-label": "Các bước đăng tin",
        className: "grid grid-cols-3 gap-3 py-6",
      })}
    >
      {renderList(ctx.postSteps, (item) => (
        <RouterLink
          key={item.step}
          {...mergeProps({
            to: {
              path: item.path,
              query: ctx.route.query,
            },
            "aria-current": ctx.current === item.step ? "step" : undefined,
            "aria-disabled": ctx.busy || undefined,
            onClick: ($event) => {
              ctx.busy && $event.preventDefault();
            },
            className: ["border-t-2 pt-2 text-xs leading-relaxed transition hover:text-[var(--ui-accent)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--ui-border)]", [
              item.step <= ctx.current
                ? "border-[var(--ui-border)] text-[var(--ui-accent)]"
                : "border-[var(--ui-border)] text-brand-muted",
              ctx.busy ? "pointer-events-none opacity-60" : "",
            ]],
            
          })}
        >
          {"Bước "}
          {display(item.step)}
          {" · "}
          {display(item.label)}
        </RouterLink>
      ))}
    </nav>,
  ]);
});
