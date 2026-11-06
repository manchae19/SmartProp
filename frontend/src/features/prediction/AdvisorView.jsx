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
  computed,
  nextTick,
  onBeforeUnmount,
  reactive,
  ref,
  watch,
} from "../../shared/state/store.js";
import { api, session } from "../auth/api.js";
import { createResearchAdvisorClient } from "./tinixAdvisor.js";
import {
  advisorRequest,
  parseAdvisorBudget,
  formatAdvisorBudget,
  createAdvisorClient,
  advisorMapData,
  advisorError,
} from "./advisor.js";
import { districts } from "../map/districts.js";
import AdvisorResults from "../../shared/components/AdvisorResults.jsx";
import "./AdvisorView.css";
function setup(__props) {
  const defaults = () => ({
    budgetVnd: "2.000.000.000",
    purpose: "LIVING",
    propertyType: "ALL",
    minAreaSqm: "",
    district: "",
    ward: "",
    limit: 10,
  });
  const form = reactive(defaults());
  const busy = ref(false),
    mapBusy = ref(false),
    error = ref(""),
    result = ref(null),
    points = ref([]),
    selected = ref(""),
    mapFailures = ref(0);
  const submitted = ref(null),
    resultsHeading = ref(null),
    budgetInput = ref(null);
  const recommend = createAdvisorClient(api);
  const researchRecommend = createResearchAdvisorClient(api);
  const research = ref(false),
    researchAvailable = ref(false);
  let sequence = 0,
    mapSequence = 0;
  watch(
    () => [session.user?.role, session.status],
    async ([role, status]) => {
      researchAvailable.value = false;
      research.value = false;
      reset();
      if (role === "ADMIN" && status === "AUTHENTICATED") {
        try {
          const config = await api("/recommendations/research/config");
          researchAvailable.value =
            session.user?.role === "ADMIN" && config.enabled === true;
        } catch {
          /* Public Advisor remains available. */
        }
      }
    },
    {
      immediate: true,
    },
  );
  function setResearch(value) {
    if (value && !researchAvailable.value) return;
    reset();
    research.value = value;
  }
  const money = (value) =>
    new Intl.NumberFormat("vi-VN", {
      style: "currency",
      currency: "VND",
      maximumFractionDigits: 0,
    }).format(value);
  const budgetHint = computed(() => {
    try {
      return formatAdvisorBudget(form.budgetVnd) + " VNĐ";
    } catch {
      return "Nhập tổng số tiền VNĐ, ví dụ 2.350.000.000";
    }
  });
  const districtSuggestions = computed(() => [
    ...new Set([
      ...districts.filter((d) => d !== "Tất cả"),
      ...(result.value?.topAreas || []).map((a) => a.district),
    ]),
  ]);
  const changed = computed(() => {
    if (!result.value) return false;
    try {
      return (
        JSON.stringify(advisorRequest(form)) !== JSON.stringify(submitted.value)
      );
    } catch {
      return true;
    }
  });
  const submittedSummary = computed(() =>
    submitted.value
      ? [
          money(submitted.value.budgetVnd),
          {
            LIVING: "Mua để ở",
            INVESTMENT: "Đầu tư",
            RENTAL: "Mua để cho thuê",
          }[submitted.value.purpose],
          submitted.value.district || "Tất cả khu vực",
          submitted.value.ward,
          submitted.value.minAreaSqm
            ? "Từ " + submitted.value.minAreaSqm + " m²"
            : "",
        ]
          .filter(Boolean)
          .join(" · ")
      : "",
  );
  function formatBudget() {
    try {
      form.budgetVnd = formatAdvisorBudget(form.budgetVnd);
    } catch {
      /* Keep invalid text for an explicit validation error. */
    }
  }
  function budgetEquals(value) {
    try {
      return parseAdvisorBudget(form.budgetVnd) === value;
    } catch {
      return false;
    }
  }
  async function loadMap() {
    if (!result.value) return;
    const current = sequence,
      mapCurrent = ++mapSequence,
      properties = result.value.topProperties;
    mapBusy.value = true;
    mapFailures.value = 0;
    try {
      const mapped = await advisorMapData(properties, (path) =>
        api(path, {
          authenticated: false,
        }),
      );
      if (current === sequence && mapCurrent === mapSequence) {
        points.value = mapped.points;
        mapFailures.value = mapped.failedCount;
      }
    } finally {
      if (current === sequence && mapCurrent === mapSequence)
        mapBusy.value = false;
    }
  }
  async function submit() {
    const current = ++sequence;
    mapSequence++;
    busy.value = true;
    mapBusy.value = false;
    error.value = "";
    result.value = null;
    points.value = [];
    selected.value = "";
    mapFailures.value = 0;
    const input = {
      ...form,
    };
    try {
      const request = advisorRequest(input),
        response = await (research.value ? researchRecommend : recommend)(
          input,
        );
      if (current !== sequence) return;
      submitted.value = request;
      result.value = response;
      await nextTick();
      resultsHeading.value?.focus({
        preventScroll: true,
      });
      void loadMap();
    } catch (failure) {
      if (current === sequence)
        error.value =
          research.value && [401, 403].includes(failure.status)
            ? "Cần phiên ADMIN hợp lệ và máy chủ demo nội bộ được bật. Không thể mở dữ liệu nghiên cứu bằng liên kết hoặc tham số URL."
            : advisorError(failure);
    } finally {
      if (current === sequence) busy.value = false;
    }
  }
  function reset() {
    sequence++;
    mapSequence++;
    Object.assign(form, defaults());
    busy.value = false;
    mapBusy.value = false;
    error.value = "";
    result.value = null;
    submitted.value = null;
    points.value = [];
    selected.value = "";
    mapFailures.value = 0;
    nextTick(() => budgetInput.value?.focus());
  }
  function adjust() {
    document.getElementById("advisor-form")?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "start",
    });
    budgetInput.value?.focus({
      preventScroll: true,
    });
  }
  function areaSelected(area) {
    form.district = area.district;
    form.ward = area.ward || "";
    submit();
  }
  onBeforeUnmount(() => {
    sequence++;
    mapSequence++;
  });
  return {
    computed,
    nextTick,
    onBeforeUnmount,
    reactive,
    ref,
    watch,
    api,
    session,
    createResearchAdvisorClient,
    advisorRequest,
    parseAdvisorBudget,
    formatAdvisorBudget,
    createAdvisorClient,
    advisorMapData,
    advisorError,
    districts,
    AdvisorResults,
    defaults,
    form,
    busy,
    mapBusy,
    error,
    result,
    points,
    selected,
    mapFailures,
    submitted,
    resultsHeading,
    budgetInput,
    recommend,
    researchRecommend,
    research,
    researchAvailable,
    sequence,
    mapSequence,
    setResearch,
    money,
    budgetHint,
    districtSuggestions,
    changed,
    submittedSummary,
    formatBudget,
    budgetEquals,
    loadMap,
    submit,
    reset,
    adjust,
    areaSelected,
  };
}
export default React.forwardRef(function AdvisorView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section data-ui-view="AdvisorView"
      {...mergeProps({
        className: "sp-container advisor-page",
        "aria-labelledby": "advisor-title",
        "data-sp-731b6e1b": "",
      })}
    >
      <div
        {...mergeProps({
          className: "advisor-intro",
          "data-sp-731b6e1b": "",
        })}
      >
        <p
          {...mergeProps({
            className: "eyebrow",
            "data-sp-731b6e1b": "",
          })}
        >
          {"SMARTPROP · TƯ VẤN BĐS"}
        </p>
        <h1
          {...mergeProps({
            id: "advisor-title",
            "data-sp-731b6e1b": "",
          })}
        >
          {"Tìm không gian phù hợp với bạn"}
        </h1>
        <p
          {...mergeProps({
            "data-sp-731b6e1b": "",
          })}
        >
          {
            "Chọn theo ngân sách và mục đích. So sánh khu vực, xem lý do đề xuất và đối chiếu vị trí trên bản đồ."
          }
        </p>
      </div>
      <p
        {...mergeProps({
          className: "mb-5",
          "data-sp-731b6e1b": "",
        })}
      >
        <RouterLink
          {...mergeProps({
            to: "/advisor/chat",
            className: "sp-button sp-button-secondary",
            "data-chat-entry": true,
            "data-sp-731b6e1b": "",
          })}
        >
          {"Trao đổi với AI Advisor ↗"}
        </RouterLink>
      </p>
      <div
        {...mergeProps({
          className: ["safe-note", {
            "research-note": ctx.research,
          }],
          
          "data-sp-731b6e1b": "",
        })}
      >
        <span
          {...mergeProps({
            "aria-hidden": "true",
            "data-sp-731b6e1b": "",
          })}
        >
          {display(ctx.research ? "!" : "✓")}
        </span>
        <div
          {...mergeProps({
            "data-sp-731b6e1b": "",
          })}
        >
          <strong
            {...mergeProps({
              "data-sp-731b6e1b": "",
            })}
          >
            {display(
              ctx.research ? "Internal Demo — chỉ ADMIN" : "Chế độ an toàn",
            )}
          </strong>
          <p
            {...mergeProps({
              "data-sp-731b6e1b": "",
            })}
          >
            {display(
              ctx.research
                ? "Dữ liệu nghiên cứu TiniX AI — chưa xác minh. Lịch sử, chưa biết còn bán; chỉ nghiên cứu phi thương mại (CC BY-NC 4.0)."
                : "Chỉ hiển thị tin đủ điều kiện công khai. Không cần đăng nhập để tìm gợi ý.",
            )}
          </p>
        </div>
      </div>
      {ctx.researchAvailable ? (
        <div
          {...mergeProps({
            className: "research-controls",
            "data-sp-731b6e1b": "",
          })}
        >
          <button
            {...mergeProps({
              type: "button",
              className: "sp-button sp-button-secondary",
              "aria-pressed": ctx.research,
              onClick: ($event) => {
                ctx.setResearch(!ctx.research);
              },
              "data-sp-731b6e1b": "",
            })}
          >
            {display(
              ctx.research
                ? "Quay lại chế độ an toàn"
                : "Mở Internal Demo TiniX AI",
            )}
          </button>
          <p
            {...mergeProps({
              "data-sp-731b6e1b": "",
            })}
          >
            {
              "Không thay đổi danh sách công khai. Quyền truy cập được kiểm tra tại Backend."
            }
          </p>
        </div>
      ) : null}
      <form
        {...mergeProps({
          id: "advisor-form",
          className: "advisor-form",
          "aria-busy": ctx.busy,
          onSubmit: ($event) => {
            $event.preventDefault();
            return ctx.submit?.($event);
          },
          "data-sp-731b6e1b": "",
        })}
      >
        <div
          {...mergeProps({
            className: "form-heading",
            "data-sp-731b6e1b": "",
          })}
        >
          <div
            {...mergeProps({
              "data-sp-731b6e1b": "",
            })}
          >
            <h2
              {...mergeProps({
                "data-sp-731b6e1b": "",
              })}
            >
              {"Nhu cầu của bạn"}
            </h2>
            <p
              {...mergeProps({
                "data-sp-731b6e1b": "",
              })}
            >
              {
                "Nhập tổng ngân sách mua bất động sản bằng VNĐ. Bạn có thể nhập số tiền bất kỳ."
              }
            </p>
          </div>
          <span
            {...mergeProps({
              className: "required-note",
              "data-sp-731b6e1b": "",
            })}
          >
            {"* Thông tin bắt buộc"}
          </span>
        </div>
        <fieldset
          {...mergeProps({
            disabled: ctx.busy,
            "data-sp-731b6e1b": "",
          })}
        >
          <legend
            {...mergeProps({
              className: "sr-only",
              "data-sp-731b6e1b": "",
            })}
          >
            {"Bộ lọc gợi ý bất động sản"}
          </legend>
          <div
            {...mergeProps({
              className: "form-grid",
              "data-sp-731b6e1b": "",
            })}
          >
            <label
              {...mergeProps({
                className: "budget-field",
                "data-sp-731b6e1b": "",
              })}
            >
              {"Ngân sách tối đa (VNĐ) *"}
              <input
                {...mergeProps(
                  {
                    ref: bindRef(ctx, "budgetInput"),
                    onBlur: ($event) => {
                      return ctx.formatBudget?.($event);
                    },
                    name: "budget",
                    type: "text",
                    inputMode: "numeric",
                    maxLength: "32",
                    required: true,
                    "aria-describedby": "budget-hint",
                    autoComplete: "off",
                    "data-sp-731b6e1b": "",
                  },
                  modelProps(
                    ctx.form.budgetVnd,
                    ($value) => {
                      ctx.form.budgetVnd = $value;
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
                  id: "budget-hint",
                  "data-sp-731b6e1b": "",
                })}
              >
                {display(ctx.budgetHint)}
              </small>
              <span
                {...mergeProps({
                  className: "budget-presets",
                  "data-sp-731b6e1b": "",
                })}
              >
                {renderList([1, 2, 3, 5, 10], (value) => (
                  <button
                    key={value}
                    {...mergeProps({
                      type: "button",
                      "aria-pressed": ctx.budgetEquals(value * 1000000000),
                      onClick: ($event) => {
                        ctx.form.budgetVnd = ctx.formatAdvisorBudget(
                          String(value * 1000000000),
                        );
                      },
                      "data-sp-731b6e1b": "",
                    })}
                  >
                    {display(value)}
                    {" tỷ"}
                  </button>
                ))}
              </span>
            </label>
            <label
              {...mergeProps({
                "data-sp-731b6e1b": "",
              })}
            >
              {"Mục đích *"}
              <select
                {...mergeProps(
                  {
                    name: "purpose",
                    "data-sp-731b6e1b": "",
                  },
                  modelProps(
                    ctx.form.purpose,
                    ($value) => {
                      ctx.form.purpose = $value;
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
                    value: "LIVING",
                    "data-sp-731b6e1b": "",
                  })}
                >
                  {"Mua để ở"}
                </option>
                <option
                  {...mergeProps({
                    value: "INVESTMENT",
                    "data-sp-731b6e1b": "",
                  })}
                >
                  {"Đầu tư"}
                </option>
                <option
                  {...mergeProps({
                    value: "RENTAL",
                    "data-sp-731b6e1b": "",
                  })}
                >
                  {"Mua để cho thuê"}
                </option>
              </select>
              <small
                {...mergeProps({
                  "data-sp-731b6e1b": "",
                })}
              >
                {display(
                  ctx.form.purpose === "RENTAL"
                    ? "Ngân sách mua nhà, không phải tiền thuê hàng tháng."
                    : ctx.form.purpose === "INVESTMENT"
                      ? "Điểm tham khảo, không dự báo lợi nhuận đầu tư."
                      : "Ưu tiên mức phù hợp với nhu cầu đã nhập.",
                )}
              </small>
            </label>
            <label
              {...mergeProps({
                "data-sp-731b6e1b": "",
              })}
            >
              {"Loại bất động sản *"}
              <select
                {...mergeProps(
                  {
                    name: "propertyType",
                    "data-sp-731b6e1b": "",
                  },
                  modelProps(
                    ctx.form.propertyType,
                    ($value) => {
                      ctx.form.propertyType = $value;
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
                    value: "ALL",
                    "data-sp-731b6e1b": "",
                  })}
                >
                  {"Tất cả loại"}
                </option>
                <option
                  {...mergeProps({
                    value: "HOUSE",
                    "data-sp-731b6e1b": "",
                  })}
                >
                  {"Nhà ở"}
                </option>
                <option
                  {...mergeProps({
                    value: "APARTMENT",
                    "data-sp-731b6e1b": "",
                  })}
                >
                  {"Căn hộ"}
                </option>
                <option
                  {...mergeProps({
                    value: "LAND",
                    "data-sp-731b6e1b": "",
                  })}
                >
                  {"Đất nền"}
                </option>
                <option
                  {...mergeProps({
                    value: "VILLA",
                    "data-sp-731b6e1b": "",
                  })}
                >
                  {"Biệt thự"}
                </option>
                <option
                  {...mergeProps({
                    value: "ROOM",
                    "data-sp-731b6e1b": "",
                  })}
                >
                  {"Phòng"}
                </option>
                <option
                  {...mergeProps({
                    value: "COMMERCIAL",
                    "data-sp-731b6e1b": "",
                  })}
                >
                  {"Bất động sản thương mại"}
                </option>
              </select>
            </label>
            <label
              {...mergeProps({
                "data-sp-731b6e1b": "",
              })}
            >
              {"Diện tích tối thiểu (m²)"}
              <input
                {...mergeProps(
                  {
                    name: "minAreaSqm",
                    type: "number",
                    min: "0.1",
                    max: "1000000",
                    step: "any",
                    placeholder: "Không giới hạn",
                    "data-sp-731b6e1b": "",
                  },
                  modelProps(
                    ctx.form.minAreaSqm,
                    ($value) => {
                      ctx.form.minAreaSqm = $value;
                    },
                    {
                      kind: "number",
                      value: "on",
                      number: false,
                      multiple: false,
                    },
                  ),
                )}
              />
              <small
                {...mergeProps({
                  "data-sp-731b6e1b": "",
                })}
              >
                {"Để trống nếu chưa có yêu cầu."}
              </small>
            </label>
            <label
              {...mergeProps({
                "data-sp-731b6e1b": "",
              })}
            >
              {"Địa bàn"}
              <input
                {...mergeProps(
                  {
                    name: "district",
                    list: "advisor-districts",
                    maxLength: "100",
                    placeholder: "Tất cả khu vực",
                    autoComplete: "off",
                    "data-sp-731b6e1b": "",
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
              <small
                {...mergeProps({
                  "data-sp-731b6e1b": "",
                })}
              >
                {"Chọn gợi ý hoặc nhập địa bàn theo nguồn tin."}
              </small>
            </label>
            <label
              {...mergeProps({
                "data-sp-731b6e1b": "",
              })}
            >
              {"Phường/xã"}
              <input
                {...mergeProps(
                  {
                    name: "ward",
                    maxLength: "100",
                    placeholder: "Không bắt buộc",
                    "data-sp-731b6e1b": "",
                  },
                  modelProps(
                    ctx.form.ward,
                    ($value) => {
                      ctx.form.ward = $value;
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
                  "data-sp-731b6e1b": "",
                })}
              >
                {"Nguồn chưa có phường/xã sẽ không khớp bộ lọc này."}
              </small>
            </label>
            <label
              {...mergeProps({
                "data-sp-731b6e1b": "",
              })}
            >
              {"Số gợi ý"}
              <select
                {...mergeProps(
                  {
                    name: "limit",
                    "data-sp-731b6e1b": "",
                  },
                  modelProps(
                    ctx.form.limit,
                    ($value) => {
                      ctx.form.limit = $value;
                    },
                    {
                      kind: "text",
                      value: "on",
                      number: true,
                      multiple: false,
                    },
                  ),
                )}
              >
                <option
                  {...mergeProps({
                    value: 10,
                    "data-sp-731b6e1b": "",
                  })}
                >
                  {"Tối đa 10 tin"}
                </option>
                <option
                  {...mergeProps({
                    value: 5,
                    "data-sp-731b6e1b": "",
                  })}
                >
                  {"Tối đa 5 tin"}
                </option>
              </select>
            </label>
          </div>
          <datalist
            {...mergeProps({
              id: "advisor-districts",
              "data-sp-731b6e1b": "",
            })}
          >
            {renderList(ctx.districtSuggestions, (district) => (
              <option
                key={district}
                {...mergeProps({
                  value: district,
                  "data-sp-731b6e1b": "",
                })}
              />
            ))}
          </datalist>
          <div
            {...mergeProps({
              className: "form-footer",
              "data-sp-731b6e1b": "",
            })}
          >
            <p
              {...mergeProps({
                "data-sp-731b6e1b": "",
              })}
            >
              {
                "Điểm phù hợp được tính theo quy tắc tham khảo; không thay thế kiểm tra pháp lý, hiện trạng hoặc định giá độc lập."
              }
            </p>
            <div
              {...mergeProps({
                className: "form-actions",
                "data-sp-731b6e1b": "",
              })}
            >
              <button
                {...mergeProps({
                  className: "sp-button sp-button-secondary",
                  type: "button",
                  onClick: ($event) => {
                    return ctx.reset?.($event);
                  },
                  "data-sp-731b6e1b": "",
                })}
              >
                {"Đặt lại"}
              </button>
              <button
                {...mergeProps({
                  className: "sp-button sp-button-primary",
                  type: "submit",
                  "data-sp-731b6e1b": "",
                })}
              >
                {display(ctx.busy ? "Đang tìm gợi ý…" : "Tìm gợi ý phù hợp")}
              </button>
            </div>
          </div>
        </fieldset>
      </form>
      {ctx.error ? (
        <div
          {...mergeProps({
            role: "alert",
            className: "advisor-error",
            "data-sp-731b6e1b": "",
          })}
        >
          <div
            {...mergeProps({
              "data-sp-731b6e1b": "",
            })}
          >
            <strong
              {...mergeProps({
                "data-sp-731b6e1b": "",
              })}
            >
              {"Chưa thể tải gợi ý"}
            </strong>
            <p
              {...mergeProps({
                "data-sp-731b6e1b": "",
              })}
            >
              {display(ctx.error)}
            </p>
          </div>
          <button
            {...mergeProps({
              type: "button",
              className: "sp-button sp-button-secondary",
              onClick: ($event) => {
                return ctx.submit?.($event);
              },
              "data-sp-731b6e1b": "",
            })}
          >
            {"Thử lại"}
          </button>
        </div>
      ) : null}
      {ctx.busy ? (
        <div
          {...mergeProps({
            role: "status",
            className: "loading-panel",
            "data-sp-731b6e1b": "",
          })}
        >
          <span
            {...mergeProps({
              className: "loading-spinner",
              "aria-hidden": "true",
              "data-sp-731b6e1b": "",
            })}
          />
          <div
            {...mergeProps({
              "data-sp-731b6e1b": "",
            })}
          >
            <strong
              {...mergeProps({
                "data-sp-731b6e1b": "",
              })}
            >
              {"Đang tìm gợi ý phù hợp…"}
            </strong>
            <p
              {...mergeProps({
                "data-sp-731b6e1b": "",
              })}
            >
              {"Đối chiếu ngân sách, khu vực và điều kiện công khai."}
            </p>
          </div>
        </div>
      ) : null}
      {ctx.result ? (
        <React.Fragment {...mergeProps({})}>
          <div
            {...mergeProps({
              className: "submitted-heading",
              "data-sp-731b6e1b": "",
            })}
          >
            <h2
              {...mergeProps({
                ref: bindRef(ctx, "resultsHeading"),
                tabIndex: "-1",
                "data-sp-731b6e1b": "",
              })}
            >
              {"Kết quả tư vấn"}
            </h2>
            <p
              {...mergeProps({
                "data-sp-731b6e1b": "",
              })}
            >
              {display(ctx.submittedSummary)}
            </p>
          </div>
          {ctx.changed ? (
            <div
              {...mergeProps({
                role: "status",
                className: "changed-note",
                "data-sp-731b6e1b": "",
              })}
            >
              {
                "Bạn đã thay đổi bộ lọc. Kết quả bên dưới vẫn theo nhu cầu đã gửi; bấm “Tìm gợi ý phù hợp” để cập nhật."
              }
            </div>
          ) : null}
          <AdvisorResults
            {...mergeProps({
              result: ctx.result,
              points: ctx.points,
              selectedId: ctx.selected,
              mapBusy: ctx.mapBusy,
              mapFailures: ctx.mapFailures,
              onSelect: ($event) => {
                ctx.selected = $event;
              },
              onArea: ($event) => {
                return ctx.areaSelected?.($event);
              },
              onAdjust: ($event) => {
                return ctx.adjust?.($event);
              },
              onRetryMap: ($event) => {
                return ctx.loadMap?.($event);
              },
              "data-sp-731b6e1b": "",
            })}
          />
        </React.Fragment>
      ) : !ctx.busy && !ctx.error ? (
        <div
          {...mergeProps({
            className: "start-note",
            "data-sp-731b6e1b": "",
          })}
        >
          <strong
            {...mergeProps({
              "data-sp-731b6e1b": "",
            })}
          >
            {"Bắt đầu từ nhu cầu, kiểm tra bằng dữ liệu"}
          </strong>
          <p
            {...mergeProps({
              "data-sp-731b6e1b": "",
            })}
          >
            {
              "Sau khi tìm, bạn có thể xem tối đa 5 khu vực và 10 bất động sản cùng điểm phù hợp, lý do và nguồn. Số kết quả phụ thuộc dữ liệu đủ điều kiện; hệ thống không thêm tin chưa xác minh."
            }
          </p>
        </div>
      ) : null}
    </section>,
  ]);
});
