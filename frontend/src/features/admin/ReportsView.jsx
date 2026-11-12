import { classNames, chainHandlers } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import { useAppNavigation } from "../../app/navigation.jsx";
import { api, session } from "../auth/api.js";
import { useList } from "../../shared/hooks/useList.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import Pagination from "../../shared/components/Pagination.jsx";
import { reasons as reasonLabels } from "../property/property.js";
import { date } from "../property/property.js";
import ReportDetails from "../report/ReportDetails.jsx";
import "./ReportsView.css";
function useReportsViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const [statusFilter] = useState(() => createStateStore("OPEN"));
  useSyncExternalStore(statusFilter.subscribe, statusFilter.getSnapshot);
  const router = useAppNavigation(),
    state = useList("/admin/reports", () => ({
      status: statusFilter.getSnapshot() || undefined
    })),
    [selected] = useState(() => createStateStore(null)),
    [note] = useState(() => createStateStore("")),
    getReportsList = () => _stateLatest.current.items.map(r => ({
      ...r,
      title: "Tin " + r.propertyId,
      reason: reasonLabels[r.reasonCode] || r.reasonCode,
      reporter: "Người dùng #" + r.reporterId,
      time: date(r.createdAt)
    }));
  const _stateLatest = useRef(state);
  _stateLatest.current = state;
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  useSyncExternalStore(note.subscribe, note.getSnapshot);
  useSyncExternalStore(selected.subscribe, selected.getSnapshot);
  const viewPost = id => {
    selected.set(_stateLatest.current.items.find(r => r.id === id));
    note.set("");
  };
  async function resolve(id, status) {
    if (!selected.getSnapshot() || selected.getSnapshot().id !== id) {
      viewPost(id);
      return;
    }
    if (!note.getSnapshot().trim()) {
      _stateLatest.current.updateState(draftValue => draftValue["error"] = "Nhập ghi chú xử lý.");
      return;
    }
    await _stateLatest.current.run(async () => {
      await api("/admin/reports/" + id + "/status", {
        method: "PATCH",
        body: {
          status,
          note: note.getSnapshot()
        }
      });
      selected.set(null);
      await _stateLatest.current.load(_stateLatest.current.page);
    });
  }
  const removePost = id => resolve(id, "RESOLVED"),
    skipReport = id => resolve(id, "REJECTED");
  return {
    ...inputProps,
    statusFilter: statusFilter.getSnapshot(),
    state,
    selected: selected.getSnapshot(),
    note: note.getSnapshot(),
    reportsList: getReportsList(),
    viewPost,
    removePost,
    skipReport,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateSelectedValue: selected.set,
    updateStatusFilterValue: statusFilter.set,
    updateNoteValue: note.set
  };
}
export default React.forwardRef(function ReportsView(props, ref) {
  const view = useReportsViewState(props, ref);
  return <><div data-ui-view="ReportsView" data-sp-fd30d3f5="" {...view.rootAttributes} className={classNames(["main", view.rootAttributes.className])}>
      <ResourceState state={view.state} data-sp-fd30d3f5="" />
      <div className="section-title" data-sp-fd30d3f5="">
        <div className="title-text" data-sp-fd30d3f5="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.totalElements)}
          {" báo cáo"}
        </div>
      </div>
      <select className="bg-brand-card border rounded-lg p-2 text-sm" data-sp-fd30d3f5="" value={view.statusFilter ?? ""} onChange={chainHandlers($event => {
        view.updateSelectedValue(null);
        view.state.load(0);
      }, event => ($value => {
        view.updateStatusFilterValue($value);
      })(event.target.value))}>
        <option value="OPEN" data-sp-fd30d3f5="">
          {"Mới tiếp nhận"}
        </option>
        <option value="PROCESSING" data-sp-fd30d3f5="">
          {"Đang xử lý"}
        </option>
        <option value="RESOLVED" data-sp-fd30d3f5="">
          {"Đã giải quyết"}
        </option>
        <option value="REJECTED" data-sp-fd30d3f5="">
          {"Đã từ chối"}
        </option>
        <option value="" data-sp-fd30d3f5="">
          {"Tất cả"}
        </option>
      </select>
      <div className="reports-list" data-sp-fd30d3f5="">
        {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.reportsList, report => <div key={report.id} className="report-card" data-report-id={report.id} data-sp-fd30d3f5="">
            <div className="report-info" data-sp-fd30d3f5="">
              <div className="report-title" data-sp-fd30d3f5="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(report.title)}
              </div>
              <div className="report-reason-badge" data-sp-fd30d3f5="">
                <span className="reason-text" data-sp-fd30d3f5="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(report.reason)}
                </span>
              </div>
              <div className="report-meta" data-sp-fd30d3f5="">
                {" Báo cáo bởi "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(report.reporter)}
                {" · "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(report.time)}
              </div>
            </div>
            <div className="report-actions" data-sp-fd30d3f5="">
              <button className="btn-view" onClick={$event => {
              view.viewPost(report.id);
            }} data-sp-fd30d3f5="">
                {" Xem báo cáo › "}
              </button>
              {!["RESOLVED", "REJECTED"].includes(report.status) ? <button className="btn-remove" onClick={$event => {
              view.removePost(report.id);
            }} data-sp-fd30d3f5="">
                  {" Giải quyết "}
                </button> : null}
              {!["RESOLVED", "REJECTED"].includes(report.status) ? <button className="btn-skip" onClick={$event => {
              view.skipReport(report.id);
            }} data-sp-fd30d3f5="">
                  {" Bỏ qua "}
                </button> : null}
            </div>
          </div>)}
      </div>
    </div>{view.selected ? <section className="rounded-2xl bg-brand-card p-6" data-sp-fd30d3f5="">
        <ReportDetails report={view.selected} admin={true} data-sp-fd30d3f5="" />
        <label className="block text-xs" data-sp-fd30d3f5="">
          {"Ghi chú xử lý"}
          <textarea maxLength="4000" className="w-full border rounded-xl p-3 my-3" data-sp-fd30d3f5="" value={view.note ?? ""} onChange={event => ($value => {
          view.updateNoteValue($value);
        })(event.target.value)} />
        </label>
        {!["RESOLVED", "REJECTED"].includes(view.selected.status) ? <button onClick={$event => {
        view.removePost(view.selected.id);
      }} className="bg-[var(--ui-soft)] text-brand-navy rounded-full px-5 py-2 text-xs" data-sp-fd30d3f5="">
            {"Giải quyết"}
          </button> : null}
        {!["RESOLVED", "REJECTED"].includes(view.selected.status) ? <button onClick={$event => {
        view.skipReport(view.selected.id);
      }} className="border rounded-full px-5 py-2 text-xs ml-2" data-sp-fd30d3f5="">
            {"Từ chối"}
          </button> : null}
      </section> : null}<Pagination state={view.state} data-sp-fd30d3f5="" {...view.rootAttributes} /></>;
});
