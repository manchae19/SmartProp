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
import { ref, onMounted, onBeforeUnmount } from "../../shared/state/store.js";
import { api } from "../auth/api.js";
import {
  applicationStatuses,
  applicationActions,
  reviewActions,
  brokerErrorText,
} from "../broker/brokerApplication.js";
function setup(__props) {
  const items = ref([]),
    status = ref("PENDING"),
    page = ref(0),
    totalPages = ref(0),
    total = ref(0),
    busy = ref(false),
    error = ref(""),
    message = ref(""),
    selected = ref(null),
    reason = ref("");
  let sequence = 0;
  async function load(reset = false) {
    if (reset) page.value = 0;
    const run = ++sequence;
    busy.value = true;
    error.value = "";
    selected.value = null;
    try {
      const q = new URLSearchParams({
        page: String(page.value),
        size: "10",
      });
      if (status.value) q.set("status", status.value);
      const result = await api("/admin/broker-applications?" + q);
      if (run !== sequence) return;
      items.value = result.items;
      total.value = result.totalElements;
      totalPages.value = result.totalPages;
    } catch (e) {
      if (run === sequence) error.value = brokerErrorText(e);
    } finally {
      if (run === sequence) busy.value = false;
    }
  }
  function select(item) {
    selected.value = item;
    reason.value = "";
    message.value = "";
  }
  async function review(action) {
    if (busy.value || !selected.value || !reason.value.trim()) return;
    const application = selected.value;
    busy.value = true;
    error.value = "";
    message.value = "";
    try {
      await api(
        "/admin/broker-applications/" +
          encodeURIComponent(application.id) +
          "/review",
        {
          method: "POST",
          body: {
            action,
            expectedVersion: application.contentVersion,
            reason: reason.value.trim(),
          },
        },
      );
      message.value =
        "Đã xử lý hồ sơ. Khi thay đổi quyền, người dùng cần đăng nhập lại.";
      reason.value = "";
      await load();
    } catch (e) {
      error.value = brokerErrorText(e);
      if (e.status === 409) {
        selected.value = null;
        error.value +=
          " Tải lại danh sách và kiểm tra hồ sơ trước khi thao tác lại.";
      }
    } finally {
      busy.value = false;
    }
  }
  async function move(delta) {
    page.value += delta;
    await load();
  }
  onMounted(() => load());
  onBeforeUnmount(() => {
    sequence++;
  });
  return {
    ref,
    onMounted,
    onBeforeUnmount,
    api,
    applicationStatuses,
    applicationActions,
    reviewActions,
    brokerErrorText,
    items,
    status,
    page,
    totalPages,
    total,
    busy,
    error,
    message,
    selected,
    reason,
    sequence,
    load,
    select,
    review,
    move,
  };
}
export default React.forwardRef(function BrokerApplicationsView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section data-ui-view="BrokerApplicationsView"
      {...mergeProps({
        className: "rounded-panel bg-brand-card p-5 text-brand-navy sm:p-7",
      })}
    >
      <h1
        {...mergeProps({
          className: "text-2xl font-semibold",
        })}
      >
        {"Duyệt quyền đăng tin"}
      </h1>
      <p
        {...mergeProps({
          className: "mt-2 text-sm leading-6 text-brand-muted",
        })}
      >
        {
          "Xét duyệt người đăng, độc lập với duyệt từng tin. Không cấp quyền ADMIN từ màn hình này."
        }
      </p>
      <div
        {...mergeProps({
          className: "my-5 flex flex-wrap items-end gap-3",
        })}
      >
        <label
          {...mergeProps({
            className: "sp-field",
          })}
        >
          {"Trạng thái"}
          <select
            {...mergeProps(
              {
                className: "sp-input",
                disabled: ctx.busy,
                onChange: ($event) => {
                  ctx.load(true);
                },
              },
              modelProps(
                ctx.status,
                ($value) => {
                  ctx.status = $value;
                },
                {
                  kind: "text",
                  value: "on",
                  number: false,
                  multiple: false,
                },
              ),
            )}
          >
            <option
              {...mergeProps({
                value: "",
              })}
            >
              {"Tất cả"}
            </option>
            {renderList(ctx.applicationStatuses, (label, key) => (
              <option
                key={key}
                {...mergeProps(
                  {
                    value: key,
                  },
                  {
                    style: {
                      display: key !== "NOT_REQUESTED" ? undefined : "none",
                    },
                  },
                )}
              >
                {display(label)}
              </option>
            ))}
          </select>
        </label>
        <button
          {...mergeProps({
            className: "sp-button sp-button-secondary",
            type: "button",
            disabled: ctx.busy,
            onClick: ($event) => {
              ctx.load();
            },
          })}
        >
          {"Tải lại danh sách"}
        </button>
        <p
          {...mergeProps({
            className: "text-sm",
          })}
        >
          {display(ctx.total)}
          {" hồ sơ"}
        </p>
      </div>
      {ctx.busy ? (
        <p
          {...mergeProps({
            role: "status",
          })}
        >
          {"Đang xử lý…"}
        </p>
      ) : null}
      {ctx.error ? (
        <p
          {...mergeProps({
            role: "alert",
            className:
              "my-4 whitespace-pre-wrap rounded-control bg-[var(--ui-error-bg)] p-4 text-sm text-[var(--ui-error-text)]",
          })}
        >
          {display(ctx.error)}
        </p>
      ) : null}
      {ctx.message ? (
        <p
          {...mergeProps({
            role: "status",
            className: "my-4 text-sm text-[var(--ui-success-text)]",
          })}
        >
          {display(ctx.message)}
        </p>
      ) : null}
      {!ctx.busy && !ctx.error && !ctx.items.length ? (
        <p
          {...mergeProps({
            className: "py-8 text-center text-brand-muted",
          })}
        >
          {"Chưa có hồ sơ ở trạng thái này."}
        </p>
      ) : null}
      <div
        {...mergeProps({
          className: "grid gap-4",
        })}
      >
        {renderList(ctx.items, (item) => (
          <article
            key={item.id}
            {...mergeProps({
              className: ["rounded-panel border p-4", ctx.selected?.id === item.id
                  ? "border-brand-gold bg-brand-cream"
                  : "border-brand-line"],
              
            })}
          >
            <div
              {...mergeProps({
                className: "flex flex-wrap items-start justify-between gap-3",
              })}
            >
              <div {...mergeProps({})}>
                <h2
                  {...mergeProps({
                    className: "font-semibold",
                  })}
                >
                  {display(item.displayName)}
                </h2>
                <p
                  {...mergeProps({
                    className: "mt-1 text-sm",
                  })}
                >
                  {display(
                    item.applicantType === "OWNER" ? "Chủ nhà" : "Môi giới",
                  )}
                  {" · "}
                  {display(item.operatingArea)}
                </p>
                <p
                  {...mergeProps({
                    className: "mt-1 text-xs text-brand-muted",
                  })}
                >
                  {"Tài khoản #"}
                  {display(item.userId)}
                  {" · "}
                  {display(ctx.applicationStatuses[item.status])}
                  {" · phiên bản "}
                  {display(item.contentVersion)}
                </p>
              </div>
              <button
                {...mergeProps({
                  className: "sp-button sp-button-secondary",
                  type: "button",
                  disabled: ctx.busy,
                  onClick: ($event) => {
                    ctx.select(item);
                  },
                })}
              >
                {"Xem hồ sơ"}
              </button>
            </div>
            {ctx.selected?.id === item.id ? (
              <div
                {...mergeProps({
                  className: "mt-5 grid gap-4 text-sm",
                })}
              >
                <p {...mergeProps({})}>
                  {"Điện thoại đã cung cấp: "}
                  {display(item.contactPhone)}
                </p>
                <p
                  {...mergeProps({
                    className: "whitespace-pre-wrap leading-6",
                  })}
                >
                  {display(item.requestMessage)}
                </p>
                <p {...mergeProps({})}>
                  {"Xác nhận trách nhiệm: "}
                  {display(
                    item.responsibilityAccepted
                      ? "Đã xác nhận"
                      : "Chưa xác nhận",
                  )}
                </p>
                {item.reviewReason ? (
                  <p
                    {...mergeProps({
                      className: "whitespace-pre-wrap",
                    })}
                  >
                    {"Phản hồi trước: "}
                    {display(item.reviewReason)}
                  </p>
                ) : null}
                {ctx.reviewActions(item.status).length ? (
                  <label
                    {...mergeProps({
                      className: "sp-field",
                    })}
                  >
                    {"Lý do / phản hồi"}
                    <textarea
                      {...mergeProps(
                        {
                          className: "sp-input min-h-24",
                          required: true,
                          maxLength: "2000",
                          disabled: ctx.busy,
                        },
                        modelProps(
                          ctx.reason,
                          ($value) => {
                            ctx.reason = $value;
                          },
                          {
                            kind: "text",
                            value: "on",
                            number: false,
                            multiple: false,
                          },
                        ),
                      )}
                    />
                  </label>
                ) : null}
                <div
                  {...mergeProps({
                    className: "flex flex-wrap gap-3",
                  })}
                >
                  {renderList(ctx.reviewActions(item.status), (action) => (
                    <button
                      key={action}
                      {...mergeProps({
                        className: ["sp-button", action === "APPROVE"
                            ? "sp-button-primary"
                            : "sp-button-secondary"],
                        
                        type: "button",
                        disabled: ctx.busy || !ctx.reason.trim(),
                        onClick: ($event) => {
                          ctx.review(action);
                        },
                      })}
                    >
                      {display(ctx.applicationActions[action])}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
          </article>
        ))}
      </div>
      {ctx.totalPages > 1 ? (
        <nav
          {...mergeProps({
            "aria-label": "Phân trang hồ sơ",
            className: "mt-5 flex items-center gap-4",
          })}
        >
          <button
            {...mergeProps({
              className: "sp-button sp-button-secondary",
              disabled: ctx.busy || ctx.page === 0,
              onClick: ($event) => {
                ctx.move(-1);
              },
            })}
          >
            {"Trước"}
          </button>
          <span {...mergeProps({})}>
            {display(ctx.page + 1)}
            {" / "}
            {display(ctx.totalPages)}
          </span>
          <button
            {...mergeProps({
              className: "sp-button sp-button-secondary",
              disabled: ctx.busy || ctx.page + 1 >= ctx.totalPages,
              onClick: ($event) => {
                ctx.move(1);
              },
            })}
          >
            {"Sau"}
          </button>
        </nav>
      ) : null}
    </section>,
  ]);
});
