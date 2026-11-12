import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { api, session, errorText } from "../auth/api.js";
import "./LegalDocuments.css";
function useLegalDocumentsState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const props = {
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const getOwn = () => String(_props.current.ownerId) === String(session.getSnapshot().user?.id),
    getAdmin = () => session.getSnapshot().user?.role === "ADMIN";
  const [rows] = useState(() => createStateStore([])),
    [busy] = useState(() => createStateStore(false)),
    [error] = useState(() => createStateStore("")),
    [notice] = useState(() => createStateStore("")),
    [selected] = useState(() => createStateStore(null)),
    [file] = useState(() => createStateStore(null)),
    [reason] = useState(() => createStateStore(""));
  useSyncExternalStore(reason.subscribe, reason.getSnapshot);
  useSyncExternalStore(file.subscribe, file.getSnapshot);
  useSyncExternalStore(selected.subscribe, selected.getSnapshot);
  useSyncExternalStore(notice.subscribe, notice.getSnapshot);
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  useSyncExternalStore(rows.subscribe, rows.getSnapshot);
  const _sequenceRef = useRef(0);
  const blank = () => ({
      documentType: "OTHER",
      ownerName: "",
      documentNumber: "",
      issueDate: ""
    }),
    [form] = useState(() => createStateStore(blank()));
  useSyncExternalStore(form.subscribe, form.getSnapshot);
  async function load() {
    const run = ++_sequenceRef.current;
    busy.set(true);
    error.set("");
    rows.set([]);
    try {
      const r = await api("/properties/" + _props.current.propertyId + "/legal-documents?page=0&size=20");
      if (run === _sequenceRef.current) rows.set(r.items || []);
    } catch (e) {
      if (run === _sequenceRef.current) error.set(errorText(e));
    } finally {
      if (run === _sequenceRef.current) busy.set(false);
    }
  }
  useEffect(() => () => (() => _sequenceRef.current++)(), []);
  const _watched = (() => [_props.current.propertyId, session.getSnapshot().user?.id])();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    _initialized.current = true;
    const result = (() => {
      selected.set(null);
      file.set(null);
      form.edit(draftValue => Object.assign(draftValue, blank()));
      load();
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  function edit(doc) {
    selected.set(doc);
    form.edit(draftValue => Object.assign(draftValue, {
      documentType: doc.documentType,
      ownerName: doc.ownerName,
      documentNumber: doc.documentNumber || "",
      issueDate: doc.issueDate || ""
    }));
    notice.set("Sửa metadata sẽ yêu cầu duyệt lại.");
  }
  function choose(e) {
    file.set(e.target.files?.[0] || null);
    e.target.value = "";
    if (file.getSnapshot() && (!["image/jpeg", "image/png", "application/pdf"].includes(file.getSnapshot().type) || file.getSnapshot().size > 10 * 1024 * 1024)) {
      file.set(null);
      error.set("Chỉ JPEG/PNG/PDF, tối đa 10 MiB mỗi tệp.");
    }
  }
  async function run(fn) {
    if (busy.getSnapshot()) return;
    busy.set(true);
    error.set("");
    notice.set("");
    try {
      await fn();
      await load();
    } catch (e) {
      error.set(e.status === 409 ? "Hồ sơ đã thay đổi hoặc vượt quota. Hãy tải lại trước khi thao tác." : errorText(e));
    } finally {
      busy.set(false);
    }
  }
  async function save() {
    if (!getOwn()) return;
    await run(async () => {
      const metadata = {
          documentType: form.getSnapshot().documentType,
          ownerName: form.getSnapshot().ownerName.trim(),
          documentNumber: form.getSnapshot().documentNumber.trim() || null,
          issueDate: form.getSnapshot().issueDate || null
        },
        base = "/properties/" + _props.current.propertyId + "/legal-documents";
      if (selected.getSnapshot()) await api(base + "/" + selected.getSnapshot().id + "?expectedVersion=" + selected.getSnapshot().contentVersion, {
        method: "PATCH",
        body: metadata
      });else {
        if (!file.getSnapshot()) throw Error("Hãy chọn tệp bằng chứng.");
        const data = new FormData();
        data.append("metadata", new Blob([JSON.stringify(metadata)], {
          type: "application/json"
        }), "metadata.json");
        data.append("file", file.getSnapshot());
        await api(base, {
          method: "POST",
          body: data
        });
      }
      selected.set(null);
      file.set(null);
      form.edit(draftValue => Object.assign(draftValue, blank()));
      notice.set("Hồ sơ đã lưu trên server và đang chờ duyệt.");
    });
  }
  async function remove(doc) {
    if (!confirm("Xóa mềm hồ sơ này?")) return;
    await run(() => api("/properties/" + _props.current.propertyId + "/legal-documents/" + doc.id + "?expectedVersion=" + doc.contentVersion, {
      method: "DELETE"
    }));
  }
  async function download(doc) {
    await run(async () => {
      const blob = await api("/properties/" + _props.current.propertyId + "/legal-documents/" + doc.id + "/content", {
        responseType: "blob"
      });
      const url = URL.createObjectURL(blob),
        a = document.createElement("a");
      a.href = url;
      a.download = "legal-document." + (doc.mimeType === "application/pdf" ? "pdf" : doc.mimeType === "image/png" ? "png" : "jpg");
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  }
  async function review(doc, status) {
    if (!reason.getSnapshot().trim()) {
      error.set("Cần lý do duyệt/từ chối.");
      return;
    }
    await run(() => api("/admin/legal-documents/" + doc.id + "/review", {
      method: "POST",
      body: {
        status,
        reason: reason.getSnapshot().trim(),
        expectedVersion: doc.contentVersion
      }
    }));
  }
  return {
    ...inputProps,
    own: getOwn(),
    admin: getAdmin(),
    rows: rows.getSnapshot(),
    busy: busy.getSnapshot(),
    error: error.getSnapshot(),
    notice: notice.getSnapshot(),
    selected: selected.getSnapshot(),
    file: file.getSnapshot(),
    reason: reason.getSnapshot(),
    blank,
    form: form.getSnapshot(),
    load,
    edit,
    choose,
    save,
    remove,
    download,
    review,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["propertyId", "ownerId", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateReasonValue: reason.set,
    updateForm: form.edit,
    updateSelectedValue: selected.set
  };
}
export default React.forwardRef(function LegalDocuments(props, ref) {
  const view = useLegalDocumentsState(props, ref);
  return <><section aria-label="Hồ sơ pháp lý trên server" data-sp-373a33e8="" {...view.rootAttributes} className={classNames(["rounded-[22px] bg-brand-card p-6", view.rootAttributes.className])}>
      <h2 className="text-lg font-semibold" data-sp-373a33e8="">
        {"Hồ sơ pháp lý"}
      </h2>
      <p className="my-3 text-xs" data-sp-373a33e8="">
        {"Tệp riêng tư chỉ chủ tin và quản trị viên được xem. Hồ sơ chỉ được lưu khi server xác nhận; tối đa 10 tệp, JPEG/PNG/PDF ≤10 MiB. Sửa thông tin sẽ đưa hồ sơ về chờ duyệt."}
      </p>
      {view.error ? <p role="alert" className="my-3 text-sm text-[var(--ui-error-text)]" data-sp-373a33e8="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}{" "}
          <button disabled={view.busy} onClick={$event => {
          return view.load?.($event);
        }} className="underline" data-sp-373a33e8="">
            {"Tải lại"}
          </button>
        </p> : null}
      {view.busy ? <p role="status" data-sp-373a33e8="">
          {"Đang xử lý hồ sơ…"}
        </p> : null}
      {view.notice ? <p role="status" data-sp-373a33e8="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.notice)}
        </p> : null}
      {!view.busy && !view.error && !view.rows.length ? <p data-sp-373a33e8="">
          {"Chưa có hồ sơ pháp lý trên server."}
        </p> : null}
      <ul data-sp-373a33e8="">
        {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.rows, doc => <li key={doc.id} className="my-4 rounded-xl border p-4 text-sm" data-sp-373a33e8="">
            <p data-sp-373a33e8="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(doc.documentType)}
              {" · "}
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(doc.status)}
              {" · phiên bản "}
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(doc.contentVersion)}
            </p>
            <p data-sp-373a33e8="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(doc.ownerName)}
              {" · "}
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(doc.documentNumber || "Chưa có số giấy")}
              {" · "}
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(doc.issueDate || "Chưa có ngày cấp")}
            </p>
            {doc.reviewReason ? <p data-sp-373a33e8="">
                {"Kết quả: "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(doc.reviewReason)}
              </p> : null}
            <button disabled={view.busy} onClick={$event => {
            view.download(doc);
          }} className="completion-button" data-sp-373a33e8="">
              {"Tải tệp riêng"}
            </button>
            {view.own ? <React.Fragment>
                <button disabled={view.busy} onClick={$event => {
              view.edit(doc);
            }} className="completion-button" data-sp-373a33e8="">
                  {"Sửa thông tin"}
                </button>
                <button disabled={view.busy} onClick={$event => {
              view.remove(doc);
            }} className="completion-button" data-sp-373a33e8="">
                  {"Xóa hồ sơ"}
                </button>
              </React.Fragment> : null}
            {view.admin && !view.own ? <React.Fragment>
                <button disabled={view.busy} onClick={$event => {
              view.review(doc, "VERIFIED");
            }} className="completion-button" data-sp-373a33e8="">
                  {"Xác minh"}
                </button>
                <button disabled={view.busy} onClick={$event => {
              view.review(doc, "REJECTED");
            }} className="completion-button" data-sp-373a33e8="">
                  {"Từ chối"}
                </button>
              </React.Fragment> : null}
          </li>)}
      </ul>
      {view.admin && !view.own ? <label className="block text-sm" data-sp-373a33e8="">
          {"Lý do kiểm duyệt "}
          <textarea maxLength="4000" className="completion-input w-full" data-sp-373a33e8="" value={view.reason ?? ""} onChange={event => ($value => {
          view.updateReasonValue($value);
        })(event.target.value)} />
        </label> : null}
      {view.admin && view.own ? <p className="text-xs" data-sp-373a33e8="">
          {"Không được tự duyệt giấy tờ của mình."}
        </p> : null}
      {view.own ? <form onSubmit={$event => {
        $event.preventDefault();
        return view.save?.($event);
      }} className="space-y-3" data-sp-373a33e8="">
          <h3 className="font-semibold" data-sp-373a33e8="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selected ? "Chỉnh sửa hồ sơ" : "Thêm hồ sơ riêng tư")}
          </h3>
          <label className="block text-sm" data-sp-373a33e8="">
            {"Loại giấy tờ "}
            <select className="completion-input" data-sp-373a33e8="" value={view.form.documentType ?? ""} onChange={event => ($value => {
            view.updateForm(draftValue => draftValue.documentType = $value);
          })(event.target.value)}>
              <option value="LAND_USE_RIGHT" data-sp-373a33e8="">
                {"Quyền sử dụng đất"}
              </option>
              <option value="HOME_OWNERSHIP" data-sp-373a33e8="">
                {"Sở hữu nhà"}
              </option>
              <option value="SALE_CONTRACT" data-sp-373a33e8="">
                {"Hợp đồng mua bán"}
              </option>
              <option value="OTHER" data-sp-373a33e8="">
                {"Khác"}
              </option>
            </select>
          </label>
          <label className="block text-sm" data-sp-373a33e8="">
            {"Chủ sở hữu trên giấy tờ "}
            <input required={true} maxLength="150" className="completion-input" data-sp-373a33e8="" value={view.form.ownerName ?? ""} onChange={event => ($value => {
            view.updateForm(draftValue => draftValue.ownerName = $value);
          })(event.target.value)} />
          </label>
          <label className="block text-sm" data-sp-373a33e8="">
            {"Số giấy "}
            <input maxLength="150" className="completion-input" data-sp-373a33e8="" value={view.form.documentNumber ?? ""} onChange={event => ($value => {
            view.updateForm(draftValue => draftValue.documentNumber = $value);
          })(event.target.value)} />
          </label>
          <label className="block text-sm" data-sp-373a33e8="">
            {"Ngày cấp "}
            <input type="date" max={new Date().toISOString().slice(0, 10)} className="completion-input" data-sp-373a33e8="" value={view.form.issueDate ?? ""} onChange={event => ($value => {
            view.updateForm(draftValue => draftValue.issueDate = $value);
          })(event.target.value)} />
          </label>
          {!view.selected ? <label className="block text-sm" data-sp-373a33e8="">
              {"Tệp riêng tư "}
              <input type="file" accept="image/jpeg,image/png,application/pdf" onChange={$event => {
            return view.choose?.($event);
          }} className="completion-input" data-sp-373a33e8="" />
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.file?.name)}
            </label> : null}
          <button disabled={view.busy || !view.selected && view.rows.length >= 10} className="completion-button" data-sp-373a33e8="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selected ? "Lưu metadata" : "Tải và lưu hồ sơ")}
          </button>
          {view.selected ? <button type="button" className="completion-button" onClick={$event => {
          view.updateSelectedValue(null);
          Object.assign(view.form, view.blank());
        }} data-sp-373a33e8="">
              {"Hủy chỉnh sửa"}
            </button> : null}
        </form> : null}
    </section></>;
});
