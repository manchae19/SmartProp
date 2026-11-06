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
  reactive,
  onMounted,
  computed,
} from "../../shared/state/store.js";
import { api, loadProfile, session } from "../auth/api.js";
import { canPublish } from "../../shared/lib/siteNavigation.js";
import {
  applicationStatuses,
  canApply,
  applicationPayload,
  brokerErrorText,
  canRequestBroker,
} from "./brokerApplication.js";
function setup(__props) {
  const state = ref(null),
    busy = ref(false),
    error = ref(""),
    message = ref(""),
    form = reactive({
      applicantType: "OWNER",
      displayName: "",
      contactPhone: "",
      operatingArea: "",
      requestMessage: "",
      responsibilityAccepted: false,
    });
  const needsReload = ref(false),
    ready = ref(false);
  const editable = computed(
    () =>
      ready.value && !needsReload.value && canApply(state.value, session.user),
  );
  async function load() {
    busy.value = true;
    error.value = "";
    ready.value = false;
    state.value = null;
    message.value = "";
    needsReload.value = false;
    try {
      await loadProfile();
      if (!canRequestBroker(session.user)) return;
      state.value = await api("/users/me/broker-application");
      const a = state.value.application;
      ready.value = true;
      if (a)
        Object.assign(form, {
          applicantType: a.applicantType,
          displayName: a.displayName,
          contactPhone: a.contactPhone,
          operatingArea: a.operatingArea,
          requestMessage: a.requestMessage,
          responsibilityAccepted: false,
        });
      else
        Object.assign(form, {
          displayName: session.user.fullName || "",
          contactPhone: session.user.phone || "",
          operatingArea: session.user.district || "",
        });
    } catch (e) {
      error.value = brokerErrorText(e);
    } finally {
      busy.value = false;
    }
  }
  async function submit() {
    if (busy.value || !editable.value) return;
    busy.value = true;
    error.value = "";
    message.value = "";
    try {
      state.value = await api("/users/me/broker-application", {
        method: "POST",
        body: applicationPayload(form, state.value, session.user),
      });
      message.value =
        "Đã gửi hồ sơ. Vui lòng chờ quản trị viên xét duyệt. Khi được cấp quyền, hãy đăng nhập lại.";
    } catch (e) {
      error.value = brokerErrorText(e);
      if (e.status === 409) needsReload.value = true;
    } finally {
      busy.value = false;
    }
  }
  onMounted(load);
  return {
    ref,
    reactive,
    onMounted,
    computed,
    api,
    loadProfile,
    session,
    canPublish,
    applicationStatuses,
    canApply,
    applicationPayload,
    brokerErrorText,
    canRequestBroker,
    state,
    busy,
    error,
    message,
    form,
    needsReload,
    ready,
    editable,
    load,
    submit,
  };
}
export default React.forwardRef(function BrokerApplicationView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="BrokerApplicationView"
      {...mergeProps({
        className: "sp-container max-w-4xl py-8 sm:py-12",
      })}
    >
      <RouterLink
        {...mergeProps({
          to: "/account",
          className: "text-sm underline",
        })}
      >
        {"← Tài khoản"}
      </RouterLink>
      <h1
        {...mergeProps({
          className: "mt-5 text-3xl font-semibold",
        })}
      >
        {"Đăng ký quyền đăng tin"}
      </h1>
      <p
        {...mergeProps({
          className: "mt-3 text-sm leading-6 text-brand-muted",
        })}
      >
        {
          "Đăng ký miễn phí bằng hồ sơ liên hệ. Không gửi căn cước hoặc giấy tờ nhạy cảm trong nội dung yêu cầu. Hồ sơ này chỉ bạn và quản trị viên được phép xem."
        }
      </p>
      {ctx.busy ? (
        <p
          {...mergeProps({
            role: "status",
            className: "mt-5",
          })}
        >
          {"Đang xử lý…"}
        </p>
      ) : null}
      {ctx.error ? (
        <p
          {...mergeProps({
            role: "alert",
            className: "mt-5 rounded-panel bg-[var(--ui-error-bg)] p-4 text-sm text-[var(--ui-error-text)]",
          })}
        >
          {display(ctx.error)}
        </p>
      ) : null}
      {ctx.message ? (
        <p
          {...mergeProps({
            role: "status",
            className:
              "mt-5 rounded-panel bg-[var(--ui-success-bg)] p-4 text-sm text-[var(--ui-success-text)]",
          })}
        >
          {display(ctx.message)}
        </p>
      ) : null}
      <button
        {...mergeProps({
          className: "sp-button sp-button-secondary mt-5",
          type: "button",
          disabled: ctx.busy,
          onClick: ($event) => {
            return ctx.load?.($event);
          },
        })}
      >
        {"Tải lại trạng thái"}
      </button>
      {ctx.state ? (
        <section
          {...mergeProps({
            className:
              "mt-6 rounded-panel border border-brand-line bg-brand-card p-5 sm:p-7",
          })}
        >
          <h2
            {...mergeProps({
              className: "text-lg font-semibold",
            })}
          >
            {display(
              ctx.applicationStatuses[ctx.state.status] || ctx.state.status,
            )}
          </h2>
          {ctx.state.legacyPublisher ? (
            <p
              {...mergeProps({
                className: "mt-2 text-sm text-brand-muted",
              })}
            >
              {"Quyền hiện có của tài khoản được giữ nguyên."}
            </p>
          ) : null}
          {ctx.state.application?.reviewReason ? (
            <p
              {...mergeProps({
                className:
                  "mt-3 whitespace-pre-wrap rounded-control bg-brand-surface p-4 text-sm leading-6",
              })}
            >
              {"Phản hồi của quản trị viên: "}
              {display(ctx.state.application.reviewReason)}
            </p>
          ) : null}
          {ctx.state.status === "PENDING" ? (
            <p
              {...mergeProps({
                className: "mt-3 text-sm leading-6",
              })}
            >
              {
                "Bạn chưa có quyền tạo tin. Có thể quay lại kiểm tra sau; không cần gửi lại yêu cầu."
              }
            </p>
          ) : null}
          {ctx.state.status === "SUSPENDED" ? (
            <p
              {...mergeProps({
                className: "mt-3 text-sm leading-6",
              })}
            >
              {
                "Quyền đăng tin đang tạm ngưng. Liên hệ quản trị viên để xem xét khôi phục, không gửi yêu cầu mới."
              }
            </p>
          ) : null}
          {ctx.canPublish(ctx.session.user) ? (
            <div
              {...mergeProps({
                className: "mt-5 flex flex-wrap gap-3",
              })}
            >
              <RouterLink
                {...mergeProps({
                  to: "/post",
                  className: "sp-button sp-button-primary",
                })}
              >
                {"Đăng tin mới"}
              </RouterLink>
              <RouterLink
                {...mergeProps({
                  to: "/my-listing",
                  className: "sp-button sp-button-secondary",
                })}
              >
                {"Quản lý tin đăng"}
              </RouterLink>
            </div>
          ) : null}
          {ctx.editable ? (
            <form
              {...mergeProps({
                className: "mt-6 grid gap-5",
                onSubmit: ($event) => {
                  $event.preventDefault();
                  return ctx.submit?.($event);
                },
              })}
            >
              <fieldset
                {...mergeProps({
                  disabled: ctx.busy,
                  className: "grid gap-5 sm:grid-cols-2",
                })}
              >
                <label
                  {...mergeProps({
                    className: "sp-field",
                  })}
                >
                  {"Loại người đăng"}
                  <select
                    {...mergeProps(
                      {
                        name: "applicantType",
                        className: "sp-input",
                        required: true,
                      },
                      modelProps(
                        ctx.form.applicantType,
                        ($value) => {
                          ctx.form.applicantType = $value;
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
                        value: "OWNER",
                      })}
                    >
                      {"Chủ nhà"}
                    </option>
                    <option
                      {...mergeProps({
                        value: "AGENT",
                      })}
                    >
                      {"Môi giới"}
                    </option>
                  </select>
                </label>
                <label
                  {...mergeProps({
                    className: "sp-field",
                  })}
                >
                  {"Họ tên / tên đơn vị"}
                  <input
                    {...mergeProps(
                      {
                        name: "displayName",
                        className: "sp-input",
                        required: true,
                        maxLength: "150",
                        autoComplete: "name",
                      },
                      modelProps(
                        ctx.form.displayName,
                        ($value) => {
                          ctx.form.displayName = $value;
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
                <label
                  {...mergeProps({
                    className: "sp-field",
                  })}
                >
                  {"Số điện thoại liên hệ"}
                  <input
                    {...mergeProps(
                      {
                        name: "contactPhone",
                        className: "sp-input",
                        required: true,
                        minLength: "8",
                        maxLength: "30",
                        type: "tel",
                        autoComplete: "tel",
                        pattern: "\\+?[0-9][0-9 \\(\\)\\-]{6,28}[0-9]",
                      },
                      modelProps(
                        ctx.form.contactPhone,
                        ($value) => {
                          ctx.form.contactPhone = $value;
                        },
                        {
                          kind: "tel",
                          value: "on",
                          number: false,
                          multiple: false,
                        },
                      ),
                    )}
                  />
                </label>
                <label
                  {...mergeProps({
                    className: "sp-field",
                  })}
                >
                  {"Khu vực hoạt động"}
                  <input
                    {...mergeProps(
                      {
                        name: "operatingArea",
                        className: "sp-input",
                        required: true,
                        maxLength: "200",
                        placeholder: "Ví dụ: Hải Châu, Đà Nẵng",
                      },
                      modelProps(
                        ctx.form.operatingArea,
                        ($value) => {
                          ctx.form.operatingArea = $value;
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
                <label
                  {...mergeProps({
                    className: "sp-field sm:col-span-2",
                  })}
                >
                  {"Nội dung yêu cầu"}
                  <textarea
                    {...mergeProps(
                      {
                        name: "requestMessage",
                        className: "sp-input min-h-32",
                        required: true,
                        maxLength: "2000",
                        rows: "4",
                      },
                      modelProps(
                        ctx.form.requestMessage,
                        ($value) => {
                          ctx.form.requestMessage = $value;
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
                <label
                  {...mergeProps({
                    className:
                      "flex items-start gap-3 text-sm leading-6 sm:col-span-2",
                  })}
                >
                  <input
                    {...mergeProps(
                      {
                        name: "responsibilityAccepted",
                        required: true,
                        type: "checkbox",
                        className: "mt-1",
                      },
                      modelProps(
                        ctx.form.responsibilityAccepted,
                        ($value) => {
                          ctx.form.responsibilityAccepted = $value;
                        },
                        {
                          kind: "checkbox",
                          value: "on",
                          number: false,
                          multiple: false,
                        },
                      ),
                    )}
                  />
                  {
                    "Tôi chịu trách nhiệm về tính chính xác và quyền sử dụng thông tin, hình ảnh trong các tin đăng."
                  }
                </label>
              </fieldset>
              <button
                {...mergeProps({
                  className: "sp-button sp-button-primary justify-self-start",
                  type: "submit",
                  disabled: ctx.busy,
                })}
              >
                {display(
                  ctx.state.status === "NOT_REQUESTED"
                    ? "Gửi yêu cầu"
                    : "Gửi lại hồ sơ",
                )}
              </button>
            </form>
          ) : ctx.state.application ? (
            <dl
              {...mergeProps({
                className: "mt-5 grid gap-3 text-sm",
              })}
            >
              <div {...mergeProps({})}>
                <dt
                  {...mergeProps({
                    className: "text-brand-muted",
                  })}
                >
                  {"Người đăng"}
                </dt>
                <dd {...mergeProps({})}>
                  {display(ctx.state.application.displayName)}
                  {" · "}
                  {display(
                    ctx.state.application.applicantType === "OWNER"
                      ? "Chủ nhà"
                      : "Môi giới",
                  )}
                </dd>
              </div>
              <div {...mergeProps({})}>
                <dt
                  {...mergeProps({
                    className: "text-brand-muted",
                  })}
                >
                  {"Liên hệ / khu vực"}
                </dt>
                <dd {...mergeProps({})}>
                  {display(ctx.state.application.contactPhone)}
                  {" · "}
                  {display(ctx.state.application.operatingArea)}
                </dd>
              </div>
              <div {...mergeProps({})}>
                <dt
                  {...mergeProps({
                    className: "text-brand-muted",
                  })}
                >
                  {"Nội dung"}
                </dt>
                <dd
                  {...mergeProps({
                    className: "whitespace-pre-wrap",
                  })}
                >
                  {display(ctx.state.application.requestMessage)}
                </dd>
              </div>
            </dl>
          ) : null}
        </section>
      ) : null}
    </div>,
  ]);
});
