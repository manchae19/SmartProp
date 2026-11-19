import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import { session } from "../auth/api.js";
import { useList } from "../../shared/hooks/useList.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import Pagination from "../../shared/components/Pagination.jsx";
import { date } from "../property/property.js";
import "./AuditLogsView.css";
function useAuditLogsViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const [currentTab] = useState(() => createStateStore("all")),
    tabs = [{
      id: "all",
      label: "Tất cả"
    }, {
      id: "post",
      label: "Duyệt / Từ chối tin"
    }, {
      id: "account",
      label: "Tài khoản"
    }, {
      id: "report",
      label: "Báo cáo"
    }],
    state = useList("/admin/audit-logs"),
    getLogsList = () => _stateLatest.current.items.map(l => ({
      ...l,
      category: l.entityType === "USER" ? "account" : l.entityType === "REPORT" ? "report" : "post",
      content: l.action + " · " + (l.entityId || l.entityNumericId) + " · " + (l.oldValues?.status || "—") + " → " + (l.newValues?.status || "—"),
      meta: "Người thao tác #" + (l.actorId || "Hệ thống"),
      time: date(l.createdAt),
      typeClass: "type-approve"
    })),
    getFilteredLogs = () => getLogsList().filter(l => currentTab.getSnapshot() === "all" || l.category === currentTab.getSnapshot());
  const _stateLatest = useRef(state);
  _stateLatest.current = state;
  useSyncExternalStore(currentTab.subscribe, currentTab.getSnapshot);
  const handlePostAction = () => {};
  return {
    ...inputProps,
    currentTab: currentTab.getSnapshot(),
    tabs,
    state,
    filteredLogs: getFilteredLogs(),
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateCurrentTabValue: currentTab.set
  };
}
export default React.forwardRef(function AuditLogsView(props, ref) {
  const view = useAuditLogsViewState(props, ref);
  return <><div data-ui-view="AuditLogsView" data-sp-7f256daf="" {...view.rootAttributes} className={classNames(["main", view.rootAttributes.className])}>
      <ResourceState state={view.state} data-sp-7f256daf="" />
      <div className="section-header" data-sp-7f256daf="">
        <div className="header-titles" data-sp-7f256daf="">
          <div className="badge-tag" data-sp-7f256daf="">
            {"QUẢN TRỊ"}
          </div>
          <div className="section-title" data-sp-7f256daf="">
            {"Nhật ký kiểm toán"}
          </div>
          <div className="section-desc" data-sp-7f256daf="">
            {"Lịch sử toàn bộ thao tác của quản trị viên và hệ thống tự động."}
          </div>
        </div>
      </div>
      <div className="stats-container" data-sp-7f256daf="">
        <div className="stat-card" data-sp-7f256daf="">
          <div className="stat-label" data-sp-7f256daf="">
            {"Thao tác hôm nay"}
          </div>
          <div className="stat-value" data-sp-7f256daf="">
            {"—"}
          </div>
        </div>
        <div className="stat-card" data-sp-7f256daf="">
          <div className="stat-label" data-sp-7f256daf="">
            {"Tài khoản bị khoá"}
          </div>
          <div className="stat-value" data-sp-7f256daf="">
            {"—"}
          </div>
        </div>
        <div className="stat-card" data-sp-7f256daf="">
          <div className="stat-label" data-sp-7f256daf="">
            {"Cảnh báo hệ thống"}
          </div>
          <div className="stat-value" data-sp-7f256daf="">
            {"—"}
          </div>
        </div>
      </div>
      <div className="filter-tabs" data-sp-7f256daf="">
        {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.tabs, tab => <button key={tab.id} className={classNames(["tab-btn", {
          active: view.currentTab === tab.id
        }])} onClick={$event => {
          view.updateCurrentTabValue(tab.id);
        }} data-sp-7f256daf="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(tab.label)}
          </button>)}
      </div>
      <div className="logs-section" data-sp-7f256daf="">
        <div className="logs-header" data-sp-7f256daf="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.totalElements)}
          {" hoạt động"}
        </div>
        <div className="logs-list" data-sp-7f256daf="">
          {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.filteredLogs, log => <div key={log.id} className="log-item" data-sp-7f256daf="">
              <div className={classNames(["log-indicator", log.typeClass])} data-sp-7f256daf="" />
              <div className="log-content-wrapper" data-sp-7f256daf="">
                <div className="log-text" data-sp-7f256daf="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(log.content)}
                </div>
                <div className="log-meta" data-sp-7f256daf="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(log.meta)}
                </div>
              </div>
              <div className="log-time" data-sp-7f256daf="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(log.time)}
              </div>
            </div>)}
        </div>
      </div>
    </div><Pagination state={view.state} data-sp-7f256daf="" {...view.rootAttributes} /></>;
});
