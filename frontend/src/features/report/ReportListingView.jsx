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
  onMounted,
  onBeforeUnmount,
} from "../../shared/state/store.js";
import { useRouter, useRoute } from "../../shared/routing/router.jsx";
import { api, session, errorText } from "../auth/api.js";
import {
  useList,
  adapt,
  money,
  LegacyState,
  LegacyPager,
  PrivateImage,
  types,
  states,
  reasons as reasonLabels,
  date,
  mapUrl,
} from "../../shared/lib/legacy.js";
function setup(__props) {
  const route = useRoute(),
    router = useRouter(),
    state = ref({
      busy: false,
      error: "",
      notice: "",
    }),
    property = ref(null),
    listing = computed(() => adapt(property.value)),
    reasons = [
      "Nghi ngờ ảnh giả mạo",
      "Thông tin sai lệch",
      "Nghi ngờ lừa đảo",
      "Tin đăng trùng lặp",
      "BĐS đã bán / đã cho thuê",
      "Lý do khác",
    ],
    codes = [
      "FAKE_IMAGES",
      "INACCURATE_INFORMATION",
      "SUSPECTED_SCAM",
      "DUPLICATE",
      "UNAVAILABLE",
      "OTHER",
    ],
    selectedReason = ref(""),
    description = ref(""),
    email = ref(session.user?.email || ""),
    confirmed = ref(false),
    selectedFile = ref(null),
    isSubmitted = ref(false),
    created = ref(null);
  const selectReason = (r) => (selectedReason.value = r),
    removeFile = () => (selectedFile.value = null),
    goBack = () => router.push("/listing/" + route.params.id),
    goHome = () => router.push("/home"),
    goAccount = () => router.push("/account");
  onMounted(async () => {
    try {
      property.value = await api("/properties/" + route.params.id);
    } catch (e) {
      state.value.error = errorText(e);
    }
  });
  function handleFile(event) {
    selectedFile.value = event.target.files?.[0] || null;
  }
  async function submitReport() {
    if (state.value.busy) return;
    state.value.error = "";
    if (
      !selectedReason.value ||
      !description.value.trim() ||
      !confirmed.value
    ) {
      state.value.error = "Vui lòng chọn lý do, mô tả và xác nhận thông tin.";
      return;
    }
    state.value.busy = true;
    try {
      if (!created.value)
        created.value = await api(
          "/properties/" + route.params.id + "/reports",
          {
            method: "POST",
            body: {
              reasonCode: codes[reasons.indexOf(selectedReason.value)],
              description: description.value,
              contactEmail: email.value || null,
            },
          },
        );
      if (selectedFile.value) {
        const data = new FormData();
        data.append("file", selectedFile.value);
        await api("/reports/" + created.value.id + "/attachments", {
          method: "POST",
          body: data,
        });
      }
      isSubmitted.value = true;
    } catch (e) {
      state.value.error = errorText(e);
    } finally {
      state.value.busy = false;
    }
  }
  return {
    ref,
    computed,
    watch,
    onMounted,
    onBeforeUnmount,
    useRouter,
    useRoute,
    api,
    session,
    errorText,
    useList,
    adapt,
    money,
    LegacyState,
    LegacyPager,
    PrivateImage,
    types,
    states,
    reasonLabels,
    date,
    mapUrl,
    route,
    router,
    state,
    property,
    listing,
    reasons,
    codes,
    selectedReason,
    description,
    email,
    confirmed,
    selectedFile,
    isSubmitted,
    created,
    selectReason,
    removeFile,
    goBack,
    goHome,
    goAccount,
    handleFile,
    submitReport,
  };
}
export default React.forwardRef(function ReportListingView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="ReportListingView"
      {...mergeProps({
        className: "min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)]",
      })}
    >
      <div
        {...mergeProps({
          className: "max-w-[1180px] mx-auto px-6 md:px-10 py-10",
        })}
      >
        <LegacyState
          {...mergeProps({
            state: ctx.state,
          })}
        />
        <button
          {...mergeProps({
            onClick: ($event) => {
              return ctx.goBack?.($event);
            },
            className: "sm:hidden text-xs text-brand-muted mb-6",
          })}
        >
          {" ‹ Quay lại tin đăng "}
        </button>
        <section
          {...mergeProps({
            className: "mb-8",
          })}
        >
          <h1
            {...mergeProps({
              className:
                "text-3xl md:text-4xl font-semibold tracking-tight text-[var(--ui-accent)]",
            })}
          >
            {" Báo cáo tin đăng "}
          </h1>
          <p
            {...mergeProps({
              className: "text-sm text-brand-muted mt-2",
            })}
          >
            {" Cho chúng tôi biết vấn đề bạn gặp phải với tin đăng này. "}
          </p>
        </section>
        {ctx.isSubmitted ? (
          <section
            {...mergeProps({
              className:
                "bg-brand-card rounded-[26px] p-8 md:p-12 shadow-sm text-center max-w-[720px] mx-auto",
            })}
          >
            <div
              {...mergeProps({
                className:
                  "w-16 h-16 rounded-full bg-[var(--ui-surface)] text-[var(--ui-accent)] flex items-center justify-center text-2xl mx-auto",
              })}
            >
              {" ✓ "}
            </div>
            <h2
              {...mergeProps({
                className: "text-2xl font-semibold mt-6",
              })}
            >
              {" Báo cáo đã được gửi "}
            </h2>
            <p
              {...mergeProps({
                className:
                  "text-sm text-brand-muted mt-3 max-w-[500px] mx-auto leading-6",
              })}
            >
              {
                " Cảm ơn bạn đã giúp SmartProp xây dựng môi trường bất động sản an toàn hơn. Đội ngũ quản trị sẽ xem xét báo cáo của bạn. "
              }
            </p>
            <div
              {...mergeProps({
                className: "mt-7 bg-[var(--ui-surface)] rounded-2xl px-5 py-4 text-sm",
              })}
            >
              {" Thời gian xem xét dự kiến: "}
              <strong {...mergeProps({})}>{"24–48 giờ"}</strong>
            </div>
            <button
              {...mergeProps({
                onClick: ($event) => {
                  return ctx.goBack?.($event);
                },
                className:
                  "mt-7 px-7 py-3 rounded-full bg-[var(--ui-soft)] text-brand-navy text-sm",
              })}
            >
              {" Quay lại tin đăng "}
            </button>
          </section>
        ) : (
          <div
            {...mergeProps({
              className:
                "grid grid-cols-1 lg:grid-cols-[1fr_310px] gap-6 items-start",
            })}
          >
            <div
              {...mergeProps({
                className: "space-y-5",
              })}
            >
              <section
                {...mergeProps({
                  className: "bg-brand-card rounded-[24px] p-6 md:p-7 shadow-sm",
                })}
              >
                <h2
                  {...mergeProps({
                    className: "text-sm font-semibold mb-4",
                  })}
                >
                  {" Tin đăng được báo cáo "}
                </h2>
                <div
                  {...mergeProps({
                    className:
                      "flex items-center gap-4 bg-[var(--ui-surface)] rounded-[18px] p-3",
                  })}
                >
                  <div
                    {...mergeProps({
                      className:
                        "w-[105px] h-[78px] rounded-[14px] overflow-hidden bg-[var(--ui-soft)] shrink-0",
                    })}
                  >
                    <PrivateImage
                      {...mergeProps({
                        src: ctx.listing.image,
                        alt: ctx.listing.title,
                        className: "w-full h-full object-cover",
                      })}
                    />
                  </div>
                  <div
                    {...mergeProps({
                      className: "min-w-0",
                    })}
                  >
                    <h3
                      {...mergeProps({
                        className:
                          "text-sm font-semibold text-[var(--ui-accent)] truncate",
                      })}
                    >
                      {display(ctx.listing.title)}
                    </h3>
                    <p
                      {...mergeProps({
                        className: "text-[12px] text-brand-muted mt-1",
                      })}
                    >
                      {display(ctx.listing.location)}
                    </p>
                    <p
                      {...mergeProps({
                        className: "text-sm font-semibold text-[var(--ui-accent)] mt-2",
                      })}
                    >
                      {display(ctx.listing.price)}
                    </p>
                  </div>
                </div>
              </section>
              <section
                {...mergeProps({
                  className: "bg-brand-card rounded-[24px] p-6 md:p-7 shadow-sm",
                })}
              >
                <h2
                  {...mergeProps({
                    className: "text-base font-semibold",
                  })}
                >
                  {" Lý do báo cáo "}
                </h2>
                <p
                  {...mergeProps({
                    className: "text-xs text-brand-muted mt-1.5",
                  })}
                >
                  {" Chọn lý do phù hợp nhất với vấn đề bạn phát hiện. "}
                </p>
                <div
                  {...mergeProps({
                    className: "grid grid-cols-1 sm:grid-cols-2 gap-3 mt-5",
                  })}
                >
                  {renderList(ctx.reasons, (reason) => (
                    <button
                      key={reason}
                      {...mergeProps({
                        type: "button",
                        onClick: ($event) => {
                          ctx.selectReason(reason);
                        },
                        className: ["relative text-left px-4 py-4 rounded-[16px] border text-xs font-medium transition", ctx.selectedReason === reason
                            ? "border-[var(--ui-border)] bg-[var(--ui-surface)] text-[var(--ui-accent)] ring-1 ring-[var(--ui-border)]"
                            : "border-brand-line bg-brand-card text-brand-muted hover:border-[var(--ui-border)]/40"],
                        
                      })}
                    >
                      <span
                        {...mergeProps({
                          className: "inline-flex items-center gap-3",
                        })}
                      >
                        <span
                          {...mergeProps({
                            className: ["w-4 h-4 rounded-full border flex items-center justify-center", ctx.selectedReason === reason
                                ? "border-[var(--ui-border)]"
                                : "border-brand-line"],
                            
                          })}
                        >
                          {ctx.selectedReason === reason ? (
                            <span
                              {...mergeProps({
                                className: "w-2 h-2 rounded-full bg-[var(--ui-soft)]",
                              })}
                            />
                          ) : null}
                        </span>{" "}
                        {display(reason)}
                      </span>
                    </button>
                  ))}
                </div>
                <div
                  {...mergeProps({
                    className: "mt-7",
                  })}
                >
                  <label
                    {...mergeProps({
                      className: "block text-sm font-semibold mb-2",
                    })}
                  >
                    {" Mô tả chi tiết "}
                  </label>
                  <textarea
                    {...mergeProps(
                      {
                        rows: "6",
                        maxLength: "1000",
                        placeholder: "Mô tả vấn đề bạn phát hiện...",
                        className:
                          "w-full resize-none rounded-[16px] border border-brand-line px-4 py-4 text-xs text-brand-muted leading-6 outline-none focus:border-[var(--ui-border)] focus:ring-1 focus:ring-[var(--ui-border)]",
                      },
                      modelProps(
                        ctx.description,
                        ($value) => {
                          ctx.description = $value;
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
                  <div
                    {...mergeProps({
                      className: "text-right text-xs text-brand-muted mt-1",
                    })}
                  >
                    {display(ctx.description.length)}
                    {"/1000 "}
                  </div>
                </div>
                <div
                  {...mergeProps({
                    className: "mt-5",
                  })}
                >
                  <label
                    {...mergeProps({
                      className: "block text-sm font-semibold mb-2",
                    })}
                  >
                    {" Đính kèm minh chứng "}
                    <span
                      {...mergeProps({
                        className: "font-normal text-brand-muted",
                      })}
                    >
                      {" (không bắt buộc) "}
                    </span>
                  </label>
                  <label
                    {...mergeProps({
                      className:
                        "relative flex flex-col items-center justify-center min-h-[135px] border border-dashed border-brand-line rounded-[16px] bg-[var(--ui-surface)] cursor-pointer hover:border-[var(--ui-border)]/50 transition",
                    })}
                  >
                    <input
                      {...mergeProps({
                        type: "file",
                        accept: ".jpg,.jpeg,.png,.pdf",
                        className: "hidden",
                        onChange: ($event) => {
                          return ctx.handleFile?.($event);
                        },
                      })}
                    />
                    {!ctx.selectedFile ? (
                      <React.Fragment {...mergeProps({})}>
                        <div
                          {...mergeProps({
                            className: "text-xl",
                          })}
                        >
                          {" 📎 "}
                        </div>
                        <p
                          {...mergeProps({
                            className:
                              "text-xs text-brand-muted text-center mt-2 px-5",
                          })}
                        >
                          {
                            " Kéo thả ảnh chụp màn hình hoặc tệp vào đây, hoặc bấm để chọn "
                          }
                        </p>
                        <p
                          {...mergeProps({
                            className: "text-xs text-brand-muted mt-1",
                          })}
                        >
                          {" Hỗ trợ JPG, PNG, PDF · tối đa 10MB "}
                        </p>
                      </React.Fragment>
                    ) : (
                      <React.Fragment {...mergeProps({})}>
                        <div
                          {...mergeProps({
                            className:
                              "w-10 h-10 rounded-full bg-[var(--ui-surface)] text-[var(--ui-accent)] flex items-center justify-center",
                          })}
                        >
                          {" ✓ "}
                        </div>
                        <p
                          {...mergeProps({
                            className:
                              "text-xs font-medium text-[var(--ui-accent)] mt-2",
                          })}
                        >
                          {display(ctx.selectedFile.name)}
                        </p>
                        <p
                          {...mergeProps({
                            className: "text-xs text-brand-muted mt-1",
                          })}
                        >
                          {display(
                            (ctx.selectedFile.size / 1024 / 1024).toFixed(2),
                          )}
                          {" MB "}
                        </p>
                      </React.Fragment>
                    )}
                  </label>
                  {ctx.selectedFile ? (
                    <button
                      {...mergeProps({
                        type: "button",
                        onClick: ($event) => {
                          return ctx.removeFile?.($event);
                        },
                        className: "text-xs text-[var(--ui-error-text)] mt-2 hover:underline",
                      })}
                    >
                      {" Xoá tệp "}
                    </button>
                  ) : null}
                </div>
                <div
                  {...mergeProps({
                    className: "mt-6",
                  })}
                >
                  <label
                    {...mergeProps({
                      className: "block text-sm font-semibold mb-2",
                    })}
                  >
                    {" Email liên hệ "}
                  </label>
                  <input
                    {...mergeProps(
                      {
                        type: "email",
                        placeholder: "example@gmail.com",
                        className:
                          "w-full h-12 rounded-[14px] border border-brand-line px-4 text-xs outline-none focus:border-[var(--ui-border)] focus:ring-1 focus:ring-[var(--ui-border)]",
                      },
                      modelProps(
                        ctx.email,
                        ($value) => {
                          ctx.email = $value;
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
                  <p
                    {...mergeProps({
                      className: "text-xs text-brand-muted mt-2",
                    })}
                  >
                    {" Chúng tôi sẽ gửi kết quả xử lý báo cáo tới email này. "}
                  </p>
                </div>
                <label
                  {...mergeProps({
                    className: "flex items-start gap-3 mt-6 cursor-pointer",
                  })}
                >
                  <input
                    {...mergeProps(
                      {
                        type: "checkbox",
                        className: "mt-0.5 w-4 h-4 accent-[#183e54]",
                      },
                      modelProps(
                        ctx.confirmed,
                        ($value) => {
                          ctx.confirmed = $value;
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
                  <span
                    {...mergeProps({
                      className: "text-[12px] text-brand-muted leading-5",
                    })}
                  >
                    {
                      " Tôi xác nhận thông tin báo cáo trên là đúng sự thật. Báo cáo sai sự thật có thể ảnh hưởng đến tài khoản của tôi. "
                    }
                  </span>
                </label>
                <div
                  {...mergeProps({
                    className: "flex flex-col-reverse sm:flex-row gap-3 mt-7",
                  })}
                >
                  <button
                    {...mergeProps({
                      type: "button",
                      onClick: ($event) => {
                        return ctx.submitReport?.($event);
                      },
                      className:
                        "sm:flex-1 h-12 rounded-full bg-[var(--ui-soft)] text-brand-navy text-xs font-medium hover:opacity-90 transition",
                    })}
                  >
                    {" Gửi báo cáo "}
                  </button>
                  <button
                    {...mergeProps({
                      type: "button",
                      onClick: ($event) => {
                        return ctx.goBack?.($event);
                      },
                      className:
                        "sm:w-[130px] h-12 rounded-full bg-brand-card border border-brand-line text-brand-muted text-xs hover:bg-brand-card transition",
                    })}
                  >
                    {" Huỷ "}
                  </button>
                </div>
              </section>
            </div>
            <aside
              {...mergeProps({
                className: "space-y-4 lg:sticky lg:top-5",
              })}
            >
              <section
                {...mergeProps({
                  className:
                    "bg-[var(--ui-soft)] text-brand-navy rounded-[24px] p-6 shadow-sm",
                })}
              >
                <p
                  {...mergeProps({
                    className:
                      "text-xs text-brand-navy/40 tracking-[0.18em] font-semibold",
                  })}
                >
                  {" SAU KHI BẠN GỬI BÁO CÁO "}
                </p>
                <h2
                  {...mergeProps({
                    className: "text-lg font-semibold mt-2",
                  })}
                >
                  {" Chuyện gì xảy ra tiếp theo? "}
                </h2>
                <div
                  {...mergeProps({
                    className: "space-y-5 mt-6",
                  })}
                >
                  <div
                    {...mergeProps({
                      className: "flex items-start gap-3",
                    })}
                  >
                    <div
                      {...mergeProps({
                        className:
                          "w-7 h-7 rounded-full bg-brand-card/10 border border-brand-line/10 flex items-center justify-center text-xs shrink-0",
                      })}
                    >
                      {" 1 "}
                    </div>
                    <p
                      {...mergeProps({
                        className: "text-[12px] text-brand-navy/65 leading-5 pt-1",
                      })}
                    >
                      {" Đội ngũ quản trị xem xét trong vòng 24–48 giờ. "}
                    </p>
                  </div>
                  <div
                    {...mergeProps({
                      className: "flex items-start gap-3",
                    })}
                  >
                    <div
                      {...mergeProps({
                        className:
                          "w-7 h-7 rounded-full bg-brand-card/10 border border-brand-line/10 flex items-center justify-center text-xs shrink-0",
                      })}
                    >
                      {" 2 "}
                    </div>
                    <p
                      {...mergeProps({
                        className: "text-[12px] text-brand-navy/65 leading-5 pt-1",
                      })}
                    >
                      {" Tin đăng có thể bị tạm ẩn nếu vi phạm rõ ràng. "}
                    </p>
                  </div>
                  <div
                    {...mergeProps({
                      className: "flex items-start gap-3",
                    })}
                  >
                    <div
                      {...mergeProps({
                        className:
                          "w-7 h-7 rounded-full bg-brand-card/10 border border-brand-line/10 flex items-center justify-center text-xs shrink-0",
                      })}
                    >
                      {" 3 "}
                    </div>
                    <p
                      {...mergeProps({
                        className: "text-[12px] text-brand-navy/65 leading-5 pt-1",
                      })}
                    >
                      {
                        ' Bạn nhận kết quả qua email và tại trang "Báo cáo của tôi". '
                      }
                    </p>
                  </div>
                </div>
              </section>
              <section
                {...mergeProps({
                  className: "bg-brand-card rounded-[24px] p-6 shadow-sm",
                })}
              >
                <div
                  {...mergeProps({
                    className: "flex items-center gap-2",
                  })}
                >
                  <div
                    {...mergeProps({
                      className:
                        "w-7 h-7 rounded-full bg-[var(--ui-surface)] flex items-center justify-center",
                    })}
                  >
                    {" 🔒 "}
                  </div>
                  <h3
                    {...mergeProps({
                      className: "text-sm font-semibold",
                    })}
                  >
                    {" Quyền riêng tư "}
                  </h3>
                </div>
                <p
                  {...mergeProps({
                    className: "text-[12px] text-brand-muted leading-5 mt-3",
                  })}
                >
                  {
                    " Danh tính người báo cáo được giữ kín và không chia sẻ với người đăng tin. "
                  }
                </p>
              </section>
            </aside>
          </div>
        )}
      </div>
    </div>,
  ]);
});
