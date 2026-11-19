import { afterPaint, classNames } from "../lib/ui.js";
import { createStateStore } from "../state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import BrowseTileMap from "../../features/map/BrowseTileMap.jsx";
import AmenityEvidence from "./AmenityEvidence.jsx";
import { advisorListingUrl, advisorWarning } from "../../features/prediction/advisor.js";
import "./AdvisorResults.css";
function useAdvisorResultsState(inputProps, forwardedRef) {
  inputProps = {
    points: (() => [])(),
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    points: (() => [])(),
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const cards = useRef(new Map()).current,
    [mapHost] = useState(() => createStateStore(null));
  useSyncExternalStore(mapHost.subscribe, mapHost.getSnapshot);
  const getLocated = () => new Set(_props.current.points.map(p => p.id));
  const getPointById = () => new Map(_props.current.points.map(p => [p.id, p]));
  const getIsResearch = () => _props.current.result.mode === "INTERNAL_DEMO";
  const getIsV11 = () => _props.current.result.method === "HEURISTIC_V1_1";
  const breakdownLabels = {
    budgetFit: "Ngân sách",
    areaFit: "Diện tích",
    propertyTypeFit: "Loại BĐS",
    amenityFit: "Tiện ích khu vực"
  };
  const typeLabel = type => ({
    HOUSE: "Nhà ở",
    APARTMENT: "Căn hộ",
    LAND: "Đất",
    VILLA: "Biệt thự/nhà liền kề"
  })[type] || type;
  const money = value => new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0
  }).format(value);
  const score = value => new Intl.NumberFormat("vi-VN", {
    maximumFractionDigits: 1
  }).format(value);
  const scrollBehavior = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth";
  async function selectFromMap(id) {
    _propsLatest.current.onSelect?.(id);
    await afterPaint();
    cards.get(id)?.scrollIntoView({
      behavior: scrollBehavior(),
      block: "center"
    });
    cards.get(id)?.focus({
      preventScroll: true
    });
  }
  async function selectFromCard(id) {
    _propsLatest.current.onSelect?.(id);
    await afterPaint();
    mapHost.getSnapshot()?.scrollIntoView({
      behavior: scrollBehavior(),
      block: "center"
    });
    mapHost.getSnapshot()?.querySelector('[role="region"]')?.focus({
      preventScroll: true
    });
  }
  return {
    ...inputProps,
    advisorListingUrl,
    advisorWarning,
    cards,
    located: getLocated(),
    pointById: getPointById(),
    isResearch: getIsResearch(),
    isV11: getIsV11(),
    breakdownLabels,
    typeLabel,
    money,
    score,
    selectFromMap,
    selectFromCard,
    updateMapHostValue: mapHost.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["result", "points", "selectedId", "mapBusy", "mapFailures", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function AdvisorResults(props, ref) {
  const view = useAdvisorResultsState(props, ref);
  return <><div data-sp-c098318d="" {...view.rootAttributes} className={classNames(["advisor-output", view.rootAttributes.className])}>
      <div className="section-heading" data-sp-c098318d="">
        <div data-sp-c098318d="">
          <p className="eyebrow" data-sp-c098318d="">
            {"TOP KHU VỰC"}
          </p>
          <h2 data-sp-c098318d="">
            {"Khu vực phù hợp với nhu cầu"}
          </h2>
        </div>
        <p data-sp-c098318d="">
          {"Tối đa 5 khu vực · "}
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.result.eligibleCandidateCount)}
          {" ứng viên đủ điều kiện"}
        </p>
      </div>
      {view.result.topAreas.length ? <div className="area-grid" data-sp-c098318d="">
          {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.result.topAreas, (area, i) => <article key={area.district + ":" + area.ward} className="area-card" data-advisor-area="" data-sp-c098318d="">
              <div className="area-top" data-sp-c098318d="">
                <span className="rank" data-sp-c098318d="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(String(i + 1).padStart(2, "0"))}
                </span>
                <span className="area-score" data-sp-c098318d="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.score(area.score))}
                  {"/100"}
                </span>
              </div>
              <h3 data-sp-c098318d="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(area.district)}
                {area.ward ? <span data-sp-c098318d="">
                    {" · "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(area.ward)}
                  </span> : null}
              </h3>
              <p data-sp-c098318d="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(area.candidateCount)}
                {" tin đủ điều kiện · Giá rao bình quân "}
                <strong data-sp-c098318d="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.money(area.averageAskingPriceVnd))}
                </strong>
              </p>
              {area.amenityScore != null ? <p className="area-amenity" data-area-amenity="" data-sp-c098318d="">
                  {"Tiện ích khu vực "}
                  <strong data-sp-c098318d="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.score(area.amenityScore))}
                    {"/100"}
                  </strong>
                  {area.amenityConfidence != null ? <span data-sp-c098318d="">
                      {" · tin cậy "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(Math.round(area.amenityConfidence * 100))}
                      {"%"}
                    </span> : null}
                  <span className="area-amenity-basis" data-sp-c098318d="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(area.amenityEvidenceBasis === "DIRECT_WARD_EVIDENCE" ? "cấp phường/xã" : "cấp quận/huyện")}
                  </span>
                </p> : view.isV11 ? <p className="area-amenity muted" data-area-amenity-missing="" data-sp-c098318d="">
                  {"Chưa có hồ sơ tiện ích cho khu vực này."}
                </p> : null}
              {area.poiEvidence?.length ? <ul className="area-pois" data-sp-c098318d="">
                  {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(area.poiEvidence, poi => <li key={poi.name + poi.category} data-sp-c098318d="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(poi.name)}{" "}
                      <span data-sp-c098318d="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(poi.category)}
                      </span>
                    </li>)}
                </ul> : null}
              <ul data-sp-c098318d="">
                {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(area.explanations, reason => <li key={reason} data-sp-c098318d="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(reason)}
                  </li>)}
              </ul>
              <p className="source" data-sp-c098318d="">
                {"Nguồn: "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(area.sources.join(", "))}
              </p>
              {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(area.warnings, warning => <p key={warning} className="quality-note" data-sp-c098318d="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.advisorWarning(warning))}
                </p>)}
              <button type="button" className="text-action" onClick={$event => {
            view.onArea?.(area);
          }} data-sp-c098318d="">
                {"Tìm trong khu vực này "}
                <span aria-hidden="true" data-sp-c098318d="">
                  {"→"}
                </span>
              </button>
            </article>)}
        </div> : view.result.topProperties.length ? <p className="muted" data-sp-c098318d="">
          {"Chưa đủ thông tin để xếp hạng khu vực. Bạn vẫn có thể xem các tin phù hợp bên dưới."}
        </p> : null}
      {!view.result.topProperties.length ? <div className="advisor-empty" role="status" data-advisor-empty="" data-sp-c098318d="">
          <span className="empty-icon" aria-hidden="true" data-sp-c098318d="">
            {"⌕"}
          </span>
          <h3 data-sp-c098318d="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.isResearch ? "Chưa có bản ghi nghiên cứu phù hợp" : "Chưa có gợi ý công khai phù hợp")}
          </h3>
          <p data-sp-c098318d="">
            {"Có thể chưa có tin khớp bộ lọc hoặc nguồn chưa đủ điều kiện công khai. Thử tăng ngân sách, giảm diện tích tối thiểu hoặc bỏ lọc khu vực."}
          </p>

          <button type="button" className="sp-button sp-button-secondary" onClick={$event => {
          view.onAdjust?.();
        }} data-sp-c098318d="">
            {"Điều chỉnh bộ lọc"}
          </button>
        </div> : null}
      <div className="result-grid" data-sp-c098318d="">
        <section aria-labelledby="property-title" data-sp-c098318d="">
          <div className="section-heading" data-sp-c098318d="">
            <div data-sp-c098318d="">
              <p className="eyebrow" data-sp-c098318d="">
                {"TOP BẤT ĐỘNG SẢN"}
              </p>
              <h2 id="property-title" data-sp-c098318d="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.result.topProperties.length)}
                {" tin được đề xuất"}
              </h2>
            </div>
          </div>
          {!view.result.topProperties.length ? <p className="muted" data-sp-c098318d="">
              {"Kết quả sẽ xuất hiện tại đây khi có tin phù hợp."}
            </p> : null}
          {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.result.topProperties, property => <article key={property.id} ref={el => el ? view.cards.set(property.id, el) : view.cards.delete(property.id)} tabIndex="-1" className={classNames(["property-card", {
            selected: view.selectedId === property.id
          }])} data-advisor-property={property.id} data-sp-c098318d="">
              <div className="property-top" data-sp-c098318d="">
                <span className="source-badge" data-sp-c098318d="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(property.source.kind === "TINIX_AI" ? "Dữ liệu nghiên cứu TiniX AI — chưa xác minh" : property.source.kind === "PROPERTY" ? "Tin công khai SmartProp" : "Nguồn đã xác minh")}
                </span>
                <span className="fit-score" data-sp-c098318d="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.score(property.score))}
                  <small data-sp-c098318d="">
                    {"/100"}
                  </small>
                </span>
              </div>
              {property.source.kind === "TINIX_AI" ? <p className="source" data-sp-c098318d="">
                  {"ID nội bộ: "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(property.source.recordKey)}
                  {" · "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.typeLabel(property.propertyType))}
                  {" · Lịch sử, chưa biết còn bán"}
                </p> : null}
              <p className="score-label" data-sp-c098318d="">
                {"Điểm phù hợp theo nhu cầu"}
              </p>
              <div className="score-track" role="meter" aria-label={"Điểm phù hợp: " + property.title} aria-valuemin="0" aria-valuemax="100" aria-valuenow={property.score} data-sp-c098318d="">
                <span style={{
                width: property.score + "%"
              }} data-sp-c098318d="" />
              </div>
              {view.isV11 && property.scoreBreakdown ? <ul className="breakdown" data-score-breakdown="" data-sp-c098318d="">
                  {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(property.scoreBreakdown, (value, key) => <li key={key} data-sp-c098318d="" style={{
                display: view.breakdownLabels[key] ? undefined : "none"
              }}>
                      <span data-sp-c098318d="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.breakdownLabels[key])}
                      </span>
                      <strong data-sp-c098318d="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.score(value))}
                      </strong>
                    </li>)}
                </ul> : null}
              <h3 data-sp-c098318d="">
                {view.advisorListingUrl(property) ? <a href={view.advisorListingUrl(property)} target={property.source.kind === "EXTERNAL" ? "_blank" : undefined} rel="noopener noreferrer" data-sp-c098318d="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(property.title)}
                    {property.source.kind === "EXTERNAL" ? <span className="sr-only" data-sp-c098318d="">
                        {" (mở nguồn trong thẻ mới)"}
                      </span> : null}
                  </a> : <span data-sp-c098318d="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(property.title)}
                  </span>}
              </h3>
              <p className="price" data-sp-c098318d="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.money(property.priceVnd))}{" "}
                <span data-sp-c098318d="">
                  {"· "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(property.areaSqm.toLocaleString("vi-VN"))}
                  {" m²"}
                </span>
              </p>
              <p className="location" data-sp-c098318d="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(property.district || "Chưa có địa bàn")}
                {property.ward ? <span data-sp-c098318d="">
                    {" · "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(property.ward)}
                  </span> : null}
              </p>
              {view.pointById.get(property.id)?.locationLabel ? <p className="source" data-sp-c098318d="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.pointById.get(property.id).locationLabel)}
                </p> : null}
              {view.isV11 && property.amenityEvidence ? <AmenityEvidence evidence={property.amenityEvidence} compact={true} data-sp-c098318d="" /> : null}
              <h4 data-sp-c098318d="">
                {"Vì sao phù hợp?"}
              </h4>
              <ul data-sp-c098318d="">
                {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(property.explanations, reason => <li key={reason} data-sp-c098318d="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(reason)}
                  </li>)}
              </ul>
              {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(property.warnings, warning => <p key={warning} className="quality-note" data-sp-c098318d="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.advisorWarning(warning))}
                </p>)}
              <div className="property-footer" data-sp-c098318d="">
                <span data-sp-c098318d="">
                  {"Nguồn: "}
                  <strong data-sp-c098318d="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(property.source.name)}
                  </strong>
                </span>
                {view.located.has(property.id) ? <button type="button" className="text-action" aria-pressed={view.selectedId === property.id} onClick={$event => {
                view.selectFromCard(property.id);
              }} data-sp-c098318d="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selectedId === property.id ? "Đang chọn trên bản đồ" : "Xem trên bản đồ")}
                  </button> : <span data-sp-c098318d="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.mapBusy ? "Đang tải vị trí…" : "Chưa có tọa độ công khai")}
                  </span>}
              </div>
            </article>)}
        </section>
        <aside ref={view.updateMapHostValue} className="gis" aria-labelledby="advisor-map-title" data-sp-c098318d="">
          <p className="eyebrow" data-sp-c098318d="">
            {"BẢN ĐỒ GIS"}
          </p>
          <h2 id="advisor-map-title" data-sp-c098318d="">
            {"Danh sách và vị trí cùng một nơi"}
          </h2>
          <p role="status" data-sp-c098318d="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.mapBusy ? "Đang tải vị trí công khai…" : view.points.length + "/" + view.result.topProperties.length + " tin có tọa độ công khai hợp lệ.")}
          </p>
          <div className="advisor-map" aria-busy={view.mapBusy} data-sp-c098318d="">
            <BrowseTileMap points={view.points} selectedId={view.selectedId} onSelect={$event => {
              return view.selectFromMap?.($event);
            }} data-sp-c098318d="" />
          </div>
          {view.mapFailures ? <p className="map-warning" role="status" data-sp-c098318d="">
              {"Chưa tải được một số vị trí. Danh sách gợi ý vẫn dùng được. "}
              <button type="button" className="text-action" disabled={view.mapBusy} onClick={$event => {
              view.onRetryMap?.();
            }} data-sp-c098318d="">
                {"Tải lại vị trí"}
              </button>
            </p> : null}
          <p className="map-note" data-sp-c098318d="">
            {"Chọn ghim để tìm thẻ tin tương ứng; chọn “Xem trên bản đồ” để định vị tin. Chỉ đặt ghim từ tọa độ công khai của chính bất động sản; không dùng tâm khu vực thay thế."}
          </p>
        </aside>
      </div>
      <details className="result-notes" data-sp-c098318d="">
        <summary data-sp-c098318d="">
          {"Cách hiểu kết quả và giới hạn dữ liệu"}
        </summary>
        {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.result.warnings, warning => <p key={warning} data-sp-c098318d="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.advisorWarning(warning))}
          </p>)}
        <p data-sp-c098318d="">
          {"Điểm phù hợp không phải độ chính xác định giá. Giá hiển thị là tổng giá rao bán; hãy kiểm tra nguồn và tình trạng bất động sản trước khi quyết định."}
        </p>
      </details>
    </div></>;
});
