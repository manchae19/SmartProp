import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { validCoordinates } from "../property/postForm.js";
import { projectPoint, unprojectPoint, visibleTiles } from "./postMap.js";
import { projectPreviewRegion } from "./locationPreview.js";
import "./ManualLocationMap.css";
function useManualLocationMapState(inputProps, forwardedRef) {
  inputProps = {
    latitude: "",
    longitude: "",
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    latitude: "",
    longitude: "",
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  // This initial center is only a viewport. No point is selected until a deliberate action.
  const [center] = useState(() => createStateStore(validCoordinates(_props.current.latitude, _props.current.longitude) ? {
    latitude: Number(_props.current.latitude),
    longitude: Number(_props.current.longitude)
  } : {
    latitude: 16.0544,
    longitude: 108.2022
  }));
  useSyncExternalStore(center.subscribe, center.getSnapshot);
  const previewZoom = () => _props.current.preview ? _props.current.precision === "APPROXIMATE_AREA" ? 13 : _props.current.precision === "APPROXIMATE_STREET" ? 15 : 17 : 17;
  const [zoom] = useState(() => createStateStore(validCoordinates(_props.current.latitude, _props.current.longitude) ? previewZoom() : 13)),
    [host] = useState(() => createStateStore(null)),
    [width] = useState(() => createStateStore(600)),
    [failed] = useState(() => createStateStore(false)),
    [attempt] = useState(() => createStateStore(0)),
    [hint] = useState(() => createStateStore("")),
    [draggingPin] = useState(() => createStateStore(null));
  useSyncExternalStore(draggingPin.subscribe, draggingPin.getSnapshot);
  useSyncExternalStore(hint.subscribe, hint.getSnapshot);
  useSyncExternalStore(attempt.subscribe, attempt.getSnapshot);
  useSyncExternalStore(failed.subscribe, failed.getSnapshot);
  useSyncExternalStore(width.subscribe, width.getSnapshot);
  useSyncExternalStore(host.subscribe, host.getSnapshot);
  useSyncExternalStore(zoom.subscribe, zoom.getSnapshot);
  const height = 320,
    getTiles = () => visibleTiles(center.getSnapshot(), zoom.getSnapshot(), width.getSnapshot(), height);
  const getAreaOverlay = () => _props.current.preview ? projectPreviewRegion(_props.current.previewRegion, center.getSnapshot(), zoom.getSnapshot(), width.getSnapshot(), height) : null;
  const template = import.meta.env?.VITE_OSM_TILE_URL || "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  const validTemplate = template.startsWith("https://") && ["{z}", "{x}", "{y}"].every(v => template.includes(v));
  function tileUrl(tile) {
    return validTemplate ? template.replace("{z}", tile.z).replace("{x}", tile.x).replace("{y}", tile.y) : "";
  }
  const getMarker = () => {
    const point = draggingPin.getSnapshot() || {
      latitude: _props.current.latitude,
      longitude: _props.current.longitude
    };
    if (!validCoordinates(point.latitude, point.longitude)) return null;
    const p = projectPoint(Number(point.latitude), Number(point.longitude), zoom.getSnapshot()),
      c = projectPoint(center.getSnapshot().latitude, center.getSnapshot().longitude, zoom.getSnapshot());
    return {
      left: p.x - c.x + width.getSnapshot() / 2,
      top: p.y - c.y + height / 2
    };
  };
  const _watched = (() => [_props.current.latitude, _props.current.longitude, _props.current.preview, _props.current.precision])();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    if (!_initialized.current) {
      _initialized.current = true;
      return;
    }
    const result = (() => {
      if (validCoordinates(_props.current.latitude, _props.current.longitude)) {
        center.set({
          latitude: Number(_props.current.latitude),
          longitude: Number(_props.current.longitude)
        });
        zoom.set(previewZoom());
      }
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  const _observerRef = useRef(undefined),
    _dragRef = useRef(undefined);
  function pan(dx, dy) {
    const c = projectPoint(center.getSnapshot().latitude, center.getSnapshot().longitude, zoom.getSnapshot());
    center.set(unprojectPoint(c.x + dx, c.y + dy, zoom.getSnapshot()));
  }
  function changeZoom(delta) {
    if (!_props.current.disabled) zoom.set(Math.max(3, Math.min(19, zoom.getSnapshot() + delta)));
  }
  function selectAt(x, y) {
    if (_props.current.disabled) return;
    const c = projectPoint(center.getSnapshot().latitude, center.getSnapshot().longitude, zoom.getSnapshot()),
      wx = c.x + x - width.getSnapshot() / 2,
      wy = c.y + y - height / 2,
      n = 2 ** zoom.getSnapshot(),
      tx = (Math.floor(wx / 256) % n + n) % n,
      ty = Math.floor(wy / 256),
      key = zoom.getSnapshot() + "/" + tx + "/" + ty;
    const tile = [...(host.getSnapshot()?.querySelectorAll("[data-tile-key]") || [])].find(image => image.dataset.tileKey === key);
    if (!tile?.complete || !tile.naturalWidth) {
      hint.set("Phần bản đồ này chưa tải được. Hãy kiểm tra kết nối và thử lại trước khi chọn ghim.");
      return;
    }
    const point = unprojectPoint(wx, wy, zoom.getSnapshot());
    if (!validCoordinates(point.latitude, point.longitude)) return;
    hint.set("Đã đặt ghim. Kiểm tra địa chỉ rồi bấm Xác nhận vị trí.");
    _propsLatest.current.onSelect?.(point);
  }
  function pointerDown(event) {
    if (_props.current.disabled || event.button !== 0 || event.target.closest("[data-map-control]")) return;
    const box = host.getSnapshot().getBoundingClientRect();
    _dragRef.current = {
      x: event.clientX,
      y: event.clientY,
      box,
      center: {
        ...center.getSnapshot()
      },
      pin: !!event.target.closest("[data-location-pin]")
    };
    host.getSnapshot().setPointerCapture(event.pointerId);
  }
  function pointerMove(event) {
    if (!_dragRef.current) return;
    const p = projectPoint(_dragRef.current.center.latitude, _dragRef.current.center.longitude, zoom.getSnapshot());
    if (_dragRef.current.pin) {
      draggingPin.set(unprojectPoint(p.x + event.clientX - _dragRef.current.box.left - width.getSnapshot() / 2, p.y + event.clientY - _dragRef.current.box.top - height / 2, zoom.getSnapshot()));
      return;
    }
    center.set(unprojectPoint(p.x - (event.clientX - _dragRef.current.x), p.y - (event.clientY - _dragRef.current.y), zoom.getSnapshot()));
  }
  function pointerUp(event) {
    if (!_dragRef.current) return;
    const start = _dragRef.current;
    _dragRef.current = null;
    draggingPin.set(null);
    if (start.pin || Math.hypot(event.clientX - start.x, event.clientY - start.y) < 5) selectAt(event.clientX - start.box.left, event.clientY - start.box.top);
    try {
      host.getSnapshot().releasePointerCapture(event.pointerId);
    } catch {}
  }
  function cancelDrag() {
    _dragRef.current = null;
    draggingPin.set(null);
  }
  function keyboard(event) {
    if (_props.current.disabled) return;
    const moves = {
      ArrowLeft: [-64, 0],
      ArrowRight: [64, 0],
      ArrowUp: [0, -64],
      ArrowDown: [0, 64]
    };
    if (moves[event.key]) {
      event.preventDefault();
      pan(...moves[event.key]);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectAt(width.getSnapshot() / 2, height / 2);
    } else if (event.key === "+" || event.key === "=") {
      event.preventDefault();
      changeZoom(1);
    } else if (event.key === "-") {
      event.preventDefault();
      changeZoom(-1);
    }
  }
  function retry() {
    failed.set(false);
    hint.set("");
    attempt.edit(draftValue => draftValue++);
  }
  useEffect(() => {
    const result = (() => {
      _observerRef.current = new ResizeObserver(entries => width.set(Math.max(1, entries[0].contentRect.width)));
      _observerRef.current.observe(host.getSnapshot());
    })();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  useEffect(() => () => (() => _observerRef.current?.disconnect())(), []);
  return {
    ...inputProps,
    zoom: zoom.getSnapshot(),
    width: width.getSnapshot(),
    failed: failed.getSnapshot(),
    attempt: attempt.getSnapshot(),
    hint: hint.getSnapshot(),
    height,
    tiles: getTiles(),
    areaOverlay: getAreaOverlay(),
    validTemplate,
    tileUrl,
    marker: getMarker(),
    changeZoom,
    selectAt,
    pointerDown,
    pointerMove,
    pointerUp,
    cancelDrag,
    keyboard,
    retry,
    updateHostValue: host.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["latitude", "longitude", "disabled", "preview", "precision", "previewRegion", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateFailedValue: failed.set
  };
}
export default React.forwardRef(function ManualLocationMap(props, ref) {
  const view = useManualLocationMapState(props, ref);
  return <><div data-sp-6f96df0e="" {...view.rootAttributes} className={classNames(["manual-map-wrap", view.rootAttributes.className])}>
      <p id="manual-map-help" className="map-help" data-sp-6f96df0e="">
        {"Bấm bản đồ để đặt ghim, kéo để di chuyển bản đồ hoặc kéo ghim để chỉnh. Dùng phím mũi tên rồi Enter để chọn điểm giữa bản đồ."}
      </p>
      <div ref={view.updateHostValue} className="manual-map" tabIndex="0" role="region" aria-label="Bản đồ chọn vị trí bất động sản" aria-describedby="manual-map-help" aria-disabled={view.disabled || undefined} onPointerDown={$event => {
        return view.pointerDown?.($event);
      }} onPointerMove={$event => {
        return view.pointerMove?.($event);
      }} onPointerUp={$event => {
        return view.pointerUp?.($event);
      }} onPointerCancel={$event => {
        return view.cancelDrag?.($event);
      }} onKeyDown={$event => {
        return view.keyboard?.($event);
      }} data-sp-6f96df0e="">
        {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.tiles, tile => <img key={view.attempt + ":" + tile.key} src={view.tileUrl(tile)} alt="" draggable="false" referrerPolicy="strict-origin-when-cross-origin" className="map-tile" data-tile-key={tile.key} style={{
          left: tile.left + "px",
          top: tile.top + "px"
        }} onError={$event => {
          view.updateFailedValue(true);
        }} data-sp-6f96df0e="" />)}
        {view.areaOverlay ? <svg className="location-area" viewBox={"0 0 " + view.width + " " + view.height} role="img" aria-label="Vùng minh họa quanh ghim đề xuất" data-location-area="illustrative" data-sp-6f96df0e="">
            <title data-sp-6f96df0e="">
              {"Vùng minh họa, không phải bán kính sai số đã xác minh"}
            </title>
            <circle cx={view.areaOverlay.cx} cy={view.areaOverlay.cy} r={view.areaOverlay.radius} data-sp-6f96df0e="" />
          </svg> : null}
        <span className="map-crosshair" aria-hidden="true" data-sp-6f96df0e="">
          {"+"}
        </span>
        {view.marker ? <span data-location-pin="" className={classNames(["location-pin", {
          "preview-pin": view.preview
        }])} style={{
          left: view.marker.left + "px",
          top: view.marker.top + "px"
        }} role="img" aria-label={view.preview ? "Ghim đề xuất chưa xác nhận" : "Ghim vị trí đã chọn"} data-sp-6f96df0e="">
            {"●"}
          </span> : null}
        <div data-map-control="" className="map-controls" onPointerDown={$event => {
          $event.stopPropagation();
          undefined;
        }} onKeyDown={$event => {
          $event.stopPropagation();
          undefined;
        }} data-sp-6f96df0e="">
          <button type="button" disabled={view.disabled || view.zoom >= 19} aria-label="Phóng to bản đồ" onClick={$event => {
            view.changeZoom(1);
          }} data-sp-6f96df0e="">
            {"+"}
          </button>
          <button type="button" disabled={view.disabled || view.zoom <= 3} aria-label="Thu nhỏ bản đồ" onClick={$event => {
            view.changeZoom(-1);
          }} data-sp-6f96df0e="">
            {"−"}
          </button>
        </div>
        <button type="button" data-map-control="" className="choose-center" disabled={view.disabled} onPointerDown={$event => {
          $event.stopPropagation();
          undefined;
        }} onKeyDown={$event => {
          $event.stopPropagation();
          undefined;
        }} onClick={$event => {
          view.selectAt(view.width / 2, view.height / 2);
        }} data-sp-6f96df0e="">
          {"Đặt ghim ở dấu +"}
        </button>
        <a data-map-control="" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer" className="map-attribution" onPointerDown={$event => {
          $event.stopPropagation();
          undefined;
        }} onKeyDown={$event => {
          $event.stopPropagation();
          undefined;
        }} data-sp-6f96df0e="">
          {"© OpenStreetMap contributors"}
        </a>
      </div>
      {view.areaOverlay ? <p className="area-explanation" data-sp-6f96df0e="">
          <span aria-hidden="true" className="area-swatch" data-sp-6f96df0e="" />
          <span data-sp-6f96df0e="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.previewRegion.label)}
          </span>
        </p> : null}
      {view.failed || !view.validTemplate ? <p role="status" className="map-error" data-sp-6f96df0e="">
          {"Chưa tải đầy đủ bản đồ. Kiểm tra mạng rồi "}
          <button type="button" className="underline" onClick={$event => {
          return view.retry?.($event);
        }} data-sp-6f96df0e="">
            {"thử lại"}
          </button>
          {". Chỉ chọn được ghim ở phần bản đồ đã tải."}
        </p> : null}
      {view.hint ? <p role="status" className="map-help" data-sp-6f96df0e="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.hint)}
        </p> : null}
    </div></>;
});
