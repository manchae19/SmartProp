import { afterPaint, classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { loadGoogleMaps, googleMapId, hasGoogleMapsKey } from "./googleMaps.js";
import { coordinatesFromPlace } from "./googleMapsLocation.js";
import { validCoordinates } from "../property/postForm.js";
import ManualLocationMap from "./ManualLocationMap.jsx";
import AutomaticLocationSearch from "./AutomaticLocationSearch.jsx";
import { candidateCanBeConfirmed, accuracyLabel } from "./geocoding.js";
import { locationPreviewRegion } from "./locationPreview.js";
import "./GooglePropertyLocation.css";
function useGooglePropertyLocationState(inputProps, forwardedRef) {
  inputProps = {
    address: "",
    city: "",
    district: "",
    ward: "",
    latitude: "",
    longitude: "",
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    address: "",
    city: "",
    district: "",
    ward: "",
    latitude: "",
    longitude: "",
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [searchHost] = useState(() => createStateStore(null)),
    [mapHost] = useState(() => createStateStore(null)),
    [ready] = useState(() => createStateStore(false)),
    [loading] = useState(() => createStateStore(false)),
    [selecting] = useState(() => createStateStore(false)),
    [message] = useState(() => createStateStore("")),
    [suggestion] = useState(() => createStateStore(""));
  useSyncExternalStore(suggestion.subscribe, suggestion.getSnapshot);
  useSyncExternalStore(message.subscribe, message.getSnapshot);
  useSyncExternalStore(selecting.subscribe, selecting.getSnapshot);
  useSyncExternalStore(loading.subscribe, loading.getSnapshot);
  useSyncExternalStore(ready.subscribe, ready.getSnapshot);
  useSyncExternalStore(mapHost.subscribe, mapHost.getSnapshot);
  useSyncExternalStore(searchHost.subscribe, searchHost.getSnapshot);
  const [automaticSearch] = useState(() => createStateStore(null)),
    [automaticCandidate] = useState(() => createStateStore(null)),
    [verifiedExact] = useState(() => createStateStore(false)),
    [publicExact] = useState(() => createStateStore(false));
  useSyncExternalStore(publicExact.subscribe, publicExact.getSnapshot);
  useSyncExternalStore(verifiedExact.subscribe, verifiedExact.getSnapshot);
  useSyncExternalStore(automaticCandidate.subscribe, automaticCandidate.getSnapshot);
  useSyncExternalStore(automaticSearch.subscribe, automaticSearch.getSnapshot);
  const getOsmCandidate = () => automaticCandidate.getSnapshot()?.provider === "GEOAPIFY" ? automaticCandidate.getSnapshot() : null;
  const getPreviewRegion = () => locationPreviewRegion(getOsmCandidate());
  function clearAutomatic() {
    automaticCandidate.set(null);
    verifiedExact.set(false);
    publicExact.set(false);
  }
  function previewAutomatic(candidate) {
    _revisionRef.current++;
    selecting.set(false);
    suggestion.set("");
    automaticCandidate.set(candidate);
    verifiedExact.set(false);
    publicExact.set(false);
    _propsLatest.current.onInvalidate?.();
    if (candidate.provider === "GOOGLE") {
      if (!ready.getSnapshot()) {
        message.set("Cần cấu hình bản đồ Google để xem gợi ý Google. Kết quả này không được hiển thị trên OSM hoặc lưu vào tin.");
        return;
      }
      _markerRef.current.position = {
        lat: candidate.latitude,
        lng: candidate.longitude
      };
      _markerRef.current.map = _mapRef.current;
      _mapRef.current.setCenter(_markerRef.current.position);
      _mapRef.current.setZoom(candidate.locationLevel === "APPROXIMATE" ? 14 : 18);
      message.set("Gợi ý Google chỉ để tham khảo trên Google; không sao chép vào tin. Chọn ghim thủ công độc lập nếu bạn biết vị trí thực tế.");
    } else message.set(candidateCanBeConfirmed(candidate) ? "Gợi ý cấp tòa nhà. Chỉ xác nhận nếu bạn đã đối chiếu đúng bất động sản; chưa xác minh căn hộ hoặc ranh giới." : "Kết quả chỉ gần đúng hoặc chưa khớp số nhà. Bấm bản đồ để đặt lại ghim đúng bất động sản.");
  }
  const getCanConfirm = () => !_props.current.disabled && !!String(_props.current.address).trim() && publicExact.getSnapshot() && (automaticCandidate.getSnapshot() ? candidateCanBeConfirmed(automaticCandidate.getSnapshot()) && verifiedExact.getSnapshot() : getSelected());
  async function confirmPoint() {
    if (!getCanConfirm()) return;
    if (automaticCandidate.getSnapshot()) {
      const point = automaticCandidate.getSnapshot();
      automaticCandidate.set(null);
      _propsLatest.current.onSelect?.({
        latitude: point.latitude,
        longitude: point.longitude
      });
      await afterPaint();
    }
    _propsLatest.current.onConfirm?.();
  }
  const getSelected = () => validCoordinates(_props.current.latitude, _props.current.longitude);
  const _mapRef = useRef(undefined),
    _markerRef = useRef(undefined),
    _autocompleteRef = useRef(undefined),
    _disposedRef = useRef(false),
    _revisionRef = useRef(0);
  const cleanup = useRef([]).current;
  function updateMarker() {
    if (!_mapRef.current || !_markerRef.current) return;
    if (!getSelected()) {
      if (!suggestion.getSnapshot()) _markerRef.current.map = null;
      return;
    }
    const p = {
      lat: Number(_props.current.latitude),
      lng: Number(_props.current.longitude)
    };
    _markerRef.current.position = p;
    _markerRef.current.map = _mapRef.current;
  }
  function movePin(latitude, longitude) {
    if (_props.current.disabled) return;
    _revisionRef.current++;
    selecting.set(false);
    suggestion.set("");
    clearAutomatic();
    automaticSearch.getSnapshot()?.clearSelection();
    _propsLatest.current.onSelect?.({
      latitude,
      longitude
    });
    message.set("Đã chọn ghim. Kiểm tra đúng địa chỉ và bấm Xác nhận vị trí.");
  }
  function unavailable() {
    if (_disposedRef.current) return;
    ready.set(false);
    suggestion.set("");
    if (_markerRef.current) _markerRef.current.map = null;
    message.set("Bản đồ Google chưa sẵn sàng. Bạn có thể đặt ghim trên bản đồ thủ công bên dưới.");
  }
  async function initialize() {
    if (loading.getSnapshot() || _disposedRef.current) return;
    if (!hasGoogleMapsKey() && !globalThis.google?.maps?.importLibrary) return;
    loading.set(true);
    message.set("");
    try {
      const maps = await loadGoogleMaps();
      const [{
        Map: GoogleMap
      }, {
        AdvancedMarkerElement
      }] = await Promise.all([maps.importLibrary("maps"), maps.importLibrary("marker")]);
      if (_disposedRef.current) return;
      ready.set(true);
      await afterPaint();
      if (_disposedRef.current) return;
      const center = getSelected() ? {
        lat: Number(_props.current.latitude),
        lng: Number(_props.current.longitude)
      } : {
        lat: 16.0544,
        lng: 108.2022
      };
      _mapRef.current = new GoogleMap(mapHost.getSnapshot(), {
        center,
        zoom: getSelected() ? 17 : 13,
        mapId: googleMapId(),
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: true,
        gestureHandling: "cooperative"
      });
      _markerRef.current = new AdvancedMarkerElement({
        gmpDraggable: true,
        title: "Kéo ghim đến bất động sản rồi xác nhận vị trí"
      });
      const dragged = () => {
        const p = _markerRef.current.position;
        if (p) movePin(typeof p.lat === "function" ? p.lat() : p.lat, typeof p.lng === "function" ? p.lng() : p.lng);
      };
      if (_markerRef.current.addEventListener) {
        _markerRef.current.addEventListener("gmp-dragend", dragged);
        cleanup.push(() => _markerRef.current.removeEventListener("gmp-dragend", dragged));
      }
      if (_markerRef.current.addListener) {
        const listener = _markerRef.current.addListener("dragend", dragged);
        cleanup.push(() => listener.remove());
      }
      const listener = _mapRef.current.addListener("click", event => {
        if (event.latLng) movePin(event.latLng.lat(), event.latLng.lng());
      });
      cleanup.push(() => listener.remove());
      updateMarker();
      try {
        const {
          PlaceAutocompleteElement
        } = await maps.importLibrary("places");
        if (_disposedRef.current) return;
        _autocompleteRef.current = new PlaceAutocompleteElement({
          includedRegionCodes: ["vn"],
          locationBias: {
            center: {
              lat: 16.0544,
              lng: 108.2022
            },
            radius: 30000
          }
        });
        _autocompleteRef.current.placeholder = "Tìm địa chỉ để đưa bản đồ đến gần bất động sản";
        _autocompleteRef.current.setAttribute("aria-label", "Tìm địa chỉ trên Google Maps");
        searchHost.getSnapshot().replaceChildren(_autocompleteRef.current);
        _autocompleteRef.current.addEventListener("input", () => {
          _revisionRef.current++;
          selecting.set(false);
        });
        _autocompleteRef.current.addEventListener("gmp-error", () => message.set("Dịch vụ tìm địa chỉ gặp lỗi. Kiểm tra kết nối, thử lại hoặc đặt ghim trực tiếp trên bản đồ."));
        _autocompleteRef.current.addEventListener("gmp-select", async event => {
          if (_props.current.disabled) return;
          clearAutomatic();
          automaticSearch.getSnapshot()?.clearSelection();
          const current = ++_revisionRef.current;
          selecting.set(true);
          suggestion.set("");
          message.set("");
          _propsLatest.current.onInvalidate?.();
          try {
            if (!event.placePrediction) throw Object.assign(Error(), {
              notFound: true
            });
            const place = event.placePrediction.toPlace();
            await place.fetchFields({
              fields: ["formattedAddress", "location", "viewport", "types"]
            });
            if (_disposedRef.current || current !== _revisionRef.current) return;
            let point;
            try {
              point = coordinatesFromPlace(place);
            } catch {
              throw Object.assign(Error(), {
                notFound: true
              });
            }
            // Places content is transient: display it on Google only, never serialize it into the draft.
            suggestion.set(place.formattedAddress);
            _markerRef.current.position = {
              lat: point.latitude,
              lng: point.longitude
            };
            _markerRef.current.map = _mapRef.current;
            if (place.viewport) _mapRef.current.fitBounds(place.viewport);else {
              _mapRef.current.setCenter(_markerRef.current.position);
              _mapRef.current.setZoom(17);
            }
            const precise = (place.types || []).some(t => ["street_address", "premise", "subpremise"].includes(t));
            message.set(precise ? "Đã tìm được gợi ý. Bấm bản đồ hoặc kéo ghim đến đúng bất động sản, rồi xác nhận." : "Kết quả chỉ xác định đường hoặc khu vực. Hãy chỉnh ghim đến đúng bất động sản trước khi xác nhận.");
          } catch (e) {
            if (!_disposedRef.current && current === _revisionRef.current) message.set(e.notFound ? "Không tìm thấy vị trí phù hợp cho địa chỉ này. Thử gợi ý khác hoặc đặt ghim trực tiếp." : "Không kết nối được dịch vụ tìm địa chỉ. Hãy thử lại hoặc đặt ghim trực tiếp trên bản đồ.");
          } finally {
            if (!_disposedRef.current && current === _revisionRef.current) selecting.set(false);
          }
        });
      } catch {
        message.set("Gợi ý địa chỉ chưa sẵn sàng. Bạn vẫn có thể bấm bản đồ hoặc kéo ghim để chọn vị trí.");
      }
    } catch {
      unavailable();
    } finally {
      if (!_disposedRef.current) loading.set(false);
    }
  }
  const _watched = (() => [_props.current.latitude, _props.current.longitude])();
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
    const result = updateMarker(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  const _watched2 = (() => [_props.current.address, _props.current.city, _props.current.district, _props.current.ward])();
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
      _revisionRef.current++;
      clearAutomatic();
      suggestion.set("");
      message.set("Địa chỉ đã thay đổi. Hãy chọn và xác nhận lại ghim.");
      if (_markerRef.current && !getSelected()) _markerRef.current.map = null;
    })(_watched2, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched2)]);
  useEffect(() => {
    const result = (() => {
      globalThis.addEventListener("smartprop:google-maps-unavailable", unavailable);
      initialize();
    })();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  useEffect(() => () => (() => {
    _disposedRef.current = true;
    _revisionRef.current++;
    globalThis.removeEventListener("smartprop:google-maps-unavailable", unavailable);
    cleanup.forEach(fn => fn());
    if (_markerRef.current) _markerRef.current.map = null;
    searchHost.getSnapshot()?.replaceChildren();
  })(), []);
  return {
    ...inputProps,
    candidateCanBeConfirmed,
    accuracyLabel,
    ready: ready.getSnapshot(),
    loading: loading.getSnapshot(),
    selecting: selecting.getSnapshot(),
    message: message.getSnapshot(),
    suggestion: suggestion.getSnapshot(),
    automaticCandidate: automaticCandidate.getSnapshot(),
    verifiedExact: verifiedExact.getSnapshot(),
    publicExact: publicExact.getSnapshot(),
    osmCandidate: getOsmCandidate(),
    previewRegion: getPreviewRegion(),
    clearAutomatic,
    previewAutomatic,
    canConfirm: getCanConfirm(),
    confirmPoint,
    selected: getSelected(),
    movePin,
    updateSearchHostValue: searchHost.set,
    updateMapHostValue: mapHost.set,
    updateAutomaticSearchValue: automaticSearch.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["address", "city", "district", "ward", "latitude", "longitude", "confirmed", "disabled", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateVerifiedExactValue: verifiedExact.set,
    updatePublicExactValue: publicExact.set
  };
}
export default React.forwardRef(function GooglePropertyLocation(props, ref) {
  const view = useGooglePropertyLocationState(props, ref);
  return <><div id="post-location" tabIndex="-1" data-sp-71e0825b="" {...view.rootAttributes} className={classNames(["location-picker", view.rootAttributes.className])}>
      <p className="location-guide" data-sp-71e0825b="">
        {"Chọn đúng vị trí bất động sản rồi xác nhận. Bạn không cần nhập kinh độ hoặc vĩ độ."}
      </p>
      <AutomaticLocationSearch ref={view.updateAutomaticSearchValue} address={view.address} city={view.city} district={view.district} ward={view.ward} disabled={view.disabled} onPreview={$event => {
        return view.previewAutomatic?.($event);
      }} onClear={$event => {
        return view.clearAutomatic?.($event);
      }} data-sp-71e0825b="" />
      <div ref={view.updateSearchHostValue} className="google-search" inert={view.disabled || undefined} data-sp-71e0825b="" style={{
        display: view.ready && !view.osmCandidate ? undefined : "none"
      }} />
      {view.ready && view.suggestion ? <p className="location-guide" data-sp-71e0825b="">
          {"Gợi ý trên Google: "}
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.suggestion)}
          {". Giữ địa chỉ tin đăng do bạn nhập ở trên."}
        </p> : null}
      {view.loading || view.selecting ? <p role="status" className="location-guide" data-sp-71e0825b="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.loading ? "Đang tải bản đồ…" : "Đang tìm vị trí địa chỉ…")}
        </p> : null}
      <div ref={view.updateMapHostValue} className="google-map" aria-label="Bản đồ Google chọn vị trí" data-sp-71e0825b="" style={{
        display: view.ready && !view.osmCandidate ? undefined : "none"
      }} />
      {!view.ready && !view.loading || view.osmCandidate ? <React.Fragment>
          <p className="location-guide" data-sp-71e0825b="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.osmCandidate ? "Ghim đề xuất chưa được xác nhận. " + view.accuracyLabel(view.osmCandidate) : "Đặt ghim thủ công trên bản đồ dưới đây khi bạn biết vị trí thực tế.")}
          </p>
          <ManualLocationMap latitude={view.osmCandidate?.latitude ?? view.latitude} longitude={view.osmCandidate?.longitude ?? view.longitude} precision={view.osmCandidate?.context?.precision || ""} preview={!!view.osmCandidate} previewRegion={view.previewRegion} disabled={view.disabled} onSelect={$event => {
          view.movePin($event.latitude, $event.longitude);
        }} data-sp-71e0825b="" />
        </React.Fragment> : null}
      {view.message ? <p role="status" className="location-message" data-sp-71e0825b="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.message)}
        </p> : null}
      {view.selected && !view.automaticCandidate ? <p className="location-guide" data-sp-71e0825b="">
          {"Ghim do người đăng chọn; chưa được xác minh độc lập. Xác nhận vị trí không phải chứng nhận độ chính xác."}
        </p> : null}
      {!view.selected && !view.suggestion ? <p className="location-guide" data-sp-71e0825b="">
          {"Chưa chọn vị trí. Tâm bản đồ đang xem không được lưu thành vị trí của tin."}
        </p> : null}
      {view.automaticCandidate && view.candidateCanBeConfirmed(view.automaticCandidate) ? <label className="location-consent" data-sp-71e0825b="">
          <input type="checkbox" disabled={view.disabled} data-sp-71e0825b="" checked={Array.isArray(view.verifiedExact) ? view.verifiedExact.includes("on") : !!view.verifiedExact} onChange={event => ($value => {
          view.updateVerifiedExactValue($value);
        })(Array.isArray(view.verifiedExact) ? event.target.checked ? [...view.verifiedExact, "on"] : view.verifiedExact.filter(item => item !== "on") : event.target.checked)} />
          {"Tôi đã kiểm tra đây là đúng vị trí bất động sản, không chỉ là tâm đường hoặc khu vực."}
        </label> : null}
      <label className="location-consent" data-sp-71e0825b="">
        <input type="checkbox" disabled={view.disabled} data-sp-71e0825b="" checked={Array.isArray(view.publicExact) ? view.publicExact.includes("on") : !!view.publicExact} onChange={event => ($value => {
          view.updatePublicExactValue($value);
        })(Array.isArray(view.publicExact) ? event.target.checked ? [...view.publicExact, "on"] : view.publicExact.filter(item => item !== "on") : event.target.checked)} />
        {"Tôi đồng ý công khai ghim và địa chỉ này. Nếu chỉ muốn hiển thị vị trí tương đối, chưa lưu tin bằng chế độ hiện tại."}
      </label>
      <div className={classNames(["confirm-location", {
        confirmed: view.confirmed
      }])} data-sp-71e0825b="">
        <div data-sp-71e0825b="">
          <strong data-sp-71e0825b="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.confirmed ? "Đã xác nhận vị trí" : view.selected ? "Ghim đã chọn · cần xác nhận" : "Chưa xác nhận vị trí")}
          </strong>
          <p data-sp-71e0825b="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.address || "Nhập địa chỉ đầy đủ trước khi xác nhận ghim.")}
          </p>
        </div>
        <button type="button" disabled={!view.canConfirm} onClick={$event => {
          return view.confirmPoint?.($event);
        }} data-sp-71e0825b="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.confirmed ? "Xác nhận lại" : "Xác nhận vị trí")}
        </button>
      </div>
    </div></>;
});
