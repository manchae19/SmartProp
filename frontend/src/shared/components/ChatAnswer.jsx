import { afterPaint, classNames } from "../lib/ui.js";
import { createStateStore } from "../state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { chatPresentation } from "../../features/prediction/chatPresentation.js";
import { amenityIntent, loadAmenityMap, amenitySummary } from "../../features/prediction/chatAmenities.js";
import PropertyNearbyPanel from "../../features/prediction/PropertyNearbyPanel.jsx";
import ChatAmenityMap from "./ChatAmenityMap.jsx";
import AppIcon from "./AppIcon.jsx";
import "./ChatAnswer.css";
function ListingAnalysisBasis({ analysis }) {
  if (!analysis || analysis.basis !== 'PUBLIC_LISTING_CLAIMS') return null;
  const money = value => {
    const number = Number(value);
    return Number.isFinite(number) && number > 0 ? new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 2}).format(number) + ' đồng' : null;
  };
  const monthly = money(analysis.monthlyRentalClaimVnd);
  return <div className="listing-analysis-basis">
    <strong>Số liệu lấy từ tin đăng</strong>
    <ul>
      {money(analysis.askingPriceVnd) && <li>Giá chào: {money(analysis.askingPriceVnd)}.</li>}
      {Number(analysis.areaSqm) > 0 && <li>Diện tích kê khai: {new Intl.NumberFormat('vi-VN').format(Number(analysis.areaSqm))} m².</li>}
      {monthly && <li>Thu nhập được nêu trong {analysis.claimField === 'title' ? 'tiêu đề' : 'mô tả'}: {monthly}/tháng, chưa xác minh.</li>}
    </ul>
    <strong>Phép tính của SmartProp</strong>
    <ul>
      {money(analysis.askingPricePerDeclaredSqmVnd) && <li>Giá chào ÷ diện tích = khoảng {money(analysis.askingPricePerDeclaredSqmVnd)}/m².</li>}
      {monthly && analysis.grossRevenueToAskingPricePercent && <li>Thu nhập tháng × 12 ÷ giá chào × 100 = khoảng {new Intl.NumberFormat('vi-VN',{maximumFractionDigits:2}).format(Number(analysis.grossRevenueToAskingPricePercent))}%/năm, giả định thu đủ 12 tháng và chưa trừ chi phí.</li>}
      {!monthly && <li>Chưa đủ số liệu thu nhập thuê để tính tỷ lệ doanh thu.</li>}
    </ul>
    <p>Đây là nội dung người đăng kê khai và phép tính từ nội dung đó. Chưa có nguồn bên ngoài xác nhận giá, doanh thu hoặc pháp lý.</p>
  </div>;
}

