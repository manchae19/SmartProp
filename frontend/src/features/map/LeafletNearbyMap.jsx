import { afterPaint, classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { POI_GROUPS, validPoint, distanceLabel } from "./nearbyExplorer.js";
import { publicMapPoint } from "./locationDisplay.js";
import { compactPrice } from "../property/property.js";
import "./LeafletNearbyMap.css";
function useLeafletNearbyMapState(inputProps, forwardedRef) {
  inputProps = {
    items: (() => [])(),
    places: (() => [])(),
    radius: 1000,
    showProperty: true,
    showRadius: true,
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    items: (() => [])(),
    places: (() => [])(),
    radius: 1000,
    showProperty: true,
    showRadius: true,
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [element] = useState(() => createStateStore(null)),
    [ready] = useState(() => createStateStore(false)),
    [mapError] = useState(() => createStateStore("")),
    [baseLayer] = useState(() => createStateStore("street"));
  useSyncExternalStore(baseLayer.subscribe, baseLayer.getSnapshot);
  useSyncExternalStore(mapError.subscribe, mapError.getSnapshot);
  useSyncExternalStore(ready.subscribe, ready.getSnapshot);
  useSyncExternalStore(element.subscribe, element.getSnapshot);
  const _mapRef = useRef(undefined),
    _routeRef = useRef(null),
    _streetRef = useRef(undefined),
    _propertiesRef = useRef(undefined),
    _poisRef = useRef(undefined),
    _circleRef = useRef(undefined),
    _observerRef = useRef(undefined),
    _tileErrorsRef = useRef(0),
    _lastSelectionRef = useRef("");
  const pins = useRef(new Map()).current,
    poiPins = useRef(new Map()).current;
  function icon(label, color, selected = false) {
    const span = document.createElement("span");
    span.className = "explorer-marker" + (selected ? " is-selected" : "");
    span.style.setProperty("--pin-color", color);
    span.textContent = label;
    return L.divIcon({
      html: span,
      className: "explorer-marker-wrap",
      iconSize: selected ? [42, 48] : [32, 38],
      iconAnchor: selected ? [21, 44] : [16, 35],
      popupAnchor: [0, -34]
    });
  }
  function popup(p, property = false) {
    const box = document.createElement("div");
    box.className = "explorer-popup";
    if (property && p.status === "PUBLISHED") {
      const cover = p.images?.find(i => i.cover) || p.images?.[0];
      const prefix = "/api/v1/properties/" + encodeURIComponent(p.id) + "/images/";
      if (cover?.url?.startsWith(prefix) && cover.url.endsWith("/content")) {
        const photo = document.createElement("img");
        photo.src = cover.url;
        photo.alt = p.title || "Ảnh bất động sản";
        photo.className = "explorer-popup-photo";
        photo.loading = "lazy";
        photo.decoding = "async";
        photo.addEventListener("error", () => photo.remove(), {
          once: true
        });
        box.append(photo);
      }
    }
    const title = document.createElement("strong");
    title.textContent = p.title || p.name;
    box.append(title);
    const text = document.createElement("p");
    text.textContent = property ? compactPrice(p) + (p.areaSqm ? " · " + p.areaSqm + " m²" : "") : distanceLabel(p.distanceMeters) + " · đường chim bay";
    box.append(text);
    if (property) {
      const link = document.createElement("a");
      link.textContent = "Xem chi tiết →";
      link.href = "/listing/" + encodeURIComponent(p.id);
      box.append(link);
    } else if (p.address) {
      const address = document.createElement("small");
      address.textContent = p.address;
      box.append(address);
    }
    return box;
  }
  function draw() {
    if (!_mapRef.current) return;
    const keepPropertyPopup = pins.get(_props.current.selectedId)?.isPopupOpen();
    _mapRef.current.stop();
    _mapRef.current.closePopup();
    _propertiesRef.current.clearLayers();
    _poisRef.current.clearLayers();
    pins.clear();
    poiPins.clear();
    if (_circleRef.current) {
      _circleRef.current.remove();
      _circleRef.current = null;
    }
    const selected = _props.current.items.find(p => p.id === _props.current.selectedId && publicMapPoint(p));
    for (const p of _props.current.items.filter(publicMapPoint)) {
      const active = p.id === _props.current.selectedId;
      const marker = L.marker([Number(p.latitude), Number(p.longitude)], {
        icon: icon("⌂", active ? "#147d80" : "#234b70", active),
        zIndexOffset: active ? 500 : 0,
        title: p.title || "Bất động sản",
        keyboard: true
      });
      marker.bindPopup(popup(p, true), {
        maxWidth: 260
      }).on("click", () => _propsLatest.current.onSelect?.(p.id));
      if (_props.current.showProperty) marker.addTo(_propertiesRef.current);
      pins.set(p.id, marker);
    }
    if (selected) {
      if (_props.current.showRadius) _circleRef.current = L.circle([Number(selected.latitude), Number(selected.longitude)], {
        radius: _props.current.radius,
        color: "#4075f5",
        weight: 2,
        dashArray: "7 6",
        fillColor: "#5795f5",
        fillOpacity: 0.09,
        interactive: false
      }).addTo(_mapRef.current);
      for (const p of _props.current.places.filter(validPoint)) {
        const group = POI_GROUPS.find(g => g.id === p.category) || POI_GROUPS[0];
        const marker = L.marker([Number(p.latitude), Number(p.longitude)], {
          icon: icon(group.icon, group.color, p.id === _props.current.activePoi),
          title: p.name,
          keyboard: true
        }).addTo(_poisRef.current);
        marker.bindPopup(popup(p)).on("click", () => _propsLatest.current.onSelectPoi?.(p.id));
        poiPins.set(p.id, marker);
        if (p.id === _props.current.activePoi) marker.openPopup();
      }
      const key = selected.id + ":" + selected.latitude + ":" + selected.longitude + ":" + _props.current.radius;
      if (_lastSelectionRef.current !== key) {
        _lastSelectionRef.current = key;
        _mapRef.current.fitBounds(L.latLng(Number(selected.latitude), Number(selected.longitude)).toBounds(_props.current.radius * 2), {
          padding: [45, 45],
          maxZoom: 17,
          animate: false
        });
        if (_props.current.showProperty) pins.get(selected.id)?.openPopup();
      }
      if (keepPropertyPopup && _props.current.showProperty) pins.get(selected.id)?.openPopup();
      poiPins.get(_props.current.activePoi)?.openPopup();
    } else if (_props.current.items.some(publicMapPoint)) {
      _lastSelectionRef.current = "";
      _mapRef.current.fitBounds(L.latLngBounds(_props.current.items.filter(publicMapPoint).map(p => [Number(p.latitude), Number(p.longitude)])), {
        padding: [45, 45],
        maxZoom: 14,
        animate: false
      });
    }
  }
  function center() {
    const p = _props.current.items.find(p => p.id === _props.current.selectedId);
    if (p && publicMapPoint(p)) {
      _mapRef.current?.setView([Number(p.latitude), Number(p.longitude)], 16);
      pins.get(p.id)?.openPopup();
    }
  }
  const _watched = (() => [_props.current.items, _props.current.selectedId, _props.current.places, _props.current.radius, _props.current.showProperty, _props.current.showRadius])();
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
    const result = draw(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  const _watched2 = (() => _props.current.activePoi)();
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
    const result = (id => {
      const pin = poiPins.get(id);
      if (pin) {
        _mapRef.current.panTo(pin.getLatLng());
        pin.openPopup();
      }
    })(_watched2, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched2)]);
  useEffect(() => {
    const result = (async () => {
      await afterPaint();
      _mapRef.current = L.map(element.getSnapshot(), {
        zoomControl: false,
        scrollWheelZoom: true,
        wheelDebounceTime: 80,
        wheelPxPerZoomLevel: 100,
        preferCanvas: true,
        zoomAnimation: false,
        fadeAnimation: false,
        markerZoomAnimation: false
      });
      // Initial viewport only; no synthetic property marker is placed here.
      _mapRef.current.setView([16.06, 108.21], 12);
      L.control.zoom({
        position: "topright"
      }).addTo(_mapRef.current);
      L.control.scale({
        imperial: false,
        position: "bottomleft"
      }).addTo(_mapRef.current);
      _streetRef.current = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
      }).addTo(_mapRef.current);
      _streetRef.current.on("tileerror", () => {
        if (++_tileErrorsRef.current >= 4) mapError.set("Chưa tải được bản đồ nền. Kiểm tra kết nối và thử lại.");
      });
      _streetRef.current.on("tileload", () => {
        mapError.set("");
        _tileErrorsRef.current = 0;
      });
      _propertiesRef.current = L.layerGroup().addTo(_mapRef.current);
      _poisRef.current = L.layerGroup().addTo(_mapRef.current);
      _observerRef.current = new ResizeObserver(() => _mapRef.current?.invalidateSize({
        animate: false
      }));
      _observerRef.current.observe(element.getSnapshot());
      ready.set(true);
      draw();
    })();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  useEffect(()=>{
    _routeRef.current?.remove();_routeRef.current=null;
    const route=_props.current.route;
    if(!ready.getSnapshot()||!_mapRef.current||!route?.geometry)return;
    const layer=L.geoJSON({type:'Feature',properties:{},geometry:route.geometry},{renderer:L.svg(),style:{className:'property-road-route',color:'#1769e0',weight:6,opacity:0.9,lineCap:'round'}}).addTo(_mapRef.current);
    layer.bindTooltip('Tuyến đường '+distanceLabel(route.distanceMeters));_routeRef.current=layer;
    const bounds=layer.getBounds();
    if(bounds.isValid())_mapRef.current.fitBounds(bounds,{padding:[35,35],maxZoom:17,animate:false});
    return()=>{layer.remove();if(_routeRef.current===layer)_routeRef.current=null};
  },[ready.getSnapshot(),inputProps.route]);
  function retryTiles() {
    _tileErrorsRef.current = 0;
    mapError.set("");
    _streetRef.current?.redraw();
  }
  useEffect(() => () => (() => {
    _observerRef.current?.disconnect();
    _mapRef.current?.remove();
    _mapRef.current = null;
  })(), []);
  return {
    ...inputProps,
    ready: ready.getSnapshot(),
    mapError: mapError.getSnapshot(),
    baseLayer: baseLayer.getSnapshot(),
    center,
    retryTiles,
    updateElementValue: element.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["items", "selectedId", "places", "radius", "showProperty", "showRadius", "activePoi", "simple", "route", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function LeafletNearbyMap(props, ref) {
  const view = useLeafletNearbyMapState(props, ref);
  return <><div {...view.rootAttributes} className={classNames(["leaflet-explorer-shell", view.rootAttributes.className])}>
      <div ref={view.updateElementValue} className="leaflet-explorer-canvas" aria-label="Bản đồ bất động sản và tiện ích xung quanh" />
      {!view.simple ? <div className="map-layer-choice" aria-label="Lớp bản đồ">
          <button type="button" aria-pressed={view.baseLayer === "street"}>
            {"Bản đồ"}
          </button>
          <button type="button" disabled={true} title="Chưa cấu hình nguồn ảnh vệ tinh có giấy phép">
            {"Vệ tinh"}
          </button>
          <button type="button" disabled={true} title="Chưa cấu hình lớp vệ tinh và nhãn">
            {"Bản đồ lai"}
          </button>
        </div> : null}
      <button className="map-recenter" type="button" onClick={$event => {
        return view.center?.($event);
      }} aria-label="Đưa bản đồ về bất động sản đang chọn" title="Về vị trí tin đang chọn">
        {"⌖"}
      </button>
      {view.mapError ? <div className="map-tile-error" role="alert">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.mapError)}{" "}
          <button type="button" onClick={$event => {
          return view.retryTiles?.($event);
        }}>
            {"Thử lại"}
          </button>
        </div> : null}
      {!view.ready ? <div className="map-boot">
          {"Đang mở bản đồ…"}
        </div> : null}
    </div></>;
});
