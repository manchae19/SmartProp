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
import "./AuditLogsView.css";
function setup(__props) {
  const currentTab = ref("all"),
    tabs = [
      {
        id: "all",
        label: "Tất cả",
      },
      {
        id: "post",
        label: "Duyệt / Từ chối tin",
      },
      {
        id: "account",
        label: "Tài khoản",
      },
      {
        id: "report",
        label: "Báo cáo",
      },
    ],
    state = useList("/admin/audit-logs"),
    logsList = computed(() =>
      state.items.map((l) => ({
        ...l,
        category:
          l.entityType === "USER"
            ? "account"
            : l.entityType === "REPORT"
              ? "report"
              : "post",
        content:
          l.action +
          " · " +
          (l.entityId || l.entityNumericId) +
          " · " +
          (l.oldValues?.status || "—") +
          " → " +
          (l.newValues?.status || "—"),
        meta: "Người thao tác #" + (l.actorId || "Hệ thống"),
        time: date(l.createdAt),
        typeClass: "type-approve",
      })),
    ),
    filteredLogs = computed(() =>
      logsList.value.filter(
        (l) => currentTab.value === "all" || l.category === currentTab.value,
      ),
    );
  const handlePostAction = () => {};
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
    currentTab,
    tabs,
    state,
    logsList,
    filteredLogs,
    handlePostAction,
  };
}
export default React.forwardRef(function AuditLogsView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="AuditLogsView"
      {...mergeProps({
        className: "main",
        "data-sp-7f256daf": "",
      })}
    >
      <LegacyState
        {...mergeProps({
          state: ctx.state,
          "data-sp-7f256daf": "",
        })}
      />
      <div
        {...mergeProps({
          className: "section-header",
          "data-sp-7f256daf": "",
        })}
      >
        <div
          {...mergeProps({
            className: "header-titles",
            "data-sp-7f256daf": "",
          })}
        >
          <div
            {...mergeProps({
              className: "badge-tag",
              "data-sp-7f256daf": "",
            })}
          >
            {"QUẢN TRỊ"}
          </div>
          <div
            {...mergeProps({
              className: "section-title",
              "data-sp-7f256daf": "",
            })}
          >
            {"Nhật ký kiểm toán"}
          </div>
          <div
            {...mergeProps({
              className: "section-desc",
              "data-sp-7f256daf": "",
            })}
          >
            {"Lịch sử toàn bộ thao tác của quản trị viên và hệ thống tự động."}
          </div>
        </div>
      </div>
      <div
        {...mergeProps({
          className: "stats-container",
          "data-sp-7f256daf": "",
        })}
      >
        <div
          {...mergeProps({
            className: "stat-card",
            "data-sp-7f256daf": "",
          })}
        >
          <div
            {...mergeProps({
              className: "stat-label",
              "data-sp-7f256daf": "",
            })}
          >
            {"Thao tác hôm nay"}
          </div>
          <div
            {...mergeProps({
              className: "stat-value",
              "data-sp-7f256daf": "",
            })}
          >
            {"—"}
          </div>
        </div>
        <div
          {...mergeProps({
            className: "stat-card",
            "data-sp-7f256daf": "",
          })}
        >
          <div
            {...mergeProps({
              className: "stat-label",
              "data-sp-7f256daf": "",
            })}
          >
            {"Tài khoản bị khoá"}
          </div>
          <div
            {...mergeProps({
              className: "stat-value",
              "data-sp-7f256daf": "",
            })}
          >
            {"—"}
          </div>
        </div>
        <div
          {...mergeProps({
            className: "stat-card",
            "data-sp-7f256daf": "",
          })}
        >
          <div
            {...mergeProps({
              className: "stat-label",
              "data-sp-7f256daf": "",
            })}
          >
            {"Cảnh báo hệ thống"}
          </div>
          <div
            {...mergeProps({
              className: "stat-value",
              "data-sp-7f256daf": "",
            })}
          >
            {"—"}
          </div>
        </div>
      </div>
      <div
        {...mergeProps({
          className: "filter-tabs",
          "data-sp-7f256daf": "",
        })}
      >
        {renderList(ctx.tabs, (tab) => (
          <button
            key={tab.id}
            {...mergeProps({
              className: [
                "tab-btn",
                {
                  active: ctx.currentTab === tab.id,
                },
              ],
              onClick: ($event) => {
                ctx.currentTab = tab.id;
              },
              "data-sp-7f256daf": "",
            })}
          >
            {display(tab.label)}
          </button>
        ))}
      </div>
      <div
        {...mergeProps({
          className: "logs-section",
          "data-sp-7f256daf": "",
        })}
      >
        <div
          {...mergeProps({
            className: "logs-header",
            "data-sp-7f256daf": "",
          })}
        >
          {display(ctx.state.totalElements)}
          {" hoạt động"}
        </div>
        <div
          {...mergeProps({
            className: "logs-list",
            "data-sp-7f256daf": "",
          })}
        >
          {renderList(ctx.filteredLogs, (log) => (
            <div
              key={log.id}
              {...mergeProps({
                className: "log-item",
                "data-sp-7f256daf": "",
              })}
            >
              <div
                {...mergeProps({
                  className: ["log-indicator", log.typeClass],
                  "data-sp-7f256daf": "",
                })}
              />
              <div
                {...mergeProps({
                  className: "log-content-wrapper",
                  "data-sp-7f256daf": "",
                })}
              >
                <div
                  {...mergeProps({
                    className: "log-text",
                    "data-sp-7f256daf": "",
                  })}
                >
                  {display(log.content)}
                </div>
                <div
                  {...mergeProps({
                    className: "log-meta",
                    "data-sp-7f256daf": "",
                  })}
                >
                  {display(log.meta)}
                </div>
              </div>
              <div
                {...mergeProps({
                  className: "log-time",
                  "data-sp-7f256daf": "",
                })}
              >
                {display(log.time)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>,
    <LegacyPager
      {...mergeProps({
        state: ctx.state,
        "data-sp-7f256daf": "",
      })}
    />,
  ]);
});
