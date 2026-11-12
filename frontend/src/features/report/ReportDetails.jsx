import { classNames, inlineStyle } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import { api, errorText } from "../auth/api.js";
import { states, reasons, date, validateFiles } from "../property/property.js";
function useReportDetailsState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [busy] = useState(() => createStateStore(false)),
    [error] = useState(() => createStateStore(""));
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  async function attach(event) {
    const file = event.target.files[0];
    event.target.value = "";
    if (!file) return;
    busy.set(true);
    error.set("");
    try {
      validateFiles([file], true);
      const data = new FormData();
      data.append("file", file);
      _propsLatest.current.onUpdated?.(await api("/reports/" + _props.current.report.id + "/attachments", {
        method: "POST",
        body: data
      }));
    } catch (e) {
      error.set(errorText(e));
    } finally {
      busy.set(false);
    }
  }
  async function download(file) {
    busy.set(true);
    error.set("");
    let url;
    try {
      const blob = await api(file.url.replace(/^\/api\/v1/, ""), {
        responseType: "blob"
      });
      url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "bang-chung-" + file.id + ({
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "application/pdf": ".pdf"
      }[file.mimeType] || "");
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      error.set(errorText(e));
    } finally {
      busy.set(false);
    }
  }
  return {
    ...inputProps,
    states,
    reasons,
    date,
    busy: busy.getSnapshot(),
    error: error.getSnapshot(),
    attach,
    download,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["report", "admin", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function ReportDetails(props, ref) {
  const view = useReportDetailsState(props, ref);
  return <><section {...view.rootAttributes} className={classNames(["sp-panel", view.rootAttributes.className])}>
      <h2>
        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.reasons[view.report.reasonCode] || view.report.reasonCode)}
      </h2>
      <p className="sp-muted">
        {"Mã báo cáo: "}
        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.report.id)}
        {" · "}
        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.date(view.report.createdAt))}
      </p>
      <span className="sp-tag">
        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.states[view.report.status])}
      </span>
      <p className="sp-pre">
        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.report.description)}
      </p>
      {view.report.contactEmail ? <p>
          {"Email liên hệ: "}
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.report.contactEmail)}
        </p> : null}
      {view.report.resolutionNote ? <p className="sp-pre">
          {"Kết quả xử lý: "}
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.report.resolutionNote)}
          {" · "}
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.date(view.report.resolvedAt))}
        </p> : null}
      <h3>{"Bằng chứng"}</h3>
      {view.error ? <p role="alert" className="sp-error">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}
        </p> : null}
      <div className="sp-row">
        {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.report.attachments, (file, index) => <button key={file.id} disabled={view.busy} onClick={$event => {
          view.download(file);
        }}>
            {"Tải tệp "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(index + 1)}
            {" · "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(file.mimeType)}
            {" · "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(Math.ceil(file.byteSize / 1024))}
            {" KB"}
          </button>)}
        {!view.report.attachments.length ? <p className="sp-muted">
            {"Chưa có tệp đính kèm."}
          </p> : null}
      </div>
      {!view.admin && !["RESOLVED", "REJECTED"].includes(view.report.status) ? <label className="sp-label" style={inlineStyle("margin-top:16px")}>
          {"Thêm bằng chứng (tối đa 10 tệp, 10 MB/tệp)"}
          <input type="file" accept="image/jpeg,image/png,application/pdf" disabled={view.busy || view.report.attachments.length >= 10} onChange={$event => {
          return view.attach?.($event);
        }} />
        </label> : null}
      {view.children ?? null}
    </section></>;
});
