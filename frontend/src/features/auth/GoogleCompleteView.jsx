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
import { onMounted, ref } from "../../shared/state/store.js";
import { useRouter } from "../../shared/routing/router.jsx";
import { completeGoogleLogin, session, errorText } from "./api.js";
function setup(__props) {
  const router = useRouter(),
    error = ref("");
  onMounted(async () => {
    try {
      await completeGoogleLogin();
      await router.replace(session.user?.role === "ADMIN" ? "/admin" : "/home");
    } catch (e) {
      error.value = errorText(e);
    }
  });
  return {
    onMounted,
    ref,
    useRouter,
    completeGoogleLogin,
    session,
    errorText,
    router,
    error,
  };
}
export default React.forwardRef(function GoogleCompleteView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <main data-ui-view="GoogleCompleteView"
      {...mergeProps({
        className: "sp-container py-16",
      })}
    >
      <section
        {...mergeProps({
          className:
            "mx-auto max-w-lg rounded-panel border border-brand-line bg-brand-card p-8",
        })}
      >
        <p
          {...mergeProps({
            className:
              "text-xs font-semibold tracking-widest text-brand-accent",
          })}
        >
          {"SMARTPROP · GOOGLE"}
        </p>
        <h1
          {...mergeProps({
            className: "mt-3 text-2xl font-semibold",
          })}
        >
          {"Hoàn tất đăng nhập"}
        </h1>
        {!ctx.error ? (
          <p
            {...mergeProps({
              role: "status",
              className: "mt-4 text-sm leading-7 text-brand-muted",
            })}
          >
            {"Đang xác minh tài khoản và khởi tạo phiên của bạn…"}
          </p>
        ) : (
          <div
            {...mergeProps({
              role: "alert",
              className: "mt-4",
            })}
          >
            <p
              {...mergeProps({
                className: "text-sm leading-7 text-[var(--ui-error-text)]",
              })}
            >
              {display(ctx.error)}
            </p>
            <RouterLink
              {...mergeProps({
                to: "/login",
                className: "sp-button sp-button-primary mt-6",
              })}
            >
              {"Quay lại đăng nhập"}
            </RouterLink>
          </div>
        )}
      </section>
    </main>,
  ]);
});
