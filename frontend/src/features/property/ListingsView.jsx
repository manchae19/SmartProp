import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import ListingFilters from "./ListingFilters.jsx";
import ListingCard from "./ListingCard.jsx";
import { useListingFilters } from "./useListingFilters.js";
import { usePublicListings } from "./usePublicListings.js";
import { useComparison } from "../../shared/hooks/useComparison.js";
import { sortOptions } from "./listingFilters.js";
import { price } from "./property.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import Pagination from "../../shared/components/Pagination.jsx";
import "./ListingsView.css";
function useListingsViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const search = useListingFilters(),
    compare = useComparison(),
    [viewMode] = useState(() => createStateStore("grid"));
  const _compareLatest = useRef(compare);
  _compareLatest.current = compare;
  const _searchLatest = useRef(search);
  _searchLatest.current = search;
  useSyncExternalStore(viewMode.subscribe, viewMode.getSnapshot);
  const state = usePublicListings(() => _searchLatest.current.filters);
  const _stateLatest = useRef(state);
  _stateLatest.current = state;
  const getAveragePrice = () => {
    const rows = _stateLatest.current.items;
    if (!rows.length || new Set(rows.map(p => `${p.transactionType}:${p.priceUnit}`)).size !== 1) return "—";
    const values = rows.map(p => String(p.priceExact ?? p.price));
    if (values.some(value => !/^\d+(?:\.\d{1,2})?$/.test(value))) return "—";
    const total = values.reduce((sum, value) => {
        const [whole, fraction = ""] = value.split(".");
        return sum + BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0"));
      }, 0n),
      cents = total / BigInt(rows.length);
    return price({
      priceExact: String(cents / 100n) + "." + String(cents % 100n).padStart(2, "0"),
      priceUnit: rows[0].priceUnit
    });
  };
  return {
    ...inputProps,
    sortOptions,
    search,
    compare,
    viewMode: viewMode.getSnapshot(),
    state,
    averagePrice: getAveragePrice(),
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateViewModeValue: viewMode.set
  };
}
export default React.forwardRef(function ListingsView(props, ref) {
  const view = useListingsViewState(props, ref);
  return <><div data-ui-view="ListingsView" data-sp-16d61e40="" {...view.rootAttributes} className={classNames(["collection-v3", view.rootAttributes.className])}>
      <div className="page-width" data-sp-16d61e40="">
        <div className="collection-intro" data-sp-16d61e40="">
          <p className="eyebrow" data-sp-16d61e40="">
            {"SMARTPROP / PROPERTY COLLECTION"}
          </p>
          <h1 data-sp-16d61e40="">
            {"Không gian sống "}
            <span data-sp-16d61e40="">
              {"dành riêng cho bạn."}
            </span>
          </h1>
          <p data-sp-16d61e40="">
            {"Tìm kiếm tin công khai, so sánh lựa chọn và khám phá vị trí trên bản đồ."}
          </p>
        </div>
        <ListingFilters value={view.search.filters} onChange={$event => {
          return view.search.set?.($event);
        }} data-sp-16d61e40="" />
        <div className="collection-stats" data-sp-16d61e40="">

          <p data-sp-16d61e40="">
            {"Giá chào trung bình của trang: "}
            <strong data-sp-16d61e40="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.averagePrice)}
            </strong>
            <small data-sp-16d61e40="">
              {"Chỉ tính khi cùng hình thức và đơn vị giá; không phải giá thị trường."}
            </small>
          </p>
        </div>
        <div className="collection-toolbar" data-sp-16d61e40="">
          <p data-sp-16d61e40="">
            <strong data-sp-16d61e40="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.totalElements)}
            </strong>
            {" tin phù hợp"}
            {view.search.filters.district ? <span data-sp-16d61e40="">
                {" · "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.search.filters.district)}
              </span> : null}
          </p>
          <div className="view-buttons" aria-label="Cách hiển thị" data-sp-16d61e40="">
            <button type="button" aria-pressed={view.viewMode === "grid"} onClick={$event => {
              view.updateViewModeValue("grid");
            }} data-sp-16d61e40="">
              {"▦ Lưới"}
            </button>
            <button type="button" aria-pressed={view.viewMode === "list"} onClick={$event => {
              view.updateViewModeValue("list");
            }} data-sp-16d61e40="">
              {"☷ Danh sách"}
            </button>
          </div>
          <label data-sp-16d61e40="">
            {"Sắp xếp"}
            <select value={view.search.filters.sort} onChange={$event => {
              view.search.patch({
                sort: $event.target.value
              });
            }} data-sp-16d61e40="">
              {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.sortOptions, (label, key) => <option key={key} value={key} data-sp-16d61e40="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(label)}
                </option>)}
            </select>
          </label>
          <button type="button" className="clear-filter" onClick={$event => {
            return view.search.reset?.($event);
          }} data-sp-16d61e40="">
            {"Xóa bộ lọc"}
          </button>
        </div>
        <ResourceState state={view.state} data-sp-16d61e40="" />
        {view.state.items.length ? <div className={classNames(["collection-grid", {
          "list-mode": view.viewMode === "list"
        }])} data-sp-16d61e40="">
            {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.state.items, property => <ListingCard key={property.id} property={property} list={view.viewMode === "list"} data-sp-16d61e40="">
                <SiteLink to={view.search.link("/map", {
              propertyId: property.id
            })} className="on-map" data-sp-16d61e40="">
                  {"⌖ Bản đồ"}
                </SiteLink>
                <button type="button" className="compare-button" aria-pressed={view.compare.has(property.id)} onClick={$event => {
              view.compare.toggle(property);
            }} data-sp-16d61e40="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.compare.has(property.id) ? "✓ Đã chọn" : "+ So sánh")}
                </button>
              </ListingCard>)}
          </div> : null}
        {!view.state.busy && !view.state.error && !view.state.items.length ? <div className="empty" data-sp-16d61e40="">
            <h2 data-sp-16d61e40="">
              {"Chưa tìm thấy bất động sản"}
            </h2>
            <p data-sp-16d61e40="">
              {"Hãy thử thay đổi khu vực hoặc điều kiện tìm kiếm."}
            </p>
            <button type="button" onClick={$event => {
            return view.search.reset?.($event);
          }} data-sp-16d61e40="">
              {"Xóa bộ lọc"}
            </button>
          </div> : null}
        {view.compare.notice ? <p role="status" className="notice" data-sp-16d61e40="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.compare.notice)}
          </p> : null}
        <Pagination state={view.state} data-sp-16d61e40="" />
      </div>
    </div></>;
});
