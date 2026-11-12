import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { projectPoint, unprojectPoint, visibleTiles } from "./postMap.js";
import { compactPrice } from "../property/property.js";
import { poiLabel, poiColor, poiColorBg, poiColorBorder } from "./nearbyPlaces.js";
import { googlePointUrl } from "./googleMapsLocation.js";
import PoiIcon from "../../shared/components/PoiIcon.jsx";
import "./BrowseTileMap.css";
function useBrowseTileMapState(inputProps, forwardedRef) {
  inputProps = {
    points: (() => [])(),
    poiItems: (() => [])(),
    boundary: null,
    mapLabel: "Bản đồ tin công khai: kéo để di chuyển, phím mũi tên để dịch chuyển, cộng trừ để thu phóng",
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    points: (() => [])(),
    poiItems: (() => [])(),
    boundary: null,
    mapLabel: "Bản đồ tin công khai: kéo để di chuyển, phím mũi tên để dịch chuyển, cộng trừ để thu phóng",
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [host] = useState(() => createStateStore(null)),
    [width] = useState(() => createStateStore(600)),
    [height] = useState(() => createStateStore(440)),
    [zoom] = useState(() => createStateStore(12));
  // Da Nang is a viewport only; every marker below comes from a public property DTO.
  useSyncExternalStore(zoom.subscribe, zoom.getSnapshot);
  useSyncExternalStore(height.subscribe, height.getSnapshot);
  useSyncExternalStore(width.subscribe, width.getSnapshot);
  useSyncExternalStore(host.subscribe, host.getSnapshot);
  const [center] = useState(() => createStateStore({
      latitude: 16.0544,
      longitude: 108.2022
    })),
    [failed] = useState(() => createStateStore(false)),
    [attempt] = useState(() => createStateStore(0));
  useSyncExternalStore(attempt.subscribe, attempt.getSnapshot);
  useSyncExternalStore(failed.subscribe, failed.getSnapshot);
  useSyncExternalStore(center.subscribe, center.getSnapshot);
  const _observerRef = useRef(null);
  const template = import.meta.env?.VITE_OSM_TILE_URL || "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  // Viewport tiles only; retain browser caching, Referer and visible attribution.
  // https://operations.osmfoundation.org/policies/tiles/ (reviewed 2026-10-26)
  const validTemplate = template.startsWith("https://") && ["{z}", "{x}", "{y}"].every(value => template.includes(value));
  const getTiles = () => visibleTiles(center.getSnapshot(), zoom.getSnapshot(), width.getSnapshot(), height.getSnapshot());
  const getBoundaryRings = () => {
    const g = _props.current.boundary;
    return g?.type === "Polygon" ? g.coordinates : g?.type === "MultiPolygon" ? g.coordinates.flat() : [];
  };
  const getBoundaryPath = () => {
    const c = projectPoint(center.getSnapshot().latitude, center.getSnapshot().longitude, zoom.getSnapshot());
    return getBoundaryRings().map(ring => ring.map(([lon, lat], i) => {
      const p = projectPoint(lat, lon, zoom.getSnapshot());
      return `${i ? "L" : "M"}${p.x - c.x + width.getSnapshot() / 2},${p.y - c.y + height.getSnapshot() / 2}`;
    }).join(" ") + "Z").join(" ");
  };
  function tileUrl(tile) {
    return validTemplate ? template.replace("{z}", tile.z).replace("{x}", tile.x).replace("{y}", tile.y) : "";
  }
  function markersFor(points) {
    const c = projectPoint(center.getSnapshot().latitude, center.getSnapshot().longitude, zoom.getSnapshot()),
      world = 256 * 2 ** zoom.getSnapshot();
    return points.map(point => {
      const p = projectPoint(point.latitude, point.longitude, zoom.getSnapshot());
      let dx = p.x - c.x;
      if (dx > world / 2) dx -= world;
      if (dx < -world / 2) dx += world;
      return {
        ...point,
        left: dx + width.getSnapshot() / 2,
        top: p.y - c.y + height.getSnapshot() / 2
      };
    }).filter(point => point.left > -80 && point.left < width.getSnapshot() + 80 && point.top > -30 && point.top < height.getSnapshot() + 30);
  }
  const getMarkers = () => markersFor(_props.current.points);
  const getPoiMarkers = () => markersFor(_props.current.poiItems);
  const getSelectedPoiMarker = () => getPoiMarkers().find(p => p.id === _props.current.selectedPoiId) || null;
  const getIsPopupFlipped = () => getSelectedPoiMarker() && getSelectedPoiMarker().top < 135;
  function formatDistance(meters) {
    if (typeof meters !== "number" || !Number.isFinite(meters) || meters < 0) return "";
    if (meters < 1000) return `${Math.round(meters)} m`;
    return `${(meters / 1000).toFixed(1).replace(".", ",")} km`;
  }
  function fit() {
    const points = [..._props.current.points, ..._props.current.poiItems, ...getBoundaryRings().flat().map(([longitude, latitude]) => ({
      latitude,
      longitude
    }))];
    if (!points.length) return;
    const lats = points.map(point => point.latitude),
      lons = points.map(point => point.longitude);
    const minLat = Math.min(...lats),
      maxLat = Math.max(...lats),
      minLon = Math.min(...lons),
      maxLon = Math.max(...lons);
    center.set({
      latitude: (minLat + maxLat) / 2,
      longitude: (minLon + maxLon) / 2
    });
    let target = 16;
    while (target > 3) {
      const p1 = projectPoint(maxLat, minLon, target),
        p2 = projectPoint(minLat, maxLon, target);
      if (Math.abs(p2.x - p1.x) <= Math.max(120, width.getSnapshot() - 60) && Math.abs(p2.y - p1.y) <= Math.max(120, height.getSnapshot() - 60)) break;
      target--;
    }
    zoom.set(Math.max(3, Math.min(18, target)));
  }
  function focus() {
    const target = _props.current.selectedPoiId ? _props.current.poiItems.find(p => p.id === _props.current.selectedPoiId) : _props.current.points.find(p => p.id === _props.current.selectedId);
    if (target) center.set({
      latitude: target.latitude,
      longitude: target.longitude
    });
  }
  function pan(dx, dy) {
    const c = projectPoint(center.getSnapshot().latitude, center.getSnapshot().longitude, zoom.getSnapshot());
    center.set(unprojectPoint(c.x + dx, c.y + dy, zoom.getSnapshot()));
  }
  function changeZoom(delta) {
    const next = Math.max(3, Math.min(19, zoom.getSnapshot() + delta));
    if (next !== zoom.getSnapshot()) zoom.set(next);
  }
  const _dragRef = useRef(null);
  function pointerDown(event) {
    if (event.target.closest("[data-map-control]")) return;
    _dragRef.current = {
      x: event.clientX,
      y: event.clientY,
      center: {
        ...center.getSnapshot()
      }
    };
    host.getSnapshot()?.setPointerCapture(event.pointerId);
  }
  function pointerMove(event) {
    if (!_dragRef.current) return;
    const p = projectPoint(_dragRef.current.center.latitude, _dragRef.current.center.longitude, zoom.getSnapshot());
    center.set(unprojectPoint(p.x - event.clientX + _dragRef.current.x, p.y - event.clientY + _dragRef.current.y, zoom.getSnapshot()));
  }
  function pointerUp(event) {
    _dragRef.current = null;
    if (host.getSnapshot().hasPointerCapture(event.pointerId)) host.getSnapshot().releasePointerCapture(event.pointerId);
  }
  function keyboard(event) {
    if (event.key === "Escape" && _props.current.selectedPoiId) {
      _propsLatest.current.onSelectPoi?.(null);
      return;
    }
    if (event.target !== host.getSnapshot()) return;
    const moves = {
      ArrowLeft: [-80, 0],
      ArrowRight: [80, 0],
      ArrowUp: [0, -80],
      ArrowDown: [0, 80]
    };
    if (moves[event.key]) {
      event.preventDefault();
      pan(...moves[event.key]);
    } else if (["+", "=", "-"].includes(event.key)) {
      event.preventDefault();
      changeZoom(event.key === "-" ? -1 : 1);
    }
  }
  const _watched = (() => _props.current.points.map(p => `${p.id}:${p.latitude}:${p.longitude}`).join("|"))();
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
      fit();
      focus();
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  const _watched2 = (() => _props.current.poiItems.map(p => `${p.id}:${p.latitude}:${p.longitude}`).join("|"))();
  const _previous2 = useRef(_watched2),
    _initialized2 = useRef(false);
  useEffect(() => {
    const previousValue = _previous2.current;
    _previous2.current = _watched2;
    let dispose;
    if (!_initialized2.current) {
      _initialized2.current = true;
      return;
    }
    const result = (() => {
      fit();
      focus();
    })(_watched2, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched2)]);
  const _watched3 = (() => _props.current.selectedId)();
  const _previous3 = useRef(_watched3),
    _initialized3 = useRef(false);
  useEffect(() => {
    const previousValue = _previous3.current;
    _previous3.current = _watched3;
    let dispose;
    if (!_initialized3.current) {
      _initialized3.current = true;
      return;
    }
    const result = focus(_watched3, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched3)]);
  const _watched4 = (() => _props.current.selectedPoiId)();
  const _previous4 = useRef(_watched4),
    _initialized4 = useRef(false);
  useEffect(() => {
    const previousValue = _previous4.current;
    _previous4.current = _watched4;
    let dispose;
    if (!_initialized4.current) {
      _initialized4.current = true;
      return;
    }
    const result = focus(_watched4, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched4)]);
  const _watched5 = (() => _props.current.boundary)();
  const _previous5 = useRef(_watched5),
    _initialized5 = useRef(false);
  useEffect(() => {
    const previousValue = _previous5.current;
    _previous5.current = _watched5;
    let dispose;
    if (!_initialized5.current) {
      _initialized5.current = true;
      return;
    }
    const result = fit(_watched5, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched5)]);
  useEffect(() => {
    const result = (() => {
      _observerRef.current = new ResizeObserver(entries => {
        const box = entries[0].contentRect;
        width.set(box.width);
        height.set(box.height);
        fit();
        focus();
      });
      _observerRef.current.observe(host.getSnapshot());
      width.set(host.getSnapshot().clientWidth);
      height.set(host.getSnapshot().clientHeight);
      fit();
      focus();
    })();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  useEffect(() => () => (() => _observerRef.current?.disconnect())(), []);
  return {
    ...inputProps,
    compactPrice,
    poiLabel,
    poiColor,
    poiColorBg,
    poiColorBorder,
    googlePointUrl,
    width: width.getSnapshot(),
    height: height.getSnapshot(),
    zoom: zoom.getSnapshot(),
    failed: failed.getSnapshot(),
    attempt: attempt.getSnapshot(),
    validTemplate,
    tiles: getTiles(),
    boundaryPath: getBoundaryPath(),
    tileUrl,
    markers: getMarkers(),
    poiMarkers: getPoiMarkers(),
    selectedPoiMarker: getSelectedPoiMarker(),
    isPopupFlipped: getIsPopupFlipped(),
    formatDistance,
    fit,
    changeZoom,
    drag: _dragRef.current,
    pointerDown,
    pointerMove,
    pointerUp,
    keyboard,
    updateHostValue: host.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["points", "selectedId", "poiItems", "selectedPoiId", "boundary", "mapLabel", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateFailedValue: failed.set,
    updateAttemptValue: attempt.set,
    updateDragValue: value => _dragRef.current = value
  };
}
export default React.forwardRef(function BrowseTileMap(props, ref) {
  const view = useBrowseTileMapState(props, ref);
  return <><div ref={view.updateHostValue} role="region" tabIndex="0" aria-label={view.mapLabel} onPointerDown={$event => {
      return view.pointerDown?.($event);
    }} onPointerMove={$event => {
      return view.pointerMove?.($event);
    }} onPointerUp={$event => {
      return view.pointerUp?.($event);
    }} onPointerCancel={$event => {
      view.updateDragValue(null);
    }} onKeyDown={$event => {
      return view.keyboard?.($event);
    }} data-sp-434e5650="" {...view.rootAttributes} className={classNames(["browse-map", view.rootAttributes.className])}>
      {((items, render) => typeof items === "number" ? Array.from({
        length: Math.max(0, items)
      }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.tiles, tile => <img key={view.attempt + ":" + tile.key} src={view.tileUrl(tile)} alt="" draggable="false" referrerPolicy="strict-origin-when-cross-origin" className="map-tile" style={{
        left: tile.left + "px",
        top: tile.top + "px"
      }} onError={$event => {
        view.updateFailedValue(true);
      }} data-sp-434e5650="" />)}
      {view.boundaryPath ? <svg className="boundary-overlay" viewBox={`0 0 ${view.width} ${view.height}`} aria-hidden="true" data-map-boundary="" data-sp-434e5650="">
          <path d={view.boundaryPath} fill="#365a9220" stroke="#365a92" strokeWidth="2" fillRule="evenodd" data-sp-434e5650="" />
        </svg> : null}
      {((items, render) => typeof items === "number" ? Array.from({
        length: Math.max(0, items)
      }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.markers, point => <button key={point.id} type="button" data-map-control="" className={classNames(["price-pin", {
        selected: view.selectedId === point.id,
        rent: point.transactionType === "RENT"
      }])} style={{
        left: point.left + "px",
        top: point.top + "px"
      }} aria-label={point.title + " · " + view.compactPrice(point)} aria-pressed={view.selectedId === point.id} data-property-id={point.id} onClick={$event => {
        view.onSelect?.(point.id);
      }} data-sp-434e5650="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.compactPrice(point))}
        </button>)}
      {((items, render) => typeof items === "number" ? Array.from({
        length: Math.max(0, items)
      }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.poiMarkers, point => <button key={"poi:" + point.id} type="button" data-map-control="" className={classNames(["poi-pin", {
        selected: view.selectedPoiId === point.id
      }])} style={{
        left: point.left + "px",
        top: point.top + "px",
        backgroundColor: view.poiColor(point.category)
      }} aria-label={point.name + " · " + (point.categoryLabel || view.poiLabel(point.category))} title={point.name + " (" + (point.categoryLabel || view.poiLabel(point.category)) + ")"} aria-pressed={view.selectedPoiId === point.id} data-poi-id={point.id} onClick={$event => {
        view.onSelectPoi?.(view.selectedPoiId === point.id ? null : point.id);
      }} data-sp-434e5650="">
          <PoiIcon category={point.category} className="size-3.5 text-brand-navy" data-sp-434e5650="" />
        </button>)}
      {view.selectedPoiMarker ? <div data-map-control="" className={classNames(["poi-map-popup", {
        flipped: view.isPopupFlipped
      }])} style={{
        left: view.selectedPoiMarker.left + "px",
        top: view.selectedPoiMarker.top + "px"
      }} onPointerDown={$event => {
        $event.stopPropagation();
        undefined;
      }} data-sp-434e5650="">
          <div className="poi-popup-card" data-sp-434e5650="">
            <div className="poi-popup-header" data-sp-434e5650="">
              <span className="poi-popup-badge" style={{
              backgroundColor: view.poiColorBg(view.selectedPoiMarker.category),
              color: view.poiColor(view.selectedPoiMarker.category),
              borderColor: view.poiColorBorder(view.selectedPoiMarker.category)
            }} data-sp-434e5650="">
                <PoiIcon category={view.selectedPoiMarker.category} className="size-3" data-sp-434e5650="" />
                <span data-sp-434e5650="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedPoiMarker.categoryLabel || view.poiLabel(view.selectedPoiMarker.category))}
                </span>
              </span>
              <button type="button" className="poi-popup-close" aria-label="Đóng bảng tiện ích" title="Đóng" onClick={$event => {
              $event.stopPropagation();
              view.onSelectPoi?.(null);
            }} data-sp-434e5650="">
                {"✕"}
              </button>
            </div>
            <div className="poi-popup-title" data-sp-434e5650="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedPoiMarker.name)}
            </div>
            {view.selectedPoiMarker.address ? <p className="poi-popup-source" data-sp-434e5650="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedPoiMarker.address)}
              </p> : null}
            {view.selectedPoiMarker.sourceName === "openstreetmap_overpass" && /^https:\/\/www\.openstreetmap\.org\/(node|way|relation)\/[1-9][0-9]*$/.test(view.selectedPoiMarker.sourceUrl) ? <a href={view.selectedPoiMarker.sourceUrl} target="_blank" rel="noopener noreferrer" className="poi-popup-source" data-sp-434e5650="">
                {"Nguồn: OpenStreetMap ↗"}
              </a> : null}
            <div className="poi-popup-meta" data-sp-434e5650="">
              {view.selectedPoiMarker.distanceMeters ? <span className="poi-popup-dist" data-sp-434e5650="">
                  <svg className="size-3.5 text-[var(--ui-success-text)] inline mr-1 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" data-sp-434e5650="">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" data-sp-434e5650="" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" data-sp-434e5650="" />
                  </svg>
                  {" Cách BĐS ~"}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.formatDistance(view.selectedPoiMarker.distanceMeters))}
                </span> : null}
              {view.googlePointUrl(view.selectedPoiMarker.latitude, view.selectedPoiMarker.longitude) ? <a href={view.googlePointUrl(view.selectedPoiMarker.latitude, view.selectedPoiMarker.longitude)} target="_blank" rel="noopener noreferrer" className="poi-popup-link" data-sp-434e5650="">
                  {"Chỉ đường ↗"}
                </a> : null}
            </div>
          </div>
          <div className="poi-popup-arrow" data-sp-434e5650="" />
        </div> : null}
      <div data-map-control="" className="map-controls" data-sp-434e5650="">
        <button type="button" aria-label="Phóng to bản đồ" disabled={view.zoom >= 19} onClick={$event => {
          view.changeZoom(1);
        }} data-sp-434e5650="">
          {"+"}
        </button>
        <button type="button" aria-label="Thu nhỏ bản đồ" disabled={view.zoom <= 3} onClick={$event => {
          view.changeZoom(-1);
        }} data-sp-434e5650="">
          {"−"}
        </button>
        <button type="button" className="fit" aria-label="Xem tất cả ghim của trang hiện tại" onClick={$event => {
          return view.fit?.($event);
        }} data-sp-434e5650="">
          {"⛶"}
        </button>
      </div>
      {view.failed || !view.validTemplate ? <p data-map-control="" className="tile-error" role="status" data-sp-434e5650="">
          {"Chưa tải đầy đủ nền bản đồ. "}
          <button type="button" onClick={$event => {
          view.updateFailedValue(false);
          view.updateAttemptValue(view.attempt + 1);
        }} data-sp-434e5650="">
            {"Thử lại"}
          </button>
        </p> : null}
      <a data-map-control="" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer" className="map-attribution" data-sp-434e5650="">
        {"© OpenStreetMap contributors"}
      </a>
    </div></>;
});
