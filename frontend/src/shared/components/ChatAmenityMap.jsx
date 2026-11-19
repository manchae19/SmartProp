import { afterPaint, classNames } from "../lib/ui.js";
import { createStateStore } from "../state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import BrowseTileMap from "../../features/map/BrowseTileMap.jsx";
import PoiIcon from "./PoiIcon.jsx";
import { amenityCategories } from "../../features/prediction/chatAmenities.js";
import { poiColor } from "../../features/map/nearbyPlaces.js";
import "./ChatAmenityMap.css";
function useChatAmenityMapState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [selected] = useState(() => createStateStore(null)),
    [expanded] = useState(() => createStateStore(false)),
    [host] = useState(() => createStateStore(null));
  useSyncExternalStore(host.subscribe, host.getSnapshot);
  useSyncExternalStore(expanded.subscribe, expanded.getSnapshot);
  useSyncExternalStore(selected.subscribe, selected.getSnapshot);
  const getItems = () => _props.current.data?.items || [];
  const getPoints = () => getItems().map(p => ({
    ...p,
    categoryLabel: amenityCategories[p.category]
  }));
  const getCards = () => expanded.getSnapshot() ? getItems() : getItems().slice(0, 6);
  const getCategories = () => [...new Set(getItems().map(p => p.category))];
  function select(id) {
    selected.set(id);
    _propsLatest.current.onReading?.();
    // In a conversation the map may be partly above the reading viewport. Bring
    // the actual map (not just a focused pin) into view so its popup stays readable.
    if (id) afterPaint(() => host.getSnapshot()?.querySelector(".browse-map")?.scrollIntoView({
      block: "center",
      inline: "nearest"
    }));
  }
  return {
    ...inputProps,
    amenityCategories,
    poiColor,
    selected: selected.getSnapshot(),
    expanded: expanded.getSnapshot(),
    items: getItems(),
    points: getPoints(),
    cards: getCards(),
    categories: getCategories(),
    select,
    updateHostValue: host.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["data", "status", "message", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateExpandedValue: expanded.set
  };
}
export default React.forwardRef(function ChatAmenityMap(props, ref) {
  const view = useChatAmenityMapState(props, ref);
  return <><section ref={view.updateHostValue} data-chat-amenities="" aria-label="Tiện ích trên bản đồ" data-sp-6a8bc544="" {...view.rootAttributes} className={classNames(["chat-amenity", view.rootAttributes.className])}>
      {view.status === "loading" ? <p className="map-state" role="status" data-amenity-loading="" data-sp-6a8bc544="">
          {"Đang tìm tiện ích trên bản đồ…"}
        </p> : view.status === "error" ? <p className="map-state map-error" role="status" data-amenity-error="" data-sp-6a8bc544="">
          {"Chưa tải được bản đồ tiện ích. Câu trả lời phía trên vẫn được giữ. "}
          <button type="button" onClick={$event => {
          view.onRetry?.();
        }} data-sp-6a8bc544="">
            {"Thử lại bản đồ"}
          </button>
        </p> : view.items.length || view.data?.boundary ? <React.Fragment>
          <div className="amenity-map-card" data-chat-map="" data-sp-6a8bc544="">
            <div className="map-heading" data-sp-6a8bc544="">
              <h3 data-sp-6a8bc544="">
                {"Tiện ích · "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.data.district)}
              </h3>
              <span data-sp-6a8bc544="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.items.length ? view.items.length + " địa điểm" : "Ranh giới khu vực")}
              </span>
            </div>
            <BrowseTileMap className="chat-poi-map" poiItems={view.points} boundary={view.data.boundary?.geometry} selectedPoiId={view.selected} mapLabel="Bản đồ tiện ích: kéo để di chuyển, phím mũi tên và cộng trừ để điều khiển" onSelectPoi={$event => {
            return view.select?.($event);
          }} data-sp-6a8bc544="" />
            {!view.items.length ? <p className="map-note" data-amenity-area-only="" data-sp-6a8bc544="">
                {"Chỉ có ranh giới khu vực lịch sử. Chưa có tọa độ tiện ích đủ điều kiện cho yêu cầu này; không đặt ghim ước lượng."}
              </p> : null}
            <div className="map-legend" aria-label="Loại tiện ích" data-sp-6a8bc544="">
              {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.categories, cat => <span key={cat} data-sp-6a8bc544="">
                  <i style={{
                background: view.poiColor(cat)
              }} aria-hidden="true" data-sp-6a8bc544="" />
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.amenityCategories[cat])}
                </span>)}
            </div>
            <p className="map-note" data-sp-6a8bc544="">
              {"Địa điểm theo nguồn bản đồ, chưa xác minh thực địa. Chọn ghim để xem tên và nguồn địa điểm."}
            </p>
            {view.data.truncated ? <p className="map-note" data-sp-6a8bc544="">
                {"Đang hiển thị một phần địa điểm, tối đa 8 mỗi loại khi xem nhiều loại tiện ích."}
              </p> : null}
          </div>
          <div className="amenity-cards" data-amenity-cards="" data-sp-6a8bc544="">
            {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.cards, p => <article key={p.id} data-amenity-card={p.id} className={classNames({
            active: view.selected === p.id
          })} data-sp-6a8bc544="">
                <button type="button" className="amenity-select" onClick={$event => {
              view.select(p.id);
            }} data-sp-6a8bc544="">
                  <span className="amenity-icon" style={{
                color: view.poiColor(p.category)
              }} data-sp-6a8bc544="">
                    <PoiIcon category={p.category} data-sp-6a8bc544="" />
                  </span>
                  <span data-sp-6a8bc544="">
                    <strong data-sp-6a8bc544="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(p.name)}
                    </strong>
                    <small data-sp-6a8bc544="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.amenityCategories[p.category])}
                      {" · "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(p.district)}
                    </small>
                  </span>
                </button>
                <div className="amenity-source" data-sp-6a8bc544="">
                  <span data-sp-6a8bc544="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(p.coordinateBasis === "GEOAPIFY_POINT" ? "Tọa độ từ Geoapify · chưa xác minh thực địa" : p.coordinateBasis === "OSM_NODE" ? "Điểm ghi trong OSM" : "Điểm đại diện đối tượng OSM")}
                  </span>
                  <a href={p.sourceUrl} target="_blank" rel="noopener noreferrer" data-sp-6a8bc544="">
                    {p.sourceName === "geoapify" ? "Nguồn Geoapify ↗" : "Nguồn OSM ↗"}
                  </a>
                </div>
              </article>)}
          </div>
          {view.items.length > 6 ? <button type="button" className="more-amenities" aria-expanded={view.expanded} onClick={$event => {
          view.updateExpandedValue(!view.expanded);
          view.onReading?.();
        }} data-sp-6a8bc544="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.expanded ? "Thu gọn tiện ích" : "Xem tất cả " + view.items.length + " tiện ích")}
            </button> : null}
          <details className="map-provenance" onToggle={$event => {
          return (event => event.target.open && view.onReading?.())?.($event);
        }} data-sp-6a8bc544="">
            <summary data-sp-6a8bc544="">
              {"Nguồn bản đồ ("}
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.items.length || 1)}
              {")"}
            </summary>
            {view.items.length ? <p data-sp-6a8bc544="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.items[0].attribution)}
                {" · "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.items[0].sourceLicense)}
              </p> : null}
            {view.data.boundary ? <p data-sp-6a8bc544="">
                <a href={view.data.boundary.sourceUrl} target="_blank" rel="noopener noreferrer" data-sp-6a8bc544="">
                  {"Ranh giới lịch sử · "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.data.boundary.attribution)}
                  {" · "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.data.boundary.license)}
                </a>
              </p> : null}
            {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.data.dataLimitations, line => <p key={line} data-sp-6a8bc544="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(line)}
              </p>)}
          </details>
        </React.Fragment> : <p className="map-state" data-amenity-empty="" data-sp-6a8bc544="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.message || "Chưa có tọa độ tiện ích đủ điều kiện hiển thị; không đặt ghim ước lượng trên bản đồ.")}
        </p>}
    </section></>;
});
