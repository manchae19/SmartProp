import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import BusinessPage from "../../shared/components/BusinessPage.jsx";
import { api } from "../auth/api.js";
import { useCollection } from "../../shared/hooks/useCollection.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import Pagination from "../../shared/components/Pagination.jsx";
function useProjectsViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const [archived] = useState(() => createStateStore(false)),
    state = useCollection("/admin/projects", null, () => ({
      archived: archived.getSnapshot()
    })),
    [selected] = useState(() => createStateStore(null)),
    [conflict] = useState(() => createStateStore(false));
  const _stateLatest = useRef(state);
  _stateLatest.current = state;
  useSyncExternalStore(conflict.subscribe, conflict.getSnapshot);
  useSyncExternalStore(selected.subscribe, selected.getSnapshot);
  useSyncExternalStore(archived.subscribe, archived.getSnapshot);
  const blank = () => ({
      name: "",
      developer: "",
      handoverYear: "",
      scale: "",
      address: "",
      latitude: "",
      longitude: "",
      amenities: ""
    }),
    [form] = useState(() => createStateStore(blank()));
  useSyncExternalStore(form.subscribe, form.getSnapshot);
  function fill(m) {
    selected.set(m);
    const p = m?.project;
    form.edit(draftValue => Object.assign(draftValue, p ? {
      ...p,
      developer: p.developer || "",
      scale: p.scale || "",
      address: p.address || "",
      handoverYear: p.handoverYear ?? "",
      latitude: p.latitude ?? "",
      longitude: p.longitude ?? "",
      amenities: (p.amenities || []).join("\n")
    } : blank()));
    conflict.set(false);
  }
  async function edit(m) {
    await _stateLatest.current.run(async () => fill(await api("/admin/projects/" + m.project.id)));
  }
  async function reload() {
    if (!selected.getSnapshot()) return;
    await edit(selected.getSnapshot());
  }
  async function save() {
    await _stateLatest.current.run(async () => {
      if (form.getSnapshot().latitude === "" !== (form.getSnapshot().longitude === "")) throw Error("Cần cả vĩ độ và kinh độ hoặc để trống cả hai.");
      const body = {
        name: form.getSnapshot().name.trim(),
        developer: form.getSnapshot().developer.trim() || null,
        handoverYear: form.getSnapshot().handoverYear === "" ? null : Number(form.getSnapshot().handoverYear),
        scale: form.getSnapshot().scale.trim() || null,
        address: form.getSnapshot().address.trim() || null,
        latitude: form.getSnapshot().latitude === "" ? null : Number(form.getSnapshot().latitude),
        longitude: form.getSnapshot().longitude === "" ? null : Number(form.getSnapshot().longitude),
        amenities: form.getSnapshot().amenities.split("\n").map(s => s.trim()).filter(Boolean)
      };
      try {
        const result = await api("/admin/projects" + (selected.getSnapshot() ? "/" + selected.getSnapshot().project.id + "?expectedVersion=" + selected.getSnapshot().contentVersion : ""), {
          method: selected.getSnapshot() ? "PATCH" : "POST",
          body
        });
        fill(result);
        _stateLatest.current.updateState(draftValue => draftValue["notice"] = "Đã lưu dự án trên server.");
        await _stateLatest.current.load(_stateLatest.current.page);
      } catch (e) {
        if (e.status === 409) conflict.set(true);
        throw e;
      }
    });
  }
  async function archive(m) {
    if (!confirm("Lưu trữ mềm dự án này? Các tin liên quan vẫn được giữ.")) return;
    await _stateLatest.current.run(async () => {
      try {
        await api("/admin/projects/" + m.project.id + "?expectedVersion=" + m.contentVersion, {
          method: "DELETE"
        });
        if (selected.getSnapshot()?.project.id === m.project.id) fill(null);
        await _stateLatest.current.load(_stateLatest.current.page);
      } catch (e) {
        if (e.status === 409) conflict.set(true);
        throw e;
      }
    });
  }
  return {
    ...inputProps,
    archived: archived.getSnapshot(),
    state,
    selected: selected.getSnapshot(),
    conflict: conflict.getSnapshot(),
    form: form.getSnapshot(),
    fill,
    edit,
    reload,
    save,
    archive,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateArchivedValue: archived.set,
    updateForm: form.edit
  };
}
export default React.forwardRef(function ProjectsView(props, ref) {
  const view = useProjectsViewState(props, ref);
  return <><BusinessPage data-ui-view="ProjectsView" title="Quản lý dự án" {...view.rootAttributes}>
      <label>
        <input type="checkbox" checked={Array.isArray(view.archived) ? view.archived.includes("on") : !!view.archived} onChange={event => ($value => {
          view.updateArchivedValue($value);
        })(Array.isArray(view.archived) ? event.target.checked ? [...view.archived, "on"] : view.archived.filter(item => item !== "on") : event.target.checked)} />
        {" Dự án đã lưu trữ"}
      </label>
      <button onClick={$event => {
        view.fill(null);
      }} disabled={view.state.busy}>
        {"Tạo dự án"}
      </button>
      <ResourceState state={view.state} />
      {view.conflict ? <p role="alert">
          {"Phiên bản đã thay đổi. Tải lại dự án để kiểm tra trước khi lưu tiếp. "}
          <button onClick={$event => {
          return view.reload?.($event);
        }} disabled={view.state.busy}>
            {"Tải lại dự án"}
          </button>
        </p> : null}
      {!view.state.busy && !view.state.items.length ? <p>{"Chưa có dự án phù hợp."}</p> : null}
      {((items, render) => typeof items === "number" ? Array.from({
        length: Math.max(0, items)
      }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.state.items, m => <section key={m.project.id}>
          <h2>{(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(m.project.name)}</h2>
          <p>
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(m.project.address)}
            {" · phiên bản "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(m.contentVersion)}
            {" · "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(m.deletedAt ? "Đã lưu trữ" : "Hoạt động")}
          </p>
          <button disabled={view.state.busy} onClick={$event => {
          view.edit(m);
        }}>
            {"Xem / sửa dự án"}
          </button>
          {!m.deletedAt ? <button disabled={view.state.busy} onClick={$event => {
          view.archive(m);
        }}>
              {"Lưu trữ dự án"}
            </button> : null}
        </section>)}
      <Pagination state={view.state} />
      <section>
        <h2>
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selected ? "Chi tiết dự án" : "Dự án mới")}
        </h2>
        <form onSubmit={$event => {
          $event.preventDefault();
          return view.save?.($event);
        }}>
          <fieldset disabled={view.state.busy || !!view.selected?.deletedAt}>
            <label>
              {"Tên dự án "}
              <input required={true} maxLength="255" value={view.form.name ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.name = $value);
              })(event.target.value)} />
            </label>
            <label>
              {"Chủ đầu tư "}
              <input maxLength="255" value={view.form.developer ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.developer = $value);
              })(event.target.value)} />
            </label>
            <label>
              {"Năm bàn giao "}
              <input type="number" min="1900" max="2200" step="1" value={view.form.handoverYear ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.handoverYear = $value);
              })(event.target.value)} />
            </label>
            <label>
              {"Quy mô "}
              <textarea maxLength="4000" value={view.form.scale ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.scale = $value);
              })(event.target.value)} />
            </label>
            <label>
              {"Địa chỉ "}
              <textarea maxLength="4000" value={view.form.address ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.address = $value);
              })(event.target.value)} />
            </label>
            <label>
              {"Vĩ độ đã xác minh "}
              <input type="number" min="-90" max="90" step="any" value={view.form.latitude ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.latitude = $value);
              })(event.target.value)} />
            </label>
            <label>
              {"Kinh độ đã xác minh "}
              <input type="number" min="-179.999999" max="180" step="any" value={view.form.longitude ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.longitude = $value);
              })(event.target.value)} />
            </label>
            <label>
              {"Tiện ích (mỗi dòng một mục, tối đa100) "}
              <textarea value={view.form.amenities ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.amenities = $value);
              })(event.target.value)} />
            </label>
            <button disabled={view.conflict}>
              {"Lưu dự án"}
            </button>
          </fieldset>
        </form>
      </section>
    </BusinessPage></>;
});
