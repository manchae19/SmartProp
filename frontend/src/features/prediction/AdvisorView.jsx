import { afterPaint, classNames, numericInput } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import { hasActiveSession, sameRestrictedSession } from "../../shared/lib/restrictedSession.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { api, session } from "../auth/api.js";
import { createResearchAdvisorClient } from "./tinixAdvisor.js";
import { advisorRequest, parseAdvisorBudget, formatAdvisorBudget, createAdvisorClient, advisorMapData, advisorError } from "./advisor.js";
import { districts } from "../map/districts.js";
import AdvisorResults from "../../shared/components/AdvisorResults.jsx";
import "./AdvisorView.css";
function useAdvisorViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const auth = useSyncExternalStore(session.subscribe, session.getSnapshot);
  const defaults = () => ({
    budgetVnd: "2.000.000.000",
    purpose: "LIVING",
    propertyType: "ALL",
    minAreaSqm: "",
    district: "",
    ward: "",
    limit: 10
  });
  const [form] = useState(() => createStateStore(defaults()));
  useSyncExternalStore(form.subscribe, form.getSnapshot);
  const [busy] = useState(() => createStateStore(false)),
    [mapBusy] = useState(() => createStateStore(false)),
    [error] = useState(() => createStateStore("")),
    [result] = useState(() => createStateStore(null)),
    [points] = useState(() => createStateStore([])),
    [selected] = useState(() => createStateStore("")),
    [mapFailures] = useState(() => createStateStore(0));
  useSyncExternalStore(mapFailures.subscribe, mapFailures.getSnapshot);
  useSyncExternalStore(selected.subscribe, selected.getSnapshot);
  useSyncExternalStore(points.subscribe, points.getSnapshot);
  useSyncExternalStore(result.subscribe, result.getSnapshot);
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(mapBusy.subscribe, mapBusy.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  const [submitted] = useState(() => createStateStore(null)),
    [resultsHeading] = useState(() => createStateStore(null)),
    [budgetInput] = useState(() => createStateStore(null));
  useSyncExternalStore(budgetInput.subscribe, budgetInput.getSnapshot);
  useSyncExternalStore(resultsHeading.subscribe, resultsHeading.getSnapshot);
  useSyncExternalStore(submitted.subscribe, submitted.getSnapshot);
  const [recommend] = useState(() => createAdvisorClient(api));
  const [researchRecommend] = useState(() => createResearchAdvisorClient(api));
  const [research] = useState(() => createStateStore(false)),
    [researchAvailable] = useState(() => createStateStore(false));
  useSyncExternalStore(researchAvailable.subscribe, researchAvailable.getSnapshot);
  useSyncExternalStore(research.subscribe, research.getSnapshot);
  const _sequenceRef = useRef(0),
    _mapSequenceRef = useRef(0);
  const hasResearchAccess = snapshot => hasActiveSession(snapshot) && snapshot.user?.role === "ADMIN";
  useEffect(() => {
    let previous;
    let probe;
    const syncResearchScope = () => {
      const next = session.getSnapshot();
      if (previous && sameRestrictedSession(previous, next)) return;
      previous = next;
      probe?.abort();
      researchAvailable.set(false);
      research.set(false);
      reset();
      if (!hasResearchAccess(next)) return;
      const controller = new AbortController();
      probe = controller;
      api("/recommendations/research/config", { signal: controller.signal })
        .then(config => {
          if (!controller.signal.aborted) researchAvailable.set(config.enabled === true);
        }).catch(() => {});
    };
    const unsubscribe = session.subscribe(syncResearchScope);
    syncResearchScope();
    return () => {
      unsubscribe();
      probe?.abort();
    };
  }, []);
  function setResearch(value) {
    if (value && (!hasResearchAccess(session.getSnapshot()) || !researchAvailable.getSnapshot())) return;
    reset();
    research.set(value);
  }
  const money = value => new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0
  }).format(value);
  const getBudgetHint = () => {
    try {
      return formatAdvisorBudget(form.getSnapshot().budgetVnd) + " VNĐ";
    } catch {
      return "Nhập tổng số tiền VNĐ, ví dụ 2.350.000.000";
    }
  };
  const getDistrictSuggestions = () => [...new Set([...districts.filter(d => d !== "Tất cả"), ...(result.getSnapshot()?.topAreas || []).map(a => a.district)])];
  const getChanged = () => {
    if (!result.getSnapshot()) return false;
    try {
      return JSON.stringify(advisorRequest(form.getSnapshot())) !== JSON.stringify(submitted.getSnapshot());
    } catch {
      return true;
    }
  };
  const getSubmittedSummary = () => submitted.getSnapshot() ? [money(submitted.getSnapshot().budgetVnd), {
    LIVING: "Mua để ở",
    INVESTMENT: "Đầu tư",
    RENTAL: "Mua để cho thuê"
  }[submitted.getSnapshot().purpose], submitted.getSnapshot().district || "Tất cả khu vực", submitted.getSnapshot().ward, submitted.getSnapshot().minAreaSqm ? "Từ " + submitted.getSnapshot().minAreaSqm + " m²" : ""].filter(Boolean).join(" · ") : "";
  function formatBudget() {
    try {
      form.edit(draftValue => draftValue["budgetVnd"] = formatAdvisorBudget(form.getSnapshot().budgetVnd));
    } catch {
      /* Keep invalid text for an explicit validation error. */
    }
  }
  function budgetEquals(value) {
    try {
      return parseAdvisorBudget(form.getSnapshot().budgetVnd) === value;
    } catch {
      return false;
    }
  }
  async function loadMap() {
    if (!result.getSnapshot()) return;
    const current = _sequenceRef.current,
      mapCurrent = ++_mapSequenceRef.current,
      properties = result.getSnapshot().topProperties;
    mapBusy.set(true);
    mapFailures.set(0);
    try {
      const mapped = await advisorMapData(properties, path => api(path, {
        authenticated: false
      }));
      if (current === _sequenceRef.current && mapCurrent === _mapSequenceRef.current) {
        points.set(mapped.points);
        mapFailures.set(mapped.failedCount);
      }
    } finally {
      if (current === _sequenceRef.current && mapCurrent === _mapSequenceRef.current) mapBusy.set(false);
    }
  }
  async function submit() {
    const current = ++_sequenceRef.current;
    _mapSequenceRef.current++;
    busy.set(true);
    mapBusy.set(false);
    error.set("");
    result.set(null);
    points.set([]);
    selected.set("");
    mapFailures.set(0);
    const input = {
      ...form.getSnapshot()
    };
    try {
      const request = advisorRequest(input),
        response = await (research.getSnapshot() ? researchRecommend : recommend)(input);
      if (current !== _sequenceRef.current) return;
      submitted.set(request);
      result.set(response);
      await afterPaint();
      resultsHeading.getSnapshot()?.focus({
        preventScroll: true
      });
      void loadMap();
    } catch (failure) {
      if (current === _sequenceRef.current) error.set(research.getSnapshot() && [401, 403].includes(failure.status) ? "Cần phiên ADMIN hợp lệ và máy chủ demo nội bộ được bật. Không thể mở dữ liệu nghiên cứu bằng liên kết hoặc tham số URL." : advisorError(failure));
    } finally {
      if (current === _sequenceRef.current) busy.set(false);
    }
  }
  function reset() {
    _sequenceRef.current++;
    _mapSequenceRef.current++;
    form.edit(draftValue => Object.assign(draftValue, defaults()));
    busy.set(false);
    mapBusy.set(false);
    error.set("");
    result.set(null);
    submitted.set(null);
    points.set([]);
    selected.set("");
    mapFailures.set(0);
    afterPaint(() => budgetInput.getSnapshot()?.focus());
  }
  function adjust() {
    document.getElementById("advisor-form")?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",
      block: "start"
    });
    budgetInput.getSnapshot()?.focus({
      preventScroll: true
    });
  }
  function areaSelected(area) {
    form.edit(draftValue => draftValue["district"] = area.district);
    form.edit(draftValue => draftValue["ward"] = area.ward || "");
    submit();
  }
  useEffect(() => () => (() => {
    _sequenceRef.current++;
    _mapSequenceRef.current++;
  })(), []);
  return {
    ...inputProps,
    formatAdvisorBudget,
    form: form.getSnapshot(),
    busy: busy.getSnapshot(),
    mapBusy: mapBusy.getSnapshot(),
    error: error.getSnapshot(),
    result: result.getSnapshot(),
    points: points.getSnapshot(),
    selected: selected.getSnapshot(),
    mapFailures: mapFailures.getSnapshot(),
    research: research.getSnapshot(),
    researchAvailable: hasResearchAccess(auth) && researchAvailable.getSnapshot(),
    setResearch,
    budgetHint: getBudgetHint(),
    districtSuggestions: getDistrictSuggestions(),
    changed: getChanged(),
    submittedSummary: getSubmittedSummary(),
    formatBudget,
    budgetEquals,
    loadMap,
    submit,
    reset,
    adjust,
    areaSelected,
    updateResultsHeadingValue: resultsHeading.set,
    updateBudgetInputValue: budgetInput.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateForm: form.edit,
    updateSelectedValue: selected.set
  };
}
export default React.forwardRef(function AdvisorView(props, ref) {
  const view = useAdvisorViewState(props, ref);
  return <><section data-ui-view="AdvisorView" aria-labelledby="advisor-title" data-sp-731b6e1b="" {...view.rootAttributes} className={classNames(["sp-container advisor-page", view.rootAttributes.className])}>
      <div className="advisor-intro" data-sp-731b6e1b="">
        <p className="eyebrow" data-sp-731b6e1b="">
          {"SMARTPROP · TƯ VẤN BĐS"}
        </p>
        <h1 id="advisor-title" data-sp-731b6e1b="">
          {"Tìm không gian phù hợp với bạn"}
        </h1>
        <p data-sp-731b6e1b="">
          {"Chọn theo ngân sách và mục đích. So sánh khu vực, xem lý do đề xuất và đối chiếu vị trí trên bản đồ."}
        </p>
      </div>
      <p className="mb-5" data-sp-731b6e1b="">
        <SiteLink to="/advisor/chat" className="sp-button sp-button-secondary" data-chat-entry={true} data-sp-731b6e1b="">
          {"Trao đổi với AI Advisor ↗"}
        </SiteLink>
      </p>
      <div className={classNames(["safe-note", {
        "research-note": view.research
      }])} data-sp-731b6e1b="">
        <span aria-hidden="true" data-sp-731b6e1b="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.research ? "!" : "✓")}
        </span>
        <div data-sp-731b6e1b="">
          <strong data-sp-731b6e1b="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.research ? "Internal Demo — chỉ ADMIN" : "Chế độ an toàn")}
          </strong>
          <p data-sp-731b6e1b="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.research ? "Dữ liệu nghiên cứu TiniX AI — chưa xác minh. Lịch sử, chưa biết còn bán; chỉ nghiên cứu phi thương mại (CC BY-NC 4.0)." : "Chỉ hiển thị tin đủ điều kiện công khai. Không cần đăng nhập để tìm gợi ý.")}
          </p>
        </div>
      </div>
      {view.researchAvailable ? <div className="research-controls" data-sp-731b6e1b="">
          <button type="button" className="sp-button sp-button-secondary" aria-pressed={view.research} onClick={$event => {
          view.setResearch(!view.research);
        }} data-sp-731b6e1b="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.research ? "Quay lại chế độ an toàn" : "Mở Internal Demo TiniX AI")}
          </button>

        </div> : null}
      <form id="advisor-form" className="advisor-form" aria-busy={view.busy} onSubmit={$event => {
        $event.preventDefault();
        return view.submit?.($event);
      }} data-sp-731b6e1b="">
        <div className="form-heading" data-sp-731b6e1b="">
          <div data-sp-731b6e1b="">
            <h2 data-sp-731b6e1b="">
              {"Nhu cầu của bạn"}
            </h2>
            <p data-sp-731b6e1b="">
              {"Nhập tổng ngân sách mua bất động sản bằng VNĐ. Bạn có thể nhập số tiền bất kỳ."}
            </p>
          </div>
          <span className="required-note" data-sp-731b6e1b="">
            {"* Thông tin bắt buộc"}
          </span>
        </div>
        <fieldset disabled={view.busy} data-sp-731b6e1b="">
          <legend className="sr-only" data-sp-731b6e1b="">
            {"Bộ lọc gợi ý bất động sản"}
          </legend>
          <div className="form-grid" data-sp-731b6e1b="">
            <label className="budget-field" data-sp-731b6e1b="">
              {"Ngân sách tối đa (VNĐ) *"}
              <input ref={view.updateBudgetInputValue} onBlur={$event => {
                return view.formatBudget?.($event);
              }} name="budget" type="text" inputMode="numeric" maxLength="32" required={true} aria-describedby="budget-hint" autoComplete="off" data-sp-731b6e1b="" value={view.form.budgetVnd ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.budgetVnd = $value);
              })(event.target.value)} />
              <small id="budget-hint" data-sp-731b6e1b="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.budgetHint)}
              </small>
              <span className="budget-presets" data-sp-731b6e1b="">
                {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))([1, 2, 3, 5, 10], value => <button key={value} type="button" aria-pressed={view.budgetEquals(value * 1000000000)} onClick={$event => {
                  view.updateForm(draftValue => draftValue.budgetVnd = view.formatAdvisorBudget(String(value * 1000000000)));
                }} data-sp-731b6e1b="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(value)}
                    {" tỷ"}
                  </button>)}
              </span>
            </label>
            <label data-sp-731b6e1b="">
              {"Mục đích *"}
              <select name="purpose" data-sp-731b6e1b="" value={view.form.purpose ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.purpose = $value);
              })(event.target.value)}>
                <option value="LIVING" data-sp-731b6e1b="">
                  {"Mua để ở"}
                </option>
                <option value="INVESTMENT" data-sp-731b6e1b="">
                  {"Đầu tư"}
                </option>
                <option value="RENTAL" data-sp-731b6e1b="">
                  {"Mua để cho thuê"}
                </option>
              </select>
              <small data-sp-731b6e1b="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.form.purpose === "RENTAL" ? "Ngân sách mua nhà, không phải tiền thuê hàng tháng." : view.form.purpose === "INVESTMENT" ? "Điểm tham khảo, không dự báo lợi nhuận đầu tư." : "Ưu tiên mức phù hợp với nhu cầu đã nhập.")}
              </small>
            </label>
            <label data-sp-731b6e1b="">
              {"Loại bất động sản *"}
              <select name="propertyType" data-sp-731b6e1b="" value={view.form.propertyType ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.propertyType = $value);
              })(event.target.value)}>
                <option value="ALL" data-sp-731b6e1b="">
                  {"Tất cả loại"}
                </option>
                <option value="HOUSE" data-sp-731b6e1b="">
                  {"Nhà ở"}
                </option>
                <option value="APARTMENT" data-sp-731b6e1b="">
                  {"Căn hộ"}
                </option>
                <option value="LAND" data-sp-731b6e1b="">
                  {"Đất nền"}
                </option>
                <option value="VILLA" data-sp-731b6e1b="">
                  {"Biệt thự"}
                </option>
                <option value="ROOM" data-sp-731b6e1b="">
                  {"Phòng"}
                </option>
                <option value="COMMERCIAL" data-sp-731b6e1b="">
                  {"Bất động sản thương mại"}
                </option>
              </select>
            </label>
            <label data-sp-731b6e1b="">
              {"Diện tích tối thiểu (m²)"}
              <input name="minAreaSqm" type="number" min="0.1" max="1000000" step="any" placeholder="Không giới hạn" data-sp-731b6e1b="" value={view.form.minAreaSqm ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.minAreaSqm = $value);
              })(event.target.value)} />
              <small data-sp-731b6e1b="">
                {"Để trống nếu chưa có yêu cầu."}
              </small>
            </label>
            <label data-sp-731b6e1b="">
              {"Địa bàn"}
              <input name="district" list="advisor-districts" maxLength="100" placeholder="Tất cả khu vực" autoComplete="off" data-sp-731b6e1b="" value={view.form.district ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.district = $value);
              })(event.target.value)} />
              <small data-sp-731b6e1b="">
                {"Chọn gợi ý hoặc nhập địa bàn theo nguồn tin."}
              </small>
            </label>
            <label data-sp-731b6e1b="">
              {"Phường/xã"}
              <input name="ward" maxLength="100" placeholder="Không bắt buộc" data-sp-731b6e1b="" value={view.form.ward ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.ward = $value);
              })(event.target.value)} />
              <small data-sp-731b6e1b="">
                {"Nguồn chưa có phường/xã sẽ không khớp bộ lọc này."}
              </small>
            </label>
            <label data-sp-731b6e1b="">
              {"Số gợi ý"}
              <select name="limit" data-sp-731b6e1b="" value={view.form.limit ?? ""} onChange={event => ($value => {
                view.updateForm(draftValue => draftValue.limit = $value);
              })(numericInput(event.target.value))}>
                <option value={10} data-sp-731b6e1b="">
                  {"Tối đa 10 tin"}
                </option>
                <option value={5} data-sp-731b6e1b="">
                  {"Tối đa 5 tin"}
                </option>
              </select>
            </label>
          </div>
          <datalist id="advisor-districts" data-sp-731b6e1b="">
            {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.districtSuggestions, district => <option key={district} value={district} data-sp-731b6e1b="" />)}
          </datalist>
          <div className="form-footer" data-sp-731b6e1b="">
            <p data-sp-731b6e1b="">
              {"Điểm phù hợp được tính theo quy tắc tham khảo; không thay thế kiểm tra pháp lý, hiện trạng hoặc định giá độc lập."}
            </p>
            <div className="form-actions" data-sp-731b6e1b="">
              <button className="sp-button sp-button-secondary" type="button" onClick={$event => {
                return view.reset?.($event);
              }} data-sp-731b6e1b="">
                {"Đặt lại"}
              </button>
              <button className="sp-button sp-button-primary" type="submit" data-sp-731b6e1b="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.busy ? "Đang tìm gợi ý…" : "Tìm gợi ý phù hợp")}
              </button>
            </div>
          </div>
        </fieldset>
      </form>
      {view.error ? <div role="alert" className="advisor-error" data-sp-731b6e1b="">
          <div data-sp-731b6e1b="">
            <strong data-sp-731b6e1b="">
              {"Chưa thể tải gợi ý"}
            </strong>
            <p data-sp-731b6e1b="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}
            </p>
          </div>
          <button type="button" className="sp-button sp-button-secondary" onClick={$event => {
          return view.submit?.($event);
        }} data-sp-731b6e1b="">
            {"Thử lại"}
          </button>
        </div> : null}
      {view.busy ? <div role="status" className="loading-panel" data-sp-731b6e1b="">
          <span className="loading-spinner" aria-hidden="true" data-sp-731b6e1b="" />
          <div data-sp-731b6e1b="">
            <strong data-sp-731b6e1b="">
              {"Đang tìm gợi ý phù hợp…"}
            </strong>
            <p data-sp-731b6e1b="">
              {"Đối chiếu ngân sách, khu vực và điều kiện công khai."}
            </p>
          </div>
        </div> : null}
      {view.result ? <React.Fragment>
          <div className="submitted-heading" data-sp-731b6e1b="">
            <h2 ref={view.updateResultsHeadingValue} tabIndex="-1" data-sp-731b6e1b="">
              {"Kết quả tư vấn"}
            </h2>
            <p data-sp-731b6e1b="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.submittedSummary)}
            </p>
          </div>
          {view.changed ? <div role="status" className="changed-note" data-sp-731b6e1b="">
              {"Bạn đã thay đổi bộ lọc. Kết quả bên dưới vẫn theo nhu cầu đã gửi; bấm “Tìm gợi ý phù hợp” để cập nhật."}
            </div> : null}
          <AdvisorResults result={view.result} points={view.points} selectedId={view.selected} mapBusy={view.mapBusy} mapFailures={view.mapFailures} onSelect={$event => {
          view.updateSelectedValue($event);
        }} onArea={$event => {
          return view.areaSelected?.($event);
        }} onAdjust={$event => {
          return view.adjust?.($event);
        }} onRetryMap={$event => {
          return view.loadMap?.($event);
        }} data-sp-731b6e1b="" />
        </React.Fragment> : !view.busy && !view.error ? <div className="start-note" data-sp-731b6e1b="">
          <strong data-sp-731b6e1b="">
            {"Bắt đầu từ nhu cầu, kiểm tra bằng dữ liệu"}
          </strong>
          <p data-sp-731b6e1b="">
            {"Sau khi tìm, bạn có thể xem tối đa 5 khu vực và 10 bất động sản cùng điểm phù hợp, lý do và nguồn. Số kết quả phụ thuộc dữ liệu đủ điều kiện; hệ thống không thêm tin chưa xác minh."}
          </p>
        </div> : null}
    </section></>;
});
