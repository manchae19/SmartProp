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
import { computed, ref } from "../../shared/state/store.js";
import { useRouter } from "../../shared/routing/router.jsx";
import { api } from "../auth/api.js";
import {
  useList,
  LegacyState,
  LegacyPager,
  PrivateImage,
} from "../../shared/lib/legacy.js";
import { collectionReport } from "../home/collection.js";
import ReportDetails from "./ReportDetails.jsx";
import { useCollection } from "../home/useCollection.js";
import "./MyReportsView.css";
function setup(__props) {
  const router = useRouter();

  // SMARTPROP MY REPORTS 2.0
  // Data is loaded from the existing backend.

  const activeFilter = ref("all");
  const searchText = ref("");
  const selectedReport = ref(null);
  const reportStatuses = {
    open: "OPEN",
    processing: "PROCESSING",
    resolved: "RESOLVED",
    rejected: "REJECTED",
  };
  const state = useCollection("/users/me/reports", "/reports/summary", () => ({
    keyword: searchText.value.trim(),
    status: reportStatuses[activeFilter.value],
    sort: "newest",
  }));
  const reports = computed(() => state.items.map(collectionReport)),
    filteredReports = reports;
  const count = (key) => state.summary?.byStatus?.[reportStatuses[key]] ?? "—";
  const processingCount = computed(() => count("processing")),
    resolvedCount = computed(() => count("resolved")),
    rejectedCount = computed(() => count("rejected"));
  const filters = computed(() => [
    {
      key: "all",
      label: "Tất cả",
      count: state.summary?.totalReports ?? "—",
    },
    ...Object.entries({
      open: "Mới gửi",
      processing: "Đang xử lý",
      resolved: "Đã xử lý",
      rejected: "Từ chối",
    }).map(([key, label]) => ({
      key,
      label,
      count: count(key),
    })),
  ]);
  function statusClass(status) {
    if (status === "processing") {
      return "bg-[#FFF1D9] text-[#A36A19]";
    }
    if (status === "resolved") {
      return "bg-[#E5F4EB] text-[#287B56]";
    }
    return "bg-[#FCE8E3] text-[#BD5D48]";
  }
  function statusDot(status) {
    if (status === "processing") return "bg-[#D69C44]";
    if (status === "resolved") return "bg-[#4DAD80]";
    return "bg-[#D17760]";
  }
  async function openReport(report) {
    await state.run(async () => {
      selectedReport.value = collectionReport(
        await api("/reports/" + report.id),
      );
    });
  }
  async function reportUpdated(report) {
    selectedReport.value = collectionReport(report);
    await state.reload();
  }
  function closeReport() {
    selectedReport.value = null;
  }
  function resetFilters() {
    activeFilter.value = "all";
    searchText.value = "";
  }
  function goHome() {
    router.push("/home");
  }
  function goAccount() {
    router.push("/account");
  }
  function goPost() {
    router.push("/post");
  }
  function goMap() {
    router.push("/map");
  }
  return {
    computed,
    ref,
    useRouter,
    api,
    useList,
    LegacyState,
    LegacyPager,
    PrivateImage,
    collectionReport,
    ReportDetails,
    useCollection,
    router,
    activeFilter,
    searchText,
    selectedReport,
    reportStatuses,
    state,
    reports,
    filteredReports,
    count,
    processingCount,
    resolvedCount,
    rejectedCount,
    filters,
    statusClass,
    statusDot,
    openReport,
    reportUpdated,
    closeReport,
    resetFilters,
    goHome,
    goAccount,
    goPost,
    goMap,
  };
}
export default React.forwardRef(function MyReportsView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="MyReportsView"
      {...mergeProps({
        className: "sp-my-reports min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)]",
        "data-sp-ef737f62": "",
      })}
    >
      <section
        {...mergeProps({
          className: "relative overflow-hidden border-b border-[var(--ui-border)]",
          "data-sp-ef737f62": "",
        })}
      >
        <div
          {...mergeProps({
            className:
              "pointer-events-none absolute -right-28 -top-32 h-[420px] w-[420px] rounded-full border border-[var(--ui-border)]/20",
            "data-sp-ef737f62": "",
          })}
        />
        <div
          {...mergeProps({
            className:
              "pointer-events-none absolute -right-10 -top-12 h-[280px] w-[280px] rounded-full border border-[var(--ui-border)]/20",
            "data-sp-ef737f62": "",
          })}
        />
        <div
          {...mergeProps({
            className:
              "relative mx-auto max-w-[1440px] px-5 py-12 md:px-10 md:py-16",
            "data-sp-ef737f62": "",
          })}
        >
          <div
            {...mergeProps({
              className: "flex flex-wrap items-end justify-between gap-8",
              "data-sp-ef737f62": "",
            })}
          >
            <div
              {...mergeProps({
                "data-sp-ef737f62": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "flex items-center gap-3",
                  "data-sp-ef737f62": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "h-px w-9 bg-[var(--ui-soft)]",
                    "data-sp-ef737f62": "",
                  })}
                />
                <p
                  {...mergeProps({
                    className:
                      "text-xs font-bold uppercase tracking-[0.22em] text-[var(--ui-muted)]",
                    "data-sp-ef737f62": "",
                  })}
                >
                  {" SMARTPROP / TRUST & TRANSPARENCY "}
                </p>
              </div>
              <h1
                {...mergeProps({
                  className:
                    "mt-6 text-[39px] font-medium leading-tight tracking-tight sm:text-[56px]",
                  "data-sp-ef737f62": "",
                })}
              >
                {" Theo dõi "}
                <span
                  {...mergeProps({
                    className: "block italic text-[var(--ui-muted)]",
                    "data-sp-ef737f62": "",
                  })}
                >
                  {"báo cáo của bạn."}
                </span>
              </h1>
              <p
                {...mergeProps({
                  className: "mt-5 max-w-2xl text-sm leading-7 text-[var(--ui-muted)]",
                  "data-sp-ef737f62": "",
                })}
              >
                {
                  " Quản lý các báo cáo đã gửi, theo dõi tiến độ xem xét và xem kết quả xử lý trong một không gian trực quan, minh bạch và dễ sử dụng. "
                }
              </p>
              <span
                {...mergeProps({
                  className:
                    "mt-5 inline-flex rounded-full border border-[var(--ui-border)] bg-[var(--ui-surface)] px-4 py-2 text-xs font-bold uppercase tracking-widest text-[var(--ui-muted)]",
                  "data-sp-ef737f62": "",
                })}
              >
                {" Dữ liệu từ hệ thống "}
              </span>
            </div>
            <button
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  return ctx.goMap?.($event);
                },
                className:
                  "rounded-full border border-[var(--ui-border)] bg-brand-card px-7 py-4 text-xs font-bold transition hover:border-[var(--ui-border)]",
                "data-sp-ef737f62": "",
              })}
            >
              {" Khám phá GIS Explorer ↗ "}
            </button>
          </div>
        </div>
      </section>
      <section
        {...mergeProps({
          className: "mx-auto max-w-[1440px] px-5 pt-10 md:px-10",
          "data-sp-ef737f62": "",
        })}
      >
        <div
          {...mergeProps({
            className: "grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-5",
            "data-sp-ef737f62": "",
          })}
        >
          <div
            {...mergeProps({
              className:
                "rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7",
              "data-sp-ef737f62": "",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]",
                "data-sp-ef737f62": "",
              })}
            >
              {" Tổng báo cáo "}
            </p>
            <div
              {...mergeProps({
                className: "mt-4 flex items-end justify-between",
                "data-sp-ef737f62": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "text-4xl font-semibold",
                  "data-sp-ef737f62": "",
                })}
              >
                {display(ctx.state.summary?.totalReports ?? "—")}
              </span>
              <span
                {...mergeProps({
                  className: "text-xl text-[var(--ui-ink)]",
                  "data-sp-ef737f62": "",
                })}
              >
                {"▤"}
              </span>
            </div>
            <p
              {...mergeProps({
                className: "mt-3 text-xs text-[var(--ui-ink)]",
                "data-sp-ef737f62": "",
              })}
            >
              {" Báo cáo đã gửi "}
            </p>
          </div>
          <div
            {...mergeProps({
              className: "rounded-[20px] bg-[var(--ui-soft)] p-5 text-brand-navy sm:p-7",
              "data-sp-ef737f62": "",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-bold uppercase tracking-widest text-brand-navy/60",
                "data-sp-ef737f62": "",
              })}
            >
              {" Đang xử lý "}
            </p>
            <div
              {...mergeProps({
                className: "mt-4 flex items-end justify-between",
                "data-sp-ef737f62": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "text-4xl font-semibold",
                  "data-sp-ef737f62": "",
                })}
              >
                {display(ctx.processingCount)}
              </span>
              <span
                {...mergeProps({
                  className: "h-3 w-3 rounded-full bg-[var(--ui-soft)]",
                  "data-sp-ef737f62": "",
                })}
              />
            </div>
            <p
              {...mergeProps({
                className: "mt-3 text-xs text-brand-navy/55",
                "data-sp-ef737f62": "",
              })}
            >
              {" Đang chờ kết quả "}
            </p>
          </div>
          <div
            {...mergeProps({
              className:
                "rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7",
              "data-sp-ef737f62": "",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]",
                "data-sp-ef737f62": "",
              })}
            >
              {" Đã xử lý "}
            </p>
            <div
              {...mergeProps({
                className: "mt-4 flex items-end justify-between",
                "data-sp-ef737f62": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "text-4xl font-semibold",
                  "data-sp-ef737f62": "",
                })}
              >
                {display(ctx.resolvedCount)}
              </span>
              <span
                {...mergeProps({
                  className: "text-xl text-[var(--ui-accent)]",
                  "data-sp-ef737f62": "",
                })}
              >
                {"✓"}
              </span>
            </div>
            <p
              {...mergeProps({
                className: "mt-3 text-xs text-[var(--ui-ink)]",
                "data-sp-ef737f62": "",
              })}
            >
              {" Đã có kết quả xem xét "}
            </p>
          </div>
          <div
            {...mergeProps({
              className:
                "rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7",
              "data-sp-ef737f62": "",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]",
                "data-sp-ef737f62": "",
              })}
            >
              {" Bị từ chối "}
            </p>
            <div
              {...mergeProps({
                className: "mt-4 flex items-end justify-between",
                "data-sp-ef737f62": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "text-4xl font-semibold",
                  "data-sp-ef737f62": "",
                })}
              >
                {display(ctx.rejectedCount)}
              </span>
              <span
                {...mergeProps({
                  className: "text-xl text-[var(--ui-ink)]",
                  "data-sp-ef737f62": "",
                })}
              >
                {"!"}
              </span>
            </div>
            <p
              {...mergeProps({
                className: "mt-3 text-xs text-[var(--ui-ink)]",
                "data-sp-ef737f62": "",
              })}
            >
              {" Báo cáo không được chấp nhận "}
            </p>
          </div>
        </div>
      </section>
      <div
        {...mergeProps({
          className: "mx-auto max-w-[1440px] px-5 pb-20 pt-12 md:px-10",
          "data-sp-ef737f62": "",
        })}
      >
        <LegacyState
          {...mergeProps({
            state: ctx.state,
            "data-sp-ef737f62": "",
          })}
        />
        {ctx.state.summaryError ? (
          <p
            {...mergeProps({
              role: "alert",
              "data-sp-ef737f62": "",
            })}
          >
            {display(ctx.state.summaryError)}{" "}
            <button
              {...mergeProps({
                onClick: ($event) => {
                  return ctx.state.loadSummary?.($event);
                },
                "data-sp-ef737f62": "",
              })}
            >
              {"Tải lại thống kê"}
            </button>
          </p>
        ) : null}
        <p
          {...mergeProps({
            className: "mb-4 text-xs text-[var(--ui-ink)]",
            "data-sp-ef737f62": "",
          })}
        >
          {display(ctx.state.totalElements)}
          {" kết quả · kết quả đã lọc trên toàn bộ báo cáo."}
        </p>
        <div
          {...mergeProps({
            className: "flex flex-wrap items-end justify-between gap-5",
            "data-sp-ef737f62": "",
          })}
        >
          <div
            {...mergeProps({
              "data-sp-ef737f62": "",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-muted)]",
                "data-sp-ef737f62": "",
              })}
            >
              {" REPORT CENTER / 01 "}
            </p>
            <h2
              {...mergeProps({
                className:
                  "mt-3 text-3xl font-medium tracking-tight sm:text-4xl",
                "data-sp-ef737f62": "",
              })}
            >
              {" Lịch sử "}
              <span
                {...mergeProps({
                  className: "italic text-[var(--ui-muted)]",
                  "data-sp-ef737f62": "",
                })}
              >
                {"báo cáo."}
              </span>
            </h2>
            <p
              {...mergeProps({
                className: "mt-3 text-xs text-[var(--ui-ink)]",
                "data-sp-ef737f62": "",
              })}
            >
              {" Theo dõi tiến độ và kết quả xử lý của từng báo cáo. "}
            </p>
          </div>
          <div
            {...mergeProps({
              className:
                "flex w-full items-center gap-3 rounded-xl border border-[var(--ui-border)] bg-brand-card px-4 sm:w-[320px]",
              "data-sp-ef737f62": "",
            })}
          >
            <span
              {...mergeProps({
                className: "text-xl text-[var(--ui-muted)]",
                "data-sp-ef737f62": "",
              })}
            >
              {"⌕"}
            </span>
            <input
              {...mergeProps(
                {
                  type: "search",
                  "aria-label": "Tìm kiếm báo cáo",
                  placeholder: "Tìm nội dung, mã tin hoặc lý do...",
                  className:
                    "h-12 min-w-0 w-full bg-transparent text-xs outline-none",
                  "data-sp-ef737f62": "",
                },
                modelProps(
                  ctx.searchText,
                  ($value) => {
                    ctx.searchText = $value;
                  },
                  {
                    kind: "search",
                    value: "on",
                    number: false,
                    multiple: false,
                  },
                ),
              )}
            />
          </div>
        </div>
        <div
          {...mergeProps({
            className: "mt-8 flex flex-wrap gap-2",
            "data-sp-ef737f62": "",
          })}
        >
          {renderList(ctx.filters, (filter) => (
            <button
              key={filter.key}
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  ctx.activeFilter = filter.key;
                },
                className: ["rounded-full border px-4 py-2.5 text-xs font-semibold transition sm:px-5", ctx.activeFilter === filter.key
                    ? "border-[var(--ui-border)] bg-[var(--ui-soft)] text-brand-navy"
                    : "border-[var(--ui-border)] bg-brand-card text-[var(--ui-accent)] hover:border-[var(--ui-border)]"],
                
                "data-sp-ef737f62": "",
              })}
            >
              {display(filter.label)}{" "}
              <span
                {...mergeProps({
                  className: "ml-1 opacity-65",
                  "data-sp-ef737f62": "",
                })}
              >
                {display(filter.count)}
              </span>
            </button>
          ))}
        </div>
        <div
          {...mergeProps({
            className: "mb-5 mt-7 flex items-center justify-between gap-4",
            "data-sp-ef737f62": "",
          })}
        >
          <p
            {...mergeProps({
              className: "text-xs text-[var(--ui-ink)]",
              "data-sp-ef737f62": "",
            })}
          >
            {" Hiển thị "}
            <strong
              {...mergeProps({
                className: "text-[var(--ui-accent)]",
                "data-sp-ef737f62": "",
              })}
            >
              {display(ctx.filteredReports.length)}
            </strong>
            {" báo cáo "}
          </p>
          <span
            {...mergeProps({
              className: "text-xs uppercase tracking-widest text-[var(--ui-muted)]",
              "data-sp-ef737f62": "",
            })}
          >
            {" REPORT HISTORY "}
          </span>
        </div>
        {ctx.filteredReports.length ? (
          <div
            {...mergeProps({
              className: "space-y-5",
              "data-sp-ef737f62": "",
            })}
          >
            {renderList(ctx.filteredReports, (report) => (
              <article
                key={report.id}
                {...mergeProps({
                  className:
                    "group grid min-w-0 overflow-hidden rounded-[22px] border border-[var(--ui-border)] bg-brand-card transition duration-300 hover:border-[var(--ui-border)] hover:shadow-[0_16px_45px_rgba(20,43,79,0.08)] lg:grid-cols-[245px_minmax(0,1fr)_225px]",
                  "data-sp-ef737f62": "",
                })}
              >
                <div
                  {...mergeProps({
                    className:
                      "relative h-[225px] overflow-hidden bg-[var(--ui-surface)] lg:h-full lg:min-h-[230px]",
                    "data-sp-ef737f62": "",
                  })}
                >
                  <PrivateImage
                    {...mergeProps({
                      src: report.image,
                      alt: `${report.title}`,
                      loading: "lazy",
                      className:
                        "h-full w-full object-cover transition duration-700 group-hover:scale-105",
                      "data-sp-ef737f62": "",
                    })}
                  />
                  <div
                    {...mergeProps({
                      className:
                        "absolute inset-0 bg-gradient-to-t from-[var(--ui-soft)]/55 to-transparent",
                      "data-sp-ef737f62": "",
                    })}
                  />
                  <span
                    {...mergeProps({
                      className:
                        "absolute bottom-4 left-4 text-xs font-bold uppercase tracking-[0.12em] text-brand-navy",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    {display(report.location)}
                  </span>
                </div>
                <div
                  {...mergeProps({
                    className:
                      "flex min-w-0 flex-col justify-center p-5 sm:p-7",
                    "data-sp-ef737f62": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className: "flex flex-wrap items-center gap-3",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className: ["inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold", ctx.statusClass(report.status)],
                        
                        "data-sp-ef737f62": "",
                      })}
                    >
                      <span
                        {...mergeProps({
                          className: ["h-1.5 w-1.5 rounded-full", ctx.statusDot(report.status)],
                          
                          "data-sp-ef737f62": "",
                        })}
                      />{" "}
                      {display(report.statusLabel)}
                    </span>
                    <span
                      {...mergeProps({
                        className: "text-xs font-semibold text-[var(--ui-muted)]",
                        "data-sp-ef737f62": "",
                      })}
                    >
                      {" REPORT #"}
                      {display(String(report.id).padStart(3, "0"))}
                    </span>
                  </div>
                  <h3
                    {...mergeProps({
                      className:
                        "mt-4 text-lg font-semibold leading-7 sm:text-xl",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    {display(report.title)}
                  </h3>
                  <p
                    {...mergeProps({
                      className: "mt-2 text-xs text-[var(--ui-ink)]",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    {" ⌖ "}
                    {display(report.location)}
                  </p>
                  <div
                    {...mergeProps({
                      className: "mt-4",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className:
                          "inline-flex max-w-full rounded-full bg-[var(--ui-surface)] px-3 py-2 text-xs font-bold tracking-wide text-[var(--ui-muted)]",
                        "data-sp-ef737f62": "",
                      })}
                    >
                      {display(report.reason)}
                    </span>
                  </div>
                  <p
                    {...mergeProps({
                      className: "mt-4 text-xs text-[var(--ui-ink)]",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    {display(report.sentAt)}
                  </p>
                  {report.result ? (
                    <p
                      {...mergeProps({
                        className:
                          "mt-4 border-l-2 border-[var(--ui-border)] pl-3 text-xs leading-6 text-[var(--ui-accent)]",
                        "data-sp-ef737f62": "",
                      })}
                    >
                      {display(report.result)}
                    </p>
                  ) : null}
                </div>
                <div
                  {...mergeProps({
                    className:
                      "flex flex-col justify-between gap-6 border-t border-[var(--ui-border)] p-5 sm:p-7 lg:border-l lg:border-t-0",
                    "data-sp-ef737f62": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className: "lg:text-right",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    <p
                      {...mergeProps({
                        className:
                          "text-xs uppercase tracking-widest text-[var(--ui-ink)]",
                        "data-sp-ef737f62": "",
                      })}
                    >
                      {" Trạng thái hiện tại "}
                    </p>
                    <p
                      {...mergeProps({
                        className: "mt-3 text-base font-semibold",
                        "data-sp-ef737f62": "",
                      })}
                    >
                      {display(report.statusLabel)}
                    </p>
                    <p
                      {...mergeProps({
                        className: "mt-2 text-xs leading-5 text-[var(--ui-ink)]",
                        "data-sp-ef737f62": "",
                      })}
                    >
                      {display(report.update)}
                    </p>
                  </div>
                  <button
                    {...mergeProps({
                      type: "button",
                      onClick: ($event) => {
                        ctx.openReport(report);
                      },
                      className:
                        "self-start rounded-full border border-[var(--ui-border)] bg-brand-card px-5 py-3 text-xs font-semibold transition hover:border-[var(--ui-border)] hover:bg-[var(--ui-soft)] hover:text-brand-navy lg:self-end",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    {" Xem báo cáo ↗ "}
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div
            {...mergeProps({
              className:
                "rounded-[24px] border border-[var(--ui-border)] bg-brand-card px-6 py-20 text-center",
              "data-sp-ef737f62": "",
            })}
          >
            <div
              {...mergeProps({
                className:
                  "mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[var(--ui-surface)] text-3xl text-[var(--ui-muted)]",
                "data-sp-ef737f62": "",
              })}
            >
              {" ⚑ "}
            </div>
            <h3
              {...mergeProps({
                className: "mt-6 text-xl font-semibold",
                "data-sp-ef737f62": "",
              })}
            >
              {" Không tìm thấy báo cáo "}
            </h3>
            <p
              {...mergeProps({
                className: "mt-3 text-sm text-[var(--ui-ink)]",
                "data-sp-ef737f62": "",
              })}
            >
              {" Hãy thử thay đổi trạng thái hoặc từ khóa tìm kiếm. "}
            </p>
            <button
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  return ctx.resetFilters?.($event);
                },
                className:
                  "mt-6 rounded-full bg-[var(--ui-soft)] px-6 py-3 text-xs font-semibold text-brand-navy",
                "data-sp-ef737f62": "",
              })}
            >
              {" Xem tất cả báo cáo "}
            </button>
          </div>
        )}
        <section
          {...mergeProps({
            className:
              "mt-10 rounded-[22px] border border-[var(--ui-border)] bg-brand-card px-6 py-6 sm:px-8",
            "data-sp-ef737f62": "",
          })}
        >
          <div
            {...mergeProps({
              className: "flex items-start gap-4",
              "data-sp-ef737f62": "",
            })}
          >
            <div
              {...mergeProps({
                className:
                  "flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[var(--ui-surface)] text-lg font-semibold text-[var(--ui-muted)]",
                "data-sp-ef737f62": "",
              })}
            >
              {" i "}
            </div>
            <div
              {...mergeProps({
                "data-sp-ef737f62": "",
              })}
            >
              <h3
                {...mergeProps({
                  className: "text-sm font-semibold",
                  "data-sp-ef737f62": "",
                })}
              >
                {" Thông tin về quá trình xử lý "}
              </h3>
              <p
                {...mergeProps({
                  className: "mt-2 max-w-3xl text-xs leading-6 text-[var(--ui-ink)]",
                  "data-sp-ef737f62": "",
                })}
              >
                {
                  " Bạn có thể theo dõi trạng thái xử lý và bổ sung bằng chứng trong chi tiết báo cáo. "
                }
              </p>
            </div>
          </div>
        </section>
        <section
          {...mergeProps({
            className:
              "relative mt-12 overflow-hidden rounded-[25px] bg-[var(--ui-soft)] px-7 py-10 text-brand-navy sm:px-10",
            "data-sp-ef737f62": "",
          })}
        >
          <div
            {...mergeProps({
              className:
                "pointer-events-none absolute -right-12 -top-24 h-72 w-72 rounded-full border border-[var(--ui-border)]/20",
              "data-sp-ef737f62": "",
            })}
          />
          <div
            {...mergeProps({
              className:
                "relative flex flex-wrap items-center justify-between gap-7",
              "data-sp-ef737f62": "",
            })}
          >
            <div
              {...mergeProps({
                "data-sp-ef737f62": "",
              })}
            >
              <p
                {...mergeProps({
                  className:
                    "text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-accent)]",
                  "data-sp-ef737f62": "",
                })}
              >
                {" SMARTPROP / TRUST & SAFETY "}
              </p>
              <h2
                {...mergeProps({
                  className: "mt-4 text-3xl font-medium",
                  "data-sp-ef737f62": "",
                })}
              >
                {" Minh bạch hơn. "}
                <span
                  {...mergeProps({
                    className: "italic text-[var(--ui-ink)]",
                    "data-sp-ef737f62": "",
                  })}
                >
                  {" An tâm hơn."}
                </span>
              </h2>
              <p
                {...mergeProps({
                  className: "mt-4 max-w-xl text-sm leading-7 text-brand-navy/60",
                  "data-sp-ef737f62": "",
                })}
              >
                {
                  " Khám phá bất động sản và các thông tin tham khảo trên nền tảng SmartProp. "
                }
              </p>
            </div>
            <button
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  return ctx.goMap?.($event);
                },
                className:
                  "rounded-full bg-[var(--ui-soft)] px-7 py-4 text-xs font-bold text-[var(--ui-accent)] transition hover:bg-[var(--ui-soft)]",
                "data-sp-ef737f62": "",
              })}
            >
              {" Khám phá bản đồ GIS ↗ "}
            </button>
          </div>
        </section>
        <p
          {...mergeProps({
            className: "mt-7 text-center text-xs leading-6 text-[var(--ui-ink)]",
            "data-sp-ef737f62": "",
          })}
        >
          {" Báo cáo và kết quả xử lý được tải từ tài khoản của bạn. "}
        </p>
        <LegacyPager
          {...mergeProps({
            state: ctx.state,
            "data-sp-ef737f62": "",
          })}
        />
      </div>
      {ctx.selectedReport ? (
        <div
          {...mergeProps({
            className:
              "fixed inset-0 z-50 flex items-center justify-center bg-[var(--ui-soft)]/70 p-4",
            onClick: ($event) => {
              if ($event.target !== $event.currentTarget) return;
              return ctx.closeReport?.($event);
            },
            "data-sp-ef737f62": "",
          })}
        >
          <div
            {...mergeProps({
              role: "dialog",
              "aria-modal": "true",
              "aria-labelledby": "report-dialog-title",
              className:
                "max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-[24px] bg-brand-card shadow-2xl",
              "data-sp-ef737f62": "",
            })}
          >
            <div
              {...mergeProps({
                className: "relative h-[210px]",
                "data-sp-ef737f62": "",
              })}
            >
              <PrivateImage
                {...mergeProps({
                  src: ctx.selectedReport.image,
                  alt: ctx.selectedReport.title,
                  className: "h-full w-full object-cover",
                  "data-sp-ef737f62": "",
                })}
              />
              <button
                {...mergeProps({
                  type: "button",
                  onClick: ($event) => {
                    return ctx.closeReport?.($event);
                  },
                  "aria-label": "Đóng chi tiết báo cáo",
                  className:
                    "absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full bg-brand-card text-[var(--ui-accent)]",
                  "data-sp-ef737f62": "",
                })}
              >
                {" ✕ "}
              </button>
            </div>
            <div
              {...mergeProps({
                className: "p-6 sm:p-8",
                "data-sp-ef737f62": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "flex flex-wrap items-center gap-3",
                  "data-sp-ef737f62": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: ["rounded-full px-3 py-1.5 text-xs font-semibold", ctx.statusClass(ctx.selectedReport.status)],
                    
                    "data-sp-ef737f62": "",
                  })}
                >
                  {display(ctx.selectedReport.statusLabel)}
                </span>
                <span
                  {...mergeProps({
                    className: "text-xs text-[var(--ui-muted)]",
                    "data-sp-ef737f62": "",
                  })}
                >
                  {" REPORT #"}
                  {display(String(ctx.selectedReport.id).padStart(3, "0"))}
                </span>
              </div>
              <h2
                {...mergeProps({
                  id: "report-dialog-title",
                  className: "mt-5 text-2xl font-semibold",
                  "data-sp-ef737f62": "",
                })}
              >
                {display(ctx.selectedReport.title)}
              </h2>
              <p
                {...mergeProps({
                  className: "mt-3 text-sm text-[var(--ui-ink)]",
                  "data-sp-ef737f62": "",
                })}
              >
                {display(ctx.selectedReport.location)}
              </p>
              <div
                {...mergeProps({
                  className: "mt-6 space-y-4 border-y border-[var(--ui-border)] py-5",
                  "data-sp-ef737f62": "",
                })}
              >
                <div
                  {...mergeProps({
                    "data-sp-ef737f62": "",
                  })}
                >
                  <p
                    {...mergeProps({
                      className:
                        "text-xs uppercase tracking-widest text-[var(--ui-ink)]",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    {" Lý do báo cáo "}
                  </p>
                  <p
                    {...mergeProps({
                      className: "mt-2 text-sm font-semibold",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    {display(ctx.selectedReport.reason)}
                  </p>
                </div>
                <div
                  {...mergeProps({
                    "data-sp-ef737f62": "",
                  })}
                >
                  <p
                    {...mergeProps({
                      className:
                        "text-xs uppercase tracking-widest text-[var(--ui-ink)]",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    {" Thời gian gửi "}
                  </p>
                  <p
                    {...mergeProps({
                      className: "mt-2 text-sm",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    {display(ctx.selectedReport.sentAt)}
                  </p>
                </div>
                <div
                  {...mergeProps({
                    "data-sp-ef737f62": "",
                  })}
                >
                  <p
                    {...mergeProps({
                      className:
                        "text-xs uppercase tracking-widest text-[var(--ui-ink)]",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    {" Cập nhật "}
                  </p>
                  <p
                    {...mergeProps({
                      className: "mt-2 text-sm",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    {display(ctx.selectedReport.update)}
                  </p>
                </div>
                <div
                  {...mergeProps({
                    "data-sp-ef737f62": "",
                  })}
                >
                  <p
                    {...mergeProps({
                      className:
                        "text-xs uppercase tracking-widest text-[var(--ui-ink)]",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    {" Kết quả "}
                  </p>
                  <p
                    {...mergeProps({
                      className: "mt-2 text-sm leading-6 text-[var(--ui-accent)]",
                      "data-sp-ef737f62": "",
                    })}
                  >
                    {display(
                      ctx.selectedReport.result ||
                        "Báo cáo đang được xử lý, chưa có kết quả.",
                    )}
                  </p>
                </div>
              </div>
              <ReportDetails
                {...mergeProps({
                  report: ctx.selectedReport.raw,
                  onUpdated: ($event) => {
                    return ctx.reportUpdated?.($event);
                  },
                  "data-sp-ef737f62": "",
                })}
              />
              <button
                {...mergeProps({
                  type: "button",
                  onClick: ($event) => {
                    return ctx.closeReport?.($event);
                  },
                  className:
                    "mt-6 rounded-full bg-[var(--ui-soft)] px-7 py-3 text-xs font-semibold text-brand-navy",
                  "data-sp-ef737f62": "",
                })}
              >
                {" Đóng chi tiết "}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>,
  ]);
});
