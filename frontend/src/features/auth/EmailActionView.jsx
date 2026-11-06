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
import { ref, computed, onBeforeUnmount } from "../../shared/state/store.js";
import { useRoute, useRouter } from "../../shared/routing/router.jsx";
import { api, errorText, clearSession, session } from "./api.js";
import BusinessPage from "../../shared/components/BusinessPage.jsx";
function setup(__props) {
  const route = useRoute(),
    router = useRouter(),
    kind =
      route.path === "/reset-password"
        ? "reset"
        : route.path === "/verify-email"
          ? "verify"
          : "request";
  const token = ref(
    new URLSearchParams(route.hash.slice(1)).get("token") || "",
  );
  if (route.hash)
    router.replace({
      path: route.path,
      query: route.query,
      hash: "",
    });
  const password = ref(""),
    confirmation = ref(""),
    busy = ref(false),
    error = ref(""),
    message = ref(""),
    done = ref(false);
  const title = computed(() =>
    kind === "reset"
      ? "Đặt lại mật khẩu"
      : kind === "verify"
        ? "Xác nhận email"
        : "Xác minh email tài khoản",
  );
  async function submit() {
    if (busy.value || done.value) return;
    error.value = "";
    message.value = "";
    if (
      kind === "reset" &&
      (password.value !== confirmation.value ||
        new TextEncoder().encode(password.value).length > 72)
    ) {
      error.value = "Mật khẩu xác nhận phải khớp, tối đa 72 byte UTF-8.";
      return;
    }
    busy.value = true;
    try {
      if (kind === "request") {
        await api("/auth/email-verification/request", {
          method: "POST",
        });
        message.value =
          "Nếu tài khoản đủ điều kiện, yêu cầu đã được tiếp nhận. Vui lòng kiểm tra email.";
      } else {
        await api(
          "/auth/" +
            (kind === "reset"
              ? "password/reset"
              : "email-verification/confirm"),
          {
            method: "POST",
            authenticated: false,
            body:
              kind === "reset"
                ? {
                    token: token.value,
                    newPassword: password.value,
                  }
                : {
                    token: token.value,
                  },
          },
        );
        if (kind === "reset") clearSession();
        done.value = true;
        token.value = "";
        password.value = confirmation.value = "";
        message.value =
          kind === "reset"
            ? "Đã đặt lại mật khẩu. Hãy đăng nhập bằng mật khẩu mới."
            : "Email đã được xác nhận.";
      }
    } catch (e) {
      error.value =
        e.code === "INVALID_OR_EXPIRED_TOKEN"
          ? "Liên kết không hợp lệ, đã hết hạn hoặc đã được sử dụng. Vui lòng yêu cầu liên kết mới."
          : errorText(e);
    } finally {
      busy.value = false;
    }
  }
  onBeforeUnmount(() => {
    token.value = "";
    password.value = confirmation.value = "";
  });
  return {
    ref,
    computed,
    onBeforeUnmount,
    useRoute,
    useRouter,
    api,
    errorText,
    clearSession,
    session,
    BusinessPage,
    route,
    router,
    kind,
    token,
    password,
    confirmation,
    busy,
    error,
    message,
    done,
    title,
    submit,
  };
}
export default React.forwardRef(function EmailActionView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <BusinessPage data-ui-view="EmailActionView"
      {...mergeProps({
        title: ctx.title,
      })}
    >
      {ctx.error ? (
        <p
          {...mergeProps({
            role: "alert",
          })}
        >
          {display(ctx.error)}
        </p>
      ) : null}
      {ctx.message ? (
        <p
          {...mergeProps({
            role: "status",
          })}
        >
          {display(ctx.message)}
        </p>
      ) : null}
      {!ctx.done ? (
        <form
          {...mergeProps({
            onSubmit: ($event) => {
              $event.preventDefault();
              return ctx.submit?.($event);
            },
          })}
        >
          {ctx.kind === "reset" ? (
            <React.Fragment {...mergeProps({})}>
              <label {...mergeProps({})}>
                {"Mật khẩu mới "}
                <input
                  {...mergeProps(
                    {
                      type: "password",
                      autoComplete: "new-password",
                      minLength: "8",
                      required: true,
                    },
                    modelProps(
                      ctx.password,
                      ($value) => {
                        ctx.password = $value;
                      },
                      {
                        kind: "password",
                        value: "on",
                        number: false,
                        multiple: false,
                      },
                    ),
                  )}
                />
              </label>
              <label {...mergeProps({})}>
                {"Nhập lại mật khẩu "}
                <input
                  {...mergeProps(
                    {
                      type: "password",
                      autoComplete: "new-password",
                      minLength: "8",
                      required: true,
                    },
                    modelProps(
                      ctx.confirmation,
                      ($value) => {
                        ctx.confirmation = $value;
                      },
                      {
                        kind: "password",
                        value: "on",
                        number: false,
                        multiple: false,
                      },
                    ),
                  )}
                />
              </label>
            </React.Fragment>
          ) : null}
          {ctx.kind === "request" ? (
            <p {...mergeProps({})}>
              {display(
                ctx.session.user?.emailVerifiedAt
                  ? "Email đã được xác minh."
                  : "Gửi liên kết xác minh đến email tài khoản của bạn.",
              )}
            </p>
          ) : null}
          {ctx.kind !== "request" && !ctx.token ? (
            <p
              {...mergeProps({
                role: "alert",
              })}
            >
              {"Thiếu token trong liên kết. Hãy yêu cầu email mới."}
            </p>
          ) : null}
          <button
            {...mergeProps({
              disabled: ctx.busy || (ctx.kind !== "request" && !ctx.token),
            })}
          >
            {display(
              ctx.busy
                ? "Đang xử lý…"
                : ctx.kind === "request"
                  ? "Gửi email xác minh"
                  : "Xác nhận",
            )}
          </button>
        </form>
      ) : null}
      <RouterLink
        {...mergeProps({
          to: "/login",
          className: "underline",
        })}
      >
        {"Về đăng nhập / yêu cầu khôi phục"}
      </RouterLink>
    </BusinessPage>,
  ]);
});
