import { createPortal } from "react-dom";
import { afterPaint, classNames, numericInput } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import LeafletNearbyMap from "./LeafletNearbyMap.jsx";
import PrivateImage from "../../shared/components/PrivateImage.jsx";
import ContactPanel from "../property/ContactPanel.jsx";
import { publicMapPoint, locationLabel } from "./locationDisplay.js";
import { canExploreNearby, canAnalyzeDistance } from "./coordinateEligibility.js";
import { compactPrice, price, types, displayDecimal } from "../property/property.js";
import { POI_GROUPS, DEFAULT_GROUPS, RADII, filteredPlaces, distanceLabel } from "./nearbyExplorer.js";
import { useNearbyPlaces } from "./useNearbyPlaces.js";
import "./PropertyExplorer.css";
function usePropertyExplorerState(inputProps, forwardedRef) {
  inputProps = {
    items: (() => [])(),
    allowNearby: true,
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    items: (() => [])(),
    allowNearby: true,
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [radius] = useState(() => createStateStore(1000)),
    [groups] = useState(() => createStateStore([...DEFAULT_GROUPS])),
    [showProperty] = useState(() => createStateStore(true)),
    [showRadius] = useState(() => createStateStore(!_props.current.preview)),
    [activePoi] = useState(() => createStateStore(null)),
    [expanded] = useState(() => createStateStore(false)),
    [panel] = useState(() => createStateStore(null)),
    [expandButton] = useState(() => createStateStore(null));
  useSyncExternalStore(expandButton.subscribe, expandButton.getSnapshot);
  useSyncExternalStore(panel.subscribe, panel.getSnapshot);
  useSyncExternalStore(expanded.subscribe, expanded.getSnapshot);
  useSyncExternalStore(activePoi.subscribe, activePoi.getSnapshot);
  useSyncExternalStore(showRadius.subscribe, showRadius.getSnapshot);
  useSyncExternalStore(showProperty.subscribe, showProperty.getSnapshot);
  useSyncExternalStore(groups.subscribe, groups.getSnapshot);
  useSyncExternalStore(radius.subscribe, radius.getSnapshot);
  const getProperty = () => _props.current.items.find(p => p.id === _props.current.selectedId) || null;
  const getOrigin = () => publicMapPoint(getProperty()) ? getProperty() : null;
  const nearby = useNearbyPlaces(() => getOrigin(), () => radius.getSnapshot(), () => groups.getSnapshot(), () => _props.current.allowNearby && canExploreNearby(getProperty()));
  const _nearbyLatest = useRef(nearby);
  _nearbyLatest.current = nearby;
  const getPlaces = () => filteredPlaces(_nearbyLatest.current.data?.items, getOrigin(), radius.getSnapshot(), groups.getSnapshot());
  const getFeaturedPlaces = () => _props.current.preview ? getPlaces().slice(0, 4) : getPlaces();
  const getImage = () => getProperty()?.images?.find(i => i.cover || i.isCover)?.url || getProperty()?.images?.[0]?.url || getProperty()?.coverImageUrl || "";
  const groupLabel = id => POI_GROUPS.find(g => g.id === id)?.label || "Tiện ích";
  const _previousOverflowRef = useRef(""),
    _previousFocusRef = useRef(undefined);
  async function toggleExpanded() {
    expanded.set(!expanded.getSnapshot());
    if (expanded.getSnapshot()) {
      _previousOverflowRef.current = document.body.style.overflow;
      _previousFocusRef.current = document.activeElement;
      document.body.style.overflow = "hidden";
      await afterPaint();
      panel.getSnapshot()?.focus();
    } else {
      document.body.style.overflow = _previousOverflowRef.current;
      await afterPaint();
      _previousFocusRef.current?.focus();
    }
  }
  function keyboard(e) {
    if (e.key === "Escape" && expanded.getSnapshot()) {
      e.preventDefault();
      toggleExpanded();
    }
    if (e.key !== "Tab" || !expanded.getSnapshot()) return;
    const elements = [...panel.getSnapshot().querySelectorAll('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),[tabindex="0"]')].filter(el => el.getClientRects().length);
    const first = elements[0],
      last = elements.at(-1);
    if (e.shiftKey && (document.activeElement === first || document.activeElement === panel.getSnapshot())) {
      e.preventDefault();
      last?.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first?.focus();
    }
  }
  const _watched = (() => _props.current.selectedId)();
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
      activePoi.set(null);
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  useEffect(() => () => (() => {
    if (expanded.getSnapshot()) document.body.style.overflow = _previousOverflowRef.current;
  })(), []);
  return {
    ...inputProps,
    locationLabel,
    compactPrice,
    price,
    types,
    displayDecimal,
    POI_GROUPS,
    RADII,
    distanceLabel,
    radius: radius.getSnapshot(),
    groups: groups.getSnapshot(),
    showProperty: showProperty.getSnapshot(),
    showRadius: showRadius.getSnapshot(),
    activePoi: activePoi.getSnapshot(),
    expanded: expanded.getSnapshot(),
    property: getProperty(),
    origin: getOrigin(),
    canExploreNearby: canExploreNearby(getProperty()),
    nearby,
    places: getPlaces(),
    featuredPlaces: getFeaturedPlaces(),
    image: getImage(),
    groupLabel,
    toggleExpanded,
    keyboard,
    updatePanelValue: panel.set,
    updateExpandButtonValue: expandButton.set,
    updateActivePoiValue: activePoi.set,
    updateShowPropertyValue: showProperty.set,
    updateGroupsValue: groups.set,
    updateShowRadiusValue: showRadius.set,
    updateRadiusValue: radius.set
  };
}
export default React.forwardRef(function PropertyExplorer(props, ref) {
  const view = usePropertyExplorerState(props, ref);
  const content = <>
      <section ref={view.updatePanelValue} tabIndex="-1" className={classNames(["property-explorer", {
      "is-expanded": view.expanded,
      "is-compact": view.compact,
      "is-preview": view.preview
    }])} role={view.expanded ? "dialog" : undefined} aria-modal={view.expanded ? "true" : undefined} aria-label="Bản đồ và tiện ích bất động sản" onKeyDown={$event => {
      return view.keyboard?.($event);
    }} data-sp-c46b683d="">
        <aside className="explorer-sidebar" data-sp-c46b683d="">
          {!view.preview ? <SiteLink to="/listings" className="explorer-back" data-sp-c46b683d="">
              {"← Quay lại kết quả tìm kiếm"}
            </SiteLink> : null}
          {view.items.length > 1 ? <div className="explorer-picker" data-sp-c46b683d="">
              <label htmlFor="explorer-property" data-sp-c46b683d="">
                {"Tin đăng đang xem"}
              </label>
              <select id="explorer-property" value={view.selectedId || ""} onChange={$event => {
            view.onSelect?.($event.target.value);
          }} data-sp-c46b683d="">
                <option value="" disabled={true} data-sp-c46b683d="">
                  {"Chọn tin đăng"}
                </option>
                {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.items, p => <option key={p.id} value={p.id} data-sp-c46b683d="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(p.title)}
                  </option>)}
              </select>
            </div> : null}
          {view.property ? <React.Fragment>
              <h2 data-sp-c46b683d="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.property.title)}
              </h2>
              <div className="explorer-price" title={view.price(view.property)} data-sp-c46b683d="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.compactPrice(view.property))}
              </div>
              {!view.preview ? <details className="explorer-exact" data-sp-c46b683d="">
                  <summary data-sp-c46b683d="">
                    {"Giá đầy đủ"}
                  </summary>
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.price(view.property))}
                </details> : null}
              <div className="explorer-photo" data-sp-c46b683d="">
                <PrivateImage key={view.property.id} src={view.image} alt={view.property.title} data-sp-c46b683d="" />
              </div>
              <div className="explorer-facts" data-sp-c46b683d="">
                <div data-sp-c46b683d="">
                  <strong data-sp-c46b683d="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.displayDecimal(view.property.areaSqm))}
                    {" m²"}
                  </strong>
                  <span data-sp-c46b683d="">
                    {"Diện tích"}
                  </span>
                </div>
                <div data-sp-c46b683d="">
                  <strong data-sp-c46b683d="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.types[view.property.propertyType] || "Chưa rõ")}
                  </strong>
                  <span data-sp-c46b683d="">
                    {"Loại hình"}
                  </span>
                </div>
                {view.property.bedrooms != null ? <div data-sp-c46b683d="">
                    <strong data-sp-c46b683d="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.property.bedrooms)}
                    </strong>
                    <span data-sp-c46b683d="">
                      {"Phòng ngủ"}
                    </span>
                  </div> : null}
              </div>
              <h3 data-sp-c46b683d="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.preview ? "Tiện ích nổi bật" : "Vị trí & khoảng cách")}
              </h3>
              {!view.preview ? <p className="explorer-address" data-sp-c46b683d="">
                  {"⌖ "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))([view.property.address, view.property.ward, view.property.district, view.property.city].filter(Boolean).join(", ") || "Chưa có địa chỉ công bố")}
                </p> : null}
              {!view.preview ? <p className="explorer-location-note" data-sp-c46b683d="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.locationLabel(view.property))}
                </p> : null}
              {!view.origin ? <p className="explorer-notice" data-sp-c46b683d="">
                  {"Tin chưa có vị trí công khai phù hợp. Không đặt ghim thay thế."}
                </p> : !view.canExploreNearby ? <p className="explorer-notice" data-sp-c46b683d="">
                  {"Bản đồ chỉ mang tính tham khảo; chưa đủ bằng chứng nguồn và độ chính xác để phân tích khoảng cách."}
                </p> : !view.allowNearby ? <p className="explorer-notice" data-sp-c46b683d="">
                  {"Tiện ích chỉ được truy vấn cho tin đang công khai."}
                </p> : null}
              {view.origin && !canAnalyzeDistance(view.property) ? <p className="explorer-location-note">Khoảng cách ước tính từ ghim tin đăng · chưa xác minh vị trí căn nhà.</p> : null}
              {view.nearby.busy ? <p role="status" className="explorer-notice" data-sp-c46b683d="">
                  {"Đang tìm tiện ích trong "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.distanceLabel(view.radius))}
                  {"…"}
                </p> : null}
              {view.nearby.error ? <div role="alert" className="explorer-warning" data-sp-c46b683d="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.nearby.error)}{" "}
                  <button type="button" onClick={$event => {
              return view.nearby.retry?.($event);
            }} data-sp-c46b683d="">
                    {"Thử lại"}
                  </button>
                </div> : view.origin && view.canExploreNearby && view.allowNearby && !view.nearby.busy && view.groups.length && view.nearby.data && !view.places.length ? <p className="explorer-notice" data-sp-c46b683d="">
                  {"Chưa tìm thấy tiện ích phù hợp trong phạm vi đã chọn."}
                </p> : null}
              {!view.groups.length ? <p className="explorer-notice" data-sp-c46b683d="">
                  {"Bật một nhóm tiện ích để tìm quanh tin đăng."}
                </p> : null}
              <ol className="explorer-pois" data-sp-c46b683d="">
                {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.featuredPlaces, p => <li key={p.id} data-sp-c46b683d="">
                    <button type="button" className={classNames({
                active: view.activePoi === p.id
              })} onClick={$event => {
                view.updateActivePoiValue(p.id);
              }} data-sp-c46b683d="">
                      <span className="poi-dot" style={{
                  background: view.POI_GROUPS.find(g => g.id === p.category)?.color
                }} data-sp-c46b683d="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.POI_GROUPS.find(g => g.id === p.category)?.icon)}
                      </span>
                      <span data-sp-c46b683d="">
                        <strong data-sp-c46b683d="">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(p.name)}
                        </strong>
                        <small data-sp-c46b683d="">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.groupLabel(p.category))}
                        </small>
                      </span>
                      {!view.preview ? <b data-sp-c46b683d="">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.distanceLabel(p.distanceMeters))}
                        </b> : null}
                    </button>
                  </li>)}
              </ol>
              {!view.preview && view.nearby.data ? <p className="explorer-source" data-sp-c46b683d="">
                  {"Đường chim bay · "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.places.length)}
                  {" tiện ích · Dữ liệu có thể chưa đầy đủ"}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.nearby.data.truncated ? " (đã giới hạn kết quả)" : "")}
                  {"."}
                  <br data-sp-c46b683d="" />
                  {"Cập nhật truy vấn: "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(new Date(view.nearby.data.fetchedAt).toLocaleString("vi-VN"))}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.nearby.data.cacheHit ? " · Bộ nhớ đệm" : "")}
                </p> : null}
              <SiteLink to={"/listing/" + view.property.id} className="explorer-detail" data-sp-c46b683d="">
                {"Xem chi tiết tin →"}
              </SiteLink>
              {view.allowNearby && !view.preview ? <ContactPanel propertyId={view.property.id} data-sp-c46b683d="" /> : null}
            </React.Fragment> : <p className="explorer-notice" data-sp-c46b683d="">
              {"Chọn một tin đăng có tọa độ để khám phá tiện ích xung quanh."}
            </p>}
        </aside>
        <div className="explorer-map-column" data-sp-c46b683d="">
          <header className="explorer-map-toolbar" data-sp-c46b683d="">
            <div data-sp-c46b683d="">
              <span className="gis-dot" data-sp-c46b683d="" />
              <strong data-sp-c46b683d="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.preview ? "Khám phá không gian sống" : "GIS Explorer")}
              </strong>
              <span className="explorer-subtitle" data-sp-c46b683d="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.preview ? "Chạm vào ghim để xem tin đăng" : "Bất động sản & tiện ích quanh bạn")}
              </span>
            </div>
            {view.preview ? <SiteLink to={view.exploreLink || {
            path: "/map",
            query: view.selectedId ? {
              propertyId: view.selectedId
            } : {}
          }} className="explorer-launch" data-sp-c46b683d="">
                {"Khám phá GIS đầy đủ ↗"}
              </SiteLink> : <button ref={view.updateExpandButtonValue} type="button" onClick={$event => {
            return view.toggleExpanded?.($event);
          }} aria-expanded={view.expanded} data-sp-c46b683d="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.expanded ? "✕ Thu nhỏ" : "⛶ Mở rộng")}
              </button>}
          </header>
          <div className="explorer-map-content" data-sp-c46b683d="">
            <LeafletNearbyMap simple={view.preview} items={view.items} selectedId={view.origin?.id} places={view.featuredPlaces} radius={view.radius} showProperty={view.showProperty} showRadius={view.showRadius} activePoi={view.activePoi} onSelect={$event => {
            view.onSelect?.($event);
          }} onSelectPoi={$event => {
            view.updateActivePoiValue($event);
          }} data-sp-c46b683d="" />
            {!view.preview ? <div className="explorer-layers" data-sp-c46b683d="">
                <h3 data-sp-c46b683d="">
                  {"Lớp hiển thị"}
                </h3>
                <label data-sp-c46b683d="">
                  <input type="checkbox" data-sp-c46b683d="" checked={Array.isArray(view.showProperty) ? view.showProperty.includes("on") : !!view.showProperty} onChange={event => ($value => {
                view.updateShowPropertyValue($value);
              })(Array.isArray(view.showProperty) ? event.target.checked ? [...view.showProperty, "on"] : view.showProperty.filter(item => item !== "on") : event.target.checked)} />
                  {" Bất động sản"}
                </label>
                {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.POI_GROUPS, group => <label key={group.id} data-sp-c46b683d="">
                    <input value={group.id} aria-label={group.label} type="checkbox" data-sp-c46b683d="" checked={Array.isArray(view.groups) ? view.groups.includes(group.id) : !!view.groups} onChange={event => ($value => {
                view.updateGroupsValue($value);
              })(Array.isArray(view.groups) ? event.target.checked ? [...view.groups, group.id] : view.groups.filter(item => item !== group.id) : event.target.checked)} />
                    <span aria-hidden="true" style={{
                color: group.color
              }} data-sp-c46b683d="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(group.icon)}
                    </span>{" "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(group.label)}
                  </label>)}
                <label data-sp-c46b683d="">
                  <input type="checkbox" data-sp-c46b683d="" checked={Array.isArray(view.showRadius) ? view.showRadius.includes("on") : !!view.showRadius} onChange={event => ($value => {
                view.updateShowRadiusValue($value);
              })(Array.isArray(view.showRadius) ? event.target.checked ? [...view.showRadius, "on"] : view.showRadius.filter(item => item !== "on") : event.target.checked)} />
                  {" Vùng tìm tiện ích"}
                </label>
              </div> : null}
            {!view.preview ? <div className="explorer-radius" data-sp-c46b683d="">
                <label data-sp-c46b683d="">
                  {"Bán kính tìm kiếm "}
                  <select aria-label="Bán kính tìm tiện ích" data-sp-c46b683d="" value={view.radius ?? ""} onChange={event => ($value => {
                view.updateRadiusValue($value);
              })(numericInput(event.target.value))}>
                    {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.RADII, r => <option key={r} value={r} data-sp-c46b683d="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.distanceLabel(r))}
                      </option>)}
                  </select>
                </label>
                <small data-sp-c46b683d="">
                  {"Vòng tròn tìm kiếm, không phải ranh giới hay sai số vị trí."}
                </small>
              </div> : null}
          </div>
          <footer className="explorer-credits" data-sp-c46b683d="">
            <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer" data-sp-c46b683d="">
              {"© OpenStreetMap contributors"}
            </a>
            <span data-sp-c46b683d="">
              {" · "}
            </span>
            <a href="https://www.geoapify.com/" target="_blank" rel="noopener noreferrer" data-sp-c46b683d="">
              {"Powered by Geoapify"}
            </a>
            {!view.preview ? <span data-sp-c46b683d="">
                {" · Khoảng cách đường chim bay, không phải quãng đường di chuyển."}
              </span> : null}
          </footer>
        </div>
      </section>
    </>;
  return view.expanded ? createPortal(content, document.body) : content;
});
