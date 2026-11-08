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
import { ref, onMounted, computed } from "../../shared/state/store.js";
import { useRouter } from "../../shared/routing/router.jsx";
import {
  api,
  loadProfile,
  logout as revokeSession,
  clearSession,
  session,
  errorText,
} from "../auth/api.js";
import BrokerApplicationCard from "../broker/BrokerApplicationCard.jsx";
import ValuationHistory from "../prediction/ValuationHistory.jsx";
import UserAvatar from "../../shared/components/UserAvatar.jsx";
import AvatarEditor from "./AvatarEditor.jsx";
import AppIcon from "../../shared/components/AppIcon.jsx";
import "./AccountView.css";
import LifestyleFields, { emptyLifestyle } from "./LifestyleFields.jsx";
function setup(__props) {
  const router = useRouter(),
    form = ref({
      fullName: "",
      email: "",
      phone: "",
      district: "",
      address: "",
    });
  const prefs = ref({
      matchingListings: false,
      brokerMessages: false,
      statusUpdates: false,
    }),
    securityTab = ref("password");
  const currentPassword = ref(""),
    newPassword = ref(""),
    confirmPassword = ref(""),
    showPassword = ref(false);
  const busy = ref(false),
    loading = ref(true),
    loaded = ref(false),
    preferencesLoaded = ref(false),
    message = ref(""),
    error = ref(""),
    prefsError = ref(""),
    nameInput = ref(null);
  const roleLabel = computed(
    () =>
      ({
        BUYER: "Người mua / người thuê",
        BROKER: "Chủ nhà / môi giới",
        ADMIN: "Quản trị viên",
      })[session.user?.role] || "Thành viên",
  );
  const statusLabel = computed(
    () =>
      ({
        ACTIVE: "Đang hoạt động",
        LOCKED: "Đã khóa",
      })[session.user?.status] || "Đang kiểm tra",
  );
  const joined = computed(() =>
    session.user?.createdAt
      ? new Date(session.user.createdAt).toLocaleDateString("vi-VN", {
          day: "2-digit",
          month: "long",
          year: "numeric",
        })
      : "Chưa có thông tin",
  );
  const tools = [
    {
      to: "/favorites",
      icon: "heart",
      title: "Tin đã lưu",
      text: "Những không gian bạn quan tâm",
    },
    {
      to: "/account/reports",
      icon: "report",
      title: "Báo cáo của tôi",
      text: "Theo dõi phản hồi và xử lý",
    },
    {
      to: "/account/notifications",
      icon: "bell",
      title: "Thông báo",
      text: "Cập nhật hoạt động tài khoản",
    },
    {
      to: "/account/messages",
      icon: "messages",
      title: "Tin nhắn",
      text: "Tiếp tục những cuộc trò chuyện",
    },
  ];
  const preferenceLabels = [
    {
      key: "matchingListings",
      title: "Tin phù hợp với bạn",
      text: "Lưu tùy chọn nhận thông báo tin đăng phù hợp.",
    },
    {
      key: "brokerMessages",
      title: "Tin nhắn liên quan",
      text: "Lưu tùy chọn thông báo khi có trao đổi.",
    },
    {
      key: "statusUpdates",
      title: "Trạng thái tin và báo cáo",
      text: "Lưu tùy chọn cập nhật xử lý từ hệ thống.",
    },
  ];
  function fill(user) {
    form.value = {
      fullName: user.fullName,
      email: user.email,
      phone: user.phone || "",
      district: user.district || "",
      address: user.address || "",
      advisorPreferences: {...emptyLifestyle(), ...user.advisorPreferences},
    };
  }
  async function load() {
    loading.value = true;
    error.value = "";
    try {
      const user = await loadProfile();
      fill(user);
      loaded.value = true;
      await loadPreferences();
    } catch (e) {
      error.value = errorText(e);
    } finally {
      loading.value = false;
    }
  }
  async function loadPreferences() {
    prefsError.value = "";
    try {
      prefs.value = await api("/users/me/notification-preferences");
      preferencesLoaded.value = true;
    } catch (e) {
      preferencesLoaded.value = false;
      prefsError.value = errorText(e);
    }
  }
  async function saveProfile() {
    if (busy.value || !loaded.value) return;
    busy.value = true;
    message.value = error.value = "";
    try {
      const { email, ...body } = form.value;
      const user = await api("/users/me", {
        method: "PATCH",
        body,
      });
      session.user = user;
      fill(user);
      message.value = "Thông tin cá nhân đã được cập nhật.";
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }
  function resetProfile() {
    if (session.user) fill(session.user);
    message.value = error.value = "";
  }
  async function savePreferences() {
    if (busy.value || !preferencesLoaded.value) return;
    busy.value = true;
    prefsError.value = "";
    message.value = "";
    try {
      await api("/users/me/notification-preferences", {
        method: "PATCH",
        body: prefs.value,
      });
      message.value = "Đã lưu tùy chọn thông báo.";
    } catch (e) {
      prefsError.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }
  async function changePassword() {
    if (busy.value) return;
    message.value = error.value = "";
    if (newPassword.value !== confirmPassword.value) {
      error.value = "Mật khẩu xác nhận không khớp.";
      return;
    }
    if (new TextEncoder().encode(newPassword.value).length > 72) {
      error.value =
        "Mật khẩu tối đa 72 byte UTF-8. Vui lòng dùng mật khẩu ngắn hơn.";
      return;
    }
    busy.value = true;
    try {
      await api("/users/me/password", {
        method: "PUT",
        body: {
          currentPassword: currentPassword.value,
          newPassword: newPassword.value,
        },
      });
      currentPassword.value = newPassword.value = confirmPassword.value = "";
      clearSession();
      await router.replace({
        path: "/login",
        query: {
          reason: "password-changed",
        },
      });
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }
  function editProfile() {
    document.getElementById("personal-information")?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "start",
    });
    nameInput.value?.focus({
      preventScroll: true,
    });
  }
  async function signOut() {
    if (busy.value) return;
    busy.value = true;
    try {
      await revokeSession();
      await router.replace("/login");
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }
  onMounted(load);
  return {
    ref,
    onMounted,
    computed,
    useRouter,
    api,
    loadProfile,
    revokeSession,
    clearSession,
    session,
    errorText,
    BrokerApplicationCard,
    ValuationHistory,
    UserAvatar,
    AvatarEditor,
    AppIcon,
    router,
    form,
    prefs,
    securityTab,
    currentPassword,
    newPassword,
    confirmPassword,
    showPassword,
    busy,
    loading,
    loaded,
    preferencesLoaded,
    message,
    error,
    prefsError,
    nameInput,
    roleLabel,
    statusLabel,
    joined,
    tools,
    preferenceLabels,
    fill,
    load,
    loadPreferences,
    saveProfile,
    resetProfile,
    savePreferences,
    changePassword,
    editProfile,
    signOut,
  };
}
export default React.forwardRef(function AccountView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="AccountView"
      {...mergeProps({
        className: "account-page sp-container py-8 sm:py-12",
        "aria-busy": ctx.loading,
        "data-sp-c8811dc0": "",
      })}
    >
      <div
        {...mergeProps({
          className: "page-intro-banner mb-7",
          "data-sp-c8811dc0": "",
        })}
      >
        <p
          {...mergeProps({
            className: "account-eyebrow",
            "data-sp-c8811dc0": "",
          })}
        >
          {"KHÔNG GIAN CỦA BẠN"}
        </p>
        <h1
          {...mergeProps({
            className: "mt-2 text-3xl font-semibold tracking-tight sm:text-4xl",
            "data-sp-c8811dc0": "",
          })}
        >
          {"Hồ sơ cá nhân"}
        </h1>
        <p
          {...mergeProps({
            className: "mt-3 text-[15px] leading-7 text-brand-muted",
            "data-sp-c8811dc0": "",
          })}
        >
          {"Quản lý thông tin, bảo mật và những điều bạn quan tâm."}
        </p>
      </div>
      {ctx.loading ? (
        <p
          {...mergeProps({
            role: "status",
            className: "account-notice mb-5",
            "data-sp-c8811dc0": "",
          })}
        >
          {"Đang tải thông tin tài khoản…"}
        </p>
      ) : null}
      {ctx.error ? (
        <div
          {...mergeProps({
            role: "alert",
            className: "account-notice account-error mb-5",
            "data-sp-c8811dc0": "",
          })}
        >
          {display(ctx.error)}{" "}
          {!ctx.loaded ? (
            <button
              {...mergeProps({
                type: "button",
                className: "underline",
                onClick: ($event) => {
                  return ctx.load?.($event);
                },
                "data-sp-c8811dc0": "",
              })}
            >
              {"Thử lại"}
            </button>
          ) : null}
        </div>
      ) : null}
      {ctx.message ? (
        <p
          {...mergeProps({
            role: "status",
            className: "account-notice account-success mb-5",
            "data-sp-c8811dc0": "",
          })}
        >
          {display(ctx.message)}
        </p>
      ) : null}
      <section
        {...mergeProps({
          "data-profile-overview": "",
          className: "profile-overview account-card mb-6",
          "aria-labelledby": "profile-name",
          "data-sp-c8811dc0": "",
        })}
      >
        <div
          {...mergeProps({
            className: "flex min-w-0 flex-wrap items-center gap-6",
            "data-sp-c8811dc0": "",
          })}
        >
          <div
            {...mergeProps({
              className: "relative",
              "data-sp-c8811dc0": "",
            })}
          >
            <UserAvatar
              {...mergeProps({
                name: ctx.session.user?.fullName,
                size: 96,
                "data-sp-c8811dc0": "",
              })}
            />
          </div>
          <div
            {...mergeProps({
              className: "min-w-0 flex-1",
              "data-sp-c8811dc0": "",
            })}
          >
            <p
              {...mergeProps({
                className: "account-eyebrow",
                "data-sp-c8811dc0": "",
              })}
            >
              {"SMARTPROP · TÀI KHOẢN CÁ NHÂN"}
            </p>
            <h2
              {...mergeProps({
                id: "profile-name",
                className: "mt-2 break-words text-2xl font-semibold",
                "data-sp-c8811dc0": "",
              })}
            >
              {display(ctx.session.user?.fullName || "Tài khoản SmartProp")}
            </h2>
            <p
              {...mergeProps({
                className: "mt-2 break-all text-[15px] text-brand-muted",
                "data-sp-c8811dc0": "",
              })}
            >
              {display(ctx.session.user?.email)}
            </p>
            <div
              {...mergeProps({
                className: "mt-4 flex flex-wrap gap-2",
                "data-sp-c8811dc0": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "account-chip",
                  "data-sp-c8811dc0": "",
                })}
              >
                {display(ctx.roleLabel)}
              </span>
              <span
                {...mergeProps({
                  className: ["account-chip", ctx.session.user?.status === "ACTIVE"
                      ? "text-[var(--ui-success-text)]"
                      : "text-[var(--ui-error-text)]"],
                  
                  "data-sp-c8811dc0": "",
                })}
              >
                {"● "}
                {display(ctx.statusLabel)}
              </span>
            </div>
            <p
              {...mergeProps({
                className: "mt-3 text-[13px] text-brand-muted",
                "data-sp-c8811dc0": "",
              })}
            >
              {"Tham gia từ "}
              {display(ctx.joined)}
            </p>
          </div>
        </div>
        <div
          {...mergeProps({
            className: "profile-actions",
            "data-sp-c8811dc0": "",
          })}
        >
          <button
            {...mergeProps({
              type: "button",
              className: "sp-button sp-button-primary",
              disabled: !ctx.loaded || ctx.busy,
              onClick: ($event) => {
                return ctx.editProfile?.($event);
              },
              "data-sp-c8811dc0": "",
            })}
          >
            <AppIcon
              {...mergeProps({
                name: "edit",
                "data-sp-c8811dc0": "",
              })}
            />
            {"Chỉnh sửa hồ sơ"}
          </button>
          <AvatarEditor
            {...mergeProps({
              "data-sp-c8811dc0": "",
            })}
          />
        </div>
      </section>
      <section
        {...mergeProps({
          id: "personal-information",
          className: "account-card mb-6",
          "aria-labelledby": "personal-heading",
          "data-sp-c8811dc0": "",
        })}
      >
        <div
          {...mergeProps({
            className: "account-section-heading",
            "data-sp-c8811dc0": "",
          })}
        >
          <span
            {...mergeProps({
              className: "account-section-icon",
              "data-sp-c8811dc0": "",
            })}
          >
            <AppIcon
              {...mergeProps({
                name: "user",
                "data-sp-c8811dc0": "",
              })}
            />
          </span>
          <div
            {...mergeProps({
              "data-sp-c8811dc0": "",
            })}
          >
            <h2
              {...mergeProps({
                id: "personal-heading",
                "data-sp-c8811dc0": "",
              })}
            >
              {"Thông tin cá nhân"}
            </h2>
            <p
              {...mergeProps({
                "data-sp-c8811dc0": "",
              })}
            >
              {"Giữ thông tin liên hệ của bạn luôn chính xác."}
            </p>
          </div>
        </div>
        <form
          {...mergeProps({
            className: "grid gap-5 sm:grid-cols-2",
            onSubmit: ($event) => {
              $event.preventDefault();
              return ctx.saveProfile?.($event);
            },
            "data-sp-c8811dc0": "",
          })}
        >
          <label
            {...mergeProps({
              className: "account-field",
              "data-sp-c8811dc0": "",
            })}
          >
            {"Họ và tên"}
            <input
              {...mergeProps(
                {
                  ref: bindRef(ctx, "nameInput"),
                  required: true,
                  maxLength: "100",
                  autoComplete: "name",
                  className: "sp-input",
                  disabled: !ctx.loaded || ctx.busy,
                  "data-sp-c8811dc0": "",
                },
                modelProps(
                  ctx.form.fullName,
                  ($value) => {
                    ctx.form.fullName = $value;
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
              className: "account-field",
              "data-sp-c8811dc0": "",
            })}
          >
            {"Email"}
            <input
              {...mergeProps(
                {
                  type: "email",
                  readOnly: true,
                  autoComplete: "email",
                  className: "sp-input bg-brand-surface",
                  "data-sp-c8811dc0": "",
                },
                modelProps(
                  ctx.form.email,
                  ($value) => {
                    ctx.form.email = $value;
                  },
                  {
                    kind: "email",
                    value: "on",
                    number: false,
                    multiple: false,
                  },
                ),
              )}
            />
            <small
              {...mergeProps({
                "data-sp-c8811dc0": "",
              })}
            >
              {"Email dùng để đăng nhập và xác thực tài khoản."}
            </small>
          </label>
          <label
            {...mergeProps({
              className: "account-field",
              "data-sp-c8811dc0": "",
            })}
          >
            {"Số điện thoại"}
            <input
              {...mergeProps(
                {
                  type: "tel",
                  maxLength: "30",
                  autoComplete: "tel",
                  className: "sp-input",
                  disabled: !ctx.loaded || ctx.busy,
                  "data-sp-c8811dc0": "",
                },
                modelProps(
                  ctx.form.phone,
                  ($value) => {
                    ctx.form.phone = $value;
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
              className: "account-field",
              "data-sp-c8811dc0": "",
            })}
          >
            {"Khu vực quan tâm"}
            <input
              {...mergeProps(
                {
                  maxLength: "100",
                  className: "sp-input",
                  disabled: !ctx.loaded || ctx.busy,
                  placeholder: "Ví dụ: Hải Châu, Đà Nẵng",
                  "data-sp-c8811dc0": "",
                },
                modelProps(
                  ctx.form.district,
                  ($value) => {
                    ctx.form.district = $value;
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
              className: "account-field sm:col-span-2",
              "data-sp-c8811dc0": "",
            })}
          >
            {"Địa chỉ liên hệ"}
            <input
              {...mergeProps(
                {
                  maxLength: "255",
                  autoComplete: "street-address",
                  className: "sp-input",
                  disabled: !ctx.loaded || ctx.busy,
                  "data-sp-c8811dc0": "",
                },
                modelProps(
                  ctx.form.address,
                  ($value) => {
                    ctx.form.address = $value;
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
          <LifestyleFields value={ctx.form.advisorPreferences} disabled={!ctx.loaded || ctx.busy} onChange={value => {ctx.form.advisorPreferences=value}} />
          <div
            {...mergeProps({
              className: "flex flex-wrap gap-3 sm:col-span-2",
              "data-sp-c8811dc0": "",
            })}
          >
            <button
              {...mergeProps({
                className: "sp-button sp-button-primary",
                disabled: !ctx.loaded || ctx.busy,
                "data-sp-c8811dc0": "",
              })}
            >
              {display(ctx.busy ? "Đang lưu…" : "Lưu thay đổi")}
            </button>
            <button
              {...mergeProps({
                type: "button",
                className: "sp-button sp-button-secondary",
                disabled: ctx.busy,
                onClick: ($event) => {
                  return ctx.resetProfile?.($event);
                },
                "data-sp-c8811dc0": "",
              })}
            >
              {"Hủy thay đổi"}
            </button>
          </div>
        </form>
      </section>
      <section
        {...mergeProps({
          id: "security-settings",
          className: "account-card mb-6",
          "aria-labelledby": "security-heading",
          "data-sp-c8811dc0": "",
        })}
      >
        <div
          {...mergeProps({
            className: "account-section-heading",
            "data-sp-c8811dc0": "",
          })}
        >
          <span
            {...mergeProps({
              className: "account-section-icon",
              "data-sp-c8811dc0": "",
            })}
          >
            <AppIcon
              {...mergeProps({
                name: "shield",
                "data-sp-c8811dc0": "",
              })}
            />
          </span>
          <div
            {...mergeProps({
              "data-sp-c8811dc0": "",
            })}
          >
            <h2
              {...mergeProps({
                id: "security-heading",
                "data-sp-c8811dc0": "",
              })}
            >
              {"Bảo mật & cài đặt"}
            </h2>
            <p
              {...mergeProps({
                "data-sp-c8811dc0": "",
              })}
            >
              {"Chủ động bảo vệ tài khoản và quản lý cách nhận thông tin."}
            </p>
          </div>
        </div>
        <div
          {...mergeProps({
            className: "account-tabs mb-6",
            role: "group",
            "aria-label": "Cài đặt tài khoản",
            "data-sp-c8811dc0": "",
          })}
        >
          {renderList(
            [
              {
                id: "password",
                label: "Mật khẩu",
              },
              {
                id: "notifications",
                label: "Thông báo",
              },
            ],
            (tab) => (
              <button
                key={tab.id}
                {...mergeProps({
                  type: "button",
                  "aria-pressed": ctx.securityTab === tab.id,
                  onClick: ($event) => {
                    ctx.securityTab = tab.id;
                  },
                  "data-sp-c8811dc0": "",
                })}
              >
                {display(tab.label)}
              </button>
            ),
          )}
          <RouterLink
            {...mergeProps({
              to: "/account/sessions",
              "data-sp-c8811dc0": "",
            })}
          >
            {"Phiên đăng nhập ↗"}
          </RouterLink>
        </div>
        {ctx.securityTab === "password" ? (
          <form
            {...mergeProps({
              className: "grid gap-5 sm:grid-cols-2",
              onSubmit: ($event) => {
                $event.preventDefault();
                return ctx.changePassword?.($event);
              },
              "data-sp-c8811dc0": "",
            })}
          >
            <label
              {...mergeProps({
                className: "account-field sm:col-span-2",
                "data-sp-c8811dc0": "",
              })}
            >
              {"Mật khẩu hiện tại"}
              <input
                {...mergeProps(
                  {
                    type: ctx.showPassword ? "text" : "password",
                    required: true,
                    maxLength: "72",
                    autoComplete: "current-password",
                    className: "sp-input",
                    "data-sp-c8811dc0": "",
                  },
                  modelProps(
                    ctx.currentPassword,
                    ($value) => {
                      ctx.currentPassword = $value;
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
                className: "account-field",
                "data-sp-c8811dc0": "",
              })}
            >
              {"Mật khẩu mới"}
              <input
                {...mergeProps(
                  {
                    type: ctx.showPassword ? "text" : "password",
                    required: true,
                    minLength: "8",
                    maxLength: "72",
                    autoComplete: "new-password",
                    className: "sp-input",
                    "data-sp-c8811dc0": "",
                  },
                  modelProps(
                    ctx.newPassword,
                    ($value) => {
                      ctx.newPassword = $value;
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
              <small
                {...mergeProps({
                  "data-sp-c8811dc0": "",
                })}
              >
                {"Từ 8 ký tự, tối đa 72 byte UTF-8."}
              </small>
            </label>
            <label
              {...mergeProps({
                className: "account-field",
                "data-sp-c8811dc0": "",
              })}
            >
              {"Xác nhận mật khẩu mới"}
              <input
                {...mergeProps(
                  {
                    type: ctx.showPassword ? "text" : "password",
                    required: true,
                    minLength: "8",
                    maxLength: "72",
                    autoComplete: "new-password",
                    className: "sp-input",
                    "data-sp-c8811dc0": "",
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
            </label>
            <div
              {...mergeProps({
                className:
                  "flex flex-wrap items-center justify-between gap-4 sm:col-span-2",
                "data-sp-c8811dc0": "",
              })}
            >
              <button
                {...mergeProps({
                  type: "button",
                  className: "text-sm font-medium underline",
                  "aria-pressed": ctx.showPassword,
                  onClick: ($event) => {
                    ctx.showPassword = !ctx.showPassword;
                  },
                  "data-sp-c8811dc0": "",
                })}
              >
                {display(ctx.showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu")}
              </button>
              <button
                {...mergeProps({
                  className: "sp-button sp-button-primary",
                  disabled: ctx.busy || !ctx.loaded,
                  "data-sp-c8811dc0": "",
                })}
              >
                {"Đổi mật khẩu"}
              </button>
            </div>
          </form>
        ) : (
          <div
            {...mergeProps({
              "data-sp-c8811dc0": "",
            })}
          >
            {ctx.prefsError ? (
              <div
                {...mergeProps({
                  role: "alert",
                  className: "account-notice account-error mb-4",
                  "data-sp-c8811dc0": "",
                })}
              >
                {display(ctx.prefsError)}{" "}
                <button
                  {...mergeProps({
                    type: "button",
                    className: "underline",
                    onClick: ($event) => {
                      return ctx.loadPreferences?.($event);
                    },
                    "data-sp-c8811dc0": "",
                  })}
                >
                  {"Thử lại"}
                </button>
              </div>
            ) : null}
            {renderList(ctx.preferenceLabels, (item) => (
              <label
                key={item.key}
                {...mergeProps({
                  className:
                    "flex cursor-pointer items-center justify-between gap-6 border-b border-brand-line py-4",
                  "data-sp-c8811dc0": "",
                })}
              >
                <span
                  {...mergeProps({
                    "data-sp-c8811dc0": "",
                  })}
                >
                  <strong
                    {...mergeProps({
                      className: "block text-[15px] font-semibold",
                      "data-sp-c8811dc0": "",
                    })}
                  >
                    {display(item.title)}
                  </strong>
                  <span
                    {...mergeProps({
                      className:
                        "mt-1 block text-sm leading-6 text-brand-muted",
                      "data-sp-c8811dc0": "",
                    })}
                  >
                    {display(item.text)}
                  </span>
                </span>
                <input
                  {...mergeProps(
                    {
                      type: "checkbox",
                      className: "size-5 shrink-0 accent-brand-navy",
                      disabled: !ctx.preferencesLoaded || ctx.busy,
                      "data-sp-c8811dc0": "",
                    },
                    modelProps(
                      ctx.prefs[item.key],
                      ($value) => {
                        ctx.prefs[item.key] = $value;
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
              </label>
            ))}
            <button
              {...mergeProps({
                type: "button",
                className: "sp-button sp-button-primary mt-5",
                disabled: !ctx.preferencesLoaded || ctx.busy,
                onClick: ($event) => {
                  return ctx.savePreferences?.($event);
                },
                "data-sp-c8811dc0": "",
              })}
            >
              {"Lưu tùy chọn"}
            </button>
          </div>
        )}
        <div
          {...mergeProps({
            className:
              "mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-brand-line pt-5 text-sm",
            "data-sp-c8811dc0": "",
          })}
        >
          <span
            {...mergeProps({
              "data-sp-c8811dc0": "",
            })}
          >
            {display(
              ctx.session.user?.emailVerifiedAt
                ? "Email của bạn đã được xác minh."
                : "Hoàn tất xác minh để bảo vệ tài khoản.",
            )}
          </span>
          {!ctx.session.user?.emailVerifiedAt ? (
            <RouterLink
              {...mergeProps({
                to: "/account/verify-email",
                className: "font-semibold underline",
                "data-sp-c8811dc0": "",
              })}
            >
              {"Xác minh email ↗"}
            </RouterLink>
          ) : null}
        </div>
      </section>
      <section
        {...mergeProps({
          id: "property-management",
          className: "mb-6",
          "aria-label": "Quản lý bất động sản",
          "data-sp-c8811dc0": "",
        })}
      >
        <BrokerApplicationCard
          {...mergeProps({
            "data-sp-c8811dc0": "",
          })}
        />
      </section>
      <section
        {...mergeProps({
          id: "valuation-history",
          className: "mb-6",
          "aria-label": "Lịch sử định giá",
          "data-sp-c8811dc0": "",
        })}
      >
        <ValuationHistory
          {...mergeProps({
            "data-sp-c8811dc0": "",
          })}
        />
      </section>
      <section
        {...mergeProps({
          id: "account-tools",
          className: "account-card",
          "aria-labelledby": "account-tools-heading",
          "data-sp-c8811dc0": "",
        })}
      >
        <div
          {...mergeProps({
            className: "account-section-heading",
            "data-sp-c8811dc0": "",
          })}
        >
          <span
            {...mergeProps({
              className: "account-section-icon",
              "data-sp-c8811dc0": "",
            })}
          >
            <AppIcon
              {...mergeProps({
                name: "briefcase",
                "data-sp-c8811dc0": "",
              })}
            />
          </span>
          <div
            {...mergeProps({
              "data-sp-c8811dc0": "",
            })}
          >
            <h2
              {...mergeProps({
                id: "account-tools-heading",
                "data-sp-c8811dc0": "",
              })}
            >
              {"Tiện ích của bạn"}
            </h2>
            <p
              {...mergeProps({
                "data-sp-c8811dc0": "",
              })}
            >
              {"Tiếp tục từ những nội dung và trao đổi đã lưu."}
            </p>
          </div>
        </div>
        <div
          {...mergeProps({
            className: "grid gap-3 sm:grid-cols-2",
            "data-sp-c8811dc0": "",
          })}
        >
          {renderList(ctx.tools, (tool) => (
            <RouterLink
              key={tool.to}
              {...mergeProps({
                to: tool.to,
                className: "account-tool",
                "data-sp-c8811dc0": "",
              })}
            >
              <AppIcon
                {...mergeProps({
                  name: tool.icon,
                  "data-sp-c8811dc0": "",
                })}
              />
              <span
                {...mergeProps({
                  className: "min-w-0 flex-1",
                  "data-sp-c8811dc0": "",
                })}
              >
                <strong
                  {...mergeProps({
                    "data-sp-c8811dc0": "",
                  })}
                >
                  {display(tool.title)}
                </strong>
                <small
                  {...mergeProps({
                    "data-sp-c8811dc0": "",
                  })}
                >
                  {display(tool.text)}
                </small>
              </span>
              <AppIcon
                {...mergeProps({
                  name: "arrow",
                  "data-sp-c8811dc0": "",
                })}
              />
            </RouterLink>
          ))}
        </div>
        <button
          {...mergeProps({
            type: "button",
            className:
              "mt-6 inline-flex items-center gap-2 text-sm font-medium text-brand-muted underline",
            disabled: ctx.busy,
            onClick: ($event) => {
              return ctx.signOut?.($event);
            },
            "data-sp-c8811dc0": "",
          })}
        >
          <AppIcon
            {...mergeProps({
              name: "logout",
              "data-sp-c8811dc0": "",
            })}
          />
          {"Đăng xuất tài khoản"}
        </button>
      </section>
    </div>,
  ]);
});
