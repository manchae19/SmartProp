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
  reactive,
  watch,
  ref,
  onBeforeUnmount,
} from "../../shared/state/store.js";
import { useRouter } from "../../shared/routing/router.jsx";
import { api, session } from "../auth/api.js";
import { createContact } from "./contact.js";
function setup(__props) {
  const props = propsForSetup(__props, {
    propertyId: String,
  });
  const emit = emitForProps(__props, ["revealed"]);
  const router = useRouter();
  const contact = createContact(api);
  const ui = reactive({
    busy: false,
    data: null,
    message: "",
    status: 0,
    retryAt: 0,
  });
  let sequence = 0;
  const clock = ref(Date.now());
  const timer = setInterval(() => (clock.value = Date.now()), 1000);
  const copiedPhone = ref(false);
  const copiedEmail = ref(false);
  function copyText(text, isEmail = false) {
    if (!text) return;
    try {
      navigator.clipboard.writeText(text);
      if (isEmail) {
        copiedEmail.value = true;
        setTimeout(() => (copiedEmail.value = false), 2000);
      } else {
        copiedPhone.value = true;
        setTimeout(() => (copiedPhone.value = false), 2000);
      }
    } catch (e) {
      // fallback
    }
  }
  const reset = () => {
    sequence++;
    contact.reset();
    Object.assign(ui, contact.state);
    emit("revealed", null);
  };
  watch(() => [props.propertyId, session.user?.id, session.token], reset);
  onBeforeUnmount(() => {
    clearInterval(timer);
    reset();
  });
  async function reveal() {
    if (!session.token) {
      return router.push({
        path: "/login",
        query: {
          reason: "login-required",
        },
      });
    }
    const run = ++sequence;
    ui.busy = true;
    await contact.reveal(props.propertyId);
    if (run === sequence) {
      Object.assign(ui, contact.state);
      if (ui.data?.available) {
        emit("revealed", ui.data);
      }
    }
  }
  const telephone = (value) =>
    /^\+?[0-9 ().-]{5,30}$/.test(value || "")
      ? "tel:" + value.replace(/[ ().-]/g, "")
      : null;
  const email = (value) =>
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value || "") ? "mailto:" + value : null;
  const zaloUrl = (value) => {
    if (!value) return null;
    const clean = value.replace(/[^0-9]/g, "");
    return clean ? `https://zalo.me/${clean}` : null;
  };
  return {
    reactive,
    watch,
    ref,
    onBeforeUnmount,
    useRouter,
    api,
    session,
    createContact,
    props,
    emit,
    router,
    contact,
    ui,
    sequence,
    clock,
    timer,
    copiedPhone,
    copiedEmail,
    copyText,
    reset,
    reveal,
    telephone,
    email,
    zaloUrl,
  };
}
export default React.forwardRef(function ContactPanel(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="ContactPanel"
      {...mergeProps({
        className: "space-y-3",
        "data-testid": "contact-panel",
        "aria-live": "polite",
      })}
    >
      {!ctx.ui.data?.available ? (
        <div {...mergeProps({})}>
          <button
            {...mergeProps({
              type: "button",
              className:
                "w-full py-3.5 px-4 rounded-2xl bg-[var(--ui-soft)] hover:bg-[var(--ui-soft)] text-brand-navy font-bold text-sm tracking-wide shadow-md flex items-center justify-center gap-2.5 transition-all duration-150 active:scale-[0.98] disabled:opacity-50 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ui-border)] focus-visible:ring-offset-2",
              disabled: ctx.ui.busy || ctx.clock < ctx.ui.retryAt,
              onClick: ($event) => {
                return ctx.reveal?.($event);
              },
            })}
          >
            {ctx.ui.busy ? (
              <svg
                {...mergeProps({
                  className: "animate-spin w-4 h-4 text-brand-navy",
                  viewBox: "0 0 24 24",
                  fill: "none",
                })}
              >
                <circle
                  {...mergeProps({
                    className: "opacity-25",
                    cx: "12",
                    cy: "12",
                    r: "10",
                    stroke: "currentColor",
                    strokeWidth: "4",
                  })}
                />
                <path
                  {...mergeProps({
                    className: "opacity-75",
                    fill: "currentColor",
                    d: "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z",
                  })}
                />
              </svg>
            ) : (
              <svg
                {...mergeProps({
                  width: "17",
                  height: "17",
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  strokeWidth: "2.2",
                  strokeLinecap: "round",
                  strokeLinejoin: "round",
                })}
              >
                <path
                  {...mergeProps({
                    d: "M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z",
                  })}
                />
              </svg>
            )}
            <span {...mergeProps({})}>
              {display(
                ctx.ui.busy
                  ? "Đang xác thực thông tin…"
                  : "Xem số điện thoại & Liên hệ",
              )}
            </span>
          </button>
          <div
            {...mergeProps({
              className:
                "flex items-center justify-center gap-1.5 text-[11px] text-brand-muted mt-2",
            })}
          >
            <svg
              {...mergeProps({
                width: "12",
                height: "12",
                viewBox: "0 0 24 24",
                fill: "none",
                stroke: "currentColor",
                strokeWidth: "2",
                className: "text-brand-muted",
              })}
            >
              <rect
                {...mergeProps({
                  x: "3",
                  y: "11",
                  width: "18",
                  height: "11",
                  rx: "2",
                  ry: "2",
                })}
              />
              <path
                {...mergeProps({
                  d: "M7 11V7a5 5 0 0 1 10 0v4",
                })}
              />
            </svg>
            <span {...mergeProps({})}>
              {"Thông tin liên hệ bảo mật chống spam"}
            </span>
          </div>
        </div>
      ) : null}
      {ctx.ui.message ? (
        <p
          {...mergeProps({
            role: ctx.ui.status ? "alert" : "status",
            className:
              "text-xs text-[var(--ui-warning-text)] bg-[var(--ui-warning-bg)]/90 p-3 rounded-xl border border-[var(--ui-warning-border)]/80 flex items-center gap-2",
          })}
        >
          <svg
            {...mergeProps({
              width: "14",
              height: "14",
              viewBox: "0 0 24 24",
              fill: "none",
              stroke: "currentColor",
              strokeWidth: "2",
              className: "shrink-0 text-[var(--ui-warning-text)]",
            })}
          >
            <circle
              {...mergeProps({
                cx: "12",
                cy: "12",
                r: "10",
              })}
            />
            <line
              {...mergeProps({
                x1: "12",
                y1: "8",
                x2: "12",
                y2: "12",
              })}
            />
            <line
              {...mergeProps({
                x1: "12",
                y1: "16",
                x2: "12.01",
                y2: "16",
              })}
            />
          </svg>
          <span {...mergeProps({})}>{display(ctx.ui.message)}</span>
        </p>
      ) : null}
      {ctx.ui.data?.available ? (
        <React.Fragment {...mergeProps({})}>
          {ctx.ui.data.contactPhone ? (
            <div
              {...mergeProps({
                className: "space-y-2",
              })}
            >
              <div
                {...mergeProps({
                  className: "flex items-center gap-2",
                })}
              >
                {ctx.telephone(ctx.ui.data.contactPhone) ? (
                  <a
                    {...mergeProps({
                      href: ctx.telephone(ctx.ui.data.contactPhone),
                      className:
                        "flex-1 py-3.5 px-4 rounded-2xl bg-[var(--ui-success-bg)] hover:bg-[var(--ui-success-bg)] text-brand-navy font-bold text-sm shadow-md flex items-center justify-center gap-2.5 transition-all duration-150 active:scale-[0.98] text-center cursor-pointer",
                    })}
                  >
                    <svg
                      {...mergeProps({
                        width: "17",
                        height: "17",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2.2",
                        strokeLinecap: "round",
                        strokeLinejoin: "round",
                      })}
                    >
                      <path
                        {...mergeProps({
                          d: "M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z",
                        })}
                      />
                    </svg>
                    <span {...mergeProps({})}>
                      {display(ctx.ui.data.contactPhone)}
                      {" · Gọi ngay"}
                    </span>
                  </a>
                ) : (
                  <div
                    {...mergeProps({
                      className:
                        "flex-1 py-3.5 px-4 rounded-2xl bg-[var(--ui-success-bg)] text-brand-navy font-bold text-sm flex items-center justify-center gap-2",
                    })}
                  >
                    <svg
                      {...mergeProps({
                        width: "17",
                        height: "17",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2.2",
                      })}
                    >
                      <path
                        {...mergeProps({
                          d: "M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z",
                        })}
                      />
                    </svg>
                    <span {...mergeProps({})}>
                      {display(ctx.ui.data.contactPhone)}
                    </span>
                  </div>
                )}
                <button
                  {...mergeProps({
                    type: "button",
                    className:
                      "px-3.5 py-3.5 rounded-2xl border border-brand-line hover:bg-brand-card/80 active:scale-95 text-xs font-semibold text-brand-muted transition-all duration-150 shrink-0 cursor-pointer shadow-2xs",
                    title: ctx.copiedPhone
                      ? "Đã sao chép!"
                      : "Sao chép số điện thoại",
                    onClick: ($event) => {
                      ctx.copyText(ctx.ui.data.contactPhone, false);
                    },
                  })}
                >
                  {ctx.copiedPhone ? (
                    <svg
                      {...mergeProps({
                        width: "16",
                        height: "16",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2.5",
                        className: "text-[var(--ui-success-text)]",
                      })}
                    >
                      <polyline
                        {...mergeProps({
                          points: "20 6 9 17 4 12",
                        })}
                      />
                    </svg>
                  ) : (
                    <svg
                      {...mergeProps({
                        width: "16",
                        height: "16",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2",
                      })}
                    >
                      <rect
                        {...mergeProps({
                          x: "9",
                          y: "9",
                          width: "13",
                          height: "13",
                          rx: "2",
                          ry: "2",
                        })}
                      />
                      <path
                        {...mergeProps({
                          d: "M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1",
                        })}
                      />
                    </svg>
                  )}
                </button>
              </div>
              <div
                {...mergeProps({
                  className: "grid grid-cols-2 gap-2 pt-1",
                })}
              >
                {ctx.zaloUrl(ctx.ui.data.contactPhone) ? (
                  <a
                    {...mergeProps({
                      href: ctx.zaloUrl(ctx.ui.data.contactPhone),
                      target: "_blank",
                      rel: "noopener noreferrer",
                      className:
                        "py-2.5 px-3 rounded-xl bg-brand-card hover:bg-brand-card border border-brand-line text-brand-muted font-bold text-xs flex items-center justify-center gap-1.5 transition-all duration-150 cursor-pointer",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className:
                          "w-4 h-4 rounded-full bg-brand-card text-brand-navy text-[9px] font-black flex items-center justify-center",
                      })}
                    >
                      {"Z"}
                    </span>
                    <span {...mergeProps({})}>{"Chat Zalo"}</span>
                  </a>
                ) : null}
                <button
                  {...mergeProps({
                    type: "button",
                    className:
                      "py-2.5 px-3 rounded-xl bg-brand-card hover:bg-brand-card border border-brand-line text-brand-muted font-semibold text-xs flex items-center justify-center gap-1.5 transition-all duration-150 cursor-pointer",
                    onClick: ($event) => {
                      ctx.copyText(ctx.ui.data.contactPhone, false);
                    },
                  })}
                >
                  <span
                    {...mergeProps({
                      className: "text-[11px]",
                    })}
                  >
                    {display(ctx.copiedPhone ? "✓ Đã chép" : "📋 Sao chép số")}
                  </span>
                </button>
              </div>
            </div>
          ) : null}
          {ctx.ui.data.contactEmail ? (
            <div
              {...mergeProps({
                className:
                  "p-3 rounded-2xl bg-brand-card border border-brand-line flex items-center justify-between gap-2.5",
              })}
            >
              <div
                {...mergeProps({
                  className: "flex items-center gap-2.5 min-w-0",
                })}
              >
                <div
                  {...mergeProps({
                    className:
                      "w-8 h-8 rounded-xl bg-brand-card text-[var(--ui-accent)] flex items-center justify-center text-xs shrink-0 border border-brand-line",
                  })}
                >
                  <svg
                    {...mergeProps({
                      width: "15",
                      height: "15",
                      viewBox: "0 0 24 24",
                      fill: "none",
                      stroke: "currentColor",
                      strokeWidth: "2",
                    })}
                  >
                    <path
                      {...mergeProps({
                        d: "M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z",
                      })}
                    />
                    <polyline
                      {...mergeProps({
                        points: "22,6 12,13 2,6",
                      })}
                    />
                  </svg>
                </div>
                <div
                  {...mergeProps({
                    className: "min-w-0",
                  })}
                >
                  <p
                    {...mergeProps({
                      className:
                        "text-[10px] text-brand-muted font-medium uppercase tracking-wider",
                    })}
                  >
                    {"Email liên hệ"}
                  </p>
                  {ctx.email(ctx.ui.data.contactEmail) ? (
                    <a
                      {...mergeProps({
                        href: ctx.email(ctx.ui.data.contactEmail),
                        className:
                          "text-xs font-bold text-[var(--ui-accent)] hover:text-[var(--ui-accent)] hover:underline truncate block",
                      })}
                    >
                      {display(ctx.ui.data.contactEmail)}
                    </a>
                  ) : (
                    <span
                      {...mergeProps({
                        className:
                          "text-xs font-bold text-[var(--ui-accent)] truncate block",
                      })}
                    >
                      {display(ctx.ui.data.contactEmail)}
                    </span>
                  )}
                </div>
              </div>
              <button
                {...mergeProps({
                  type: "button",
                  className:
                    "p-2 rounded-xl text-brand-muted hover:text-brand-muted hover:bg-brand-card transition cursor-pointer",
                  title: ctx.copiedEmail
                    ? "Đã sao chép email!"
                    : "Sao chép email",
                  onClick: ($event) => {
                    ctx.copyText(ctx.ui.data.contactEmail, true);
                  },
                })}
              >
                {ctx.copiedEmail ? (
                  <svg
                    {...mergeProps({
                      width: "14",
                      height: "14",
                      viewBox: "0 0 24 24",
                      fill: "none",
                      stroke: "currentColor",
                      strokeWidth: "2.5",
                      className: "text-[var(--ui-success-text)]",
                    })}
                  >
                    <polyline
                      {...mergeProps({
                        points: "20 6 9 17 4 12",
                      })}
                    />
                  </svg>
                ) : (
                  <svg
                    {...mergeProps({
                      width: "14",
                      height: "14",
                      viewBox: "0 0 24 24",
                      fill: "none",
                      stroke: "currentColor",
                      strokeWidth: "2",
                    })}
                  >
                    <rect
                      {...mergeProps({
                        x: "9",
                        y: "9",
                        width: "13",
                        height: "13",
                        rx: "2",
                        ry: "2",
                      })}
                    />
                    <path
                      {...mergeProps({
                        d: "M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1",
                      })}
                    />
                  </svg>
                )}
              </button>
            </div>
          ) : null}
        </React.Fragment>
      ) : null}
      {ctx.clock < ctx.ui.retryAt ? (
        <p
          {...mergeProps({
            className: "text-xs text-brand-muted text-center",
          })}
        >
          {" Có thể thử lại sau "}
          {display(Math.ceil((ctx.ui.retryAt - ctx.clock) / 1000))}
          {" giây. "}
        </p>
      ) : null}
    </div>,
  ]);
});
