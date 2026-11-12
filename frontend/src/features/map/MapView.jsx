import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { useRouteState, useAppNavigation } from "../../app/navigation.jsx";
import { api } from "../auth/api.js";
import { usePublicListings, isPublicProperty } from "../property/usePublicListings.js";
import { useListingFilters } from "../property/useListingFilters.js";
import PropertyExplorer from "./PropertyExplorer.jsx";
import ListingFilters from "../property/ListingFilters.jsx";
import ResourceState from "../../shared/components/ResourceState.jsx";
import Pagination from "../../shared/components/Pagination.jsx";
import "./MapView.css";
function useMapViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const route = useRouteState(),
    router = useAppNavigation(),
    search = useListingFilters();
  const _searchLatest = useRef(search);
  _searchLatest.current = search;
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  const state = usePublicListings(() => _searchLatest.current.filters, {
    endpoint: "/properties/map"
  });
  const _stateLatest = useRef(state);
  _stateLatest.current = state;
  const [selectedId] = useState(() => createStateStore(null)),
    [requested] = useState(() => createStateStore(null)),
    [selectionError] = useState(() => createStateStore(""));
  useSyncExternalStore(selectionError.subscribe, selectionError.getSnapshot);
  useSyncExternalStore(requested.subscribe, requested.getSnapshot);
  useSyncExternalStore(selectedId.subscribe, selectedId.getSnapshot);
  const _sequenceRef = useRef(0);
  const getMapItems = () => requested.getSnapshot() && !_stateLatest.current.items.some(p => p.id === requested.getSnapshot().id) ? [..._stateLatest.current.items, requested.getSnapshot()] : _stateLatest.current.items;
  async function loadRequested(id) {
    const run = ++_sequenceRef.current;
    selectionError.set("");
    requested.set(null);
    selectedId.set(id ? String(id) : null);
    if (!id) {
      selectedId.set(_stateLatest.current.items[0]?.id || null);
      return;
    }
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(id))) {
      selectionError.set("Mã tin trên bản đồ không hợp lệ.");
      return;
    }
    try {
      const p = await api("/properties/" + encodeURIComponent(id), {
        authenticated: false
      });
      if (run !== _sequenceRef.current) return;
      if (!isPublicProperty(p)) throw Error();
      requested.set(p);
    } catch {
      if (run === _sequenceRef.current) selectionError.set("Không tìm thấy tin công khai đang chọn; không thay bằng vị trí của tin khác.");
    }
  }
  const _watched = (() => _routeLatest.current.query.propertyId)();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    _initialized.current = true;
    const result = loadRequested(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  const _watched2 = (() => _stateLatest.current.items)();
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
    const result = (items => {
      if (!_routeLatest.current.query.propertyId && !items.some(p => p.id === selectedId.getSnapshot())) selectedId.set(items[0]?.id || null);
    })(_watched2, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched2)]);
  function select(id) {
    _routerLatest.current.replace({
      query: {
        ..._routeLatest.current.query,
        propertyId: id
      }
    });
  }
  useEffect(() => () => (() => _sequenceRef.current++)(), []);
  return {
    ...inputProps,
    search,
    state,
    selectedId: selectedId.getSnapshot(),
    requested: requested.getSnapshot(),
    selectionError: selectionError.getSnapshot(),
    mapItems: getMapItems(),
    select,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function MapView(props, ref) {
  const view = useMapViewState(props, ref);
  return <><div data-ui-view="MapView" data-sp-2646eeb9="" {...view.rootAttributes} className={classNames(["map-v3", view.rootAttributes.className])}>
      <div className="map-page-width" data-sp-2646eeb9="">
        <div className="map-heading page-intro-banner" data-sp-2646eeb9="">
          <p data-sp-2646eeb9="">
            {"GIS EXPLORER"}
          </p>
          <h1 data-sp-2646eeb9="">
            {"Bản đồ bất động sản"}
          </h1>

        </div>
        <details className="map-search-panel" data-sp-2646eeb9="">
          <summary data-sp-2646eeb9="">
            {"Bộ lọc tìm kiếm bất động sản"}
          </summary>
          <ListingFilters value={view.search.filters} onChange={$event => {
            return view.search.set?.($event);
          }} data-sp-2646eeb9="" />
        </details>
        <ResourceState state={view.state} data-sp-2646eeb9="" />
        {view.selectionError ? <p role="alert" className="selection-error" data-sp-2646eeb9="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectionError)}
          </p> : null}
        {view.requested && !view.state.items.some(p => p.id === view.requested.id) ? <p className="selection-info" data-sp-2646eeb9="">
            {"Tin đang xem có thể nằm ngoài bộ lọc hiện tại."}
          </p> : null}
        <PropertyExplorer selectedId={view.selectedId} items={view.mapItems} onSelect={$event => {
          return view.select?.($event);
        }} data-sp-2646eeb9="" />
        <Pagination state={view.state} data-sp-2646eeb9="" />
      </div>
    </div></>;
});