function useChatAnswerState(inputProps, forwardedRef) {
  inputProps = {
    question: "",
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    question: "",
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [expanded] = useState(() => createStateStore(false));
  useSyncExternalStore(expanded.subscribe, expanded.getSnapshot);
  const getView = () => chatPresentation(_props.current.result, {historical:!!_props.current.historical});
  const getIntent = () => amenityIntent(_props.current.question, _props.current.result);
  const [mapData] = useState(() => createStateStore(null)),
    [mapStatus] = useState(() => createStateStore("idle"));
  useSyncExternalStore(mapStatus.subscribe, mapStatus.getSnapshot);
  useSyncExternalStore(mapData.subscribe, mapData.getSnapshot);
  const getSummary = () => getIntent().requested && mapData.getSnapshot()?.items?.length ? amenitySummary(mapData.getSnapshot()) : getView().summary;
  const _disposedRef = useRef(false);
  async function loadMap() {
    if (!getIntent().enabled || mapStatus.getSnapshot() === "loading") return;
    mapStatus.set("loading");
    try {
      const data = await loadAmenityMap(getIntent());
      if (!_disposedRef.current) {
        mapData.set(data);
        mapStatus.set("ready");
      }
    } catch {
      if (!_disposedRef.current) mapStatus.set("error");
    }
    if (!_disposedRef.current) {
      await afterPaint();
      _propsLatest.current.onResized?.();
    }
  }
  useEffect(() => {
    _disposedRef.current = false;
    const result = loadMap();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  useEffect(() => () => (() => {
    _disposedRef.current = true;
  })(), []);
  const getVisibleCards = () => expanded.getSnapshot() ? getView().cards : getView().cards.slice(0, 3);
  function expand() {
    _propsLatest.current.onReading?.();
    expanded.set(!expanded.getSnapshot());
  }
  function reading(event) {
    if (event.target.open) _propsLatest.current.onReading?.();
  }
  return {
    ...inputProps,
    expanded: expanded.getSnapshot(),
    view: getView(),
    intent: getIntent(),
    mapData: mapData.getSnapshot(),
    mapStatus: mapStatus.getSnapshot(),
    summary: getSummary(),
    loadMap,
    visibleCards: getVisibleCards(),
    expand,
    reading,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["historical", "result", "messageId", "question", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function ChatAnswer(props, ref) {
  const view = useChatAnswerState(props, ref);
  return <><div data-chat-answer="" data-generation-mode={view.result.generationMode} data-sp-73584f77="" {...view.rootAttributes} className={classNames(["chat-answer", view.rootAttributes.className])}>
      <div className="ai-bubble" data-chat-empty={!view.view.cards.length && !view.view.clarification && view.result.evidence.criteria?.budgetVnd ? "" : undefined} data-sp-73584f77="">
        <p className="ai-summary" data-chat-summary="" data-sp-73584f77="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.summary)}
        </p>
        {view.view.clarification ? <p className="clarification-note" role="status" data-chat-clarification="" data-sp-73584f77="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.view.clarification)}
          </p> : null}
        {view.view.fallback ? <p className="fallback-note" role="status" data-chat-fallback="" data-sp-73584f77="">
            {"Kết quả tham khảo từ dữ liệu hiện có."}
          </p> : null}
        {view.view.noMatches ? <p className="empty-followup" data-sp-73584f77="">
            {"Hãy nhắc lại ngân sách, loại BĐS và địa bàn trong câu hỏi tiếp theo. "}
            <SiteLink to="/advisor" data-sp-73584f77="">
              {"Mở bộ lọc"}
            </SiteLink>
          </p> : null}
        <p className="answer-basis" data-sp-73584f77="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.view.isListingSource ? "Phân tích từ tin đăng của người dùng · chưa có nguồn xác minh bên ngoài" : view.view.clarification ? "Cần bạn xác nhận trước khi tra cứu" : view.view.noMatches ? "Kết quả tra cứu dữ liệu công khai" : "Tổng hợp từ nguồn công khai · mở Nguồn để đối chiếu")}
        </p>
      </div>
      {view.intent.enabled || view.intent.requested ? <ChatAmenityMap data={view.mapData} status={view.mapStatus} message={view.intent.message} onRetry={$event => {
        return view.loadMap?.($event);
      }} onReading={$event => {
        view.onReading?.();
      }} data-sp-73584f77="" /> : null}
      {view.view.cards.length ? <section className="chat-properties" aria-label={"Bất động sản đề xuất trong phản hồi " + view.messageId} data-chat-properties="" data-sp-73584f77="">
          {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.visibleCards, (card, index) => <article key={card.id} className="chat-property" data-chat-property={card.id} data-sp-73584f77="">
              <div className="card-heading" data-sp-73584f77="">
                <span className="card-rank" data-sp-73584f77="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(String(index + 1).padStart(2, "0"))}
                </span>
                <p className="card-location" data-sp-73584f77="">
                  <AppIcon name="gis" data-sp-73584f77="" />
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(card.location)}
                </p>
              </div>
              <h3 data-sp-73584f77="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(card.title)}
              </h3>
              <div className="card-facts" data-sp-73584f77="">
                <p className="card-price" title={card.price.exact} data-sp-73584f77="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(card.price.text)}
                </p>
                <span aria-hidden="true" data-sp-73584f77="">
                  {"·"}
                </span>
                <p data-sp-73584f77="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(card.area)}
                  {" m²"}
                </p>
              </div>
              {card.reason ? <p className="card-reason" title={card.reason} data-sp-73584f77="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(card.reason)}
                </p> : null}
              <div className="card-footer" data-sp-73584f77="">
                <span className="card-score" hidden={card.score == null} data-sp-73584f77="">
                  <strong data-sp-73584f77="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(card.score)}
                  </strong>
                  {"/100 "}
                  <span data-sp-73584f77="">
                    {"phù hợp"}
                  </span>
                </span>
                {card.href && card.platform ? <SiteLink to={card.href} className="card-link" data-sp-73584f77="">
                    {"Xem chi tiết "}
                    <AppIcon name="arrow" data-sp-73584f77="" />
                  </SiteLink> : card.href ? <a href={card.href} target="_blank" rel="noopener noreferrer" className="card-link" data-sp-73584f77="">
                    {"Xem chi tiết "}
                    <AppIcon name="arrow" data-sp-73584f77="" />
                  </a> : <span className="no-link" data-sp-73584f77="">
                    {"Chưa có đường dẫn nguồn"}
                  </span>}
              </div>
              <PropertyNearbyPanel property={view.result.recommendedProperties.find(p=>p.id===card.id)} needs={view.result.evidence?.needs} />
              {card.warnings.length ? <p className="quality-note" data-sp-73584f77="">
                  {"Thông tin nguồn cần được đối chiếu trước khi quyết định."}
                </p> : null}
            </article>)}
          {view.view.cards.length > 3 ? <button type="button" className="expand-properties" aria-expanded={view.expanded} onClick={$event => {
          return view.expand?.($event);
        }} data-chat-expand="" data-sp-73584f77="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.expanded ? "Thu gọn danh sách" : "Xem tất cả " + view.view.cards.length + " bất động sản")}
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true" className={classNames({
            rotated: view.expanded
          })} data-sp-73584f77="">
                <path d="m6 9 6 6 6-6" data-sp-73584f77="" />
              </svg>
            </button> : null}
        </section> : null}
      {view.view.citations.length ? <details className="citation-panel" data-chat-sources="" onToggle={$event => {
        return view.reading?.($event);
      }} data-sp-73584f77="">
          <summary data-sp-73584f77="">
            <AppIcon name="report" data-sp-73584f77="" />
            <span data-sp-73584f77="">
              {view.view.isListingSource ? "Dữ liệu dùng để phân tích (" : "Nguồn tham khảo ("}
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.view.citations.length)}
              {")"}
            </span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true" className="source-chevron" data-sp-73584f77="">
              <path d="m6 9 6 6 6-6" data-sp-73584f77="" />
            </svg>
          </summary>
          <ol className="source-list" data-sp-73584f77="">
            {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.view.citations, source => <li key={source.sourceId} data-sp-73584f77="">
                <span className="source-number" data-sp-73584f77="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(source.number)}
                </span>
                <div className="source-body" data-sp-73584f77="">
                  {source.kind === 'PROPERTY_DETAIL' && view.result.evidence.listingAnalysis && <ListingAnalysisBasis analysis={view.result.evidence.listingAnalysis} />}
                  <a href={source.href} target="_blank" rel="noopener noreferrer" data-chat-citation="" data-sp-73584f77="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(source.kind === 'PROPERTY_DETAIL' ? 'Xem tin đăng gốc ↗' : source.label)}
                  </a>
                  <p data-sp-73584f77="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(source.basis)}
                  </p>

                </div>
              </li>)}
          </ol>
          {view.view.showOriginalAnswer && <details className="original-evidence" onToggle={$event => {
          return view.reading?.($event);
        }} data-sp-73584f77="">
            <summary data-sp-73584f77="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.view.generated ? "Xem câu trả lời đầy đủ" : "Xem nội dung đầy đủ")}
            </summary>
            <p className="original-answer" data-chat-original="" data-sp-73584f77="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.view.originalAnswer)}
            </p>
          </details>}
          {view.result.recommendedProperties.length ? <details className="original-evidence" onToggle={$event => {
          return view.reading?.($event);
        }} data-sp-73584f77="">
              <summary data-sp-73584f77="">
                {"Chi tiết giá và thông tin nguồn"}
              </summary>
              {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.result.recommendedProperties, property => <div key={property.id} className="property-audit" data-sp-73584f77="">
                  <strong data-sp-73584f77="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(property.title)}
                  </strong>
                  <p data-sp-73584f77="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.view.cards.find(c => c.id === property.id).price.exact)}
                    {" · Nguồn "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(property.source.name)}
                  </p>
                  {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(property.explanations, line => <p key={line} data-sp-73584f77="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(line)}
                    </p>)}
                  {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(property.warnings, warning => <p key={warning} data-sp-73584f77="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(warning)}
                    </p>)}
                  <code data-sp-73584f77="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(property.id)}
                  </code>
                </div>)}
            </details> : null}
          <details className="original-evidence" onToggle={$event => {
          return view.reading?.($event);
        }} data-sp-73584f77="">
            <summary data-sp-73584f77="">
              {"Giới hạn dữ liệu"}
            </summary>
            <ul data-sp-73584f77="">
              {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.view.limitations, item => <li key={item} data-sp-73584f77="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item)}
                </li>)}
            </ul>
          </details>
        </details> : null}
      {view.view.citations.length && !view.result?.evidence?.amenityIntent ? <p className="answer-caution" data-sp-73584f77="">
          {view.view.isListingSource ? "Các phép tính dựa trên số liệu người đăng kê khai; không phải kết quả thẩm định hoặc xác minh doanh thu." : "Giá rao và điểm phù hợp để tham khảo. Bằng chứng khu vực không chứng minh khoảng cách từ căn nhà."}
        </p> : null}
    </div></>;
});
