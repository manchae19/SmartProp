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
import { computed, ref, watch, onMounted } from "../../shared/state/store.js";
import { useRouter, useRoute } from "../../shared/routing/router.jsx";
import { api, login, register, errorText } from "./api.js";
import { safeLoginDestination } from "./authNavigation.js";
import GoogleLoginButton from "./GoogleLoginButton.jsx";
function setup(__props) {
  const props = propsForSetup(__props, {
      initialRegister: Boolean,
    }),
    router = useRouter(),
    route = useRoute();
  const isRegister = computed(
      () => props.initialRegister || route.path === "/register",
    ),
    forgot = ref(false);
  const fullName = ref(""),
    email = ref(""),
    password = ref(""),
    confirmPassword = ref(""),
    showPassword = ref(false),
    showConfirm = ref(false);
  const busy = ref(false),
    message = ref(""),
    error = ref(""),
    video = ref(null),
    playing = ref(false);
  const reasons = {
    "password-changed":
      "Đổi mật khẩu thành công. Vui lòng đăng nhập bằng mật khẩu mới.",
    "session-expired":
      "Phiên đã hết hạn hoặc bị thu hồi. Vui lòng đăng nhập lại.",
    "session-unavailable": "Vui lòng đăng nhập lại để tiếp tục.",
    "login-required": "Đăng nhập để sử dụng chức năng này.",
    "google-failed":
      "Chưa hoàn tất đăng nhập Google. Vui lòng thử lại hoặc đăng nhập bằng email.",
  };
  watch(
    () => route.fullPath,
    () => {
      message.value =
        route.query.registered === "1"
          ? "Tạo tài khoản thành công. Bạn có thể đăng nhập ngay."
          : reasons[route.query.reason] || "";
      error.value = "";
      forgot.value = false;
    },
    {
      immediate: true,
    },
  );
  const heading = computed(() =>
    forgot.value
      ? "Khôi phục mật khẩu"
      : isRegister.value
        ? "Bắt đầu cùng SmartProp"
        : "Chào mừng bạn trở lại",
  );
  function switchTab(path) {
    if (!busy.value) router.push(path);
  }
  async function toggleVideo() {
    if (!video.value) return;
    if (playing.value) {
      video.value.pause();
      playing.value = false;
    } else {
      try {
        await video.value.play();
        playing.value = true;
      } catch {
        playing.value = false;
      }
    }
  }
  onMounted(() => {
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches)
      toggleVideo();
  });
  async function submit() {
    if (busy.value) return;
    error.value = message.value = "";
    if (!forgot.value && new TextEncoder().encode(password.value).length > 72) {
      error.value = "Mật khẩu tối đa 72 byte UTF-8. Vui lòng kiểm tra lại.";
      return;
    }
    if (
      isRegister.value &&
      !forgot.value &&
      password.value !== confirmPassword.value
    ) {
      error.value = "Mật khẩu xác nhận không khớp.";
      return;
    }
    busy.value = true;
    try {
      if (forgot.value) {
        await api("/auth/password/forgot", {
          method: "POST",
          body: {
            email: email.value.trim(),
          },
          authenticated: false,
        });
        message.value =
          "Nếu tài khoản đủ điều kiện, liên kết đặt lại mật khẩu sẽ được gửi đến email của bạn.";
      } else if (isRegister.value) {
        await register({
          fullName: fullName.value.trim(),
          email: email.value,
          password: password.value,
          role: "BUYER",
        });
        password.value = confirmPassword.value = "";
        await router.replace({
          path: "/login",
          query: {
            registered: "1",
          },
        });
      } else {
        const user = await login(email.value, password.value, false);
        password.value = "";
        await router.replace(safeLoginDestination(route.query.next, user.role));
      }
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }
  return {
    computed,
    ref,
    watch,
    onMounted,
    useRouter,
    useRoute,
    api,
    login,
    register,
    errorText,
    safeLoginDestination,
    GoogleLoginButton,
    props,
    router,
    route,
    isRegister,
    forgot,
    fullName,
    email,
    password,
    confirmPassword,
    showPassword,
    showConfirm,
    busy,
    message,
    error,
    video,
    playing,
    reasons,
    heading,
    switchTab,
    toggleVideo,
    submit,
  };
}
export default React.forwardRef(function LoginView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <main data-ui-view="LoginView"
      {...mergeProps({
        className:
          "min-h-screen relative isolation-auto bg-[var(--ui-soft)] flex items-center justify-center p-4 sm:p-6 lg:p-10 font-sans selection:bg-[var(--ui-soft)] selection:text-brand-navy",
      })}
    >
      <video
        {...mergeProps({
          ref: bindRef(ctx, "video"),
          className:
            "absolute inset-0 w-full h-full object-cover z-0 pointer-events-none opacity-50",
          src: "/background.mp4",
          loop: true,
          muted: true,
          playsInline: true,
          "aria-hidden": "true",
        })}
      />
      <div
        {...mergeProps({
          className:
            "absolute inset-0 bg-gradient-to-tr from-[var(--ui-soft)]/95 via-[var(--ui-soft)]/80 to-[var(--ui-soft)]/95 z-0 pointer-events-none",
        })}
      />
      <div
        {...mergeProps({
          className:
            "relative z-10 w-full max-w-[1200px] mx-auto grid grid-cols-1 lg:grid-cols-[1.1fr_480px] gap-8 lg:gap-14 items-center",
        })}
      >
        <section
          {...mergeProps({
            className:
              "hidden lg:flex flex-col justify-between min-h-[600px] text-brand-navy py-4 pr-6",
            "aria-label": "SmartProp",
          })}
        >
          <div {...mergeProps({})}>
            <RouterLink
              {...mergeProps({
                to: "/home",
                className: "inline-flex items-center gap-3 group",
              })}
            >
              <span
                {...mergeProps({
                  className:
                    "w-11 h-11 rounded-xl bg-brand-card text-[var(--ui-accent)] font-black text-2xl flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform duration-200",
                })}
              >
                {" S "}
              </span>
              <span
                {...mergeProps({
                  className:
                    "text-2xl font-bold tracking-tight text-brand-navy block",
                })}
              >
                {"SmartProp."}
              </span>
            </RouterLink>
          </div>
          <div
            {...mergeProps({
              className: "space-y-5 my-auto max-w-[500px]",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-semibold tracking-[0.18em] text-[var(--ui-ink)] uppercase",
              })}
            >
              {" ĐÀ NẴNG · SMARTPROP "}
            </p>
            <h1
              {...mergeProps({
                className:
                  "text-4xl xl:text-5xl font-medium tracking-tight text-brand-navy leading-[1.25]",
              })}
            >
              {" Không gian sống."}
              <br {...mergeProps({})} />
              <em
                {...mergeProps({
                  className: "font-serif not-italic text-[var(--ui-ink)]",
                })}
              >
                {"Khởi đầu của bạn."}
              </em>
            </h1>
            <p
              {...mergeProps({
                className:
                  "text-brand-navy text-sm xl:text-base leading-relaxed",
              })}
            >
              {
                " Khám phá bất động sản, lưu những lựa chọn yêu thích và tìm hiểu giá trị từ dữ liệu. "
              }
            </p>
          </div>
          <div
            {...mergeProps({
              className: "pt-4",
            })}
          >
            <button
              {...mergeProps({
                type: "button",
                className:
                  "inline-flex items-center gap-2 px-4 py-2 rounded-full border border-brand-line/40 hover:border-brand-line text-xs text-brand-navy transition-all cursor-pointer backdrop-blur-sm",
                "aria-pressed": ctx.playing,
                onClick: ($event) => {
                  return ctx.toggleVideo?.($event);
                },
              })}
            >
              <span {...mergeProps({})}>
                {display(ctx.playing ? "Ⅱ" : "▷")}
              </span>
              <span {...mergeProps({})}>
                {display(ctx.playing ? "Tạm dừng nền" : "Phát video nền")}
              </span>
            </button>
          </div>
        </section>
        <section
          {...mergeProps({
            className:
              "bg-brand-card/95 backdrop-blur-xl rounded-3xl p-6 sm:p-9 shadow-2xl border border-brand-line/60 relative",
            "aria-busy": ctx.busy,
            "aria-labelledby": "auth-heading",
          })}
        >
          <div
            {...mergeProps({
              className: "mb-5",
            })}
          >
            <RouterLink
              {...mergeProps({
                to: "/home",
                className:
                  "inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--ui-accent)] hover:text-[var(--ui-accent)] transition-all cursor-pointer",
              })}
            >
              <svg
                {...mergeProps({
                  width: "13",
                  height: "13",
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  strokeWidth: "2.5",
                })}
              >
                <line
                  {...mergeProps({
                    x1: "19",
                    y1: "12",
                    x2: "5",
                    y2: "12",
                  })}
                />
                <polyline
                  {...mergeProps({
                    points: "12 19 5 12 12 5",
                  })}
                />
              </svg>
              <span {...mergeProps({})}>{"Trang chủ SmartProp"}</span>
            </RouterLink>
          </div>
          {!ctx.forgot ? (
            <div
              {...mergeProps({
                className:
                  "bg-brand-card p-1.5 rounded-2xl flex border border-brand-line/80 mb-6",
                role: "tablist",
                "aria-label": "Đăng nhập hoặc đăng ký",
              })}
            >
              <button
                {...mergeProps({
                  type: "button",
                  role: "tab",
                  "aria-selected": !ctx.isRegister,
                  disabled: ctx.busy,
                  className: ["w-1/2 py-2.5 px-4 rounded-xl text-xs font-bold transition-all duration-150 cursor-pointer text-center", !ctx.isRegister
                    ? "bg-brand-card text-[var(--ui-accent)] shadow-xs"
                    : "text-brand-muted hover:text-[var(--ui-accent)]"],
                  
                  onClick: ($event) => {
                    ctx.switchTab("/login");
                  },
                })}
              >
                {" Đăng nhập "}
              </button>
              <button
                {...mergeProps({
                  type: "button",
                  role: "tab",
                  "aria-selected": ctx.isRegister,
                  disabled: ctx.busy,
                  className: ["w-1/2 py-2.5 px-4 rounded-xl text-xs font-bold transition-all duration-150 cursor-pointer text-center", ctx.isRegister
                    ? "bg-brand-card text-[var(--ui-accent)] shadow-xs"
                    : "text-brand-muted hover:text-[var(--ui-accent)]"],
                  
                  onClick: ($event) => {
                    ctx.switchTab("/register");
                  },
                })}
              >
                {" Đăng ký "}
              </button>
            </div>
          ) : (
            <button
              {...mergeProps({
                type: "button",
                className:
                  "inline-flex items-center gap-1.5 text-xs font-bold text-[var(--ui-accent)] hover:text-[var(--ui-accent)] transition mb-5 cursor-pointer",
                onClick: ($event) => {
                  ctx.forgot = false;
                  ctx.message = ctx.error = "";
                },
              })}
            >
              <svg
                {...mergeProps({
                  width: "13",
                  height: "13",
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  strokeWidth: "2.5",
                })}
              >
                <line
                  {...mergeProps({
                    x1: "19",
                    y1: "12",
                    x2: "5",
                    y2: "12",
                  })}
                />
                <polyline
                  {...mergeProps({
                    points: "12 19 5 12 12 5",
                  })}
                />
              </svg>
              <span {...mergeProps({})}>{"Quay lại đăng nhập"}</span>
            </button>
          )}
          <div
            {...mergeProps({
              className: "mb-5",
            })}
          >
            <h2
              {...mergeProps({
                id: "auth-heading",
                className:
                  "text-2xl sm:text-3xl font-extrabold text-[var(--ui-accent)] tracking-tight",
              })}
            >
              {display(ctx.heading)}
            </h2>
            <p
              {...mergeProps({
                className:
                  "text-xs sm:text-sm text-[var(--ui-accent)] mt-1.5 leading-relaxed",
              })}
            >
              {display(
                ctx.forgot
                  ? "Nhập email để nhận liên kết đặt lại mật khẩu."
                  : ctx.isRegister
                    ? "Một tài khoản cho mọi trải nghiệm của bạn."
                    : "Đăng nhập để tiếp tục từ những điều bạn quan tâm.",
              )}
            </p>
          </div>
          {ctx.message ? (
            <div
              {...mergeProps({
                role: "status",
                className:
                  "p-3.5 rounded-xl bg-[var(--ui-surface)] border border-[var(--ui-success-border)] text-xs font-semibold text-[var(--ui-accent)] flex items-center gap-2 mb-4",
              })}
            >
              <svg
                {...mergeProps({
                  width: "16",
                  height: "16",
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  strokeWidth: "2.5",
                  className: "shrink-0 text-[var(--ui-accent)]",
                })}
              >
                <polyline
                  {...mergeProps({
                    points: "20 6 9 17 4 12",
                  })}
                />
              </svg>
              <span {...mergeProps({})}>{display(ctx.message)}</span>
            </div>
          ) : null}
          {ctx.error ? (
            <div
              {...mergeProps({
                role: "alert",
                className:
                  "p-3.5 rounded-xl bg-[var(--ui-surface)] border border-[var(--ui-error-border)] text-xs font-semibold text-[var(--ui-muted)] flex items-center gap-2 mb-4",
              })}
            >
              <svg
                {...mergeProps({
                  width: "16",
                  height: "16",
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  strokeWidth: "2.5",
                  className: "shrink-0 text-[var(--ui-muted)]",
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
              <span {...mergeProps({})}>{display(ctx.error)}</span>
            </div>
          ) : null}
          <form
            {...mergeProps({
              className: "space-y-4",
              onSubmit: ($event) => {
                $event.preventDefault();
                return ctx.submit?.($event);
              },
            })}
          >
            {ctx.isRegister && !ctx.forgot ? (
              <div
                {...mergeProps({
                  className: "space-y-1.5",
                })}
              >
                <label
                  {...mergeProps({
                    className: "block text-xs font-bold text-[var(--ui-accent)]",
                    htmlFor: "name-input",
                  })}
                >
                  {" Họ và tên "}
                </label>
                <div
                  {...mergeProps({
                    className: "relative flex items-center",
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
                      className:
                        "absolute left-3.5 text-brand-muted pointer-events-none",
                    })}
                  >
                    <path
                      {...mergeProps({
                        d: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2",
                      })}
                    />
                    <circle
                      {...mergeProps({
                        cx: "12",
                        cy: "7",
                        r: "4",
                      })}
                    />
                  </svg>
                  <input
                    {...mergeProps(
                      {
                        id: "name-input",
                        type: "text",
                        autoComplete: "name",
                        required: true,
                        maxLength: "100",
                        placeholder: "Họ và tên của bạn",
                        disabled: ctx.busy,
                        className:
                          "w-full pl-10 pr-4 py-2.5 sm:py-3 rounded-xl border border-brand-line bg-brand-card text-[var(--ui-accent)] text-xs sm:text-sm font-normal placeholder:text-brand-muted focus:outline-none focus:border-[var(--ui-border)] focus:ring-4 focus:ring-[var(--ui-border)]/15 transition-all duration-150 disabled:bg-brand-card shadow-2xs",
                      },
                      modelProps(
                        ctx.fullName,
                        ($value) => {
                          ctx.fullName = $value;
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
                </div>
              </div>
            ) : null}
            <div
              {...mergeProps({
                className: "space-y-1.5",
              })}
            >
              <label
                {...mergeProps({
                  className: "block text-xs font-bold text-[var(--ui-accent)]",
                  htmlFor: "email-input",
                })}
              >
                {display(
                  !ctx.isRegister && !ctx.forgot
                    ? "Email / tên quản trị"
                    : "Email",
                )}
              </label>
              <div
                {...mergeProps({
                  className: "relative flex items-center",
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
                    className:
                      "absolute left-3.5 text-brand-muted pointer-events-none",
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
                <input
                  {...mergeProps(
                    {
                      id: "email-input",
                      type: !ctx.isRegister && !ctx.forgot ? "text" : "email",
                      autoComplete:
                        !ctx.isRegister && !ctx.forgot ? "username" : "email",
                      maxLength: "254",
                      required: true,
                      placeholder:
                        !ctx.isRegister && !ctx.forgot
                          ? "Email hoặc Admin"
                          : "ban@email.com",
                      disabled: ctx.busy,
                      className:
                        "w-full pl-10 pr-4 py-2.5 sm:py-3 rounded-xl border border-brand-line bg-brand-card text-[var(--ui-accent)] text-xs sm:text-sm font-normal placeholder:text-brand-muted focus:outline-none focus:border-[var(--ui-border)] focus:ring-4 focus:ring-[var(--ui-border)]/15 transition-all duration-150 disabled:bg-brand-card shadow-2xs",
                    },
                    modelProps(
                      ctx.email,
                      ($value) => {
                        ctx.email = $value;
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
              </div>
            </div>
            {!ctx.forgot ? (
              <div
                {...mergeProps({
                  className: "space-y-1.5",
                })}
              >
                <div
                  {...mergeProps({
                    className: "flex items-center justify-between",
                  })}
                >
                  <label
                    {...mergeProps({
                      className: "block text-xs font-bold text-[var(--ui-accent)]",
                      htmlFor: "password-input",
                    })}
                  >
                    {" Mật khẩu "}
                  </label>
                  {!ctx.isRegister && !ctx.forgot ? (
                    <button
                      {...mergeProps({
                        type: "button",
                        className:
                          "text-xs text-[var(--ui-accent)] hover:text-[var(--ui-accent)] hover:underline cursor-pointer",
                        onClick: ($event) => {
                          ctx.forgot = true;
                          ctx.error = ctx.message = "";
                        },
                      })}
                    >
                      {" Quên mật khẩu? "}
                    </button>
                  ) : null}
                </div>
                <div
                  {...mergeProps({
                    className: "relative flex items-center",
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
                      className:
                        "absolute left-3.5 text-brand-muted pointer-events-none",
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
                  <input
                    {...mergeProps(
                      {
                        id: "password-input",
                        type: ctx.showPassword ? "text" : "password",
                        autoComplete: ctx.isRegister
                          ? "new-password"
                          : "current-password",
                        minLength: ctx.isRegister ? 8 : undefined,
                        maxLength: "72",
                        required: true,
                        placeholder: ctx.isRegister
                          ? "Tối thiểu 8 ký tự"
                          : "Nhập mật khẩu",
                        disabled: ctx.busy,
                        className:
                          "w-full pl-10 pr-11 py-2.5 sm:py-3 rounded-xl border border-brand-line bg-brand-card text-[var(--ui-accent)] text-xs sm:text-sm font-normal placeholder:text-brand-muted focus:outline-none focus:border-[var(--ui-border)] focus:ring-4 focus:ring-[var(--ui-border)]/15 transition-all duration-150 disabled:bg-brand-card shadow-2xs",
                      },
                      modelProps(
                        ctx.password,
                        ($value) => {
                          ctx.password = $value;
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
                  <button
                    {...mergeProps({
                      type: "button",
                      className:
                        "absolute right-2.5 p-1.5 text-brand-muted hover:text-[var(--ui-accent)] transition cursor-pointer",
                      "aria-label": ctx.showPassword
                        ? "Ẩn mật khẩu"
                        : "Hiện mật khẩu",
                      onClick: ($event) => {
                        ctx.showPassword = !ctx.showPassword;
                      },
                    })}
                  >
                    {ctx.showPassword ? (
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
                        <path
                          {...mergeProps({
                            d: "M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24",
                          })}
                        />
                        <line
                          {...mergeProps({
                            x1: "1",
                            y1: "1",
                            x2: "23",
                            y2: "23",
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
                        <path
                          {...mergeProps({
                            d: "M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z",
                          })}
                        />
                        <circle
                          {...mergeProps({
                            cx: "12",
                            cy: "12",
                            r: "3",
                          })}
                        />
                      </svg>
                    )}
                  </button>
                </div>
                {ctx.isRegister ? (
                  <p
                    {...mergeProps({
                      className: "text-[11px] text-[var(--ui-accent)]",
                    })}
                  >
                    {" Từ 8 ký tự, tối đa 72 byte UTF-8. "}
                  </p>
                ) : null}
              </div>
            ) : null}
            {ctx.isRegister && !ctx.forgot ? (
              <div
                {...mergeProps({
                  className: "space-y-1.5",
                })}
              >
                <label
                  {...mergeProps({
                    className: "block text-xs font-bold text-[var(--ui-accent)]",
                    htmlFor: "confirm-password-input",
                  })}
                >
                  {" Xác nhận mật khẩu "}
                </label>
                <div
                  {...mergeProps({
                    className: "relative flex items-center",
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
                      className:
                        "absolute left-3.5 text-brand-muted pointer-events-none",
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
                  <input
                    {...mergeProps(
                      {
                        id: "confirm-password-input",
                        type: ctx.showConfirm ? "text" : "password",
                        autoComplete: "new-password",
                        minLength: "8",
                        maxLength: "72",
                        required: true,
                        placeholder: "Nhập lại mật khẩu",
                        disabled: ctx.busy,
                        className:
                          "w-full pl-10 pr-11 py-2.5 sm:py-3 rounded-xl border border-brand-line bg-brand-card text-[var(--ui-accent)] text-xs sm:text-sm font-normal placeholder:text-brand-muted focus:outline-none focus:border-[var(--ui-border)] focus:ring-4 focus:ring-[var(--ui-border)]/15 transition-all duration-150 disabled:bg-brand-card shadow-2xs",
                      },
                      modelProps(
                        ctx.confirmPassword,
                        ($value) => {
                          ctx.confirmPassword = $value;
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
                  <button
                    {...mergeProps({
                      type: "button",
                      className:
                        "absolute right-2.5 p-1.5 text-brand-muted hover:text-[var(--ui-accent)] transition cursor-pointer",
                      "aria-label": ctx.showConfirm
                        ? "Ẩn mật khẩu xác nhận"
                        : "Hiện mật khẩu xác nhận",
                      onClick: ($event) => {
                        ctx.showConfirm = !ctx.showConfirm;
                      },
                    })}
                  >
                    {ctx.showConfirm ? (
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
                        <path
                          {...mergeProps({
                            d: "M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24",
                          })}
                        />
                        <line
                          {...mergeProps({
                            x1: "1",
                            y1: "1",
                            x2: "23",
                            y2: "23",
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
                        <path
                          {...mergeProps({
                            d: "M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z",
                          })}
                        />
                        <circle
                          {...mergeProps({
                            cx: "12",
                            cy: "12",
                            r: "3",
                          })}
                        />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
            ) : null}
            <button
              {...mergeProps({
                type: "submit",
                className:
                  "w-full min-h-[48px] py-3.5 px-6 rounded-xl bg-[var(--ui-soft)] hover:bg-[var(--ui-soft)] active:bg-[var(--ui-soft)] text-brand-navy font-bold text-sm tracking-wide shadow-md flex items-center justify-center gap-2 transition-all duration-150 active:scale-[0.99] disabled:opacity-60 disabled:cursor-wait cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ui-border)]",
                disabled: ctx.busy,
              })}
            >
              {ctx.busy ? (
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
              ) : null}
              <span {...mergeProps({})}>
                {display(
                  ctx.busy
                    ? "Đang xử lý…"
                    : ctx.forgot
                      ? "Gửi liên kết đặt lại"
                      : ctx.isRegister
                        ? "Tạo tài khoản"
                        : "Đăng nhập",
                )}
              </span>
            </button>
          </form>
          {!ctx.forgot ? (
            <GoogleLoginButton
              {...mergeProps({
                disabled: ctx.busy,
              })}
            />
          ) : null}
          <p
            {...mergeProps({
              className: "text-xs text-[var(--ui-accent)] text-center mt-6",
            })}
          >
            {" Tiếp tục khám phá không gian sống cùng SmartProp. "}
          </p>
        </section>
      </div>
    </main>,
  ]);
});
