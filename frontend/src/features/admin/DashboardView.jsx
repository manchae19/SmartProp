import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useEffect, useRef } from "react";
import { api, session, errorText } from "../auth/api.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import Pagination from "../../shared/components/Pagination.jsx";
import "./DashboardView.css";
function useDashboardViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const [state] = useState(() => createStateStore({
      busy: false,
      error: "",
      notice: ""
    })),
    [stats] = useState(() => createStateStore({})),
    [chartData] = useState(() => createStateStore([]));
  useSyncExternalStore(chartData.subscribe, chartData.getSnapshot);
  useSyncExternalStore(stats.subscribe, stats.getSnapshot);
  useSyncExternalStore(state.subscribe, state.getSnapshot);
  useEffect(() => {
    const result = (async () => {
      state.edit(draftValue => draftValue["busy"] = true);
      try {
        stats.set(await api("/admin/dashboard"));
      } catch (e) {
        state.edit(draftValue => draftValue["error"] = errorText(e));
      } finally {
        state.edit(draftValue => draftValue["busy"] = false);
      }
    })();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  return {
    ...inputProps,
    state: state.getSnapshot(),
    stats: stats.getSnapshot(),
    chartData: chartData.getSnapshot(),
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function DashboardView(props, ref) {
  const view = useDashboardViewState(props, ref);
  return <><div data-ui-view="DashboardView" data-sp-9b34df92="" {...view.rootAttributes} className={classNames(["main", view.rootAttributes.className])}>
      <ResourceState state={view.state} data-sp-9b34df92="" />
      <div className="stats" data-sp-9b34df92="">
        <div className="stat" data-sp-9b34df92="">
          <div className="tin-ang-hi-n-th" data-sp-9b34df92="">
            {"Tin đang hiển thị"}
          </div>
          <div className="_2-417" data-sp-9b34df92="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.stats.publishedProperties ?? 0)}
          </div>
        </div>
        <div className="stat" data-sp-9b34df92="">
          <div className="ch-duy-t" data-sp-9b34df92="">
            {"Chờ duyệt"}
          </div>
          <div className="_182" data-sp-9b34df92="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.stats.pendingProperties ?? 0)}
          </div>
        </div>
        <div className="stat2" data-sp-9b34df92="">
          <div className="c-nh-b-o-nh-tr-ng" data-sp-9b34df92="">
            {"Báo cáo mới"}
          </div>
          <div className="_9" data-sp-9b34df92="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.stats.openReports ?? 0)}
          </div>
        </div>
        <div className="stat" data-sp-9b34df92="">
          <div className="ng-i-d-ng-ho-t-ng" data-sp-9b34df92="">
            {"Người dùng hoạt động"}
          </div>
          <div className="_1-043" data-sp-9b34df92="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.stats.activeUsers ?? 0)}
          </div>
        </div>
      </div>
      <div className="row-2" data-sp-9b34df92="">
        <div className="chart" data-sp-9b34df92="">
          <div className="tin-ng-m-i-theo-tu" data-sp-9b34df92="">
            {"Tin đăng mới theo tuần · Chưa có dữ liệu"}
          </div>
          <div className="bars" data-sp-9b34df92="">
            {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.chartData, (item, index) => <div key={index} className="col" data-sp-9b34df92="">
                <div className={classNames(["bar-fill", {
                active: index === 5
              }])} style={{
                height: item.height
              }} data-sp-9b34df92="" />
                <div className="label-day" data-sp-9b34df92="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.day)}
                </div>
              </div>)}
          </div>
        </div>
        <div className="ai" data-sp-9b34df92="">
          <div className="t-nh-tr-ng-d-ch-v-a" data-sp-9b34df92="">
            {"Tình trạng dịch vụ AI"}
          </div>
          <div className="row" data-sp-9b34df92="">
            <div className="ellipse green" data-sp-9b34df92="" />
            <div className="nh-gi-xg-boost" data-sp-9b34df92="">
              {"Định giá XGBoost"}
            </div>
            <div className="_82-ms-q-0" data-sp-9b34df92="">
              {"Chưa tích hợp"}
            </div>
          </div>
          <div className="row" data-sp-9b34df92="">
            <div className="ellipse green" data-sp-9b34df92="" />
            <div className="nh-n-di-n-nh-tr-ng" data-sp-9b34df92="">
              {"Nhận diện ảnh trùng"}
            </div>
            <div className="_340-ms-q-2" data-sp-9b34df92="">
              {"Chưa tích hợp"}
            </div>
          </div>
          <div className="row" data-sp-9b34df92="">
            <div className="ellipse red" data-sp-9b34df92="" />
            <div className="g-i-ti-n-ch-t" data-sp-9b34df92="">
              {"Gợi ý tiện ích tự động"}
            </div>
            <div className="l-i-q-5" data-sp-9b34df92="">
              {"Chưa tích hợp"}
            </div>
          </div>
        </div>
      </div>
    </div><Pagination state={view.state} data-sp-9b34df92="" {...view.rootAttributes} /></>;
});
