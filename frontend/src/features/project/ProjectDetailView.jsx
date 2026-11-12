import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { useRouteState } from "../../app/navigation.jsx";
import { api, errorText } from "../auth/api.js";
import { googlePointUrl } from "../map/googleMapsLocation.js";
function useProjectDetailViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const route = useRouteState(),
    [project] = useState(() => createStateStore(null)),
    [busy] = useState(() => createStateStore(false)),
    [error] = useState(() => createStateStore(""));
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  useSyncExternalStore(project.subscribe, project.getSnapshot);
  const _sequenceRef = useRef(0);
  async function load() {
    const run = ++_sequenceRef.current;
    busy.set(true);
    error.set("");
    project.set(null);
    try {
      const result = await api("/projects/" + encodeURIComponent(String(_routeLatest.current.params.id)), {
        authenticated: false
      });
      if (run === _sequenceRef.current) project.set(result);
    } catch (failure) {
      if (run === _sequenceRef.current) error.set(failure.status === 404 ? "Dự án không tồn tại hoặc chưa được công bố." : errorText(failure));
    } finally {
      if (run === _sequenceRef.current) busy.set(false);
    }
  }
  const _watched = (() => _routeLatest.current.params.id)();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    _initialized.current = true;
    const result = load(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  useEffect(() => () => (() => _sequenceRef.current++)(), []);
  const getMapLink = () => project.getSnapshot() ? googlePointUrl(project.getSnapshot().latitude, project.getSnapshot().longitude) : "";
  return {
    ...inputProps,
    project: project.getSnapshot(),
    busy: busy.getSnapshot(),
    error: error.getSnapshot(),
    load,
    mapLink: getMapLink(),
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function ProjectDetailView(props, ref) {
  const view = useProjectDetailViewState(props, ref);
  return <><div data-ui-view="ProjectDetailView" data-project-detail="" {...view.rootAttributes} className={classNames(["sp-container py-10 sm:py-14", view.rootAttributes.className])}>
      <SiteLink to="/projects" className="text-sm font-semibold text-brand-accent">
        {"← Danh sách dự án"}
      </SiteLink>
      {view.busy ? <p role="status" className="mt-8 text-sm text-brand-muted">
          {"Đang tải dự án…"}
        </p> : view.error ? <div role="alert" className="mt-8 rounded-panel border border-[var(--ui-error-border)] bg-[var(--ui-error-bg)] p-6 text-sm text-[var(--ui-error-text)]">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}
          <button type="button" className="ml-3 font-semibold underline" onClick={$event => {
          return view.load?.($event);
        }}>
            {"Thử lại"}
          </button>
        </div> : view.project ? <article className="mt-8">
          <p className="text-xs font-semibold tracking-[.2em] text-brand-accent">
            {"DỮ LIỆU TỪ SMARTPROP"}
          </p>
          <h1 className="mt-3 max-w-4xl break-words text-3xl font-semibold tracking-tight sm:text-5xl">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.project.name)}
          </h1>
          <p className="mt-4 text-sm leading-7 text-brand-muted">
            {"Chưa có ảnh dự án."}
          </p>
          <dl className="mt-8 grid gap-5 rounded-panel border border-brand-line bg-brand-card p-6 sm:grid-cols-2 sm:p-8">
            {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))({
            developer: "Chủ đầu tư",
            address: "Địa chỉ",
            scale: "Quy mô",
            handoverYear: "Năm bàn giao"
          }, (label, key) => <div key={key} className="min-w-0">
                  <dt className="text-xs text-brand-muted">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(label)}
                  </dt>
                  <dd className="mt-2 break-words text-base font-medium">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.project[key] || "Chưa cung cấp")}
                  </dd>
                </div>)}
            <div className="sm:col-span-2">
              <dt className="text-xs text-brand-muted">
                {"Tiện ích theo hồ sơ dự án"}
              </dt>
              <dd className="mt-2 text-sm leading-7">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.project.amenities?.join(", ") || "Chưa cung cấp")}
              </dd>
            </div>
          </dl>
          {view.mapLink ? <a href={view.mapLink} target="_blank" rel="noopener noreferrer" className="sp-button sp-button-secondary mt-6">
              {"Mở tọa độ dự án trên Google Maps ↗"}
            </a> : null}
        </article> : null}
    </div></>;
});
