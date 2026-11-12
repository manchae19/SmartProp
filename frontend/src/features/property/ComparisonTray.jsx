import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { useRouteState } from "../../app/navigation.jsx";
import { useComparison } from "../../shared/hooks/useComparison.js";
import { api } from "../auth/api.js";
import { isPublicProperty } from "./usePublicListings.js";
import { price, compactPrice, types } from "./property.js";
import PrivateImage from "../../shared/components/PrivateImage.jsx";
import BrowseTileMap from "../map/BrowseTileMap.jsx";
import "./ComparisonTray.css";
function useComparisonTrayState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const route = useRouteState();
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  const compare = useComparison();
  const _compareLatest = useRef(compare);
  _compareLatest.current = compare;
  const [dialog] = useState(() => createStateStore(null));
  useSyncExternalStore(dialog.subscribe, dialog.getSnapshot);
  const [busy] = useState(() => createStateStore(false));
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  const [error] = useState(() => createStateStore(""));
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  const [showOnlyDiff] = useState(() => createStateStore(false));
  useSyncExternalStore(showOnlyDiff.subscribe, showOnlyDiff.getSnapshot);
  const [showMap] = useState(() => createStateStore(true));
  useSyncExternalStore(showMap.subscribe, showMap.getSnapshot);
  const getVisible = () => ["/home", "/listings", "/map"].includes(_routeLatest.current.path);
  const getMixed = () => new Set(_compareLatest.current.items.map(p => `${p.transactionType}:${p.priceUnit}`)).size > 1;
  const _sequenceRef = useRef(0);
  async function open() {
    const run = ++_sequenceRef.current;
    busy.set(true);
    error.set("");
    const originals = [..._compareLatest.current.items];
    const result = await Promise.allSettled(originals.map(p => api("/properties/" + encodeURIComponent(p.id), {
      authenticated: false
    })));
    if (run !== _sequenceRef.current) return;
    busy.set(false);
    if (_compareLatest.current.items.map(p => p.id).join("|") !== originals.map(p => p.id).join("|")) {
      error.set("Lựa chọn đã thay đổi trong lúc kiểm tra. Hãy bấm so sánh lại.");
      return;
    }
    if (result.some(r => r.status === "rejected" && r.reason?.status !== 404)) {
      error.set("Chưa xác minh được trạng thái mới nhất của các tin. Hãy thử lại.");
      return;
    }
    const current = result.flatMap(r => r.status === "fulfilled" && isPublicProperty(r.value) ? [r.value] : []);
    _compareLatest.current.replace(current);
    if (current.length !== originals.length) {
      error.set("Đã bỏ tin không còn công khai. Hãy chọn ít nhất 2 tin hợp lệ.");
      return;
    }
    if (current.length < 2) return;
    dialog.getSnapshot().showModal();
  }
  function close() {
    dialog.getSnapshot()?.close();
  }
  const _watched = (() => _routeLatest.current.fullPath)();
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
      _sequenceRef.current++;
      busy.set(false);
      close();
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  useEffect(() => () => (() => {
    _sequenceRef.current++;
    close();
  })(), []);

  // Helper methods for calculations & visuals
  function cover(p) {
    return (p.images?.find(i => i.cover) || p.images?.[0])?.url;
  }
  function getNumericPrice(p) {
    const raw = Number(p.priceExact ?? p.price ?? 0);
    return Number.isFinite(raw) ? raw : 0;
  }
  function getNumericArea(p) {
    const raw = Number(p.areaSqmExact ?? p.areaSqm ?? 0);
    return Number.isFinite(raw) ? raw : 0;
  }
  function getUnitPricePerSqm(p) {
    const pr = getNumericPrice(p);
    const ar = getNumericArea(p);
    if (pr > 0 && ar > 0 && p.transactionType === "SALE" && p.priceUnit === "TOTAL") {
      return Math.round(pr / ar);
    }
    return null;
  }
  function formatUnitPrice(p) {
    const u = getUnitPricePerSqm(p);
    if (!u) return "—";
    const million = (u / 1000000).toLocaleString("vi-VN", {
      maximumFractionDigits: 1
    });
    return `${million} tr/m²`;
  }
  function calculateDistanceKm(lat1, lon1, lat2, lon2) {
    if (lat1 == null || lon1 == null || lat2 == null || lon2 == null) return null;
    const y1 = Number(lat1),
      x1 = Number(lon1),
      y2 = Number(lat2),
      x2 = Number(lon2);
    if (!Number.isFinite(y1) || !Number.isFinite(x1) || !Number.isFinite(y2) || !Number.isFinite(x2)) return null;
    const R = 6371; // km
    const dLat = (y2 - y1) * Math.PI / 180;
    const dLon = (x2 - x1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(y1 * Math.PI / 180) * Math.cos(y2 * Math.PI / 180) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const d = R * c;
    return d < 1 ? `${Math.round(d * 1000)} m` : `${d.toFixed(1)} km`;
  }

  // Visual comparisons
  const getMetricsComparison = () => {
    const items = _compareLatest.current.items;
    if (items.length < 2) return null;

    // 1. Price
    const prices = items.map(getNumericPrice);
    const maxPrice = Math.max(...prices) || 1;
    const priceBars = items.map(p => ({
      id: p.id,
      pct: Math.max(10, Math.round(getNumericPrice(p) / maxPrice * 100)),
      label: compactPrice(p),
      isLowest: getNumericPrice(p) === Math.min(...prices) && prices.some(v => v !== prices[0])
    }));

    // 2. Unit Price
    const units = items.map(getUnitPricePerSqm).filter(Boolean);
    let unitBars = [];
    if (units.length === items.length) {
      const maxUnit = Math.max(...units) || 1;
      const minUnit = Math.min(...units);
      unitBars = items.map(p => {
        const u = getUnitPricePerSqm(p);
        return {
          id: p.id,
          pct: Math.max(10, Math.round(u / maxUnit * 100)),
          label: formatUnitPrice(p),
          isLowest: u === minUnit && minUnit !== maxUnit,
          savingPct: u === minUnit && minUnit !== maxUnit ? Math.round((maxUnit - minUnit) / maxUnit * 100) : 0
        };
      });
    }

    // 3. Area
    const areas = items.map(getNumericArea);
    const maxArea = Math.max(...areas) || 1;
    const areaBars = items.map(p => ({
      id: p.id,
      pct: Math.max(10, Math.round(getNumericArea(p) / maxArea * 100)),
      label: `${p.areaSqmExact ?? p.areaSqm} m²`,
      isLargest: getNumericArea(p) === maxArea && areas.some(v => v !== areas[0])
    }));

    // 4. Distance (if 2 properties)
    let distance = null;
    if (items.length === 2 && items[0].latitude && items[1].latitude) {
      distance = calculateDistanceKm(items[0].latitude, items[0].longitude, items[1].latitude, items[1].longitude);
    }
    return {
      priceBars,
      unitBars,
      areaBars,
      distance
    };
  };

  // Smart highlights per property
  function getPropertyHighlights(p) {
    const items = _compareLatest.current.items;
    if (items.length < 2) return [];
    const badges = [];
    const prices = items.map(getNumericPrice);
    const units = items.map(getUnitPricePerSqm).filter(Boolean);
    const areas = items.map(getNumericArea);
    if (prices.length > 1 && getNumericPrice(p) === Math.min(...prices) && new Set(prices).size > 1) {
      badges.push({
        text: "Giá tổng tốt nhất",
        type: "best-price"
      });
    }
    const u = getUnitPricePerSqm(p);
    if (units.length === items.length && u === Math.min(...units) && new Set(units).size > 1) {
      badges.push({
        text: "Đơn giá/m² tối ưu",
        type: "best-unit"
      });
    }
    if (areas.length > 1 && getNumericArea(p) === Math.max(...areas) && new Set(areas).size > 1) {
      badges.push({
        text: "Diện tích lớn nhất",
        type: "best-area"
      });
    }
    if (p.bedrooms && items.some(other => (other.bedrooms || 0) < p.bedrooms)) {
      badges.push({
        text: `${p.bedrooms} phòng ngủ`,
        type: "highlight"
      });
    }
    return badges;
  }

  // Amenities Union
  const getAllAmenities = () => {
    const set = new Set();
    for (const p of _compareLatest.current.items) {
      if (Array.isArray(p.declaredAmenities)) {
        for (const a of p.declaredAmenities) {
          if (a && typeof a === "string" && a.trim()) set.add(a.trim());
        }
      }
    }
    return Array.from(set);
  };

  // Grouped Criteria Matrix
  const getCriteriaGroups = () => {
    const groups = [{
      name: "Tài chính & Hiệu quả",
      icon: "💰",
      rows: [{
        label: "Tổng giá chào",
        isDiff: items => new Set(items.map(p => getNumericPrice(p))).size > 1,
        render: p => ({
          highlight: true,
          text: compactPrice(p),
          sub: price(p)
        })
      }, {
        label: "Đơn giá / m²",
        isDiff: items => new Set(items.map(p => getUnitPricePerSqm(p))).size > 1,
        render: p => ({
          text: formatUnitPrice(p),
          highlight: false
        })
      }]
    }, {
      name: "Vị trí & Quy hoạch",
      icon: "📍",
      rows: [{
        label: "Quận / Huyện",
        isDiff: items => new Set(items.map(p => p.district || "")).size > 1,
        render: p => ({
          text: p.district || "—"
        })
      }, {
        label: "Tuyến đường & Phường",
        isDiff: items => new Set(items.map(p => `${p.address}-${p.ward}`)).size > 1,
        render: p => ({
          text: [p.address, p.ward].filter(Boolean).join(", ") || "—"
        })
      }, {
        label: "Hướng phong thủy",
        isDiff: items => new Set(items.map(p => p.direction || "")).size > 1,
        render: p => ({
          text: p.direction ? `🧭 Hướng ${p.direction}` : "—"
        })
      }]
    }, {
      name: "Quy mô & Thiết kế",
      icon: "📐",
      rows: [{
        label: "Loại hình BĐS",
        isDiff: items => new Set(items.map(p => p.propertyType)).size > 1,
        render: p => ({
          text: types[p.propertyType] || p.propertyType
        })
      }, {
        label: "Diện tích đất / sàn",
        isDiff: items => new Set(items.map(p => getNumericArea(p))).size > 1,
        render: p => ({
          text: `${p.areaSqmExact ?? p.areaSqm} m²`
        })
      }, {
        label: "Số phòng ngủ",
        isDiff: items => new Set(items.map(p => p.bedrooms ?? "")).size > 1,
        render: p => ({
          text: p.bedrooms != null ? `${p.bedrooms} phòng ngủ` : "—"
        })
      }, {
        label: "Số phòng tắm / WC",
        isDiff: items => new Set(items.map(p => p.bathrooms ?? "")).size > 1,
        render: p => ({
          text: p.bathrooms != null ? `${p.bathrooms} phòng tắm` : "—"
        })
      }, {
        label: "Số tầng kết cấu",
        isDiff: items => new Set(items.map(p => p.floor ?? "")).size > 1,
        render: p => ({
          text: p.floor != null ? `${p.floor} tầng` : "—"
        })
      }]
    }];
    if (!showOnlyDiff.getSnapshot()) return groups;
    return groups.map(g => ({
      ...g,
      rows: g.rows.filter(r => r.isDiff(_compareLatest.current.items))
    })).filter(g => g.rows.length > 0);
  };

  // Map points for BrowseTileMap
  const getMapPoints = () => {
    return _compareLatest.current.items.filter(p => Number.isFinite(Number(p.latitude)) && Number.isFinite(Number(p.longitude))).map(p => ({
      id: p.id,
      latitude: Number(p.latitude),
      longitude: Number(p.longitude),
      title: p.title,
      transactionType: p.transactionType,
      priceExact: p.priceExact,
      price: p.price,
      priceUnit: p.priceUnit
    }));
  };
  return {
    ...inputProps,
    price,
    compactPrice,
    types,
    compare,
    dialog: dialog.getSnapshot(),
    busy: busy.getSnapshot(),
    error: error.getSnapshot(),
    showOnlyDiff: showOnlyDiff.getSnapshot(),
    showMap: showMap.getSnapshot(),
    visible: getVisible(),
    mixed: getMixed(),
    open,
    close,
    cover,
    metricsComparison: getMetricsComparison(),
    getPropertyHighlights,
    allAmenities: getAllAmenities(),
    criteriaGroups: getCriteriaGroups(),
    mapPoints: getMapPoints(),
    updateDialogValue: dialog.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateShowOnlyDiffValue: showOnlyDiff.set,
    updateShowMapValue: showMap.set
  };
}
export default React.forwardRef(function ComparisonTray(props, ref) {
  const view = useComparisonTrayState(props, ref);
  return <>{view.visible && view.compare.items.length ? <aside className="comparison-tray" aria-label="Các tin đã chọn để so sánh" data-sp-f380b3c4="">
        <div className="tray-items" data-sp-f380b3c4="">
          <div className="tray-count-badge" data-sp-f380b3c4="">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" data-sp-f380b3c4="">
              <path d="M16 3h5v5M4 20L21 3m0 13v5h-5M4 4l5 5" data-sp-f380b3c4="" />
            </svg>
            <strong data-sp-f380b3c4="">
              {"So sánh "}
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.compare.items.length)}
              {"/3"}
            </strong>
          </div>
          {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.compare.items, item => <div key={item.id} className="tray-chip" data-sp-f380b3c4="">
              <div className="chip-thumb" data-sp-f380b3c4="">
                <PrivateImage src={view.cover(item)} alt={item.title} data-sp-f380b3c4="" />
              </div>
              <span className="chip-title" title={item.title} data-sp-f380b3c4="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.title)}
              </span>
              <button type="button" disabled={view.busy} aria-label={"Bỏ so sánh " + item.title} className="chip-remove" onClick={$event => {
            view.compare.toggle(item);
          }} data-sp-f380b3c4="">
                {"×"}
              </button>
            </div>)}
        </div>
        <div className="tray-actions" data-sp-f380b3c4="">
          <button type="button" className="btn-clear" disabled={view.busy} onClick={$event => {
          return view.compare.clear?.($event);
        }} data-sp-f380b3c4="">
            {"Xóa hết"}
          </button>
          <button type="button" className="btn-compare primary" disabled={view.busy || view.compare.items.length < 2} onClick={$event => {
          return view.open?.($event);
        }} data-sp-f380b3c4="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.busy ? "Đang kiểm tra…" : `So sánh ngay (${view.compare.items.length}) ↗`)}
          </button>
        </div>
        {view.compare.notice || view.error ? <p className="tray-status" role="status" data-sp-f380b3c4="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error || view.compare.notice)}
          </p> : null}
      </aside> : null}<dialog data-ui-view="ComparisonTray" ref={view.updateDialogValue} aria-labelledby="compare-heading" onClick={$event => {
      return (event => {
        if (event.target === view.dialog) view.close();
      })?.($event);
    }} data-sp-f380b3c4="" {...view.rootAttributes} className={classNames(["comparison-dialog", view.rootAttributes.className])}>
      <div className="dialog-inner" data-sp-f380b3c4="">
        <header className="dialog-header" data-sp-f380b3c4="">
          <div data-sp-f380b3c4="">
            <div className="dialog-badge" data-sp-f380b3c4="">
              {"SMARTPROP / BỘ SO SÁNH TRỰC QUAN"}
            </div>
            <h2 id="compare-heading" data-sp-f380b3c4="">
              {"So sánh bất động sản"}
            </h2>
            <p className="dialog-subtitle" data-sp-f380b3c4="">
              {"Phân tích đa chiều về giá cả, đơn giá/m², quy mô và vị trí địa lý tương quan"}
            </p>
          </div>
          <div className="dialog-controls" data-sp-f380b3c4="">
            <label className={classNames(["toggle-btn", {
              active: view.showOnlyDiff
            }])} data-sp-f380b3c4="">
              <input type="checkbox" data-sp-f380b3c4="" checked={Array.isArray(view.showOnlyDiff) ? view.showOnlyDiff.includes("on") : !!view.showOnlyDiff} onChange={event => ($value => {
                view.updateShowOnlyDiffValue($value);
              })(Array.isArray(view.showOnlyDiff) ? event.target.checked ? [...view.showOnlyDiff, "on"] : view.showOnlyDiff.filter(item => item !== "on") : event.target.checked)} />
              <span data-sp-f380b3c4="">
                {"⚡ Chỉ xem điểm khác biệt"}
              </span>
            </label>
            {view.mapPoints.length ? <button type="button" className={classNames(["btn-map-toggle", {
              active: view.showMap
            }])} onClick={$event => {
              view.updateShowMapValue(!view.showMap);
            }} data-sp-f380b3c4="">
                {" 🗺️ "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.showMap ? "Ẩn bản đồ" : "Xem bản đồ vị trí")}
              </button> : null}
            <button type="button" className="btn-close" aria-label="Đóng so sánh" onClick={$event => {
              return view.close?.($event);
            }} data-sp-f380b3c4="">
              {"✕"}
            </button>
          </div>
        </header>
        {view.mixed ? <div className="mixed-note" data-sp-f380b3c4="">
            {" ⚠️ "}
            <strong data-sp-f380b3c4="">
              {"Lưu ý:"}
            </strong>
            {" Các tin có hình thức giao dịch hoặc đơn vị tính khác nhau (Bán vs Cho thuê). Hệ thống không so sánh trực tiếp tổng giá bán với giá thuê theo kỳ. "}
          </div> : null}
        {view.metricsComparison ? <section className="metrics-dashboard" data-sp-f380b3c4="">
            <h3 className="section-title" data-sp-f380b3c4="">
              {"📊 Trực quan hóa tương quan chỉ số"}
            </h3>
            <div className="metrics-grid" data-sp-f380b3c4="">
              <div className="metric-card" data-sp-f380b3c4="">
                <div className="metric-head" data-sp-f380b3c4="">
                  <span className="metric-name" data-sp-f380b3c4="">
                    {"Tổng giá chào"}
                  </span>
                  <span className="metric-sub" data-sp-f380b3c4="">
                    {"Thấp nhất là lợi thế"}
                  </span>
                </div>
                <div className="metric-bars" data-sp-f380b3c4="">
                  {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.metricsComparison.priceBars, (b, idx) => <div key={b.id} className="bar-row" data-sp-f380b3c4="">
                      <span className={classNames(["bar-index", "prop-idx-" + idx])} data-sp-f380b3c4="">
                        {"Căn "}
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(idx + 1)}
                      </span>
                      <div className="bar-track" data-sp-f380b3c4="">
                        <div className={classNames(["bar-fill", ["fill-" + idx, {
                      best: b.isLowest
                    }]])} style={{
                      width: b.pct + "%"
                    }} data-sp-f380b3c4="" />
                      </div>
                      <span className="bar-val" data-sp-f380b3c4="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(b.label)}
                      </span>
                      {b.isLowest ? <span className="bar-badge green" data-sp-f380b3c4="">
                          {"✓ Giá tốt"}
                        </span> : null}
                    </div>)}
                </div>
              </div>
              {view.metricsComparison.unitBars.length ? <div className="metric-card" data-sp-f380b3c4="">
                  <div className="metric-head" data-sp-f380b3c4="">
                    <span className="metric-name" data-sp-f380b3c4="">
                      {"Đơn giá trên mỗi m²"}
                    </span>
                    <span className="metric-sub" data-sp-f380b3c4="">
                      {"Đo lường độ đắt / rẻ thực tế"}
                    </span>
                  </div>
                  <div className="metric-bars" data-sp-f380b3c4="">
                    {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.metricsComparison.unitBars, (b, idx) => <div key={b.id} className="bar-row" data-sp-f380b3c4="">
                        <span className={classNames(["bar-index", "prop-idx-" + idx])} data-sp-f380b3c4="">
                          {"Căn "}
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(idx + 1)}
                        </span>
                        <div className="bar-track" data-sp-f380b3c4="">
                          <div className={classNames(["bar-fill", ["fill-" + idx, {
                      best: b.isLowest
                    }]])} style={{
                      width: b.pct + "%"
                    }} data-sp-f380b3c4="" />
                        </div>
                        <span className="bar-val" data-sp-f380b3c4="">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(b.label)}
                        </span>
                        {b.isLowest && b.savingPct > 0 ? <span className="bar-badge green" data-sp-f380b3c4="">
                            {"Tiết kiệm "}
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(b.savingPct)}
                            {"%"}
                          </span> : null}
                      </div>)}
                  </div>
                </div> : null}
              <div className="metric-card" data-sp-f380b3c4="">
                <div className="metric-head" data-sp-f380b3c4="">
                  <span className="metric-name" data-sp-f380b3c4="">
                    {"Diện tích sử dụng"}
                  </span>
                  <span className="metric-sub" data-sp-f380b3c4="">
                    {"Không gian sống"}
                  </span>
                </div>
                <div className="metric-bars" data-sp-f380b3c4="">
                  {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.metricsComparison.areaBars, (b, idx) => <div key={b.id} className="bar-row" data-sp-f380b3c4="">
                      <span className={classNames(["bar-index", "prop-idx-" + idx])} data-sp-f380b3c4="">
                        {"Căn "}
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(idx + 1)}
                      </span>
                      <div className="bar-track" data-sp-f380b3c4="">
                        <div className={classNames(["bar-fill", ["fill-" + idx, {
                      best: b.isLargest
                    }]])} style={{
                      width: b.pct + "%"
                    }} data-sp-f380b3c4="" />
                      </div>
                      <span className="bar-val" data-sp-f380b3c4="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(b.label)}
                      </span>
                      {b.isLargest ? <span className="bar-badge gold" data-sp-f380b3c4="">
                          {"Rộng nhất"}
                        </span> : null}
                    </div>)}
                </div>
              </div>
              {view.metricsComparison.distance ? <div className="metric-card distance-card" data-sp-f380b3c4="">
                  <div className="metric-head" data-sp-f380b3c4="">
                    <span className="metric-name" data-sp-f380b3c4="">
                      {"Khoảng cách địa lý"}
                    </span>
                    <span className="metric-sub" data-sp-f380b3c4="">
                      {"Giữa 2 bất động sản"}
                    </span>
                  </div>
                  <div className="distance-content" data-sp-f380b3c4="">
                    <div className="distance-icon" data-sp-f380b3c4="">
                      {"📍 ⟷ 📍"}
                    </div>
                    <div className="distance-number" data-sp-f380b3c4="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.metricsComparison.distance)}
                    </div>
                    <p className="distance-desc" data-sp-f380b3c4="">
                      {"Khoảng cách đường chim bay giữa 2 vị trí trên bản đồ Đà Nẵng"}
                    </p>
                  </div>
                </div> : null}
            </div>
          </section> : null}
        {view.showMap && view.mapPoints.length ? <section className="map-section" data-sp-f380b3c4="">
            <div className="map-header" data-sp-f380b3c4="">
              <div className="map-title" data-sp-f380b3c4="">
                <span className="pin-symbol" data-sp-f380b3c4="">
                  {"📍"}
                </span>
                <strong data-sp-f380b3c4="">
                  {"Bản đồ so sánh vị trí địa lý tương quan"}
                </strong>
                <span className="map-hint" data-sp-f380b3c4="">
                  {"Đã ghim "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.mapPoints.length)}
                  {" bất động sản trên cùng bản đồ"}
                </span>
              </div>
            </div>
            <div className="map-viewport-wrapper" data-sp-f380b3c4="">
              <BrowseTileMap points={view.mapPoints} data-sp-f380b3c4="" />
            </div>
          </section> : null}
        <section className="table-container" data-sp-f380b3c4="">
          <h3 className="section-title" data-sp-f380b3c4="">
            {"📋 Bảng ma trận so sánh chi tiết"}
          </h3>
          <div className="table-scroll" tabIndex="0" role="region" aria-label="Bảng so sánh chi tiết, cuộn ngang để xem thêm" data-sp-f380b3c4="">
            <table className="comparison-table" data-sp-f380b3c4="">
              <thead data-sp-f380b3c4="">
                <tr data-sp-f380b3c4="">
                  <th scope="col" className="corner-header" data-sp-f380b3c4="">
                    <div className="criteria-header-box" data-sp-f380b3c4="">
                      <span data-sp-f380b3c4="">
                        {"Tiêu chí so sánh"}
                      </span>
                      {view.showOnlyDiff ? <small data-sp-f380b3c4="">
                          {"Đang lọc điểm khác"}
                        </small> : null}
                    </div>
                  </th>
                  {((items, render) => typeof items === "number" ? Array.from({
                    length: Math.max(0, items)
                  }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.compare.items, (p, idx) => <th key={p.id} scope="col" className="property-col-header" data-sp-f380b3c4="">
                      <div className="prop-card-header" data-sp-f380b3c4="">
                        <div className="card-badge-row" data-sp-f380b3c4="">
                          <span className={classNames(["card-num-pill", "bg-idx-" + idx])} data-sp-f380b3c4="">
                            {"Căn "}
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(idx + 1)}
                          </span>
                          <span className="card-type-pill" data-sp-f380b3c4="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.types[p.propertyType] || p.propertyType)}
                          </span>
                          <button type="button" className="btn-remove-col" title={"Bỏ so sánh " + p.title} onClick={$event => {
                          view.compare.toggle(p);
                        }} data-sp-f380b3c4="">
                            {"×"}
                          </button>
                        </div>
                        <div className="card-img-box" data-sp-f380b3c4="">
                          <PrivateImage src={view.cover(p)} alt={p.title} data-sp-f380b3c4="" />
                          <span className="card-tag" data-sp-f380b3c4="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(p.transactionType === "RENT" ? "Cho thuê" : "Bán")}
                          </span>
                        </div>
                        <div className="card-info-box" data-sp-f380b3c4="">
                          <SiteLink to={"/listing/" + p.id} className="card-title-link" title={p.title} onClick={$event => {
                          return view.close?.($event);
                        }} data-sp-f380b3c4="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(p.title)}
                            {" ↗ "}
                          </SiteLink>
                          <div className="card-price-row" data-sp-f380b3c4="">
                            <strong className="card-price-compact" data-sp-f380b3c4="">
                              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.compactPrice(p))}
                            </strong>
                            <span className="card-price-full" data-sp-f380b3c4="">
                              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.price(p))}
                            </span>
                          </div>
                        </div>
                        <div className="card-advantages" data-sp-f380b3c4="">
                          {((items, render) => typeof items === "number" ? Array.from({
                          length: Math.max(0, items)
                        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.getPropertyHighlights(p), badge => <span key={badge.text} className={classNames(["advantage-pill", badge.type])} data-sp-f380b3c4="">
                              {" ★ "}
                              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(badge.text)}
                            </span>)}
                        </div>
                        <SiteLink to={"/listing/" + p.id} className="btn-view-detail" onClick={$event => {
                        return view.close?.($event);
                      }} data-sp-f380b3c4="">
                          {" Xem chi tiết tin ↗ "}
                        </SiteLink>
                      </div>
                    </th>)}
                </tr>
              </thead>
              <tbody data-sp-f380b3c4="">
                {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.criteriaGroups, group => <React.Fragment key={group.name}>
                    <tr className="group-header-row" data-sp-f380b3c4="">
                      <th colSpan={view.compare.items.length + 1} scope="colgroup" data-sp-f380b3c4="">
                        <span className="group-icon" data-sp-f380b3c4="">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(group.icon)}
                        </span>
                        <span className="group-title" data-sp-f380b3c4="">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(group.name)}
                        </span>
                      </th>
                    </tr>
                    {((items, render) => typeof items === "number" ? Array.from({
                    length: Math.max(0, items)
                  }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(group.rows, row => <tr key={row.label} className="data-row" data-sp-f380b3c4="">
                        <th scope="row" className="row-label" data-sp-f380b3c4="">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(row.label)}
                        </th>
                        {((items, render) => typeof items === "number" ? Array.from({
                      length: Math.max(0, items)
                    }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.compare.items, p => <td key={p.id} className="row-cell" data-sp-f380b3c4="">
                            {row.render(p).sub ? <div className="cell-price-box" data-sp-f380b3c4="">
                                <strong className="cell-main-price" data-sp-f380b3c4="">
                                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(row.render(p).text)}
                                </strong>
                                <small className="cell-sub-price" data-sp-f380b3c4="">
                                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(row.render(p).sub)}
                                </small>
                              </div> : <span className={classNames(["cell-text", {
                        "text-highlight": row.render(p).highlight
                      }])} data-sp-f380b3c4="">
                                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(row.render(p).text)}
                              </span>}
                          </td>)}
                      </tr>)}
                  </React.Fragment>)}
                {view.allAmenities.length ? <tr className="group-header-row" data-sp-f380b3c4="">
                    <th colSpan={view.compare.items.length + 1} scope="colgroup" data-sp-f380b3c4="">
                      <span className="group-icon" data-sp-f380b3c4="">
                        {"✨"}
                      </span>
                      <span className="group-title" data-sp-f380b3c4="">
                        {"Tiện ích khai báo & Điểm nổi bật"}
                      </span>
                    </th>
                  </tr> : null}
                {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.allAmenities, amenity => <tr key={amenity} className="data-row" data-sp-f380b3c4="">
                    <th scope="row" className="row-label" data-sp-f380b3c4="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(amenity)}
                    </th>
                    {((items, render) => typeof items === "number" ? Array.from({
                    length: Math.max(0, items)
                  }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.compare.items, p => <td key={p.id} className="row-cell" data-sp-f380b3c4="">
                        {p.declaredAmenities?.includes(amenity) ? <span className="amenity-pill has" data-sp-f380b3c4="">
                            {" ✓ Có sẵn "}
                          </span> : <span className="amenity-pill missing" data-sp-f380b3c4="">
                            {" — Chưa có "}
                          </span>}
                      </td>)}
                  </tr>)}
                <tr className="group-header-row" data-sp-f380b3c4="">
                  <th colSpan={view.compare.items.length + 1} scope="colgroup" data-sp-f380b3c4="">
                    <span className="group-icon" data-sp-f380b3c4="">
                      {"🛡️"}
                    </span>
                    <span className="group-title" data-sp-f380b3c4="">
                      {"Pháp lý & Giấy tờ"}
                    </span>
                  </th>
                </tr>
                <tr className="data-row" data-sp-f380b3c4="">
                  <th scope="row" className="row-label" data-sp-f380b3c4="">
                    {"Tình trạng pháp lý"}
                  </th>
                  {((items, render) => typeof items === "number" ? Array.from({
                    length: Math.max(0, items)
                  }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.compare.items, p => <td key={p.id} className="row-cell" data-sp-f380b3c4="">
                      <span className="legal-badge" data-sp-f380b3c4="">
                        {"Sổ đỏ / Sổ hồng chính chủ"}
                      </span>
                      <small className="legal-note" data-sp-f380b3c4="">
                        {"Xem hồ sơ công khai tại trang chi tiết tin đăng"}
                      </small>
                    </td>)}
                </tr>
              </tbody>
            </table>
          </div>
        </section>
        <footer className="dialog-footer" data-sp-f380b3c4="">
          <p className="dialog-disclaimer" data-sp-f380b3c4="">
            {" * Thông tin, hình ảnh và giá chào do người đăng cung cấp. SmartProp hỗ trợ công cụ so sánh trực quan độc lập nhằm giúp bạn đưa ra quyết định tối ưu nhất. "}
          </p>
          <button type="button" className="btn-close-bottom" onClick={$event => {
            return view.close?.($event);
          }} data-sp-f380b3c4="">
            {"Đóng bảng so sánh"}
          </button>
        </footer>
      </div>
    </dialog></>;
});
