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
import ReportDetails from "../report/ReportDetails.jsx";
import "./ReportsView.css";
function setup(__props) {
  const statusFilter = ref("OPEN");
  const router = useRouter(),
    state = useList("/admin/reports", () => ({
      status: statusFilter.value || undefined,
    })),
    selected = ref(null),
    note = ref(""),
    reportsList = computed(() =>
      state.items.map((r) => ({
        ...r,
        title: "Tin " + r.propertyId,
        reason: reasonLabels[r.reasonCode] || r.reasonCode,
        reporter: "Người dùng #" + r.reporterId,
        time: date(r.createdAt),
      })),
    );
  const viewPost = (id) => {
    selected.value = state.items.find((r) => r.id === id);
    note.value = "";
  };
  async function resolve(id, status) {
    if (!selected.value || selected.value.id !== id) {
      viewPost(id);
      return;
    }
    if (!note.value.trim()) {
      state.error = "Nhập ghi chú xử lý.";
      return;
    }
    await state.run(async () => {
      await api("/admin/reports/" + id + "/status", {
        method: "PATCH",
        body: {
          status,
          note: note.value,
        },
      });
      selected.value = null;
      await state.load(state.page);
    });
  }
  const removePost = (id) => resolve(id, "RESOLVED"),
    skipReport = (id) => resolve(id, "REJECTED");
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
    ReportDetails,
    statusFilter,
    router,
    state,
    selected,
    note,
    reportsList,
    viewPost,
    resolve,
    removePost,
    skipReport,
  };
}
export default React.forwardRef(function ReportsView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="ReportsView"
      {...mergeProps({
        className: "main",
        "data-sp-fd30d3f5": "",
      })}
    >
      <LegacyState
        {...mergeProps({
          state: ctx.state,
          "data-sp-fd30d3f5": "",
        })}
      />
      <div
        {...mergeProps({
          className: "section-title",
          "data-sp-fd30d3f5": "",
        })}
      >
        <div
          {...mergeProps({
            className: "title-text",
            "data-sp-fd30d3f5": "",
          })}
        >
          {display(ctx.state.totalElements)}
          {" báo cáo"}
        </div>
      </div>
      <select
        {...mergeProps(
          {
            onChange: ($event) => {
              ctx.selected = null;
              ctx.state.load(0);
            },
            className: "bg-brand-card border rounded-lg p-2 text-sm",
            "data-sp-fd30d3f5": "",
          },
          modelProps(
            ctx.statusFilter,
            ($value) => {
              ctx.statusFilter = $value;
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
            value: "OPEN",
            "data-sp-fd30d3f5": "",
          })}
        >
          {"Mới tiếp nhận"}
        </option>
        <option
          {...mergeProps({
            value: "PROCESSING",
            "data-sp-fd30d3f5": "",
          })}
        >
          {"Đang xử lý"}
        </option>
        <option
          {...mergeProps({
            value: "RESOLVED",
            "data-sp-fd30d3f5": "",
          })}
        >
          {"Đã giải quyết"}
        </option>
        <option
          {...mergeProps({
            value: "REJECTED",
            "data-sp-fd30d3f5": "",
          })}
        >
          {"Đã từ chối"}
        </option>
        <option
          {...mergeProps({
            value: "",
            "data-sp-fd30d3f5": "",
          })}
        >
          {"Tất cả"}
        </option>
      </select>
      <div
        {...mergeProps({
          className: "reports-list",
          "data-sp-fd30d3f5": "",
        })}
      >
        {renderList(ctx.reportsList, (report) => (
          <div
            key={report.id}
            {...mergeProps({
              className: "report-card",
              "data-report-id": report.id,
              "data-sp-fd30d3f5": "",
            })}
          >
            <div
              {...mergeProps({
                className: "report-info",
                "data-sp-fd30d3f5": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "report-title",
                  "data-sp-fd30d3f5": "",
                })}
              >
                {display(report.title)}
              </div>
              <div
                {...mergeProps({
                  className: "report-reason-badge",
                  "data-sp-fd30d3f5": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "reason-text",
                    "data-sp-fd30d3f5": "",
                  })}
                >
                  {display(report.reason)}
                </span>
              </div>
              <div
                {...mergeProps({
                  className: "report-meta",
                  "data-sp-fd30d3f5": "",
                })}
              >
                {" Báo cáo bởi "}
                {display(report.reporter)}
                {" · "}
                {display(report.time)}
              </div>
            </div>
            <div
              {...mergeProps({
                className: "report-actions",
                "data-sp-fd30d3f5": "",
              })}
            >
              <button
                {...mergeProps({
                  className: "btn-view",
                  onClick: ($event) => {
                    ctx.viewPost(report.id);
                  },
                  "data-sp-fd30d3f5": "",
                })}
              >
                {" Xem báo cáo › "}
              </button>
              {!["RESOLVED", "REJECTED"].includes(report.status) ? (
                <button
                  {...mergeProps({
                    className: "btn-remove",
                    onClick: ($event) => {
                      ctx.removePost(report.id);
                    },
                    "data-sp-fd30d3f5": "",
                  })}
                >
                  {" Giải quyết "}
                </button>
              ) : null}
              {!["RESOLVED", "REJECTED"].includes(report.status) ? (
                <button
                  {...mergeProps({
                    className: "btn-skip",
                    onClick: ($event) => {
                      ctx.skipReport(report.id);
                    },
                    "data-sp-fd30d3f5": "",
                  })}
                >
                  {" Bỏ qua "}
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>,
    ctx.selected ? (
      <section
        {...mergeProps({
          className: "rounded-2xl bg-brand-card p-6",
          "data-sp-fd30d3f5": "",
        })}
      >
        <ReportDetails
          {...mergeProps({
            report: ctx.selected,
            admin: true,
            "data-sp-fd30d3f5": "",
          })}
        />
        <label
          {...mergeProps({
            className: "block text-xs",
            "data-sp-fd30d3f5": "",
          })}
        >
          {"Ghi chú xử lý"}
          <textarea
            {...mergeProps(
              {
                maxLength: "4000",
                className: "w-full border rounded-xl p-3 my-3",
                "data-sp-fd30d3f5": "",
              },
              modelProps(
                ctx.note,
                ($value) => {
                  ctx.note = $value;
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
        {!["RESOLVED", "REJECTED"].includes(ctx.selected.status) ? (
          <button
            {...mergeProps({
              onClick: ($event) => {
                ctx.removePost(ctx.selected.id);
              },
              className:
                "bg-[var(--ui-soft)] text-brand-navy rounded-full px-5 py-2 text-xs",
              "data-sp-fd30d3f5": "",
            })}
          >
            {"Giải quyết"}
          </button>
        ) : null}
        {!["RESOLVED", "REJECTED"].includes(ctx.selected.status) ? (
          <button
            {...mergeProps({
              onClick: ($event) => {
                ctx.skipReport(ctx.selected.id);
              },
              className: "border rounded-full px-5 py-2 text-xs ml-2",
              "data-sp-fd30d3f5": "",
            })}
          >
            {"Từ chối"}
          </button>
        ) : null}
      </section>
    ) : null,
    <LegacyPager
      {...mergeProps({
        state: ctx.state,
        "data-sp-fd30d3f5": "",
      })}
    />,
  ]);
});
