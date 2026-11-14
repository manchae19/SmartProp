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
export default React.forwardRef(function LegacyPager(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    ctx.state.totalPages > 1 ? (
      <div
        {...mergeProps({
          className:
            "flex justify-center items-center gap-5 py-6 text-xs text-[var(--ui-accent)]",
        })}
      >
        <button
          {...mergeProps({
            disabled: ctx.state.busy || !ctx.state.page,
            className:
              "rounded-full border px-4 py-2 bg-brand-card disabled:opacity-40",
            onClick: ($event) => {
              ctx.state.load(ctx.state.page - 1);
            },
          })}
        >
          {"← Trước"}
        </button>
        <span {...mergeProps({})}>
          {"Trang "}
          {display(ctx.state.page + 1)}
          {" / "}
          {display(ctx.state.totalPages)}
          {" · "}
          {display(ctx.state.totalElements)}
          {" kết quả"}
        </span>
        <button
          {...mergeProps({
            disabled:
              ctx.state.busy || ctx.state.page + 1 >= ctx.state.totalPages,
            className:
              "rounded-full border px-4 py-2 bg-brand-card disabled:opacity-40",
            onClick: ($event) => {
              ctx.state.load(ctx.state.page + 1);
            },
          })}
        >
          {"Sau →"}
        </button>
      </div>
    ) : null,
  ]);
});
