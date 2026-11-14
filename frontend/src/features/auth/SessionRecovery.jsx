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
import { ref } from "../../shared/state/store.js";
import { useRoute, useRouter } from "../../shared/routing/router.jsx";
import { initializeAuth, session } from "./api.js";
function setup(__props) {
  const router = useRouter(),
    route = useRoute(),
    busy = ref(false);
  async function retry() {
    if (busy.value) return;
    busy.value = true;
    try {
      await initializeAuth({
        force: true,
      });
      if (session.status !== "UNAVAILABLE") {
        const target =
          typeof route.query.returnTo === "string" &&
          route.query.returnTo.startsWith("/") &&
          !route.query.returnTo.startsWith("//")
            ? route.query.returnTo
            : route.path === "/session-recovery"
              ? "/home"
              : route.fullPath;
        await router.replace(target);
      }
    } finally {
      busy.value = false;
    }
  }
  return {
    ref,
    useRoute,
    useRouter,
    initializeAuth,
    session,
    router,
    route,
    busy,
    retry,
  };
}
export default React.forwardRef(function SessionRecovery(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <main data-ui-view="SessionRecovery"
      {...mergeProps({
        className:
          "grid min-h-screen place-items-center bg-brand-cream p-6 text-brand-navy",
      })}
    >
      <section
        {...mergeProps({
          className:
            "w-full max-w-lg rounded-panel border border-brand-line bg-brand-card p-7",
        })}
      >
        <h1
          {...mergeProps({
            className: "text-2xl font-semibold",
          })}
        >
          {"Chưa thể kiểm tra phiên đăng nhập"}
        </h1>
        <p
          {...mergeProps({
            className: "mt-4 text-sm leading-6",
          })}
        >
          {
            "Kết nối đang gián đoạn. Bạn có thể thử lại khi máy chủ hoặc mạng hoạt động trở lại."
          }
        </p>
        {ctx.session.error ? (
          <p
            {...mergeProps({
              role: "alert",
              className: "mt-3 text-sm leading-6 text-brand-muted",
            })}
          >
            {display(ctx.session.error)}
          </p>
        ) : null}
        <button
          {...mergeProps({
            className: "sp-button sp-button-primary mt-5",
            disabled: ctx.busy,
            onClick: ($event) => {
              return ctx.retry?.($event);
            },
          })}
        >
          {display(ctx.busy ? "Đang kiểm tra…" : "Thử lại kết nối")}
        </button>
      </section>
    </main>,
  ]);
});
