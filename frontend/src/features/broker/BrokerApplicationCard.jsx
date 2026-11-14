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
import {
  ref,
  computed,
  watch,
  onBeforeUnmount,
} from "../../shared/state/store.js";
import { api, session } from "../auth/api.js";
import { canPublish } from "../../shared/lib/siteNavigation.js";
import {
  applicationStatuses,
  canRequestBroker,
  brokerErrorText,
} from "./brokerApplication.js";
function setup(__props) {
  const state = ref(null),
    busy = ref(false),
    error = ref("");
  const buyer = computed(() => canRequestBroker(session.user)),
    admin = computed(
      () => session.user?.role === "ADMIN" && session.user?.status === "ACTIVE",
    );
  let sequence = 0;
  async function load() {
    const run = ++sequence;
    state.value = null;
    error.value = "";
    busy.value = false;
    if (!buyer.value) return;
    busy.value = true;
    try {
      const result = await api("/users/me/broker-application");
      if (run === sequence) state.value = result;
    } catch (e) {
      if (run === sequence) error.value = brokerErrorText(e);
    } finally {
      if (run === sequence) busy.value = false;
    }
  }
  watch(
    () => [session.user?.id, session.user?.role, session.user?.status],
    load,
    {
      immediate: true,
    },
  );
  onBeforeUnmount(() => sequence++);
  return {
    ref,
    computed,
    watch,
    onBeforeUnmount,
    api,
    session,
    canPublish,
    applicationStatuses,
    canRequestBroker,
    brokerErrorText,
    state,
    busy,
    error,
    buyer,
    admin,
    sequence,
    load,
  };
}
export default React.forwardRef(function BrokerApplicationCard(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section
      {...mergeProps({
        "aria-labelledby": "broker-card-title",
        className: "rounded-panel border border-brand-line bg-brand-card p-5 sm:p-6",
      })}
    >
      <div
        {...mergeProps({
          className: "flex flex-wrap items-start justify-between gap-4",
        })}
      >
        <div {...mergeProps({})}>
          <p
            {...mergeProps({
              className:
                "text-xs font-semibold tracking-widest text-brand-accent",
            })}
          >
            {"QUYỀN ĐĂNG TIN"}
          </p>
          <h2
            {...mergeProps({
              id: "broker-card-title",
              className: "mt-2 text-xl font-semibold",
            })}
          >
            {display(
              ctx.admin
                ? "Quản trị người đăng"
                : ctx.canPublish(ctx.session.user)
                  ? "Quản lý bất động sản của bạn"
                  : "Đăng ký quyền đăng tin",
            )}
          </h2>
          <p
            {...mergeProps({
              className: "mt-2 text-sm leading-6 text-brand-muted",
            })}
          >
            {
              "Hồ sơ người đăng và từng tin bất động sản được xét duyệt riêng. Chỉ tin đã duyệt mới xuất hiện công khai."
            }
          </p>
        </div>
        {ctx.buyer && ctx.state ? (
          <span
            {...mergeProps({
              className:
                "rounded-full bg-brand-surface px-3 py-2 text-sm font-semibold",
            })}
          >
            {display(
              ctx.applicationStatuses[ctx.state.status] || ctx.state.status,
            )}
          </span>
        ) : null}
      </div>
      {ctx.buyer ? (
        <React.Fragment {...mergeProps({})}>
          {ctx.busy ? (
            <p
              {...mergeProps({
                role: "status",
                className: "mt-3 text-sm",
              })}
            >
              {"Đang tải trạng thái…"}
            </p>
          ) : null}
          {ctx.error ? (
            <p
              {...mergeProps({
                role: "alert",
                className: "mt-3 text-sm leading-6 text-[var(--ui-error-text)]",
              })}
            >
              {display(ctx.error)}{" "}
              <button
                {...mergeProps({
                  type: "button",
                  className: "underline",
                  disabled: ctx.busy,
                  onClick: ($event) => {
                    return ctx.load?.($event);
                  },
                })}
              >
                {"Thử lại"}
              </button>
            </p>
          ) : null}
          {ctx.state?.application?.reviewReason ? (
            <p
              {...mergeProps({
                className: "mt-3 whitespace-pre-wrap text-sm leading-6",
              })}
            >
              {"Phản hồi: "}
              {display(ctx.state.application.reviewReason)}
            </p>
          ) : null}
          {ctx.state?.status === "PENDING" ? (
            <p
              {...mergeProps({
                className: "mt-3 text-sm leading-6",
              })}
            >
              {
                "Yêu cầu đang chờ xét duyệt. Bạn chưa có quyền đăng tin và không cần gửi yêu cầu trùng."
              }
            </p>
          ) : null}
          {ctx.state?.status === "SUSPENDED" ? (
            <p
              {...mergeProps({
                className: "mt-3 text-sm leading-6",
              })}
            >
              {"Quyền đăng tin đang tạm ngưng. Vui lòng liên hệ quản trị viên."}
            </p>
          ) : null}
          {ctx.state ? (
            <RouterLink
              {...mergeProps({
                className: "sp-button sp-button-primary mt-4",
                to: "/account/broker-application",
              })}
            >
              {display(
                ctx.state.status === "NOT_REQUESTED"
                  ? "Đăng ký quyền đăng tin"
                  : ["REJECTED", "NEEDS_INFORMATION"].includes(ctx.state.status)
                    ? "Bổ sung và gửi lại hồ sơ"
                    : "Xem trạng thái hồ sơ",
              )}
            </RouterLink>
          ) : null}
        </React.Fragment>
      ) : null}
      {ctx.canPublish(ctx.session.user) ? (
        <div
          {...mergeProps({
            className: "mt-4 flex flex-wrap gap-3",
          })}
        >
          {ctx.admin ? (
            <RouterLink
              {...mergeProps({
                className: "sp-button sp-button-primary",
                to: "/admin/broker-applications",
              })}
            >
              {"Duyệt quyền đăng tin"}
            </RouterLink>
          ) : null}
          {ctx.admin ? (
            <RouterLink
              {...mergeProps({
                className: "sp-button sp-button-secondary",
                to: "/admin/posts",
              })}
            >
              {"Duyệt tin bất động sản"}
            </RouterLink>
          ) : null}
          <RouterLink
            {...mergeProps({
              className: "sp-button sp-button-secondary",
              to: "/post",
            })}
          >
            {"Đăng tin mới"}
          </RouterLink>
          <RouterLink
            {...mergeProps({
              className: "sp-button sp-button-secondary",
              to: "/my-listing",
            })}
          >
            {"Quản lý tin đăng"}
          </RouterLink>
        </div>
      ) : null}
    </section>,
  ]);
});
