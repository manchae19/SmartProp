import React from "react";
import {
  useSetup,
  propsForSetup,
  emitForProps,
  exposeForSetup,
} from "../state/store.js";
import {
  mergeProps,
  bindRef,
  renderList,
  display,
  modelProps,
  rootProps,
  Teleport,
} from "./rendering.js";
import { RouterLink, RouterView } from "../routing/router.jsx";
function setup(__props) {
  propsForSetup(__props, {
    state: Object,
  });
  return {};
}
export default React.forwardRef(function LegacyState(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    ctx.state.error ? (
      <div
        {...mergeProps({
          role: "alert",
          className: "my-4 rounded-xl bg-[var(--ui-error-bg)] text-[var(--ui-error-text)] p-4 text-xs",
        })}
      >
        {display(ctx.state.error)}{" "}
        <button
          {...mergeProps({
            className: "underline ml-3",
            disabled: ctx.state.busy,
            onClick: ($event) => {
              ctx.state.load?.(ctx.state.page || 0);
            },
          })}
        >
          {"Thử lại"}
        </button>
      </div>
    ) : null,
    ctx.state.busy ? (
      <p
        {...mergeProps({
          role: "status",
          className: "my-4 text-xs text-brand-muted",
        })}
      >
        {"Đang xử lý…"}
      </p>
    ) : null,
    ctx.state.notice ? (
      <p
        {...mergeProps({
          role: "status",
          className:
            "my-4 rounded-xl bg-[var(--ui-success-bg)] text-[var(--ui-success-text)] p-4 text-xs",
        })}
      >
        {display(ctx.state.notice)}
      </p>
    ) : null,
  ]);
});
