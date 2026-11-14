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
import ValuationPanel from "./ValuationPanel.jsx";
import ValuationHistory from "./ValuationHistory.jsx";
import { ref } from "../../shared/state/store.js";
function setup(__props) {
  const history = ref(null),
    refreshKey = ref(0);
  return {
    ValuationPanel,
    ValuationHistory,
    ref,
    history,
    refreshKey,
  };
}
export default React.forwardRef(function ValuationView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <main data-ui-view="ValuationView"
      {...mergeProps({
        className:
          "min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)] px-5 py-8 sm:py-12",
      })}
    >
      <div
        {...mergeProps({
          className: "max-w-3xl mx-auto",
        })}
      >
        <nav
          {...mergeProps({
            className: "flex flex-wrap justify-between gap-4 mb-8 text-sm",
          })}
        >
          <RouterLink
            {...mergeProps({
              to: "/home",
              className: "font-semibold",
            })}
          >
            {"SmartProp"}
          </RouterLink>
          <RouterLink
            {...mergeProps({
              to: "/listings",
              className: "underline underline-offset-4",
            })}
          >
            {"Xem tin bất động sản"}
          </RouterLink>
        </nav>
        <header className="page-intro-banner">
        <h1
          {...mergeProps({
            className: "text-3xl sm:text-4xl font-semibold tracking-tight",
          })}
        >
          {"Tham khảo giá trước khi quyết định"}
        </h1>
        <p
          {...mergeProps({
            className: "mt-4 mb-8 text-sm leading-6 text-[var(--ui-accent)]",
          })}
        >
          {
            "Ước tính tổng giá rao nhà ở, đất nền và căn hộ tại các địa bàn Đà Nẵng mà mô hình hỗ trợ."
          }
        </p>
        </header>
        <ValuationPanel
          {...mergeProps({
            historyEnabled: true,
            onSaved: ($event) => {
              ctx.refreshKey++;
            },
            onOptionsLoaded: ($event) => {
              ctx.history?.setLabels($event);
            },
          })}
        />
        <ValuationHistory
          {...mergeProps({
            ref: bindRef(ctx, "history"),
            refreshKey: ctx.refreshKey,
          })}
        />
      </div>
    </main>,
  ]);
});
