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
import "./DashboardView.css";
function setup(__props) {
  const state = ref({
      busy: false,
      error: "",
      notice: "",
    }),
    stats = ref({}),
    chartData = ref([]);
  onMounted(async () => {
    state.value.busy = true;
    try {
      stats.value = await api("/admin/dashboard");
    } catch (e) {
      state.value.error = errorText(e);
    } finally {
      state.value.busy = false;
    }
  });
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
    state,
    stats,
    chartData,
  };
}
export default React.forwardRef(function DashboardView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="DashboardView"
      {...mergeProps({
        className: "main",
        "data-sp-9b34df92": "",
      })}
    >
      <LegacyState
        {...mergeProps({
          state: ctx.state,
          "data-sp-9b34df92": "",
        })}
      />
      <div
        {...mergeProps({
          className: "stats",
          "data-sp-9b34df92": "",
        })}
      >
        <div
          {...mergeProps({
            className: "stat",
            "data-sp-9b34df92": "",
          })}
        >
          <div
            {...mergeProps({
              className: "tin-ang-hi-n-th",
              "data-sp-9b34df92": "",
            })}
          >
            {"Tin đang hiển thị"}
          </div>
          <div
            {...mergeProps({
              className: "_2-417",
              "data-sp-9b34df92": "",
            })}
          >
            {display(ctx.stats.publishedProperties ?? 0)}
          </div>
        </div>
        <div
          {...mergeProps({
            className: "stat",
            "data-sp-9b34df92": "",
          })}
        >
          <div
            {...mergeProps({
              className: "ch-duy-t",
              "data-sp-9b34df92": "",
            })}
          >
            {"Chờ duyệt"}
          </div>
          <div
            {...mergeProps({
              className: "_182",
              "data-sp-9b34df92": "",
            })}
          >
            {display(ctx.stats.pendingProperties ?? 0)}
          </div>
        </div>
        <div
          {...mergeProps({
            className: "stat2",
            "data-sp-9b34df92": "",
          })}
        >
          <div
            {...mergeProps({
              className: "c-nh-b-o-nh-tr-ng",
              "data-sp-9b34df92": "",
            })}
          >
            {"Báo cáo mới"}
          </div>
          <div
            {...mergeProps({
              className: "_9",
              "data-sp-9b34df92": "",
            })}
          >
            {display(ctx.stats.openReports ?? 0)}
          </div>
        </div>
        <div
          {...mergeProps({
            className: "stat",
            "data-sp-9b34df92": "",
          })}
        >
          <div
            {...mergeProps({
              className: "ng-i-d-ng-ho-t-ng",
              "data-sp-9b34df92": "",
            })}
          >
            {"Người dùng hoạt động"}
          </div>
          <div
            {...mergeProps({
              className: "_1-043",
              "data-sp-9b34df92": "",
            })}
          >
            {display(ctx.stats.activeUsers ?? 0)}
          </div>
        </div>
      </div>
      <div
        {...mergeProps({
          className: "row-2",
          "data-sp-9b34df92": "",
        })}
      >
        <div
          {...mergeProps({
            className: "chart",
            "data-sp-9b34df92": "",
          })}
        >
          <div
            {...mergeProps({
              className: "tin-ng-m-i-theo-tu",
              "data-sp-9b34df92": "",
            })}
          >
            {"Tin đăng mới theo tuần · Chưa có dữ liệu"}
          </div>
          <div
            {...mergeProps({
              className: "bars",
              "data-sp-9b34df92": "",
            })}
          >
            {renderList(ctx.chartData, (item, index) => (
              <div
                key={index}
                {...mergeProps({
                  className: "col",
                  "data-sp-9b34df92": "",
                })}
              >
                <div
                  {...mergeProps({
                    className: ["bar-fill", {
                      active: index === 5,
                    }],
                    
                    style: {
                      height: item.height,
                    },
                    "data-sp-9b34df92": "",
                  })}
                />
                <div
                  {...mergeProps({
                    className: "label-day",
                    "data-sp-9b34df92": "",
                  })}
                >
                  {display(item.day)}
                </div>
              </div>
            ))}
          </div>
        </div>
        <div
          {...mergeProps({
            className: "ai",
            "data-sp-9b34df92": "",
          })}
        >
          <div
            {...mergeProps({
              className: "t-nh-tr-ng-d-ch-v-a",
              "data-sp-9b34df92": "",
            })}
          >
            {"Tình trạng dịch vụ AI"}
          </div>
          <div
            {...mergeProps({
              className: "row",
              "data-sp-9b34df92": "",
            })}
          >
            <div
              {...mergeProps({
                className: "ellipse green",
                "data-sp-9b34df92": "",
              })}
            />
            <div
              {...mergeProps({
                className: "nh-gi-xg-boost",
                "data-sp-9b34df92": "",
              })}
            >
              {"Định giá XGBoost"}
            </div>
            <div
              {...mergeProps({
                className: "_82-ms-q-0",
                "data-sp-9b34df92": "",
              })}
            >
              {"Chưa tích hợp"}
            </div>
          </div>
          <div
            {...mergeProps({
              className: "row",
              "data-sp-9b34df92": "",
            })}
          >
            <div
              {...mergeProps({
                className: "ellipse green",
                "data-sp-9b34df92": "",
              })}
            />
            <div
              {...mergeProps({
                className: "nh-n-di-n-nh-tr-ng",
                "data-sp-9b34df92": "",
              })}
            >
              {"Nhận diện ảnh trùng"}
            </div>
            <div
              {...mergeProps({
                className: "_340-ms-q-2",
                "data-sp-9b34df92": "",
              })}
            >
              {"Chưa tích hợp"}
            </div>
          </div>
          <div
            {...mergeProps({
              className: "row",
              "data-sp-9b34df92": "",
            })}
          >
            <div
              {...mergeProps({
                className: "ellipse red",
                "data-sp-9b34df92": "",
              })}
            />
            <div
              {...mergeProps({
                className: "g-i-ti-n-ch-t",
                "data-sp-9b34df92": "",
              })}
            >
              {"Gợi ý tiện ích tự động"}
            </div>
            <div
              {...mergeProps({
                className: "l-i-q-5",
                "data-sp-9b34df92": "",
              })}
            >
              {"Chưa tích hợp"}
            </div>
          </div>
        </div>
      </div>
    </div>,
    <LegacyPager
      {...mergeProps({
        state: ctx.state,
        "data-sp-9b34df92": "",
      })}
    />,
  ]);
});
