import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useImperativeHandle, useEffect } from "react";
import { addressScopeConflict, accuracyLabel, geocodingSignature, geocodingConfiguration, normalizeAddressQuery, searchLocations, geocodingErrorMessage } from "./geocoding.js";
import "./AutomaticLocationSearch.css";
function useAutomaticLocationSearchState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [busy] = useState(() => createStateStore(false)),
    [consent] = useState(() => createStateStore(false)),
    [error] = useState(() => createStateStore("")),
    [status] = useState(() => createStateStore("")),
    [candidates] = useState(() => createStateStore([])),
    [selected] = useState(() => createStateStore(""));
  useSyncExternalStore(selected.subscribe, selected.getSnapshot);
  useSyncExternalStore(candidates.subscribe, candidates.getSnapshot);
  useSyncExternalStore(status.subscribe, status.getSnapshot);
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(consent.subscribe, consent.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  const [retryRemaining] = useState(() => createStateStore(0));
  useSyncExternalStore(retryRemaining.subscribe, retryRemaining.getSnapshot);
  const _retryTimerRef = useRef(undefined);
  function clearRetry() {
    clearInterval(_retryTimerRef.current);
    retryRemaining.set(0);
  }
  function waitBeforeRetry(seconds) {
    clearRetry();
    const until = Date.now() + Math.min(86400, Math.max(1, seconds)) * 1000;
    const tick = () => {
      retryRemaining.set(Math.max(0, Math.ceil((until - Date.now()) / 1000)));
      if (!retryRemaining.getSnapshot()) clearInterval(_retryTimerRef.current);
    };
    tick();
    _retryTimerRef.current = setInterval(tick, 1000);
  }
  const _revisionRef = useRef(0),
    _configRevisionRef = useRef(0);
  const [configuration] = useState(() => createStateStore(null)),
    [checking] = useState(() => createStateStore(true)),
    [configurationError] = useState(() => createStateStore(""));
  useSyncExternalStore(configurationError.subscribe, configurationError.getSnapshot);
  useSyncExternalStore(checking.subscribe, checking.getSnapshot);
  useSyncExternalStore(configuration.subscribe, configuration.getSnapshot);
  const [scopeUnavailable] = useState(() => createStateStore(false)), [districtScope] = useState(() => createStateStore(false));
  useSyncExternalStore(scopeUnavailable.subscribe,scopeUnavailable.getSnapshot);
  useSyncExternalStore(districtScope.subscribe,districtScope.getSnapshot);
  const getQuery = () => normalizeAddressQuery(_props.current);
  const getSearchScope = () => [_props.current.city === "Da Nang" ? "Đà Nẵng" : _props.current.city, _props.current.district, _props.current.ward].filter(Boolean).join(" · ");
  const getProviderName = () => configuration.getSnapshot()?.provider === "GOOGLE" ? "Google Maps" : "Geoapify";
  async function checkConfiguration() {
    const run = ++_configRevisionRef.current;
    checking.set(true);
    configurationError.set("");
    try {
      const value = await geocodingConfiguration();
      if (run === _configRevisionRef.current) configuration.set(value);
    } catch {
      if (run === _configRevisionRef.current) {
        configuration.set(null);
        configurationError.set("Chưa kiểm tra được dịch vụ tìm vị trí. Bạn vẫn có thể đặt ghim thủ công.");
      }
    } finally {
      if (run === _configRevisionRef.current) checking.set(false);
    }
  }
  const getSignature = () => geocodingSignature(_props.current);
  const getCanSearch = () => !addressScopeConflict(_props.current) && !_props.current.disabled && !checking.getSnapshot() && configuration.getSnapshot()?.available === true && !busy.getSnapshot() && retryRemaining.getSnapshot() === 0 && consent.getSnapshot() && !!_props.current.address?.trim() && !!_props.current.city?.trim();
  async function search(option) {
    const districtOnly = option === true;
    if (!getCanSearch()) return;
    const current = ++_revisionRef.current;
    busy.set(true);
    districtScope.set(districtOnly);
    scopeUnavailable.set(false);
    error.set("");
    status.set("");
    candidates.set([]);
    selected.set("");
    _propsLatest.current.onClear?.();
    try {
      const result = await searchLocations({
        ..._props.current,
        shareAddress: consent.getSnapshot(),
        districtOnly
      });
      if (current !== _revisionRef.current) return;
      candidates.set(result.candidates);
      scopeUnavailable.set(result.status === "SCOPE_UNAVAILABLE");
      status.set(result.candidates.length ? "Chọn một kết quả trong khu vực đã chọn để xem ghim đề xuất; chưa lưu hoặc xác nhận vị trí." : (result.status === "SCOPE_UNAVAILABLE" ? "Chưa có ranh giới phường đủ điều kiện để tìm theo lựa chọn hiện tại. Bạn có thể chủ động tìm trong quận bên dưới hoặc đặt ghim thủ công." : "Không tìm thấy địa điểm phù hợp trong phạm vi đang tìm. Thử địa chỉ số nhà/tên đường hoặc đặt ghim thủ công nếu đây là tên thương mại của dự án."));
      if (result.candidates.length === 1) {
        preview(result.candidates[0]);
        status.set(result.candidates[0].context?.precision === "APPROXIMATE_STREET" ? "Đã tìm thấy đường. Ghim đang là vị trí tham khảo trên đường, chưa phải căn nhà. Hãy chỉnh ghim tới vị trí thực tế rồi xác nhận." : "Đã đưa bản đồ đến gợi ý. Kiểm tra số nhà, vị trí và độ chính xác trước khi xác nhận.");
      }
    } catch (e) {
      if (current === _revisionRef.current) {
        error.set(geocodingErrorMessage(e));
        if (e.status === 429) waitBeforeRetry(e.retryAfter || 2);
      }
    } finally {
      if (current === _revisionRef.current) busy.set(false);
    }
  }
  function preview(candidate) {
    selected.set(candidate.id);
    _propsLatest.current.onPreview?.(candidate);
  }
  function clearSelection() {
    selected.set("");
  }
  useImperativeHandle(forwardedRef, () => ({
    clearSelection
  }), []);
  const _watched = getSignature();
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
      _revisionRef.current++;
      clearRetry();
      busy.set(false);
      consent.set(false);
      scopeUnavailable.set(false);districtScope.set(false);
      candidates.set([]);
      selected.set("");
      error.set("");
      status.set("");
      _propsLatest.current.onClear?.();
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  useEffect(() => {
    const result = checkConfiguration();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  useEffect(() => () => (() => {
    _revisionRef.current++;
    _configRevisionRef.current++;
    clearRetry();
  })(), []);
  return {
    ...inputProps,
    accuracyLabel,
    busy: busy.getSnapshot(),
    consent: consent.getSnapshot(),
    error: error.getSnapshot(),
    status: status.getSnapshot(),
    candidates: candidates.getSnapshot(),
    selected: selected.getSnapshot(),
    retryRemaining: retryRemaining.getSnapshot(),
    configuration: configuration.getSnapshot(),
    checking: checking.getSnapshot(),
    configurationError: configurationError.getSnapshot(),
    query: getQuery(),
    searchScope: getSearchScope(),
    providerName: getProviderName(),
    checkConfiguration,
    canSearch: getCanSearch(),
    scopeConflict: addressScopeConflict(_props.current),
    scopeUnavailable: scopeUnavailable.getSnapshot(),
    districtScope: districtScope.getSnapshot(),
    searchDistrict: () => search(true),
    search,
    preview,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["address", "city", "district", "ward", "disabled", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateConsentValue: consent.set
  };
}
export default React.forwardRef(function AutomaticLocationSearch(props, ref) {
  const view = useAutomaticLocationSearchState(props, ref);
  return <><div aria-busy={view.busy} data-sp-b9243b48="" {...view.rootAttributes} className={classNames(["automatic-location", view.rootAttributes.className])}>
      <div className="search-heading" data-sp-b9243b48="">
        <div data-sp-b9243b48="">
          <strong data-sp-b9243b48="">
            {"Tìm vị trí từ địa chỉ"}
          </strong>
          <p data-sp-b9243b48="">
            {"Giữ nguyên địa chỉ bạn nhập; kết quả tìm kiếm chỉ là đề xuất cần kiểm tra."}
          </p>
        </div>
        <button type="button" disabled={!view.canSearch} onClick={$event => {
          return view.search?.($event);
        }} data-sp-b9243b48="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.busy ? "Đang tìm…" : "Tìm vị trí tự động")}
        </button>
      </div>
      {view.checking ? <p role="status" data-sp-b9243b48="">
          {"Đang kiểm tra dịch vụ tìm vị trí…"}
        </p> : view.configurationError || !view.configuration?.available ? <p role="status" data-sp-b9243b48="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.configurationError || "Tìm vị trí tự động hiện chưa được bật trên hệ thống. Bạn vẫn có thể đặt ghim thủ công.")}{" "}
          <button type="button" className="check-service" disabled={view.disabled} onClick={$event => {
          return view.checkConfiguration?.($event);
        }} data-sp-b9243b48="">
            {"Kiểm tra lại"}
          </button>
        </p> : <label className="search-consent" data-sp-b9243b48="">
          <input type="checkbox" disabled={view.disabled || view.busy} data-sp-b9243b48="" checked={Array.isArray(view.consent) ? view.consent.includes("on") : !!view.consent} onChange={event => ($value => {
          view.updateConsentValue($value);
        })(Array.isArray(view.consent) ? event.target.checked ? [...view.consent, "on"] : view.consent.filter(item => item !== "on") : event.target.checked)} />
          {"Tôi đồng ý gửi địa chỉ này tới "}
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.providerName)}
          {" để tìm vị trí."}
        </label>}
      {view.configuration?.available && view.address?.trim() ? <p className="search-query" data-sp-b9243b48="">
          {"Địa chỉ dùng để tìm: "}
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.query)}
        </p> : null}
      {view.configuration?.available ? <p className="search-scope" data-sp-b9243b48="">
          {"Giới hạn tìm kiếm: "}
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.searchScope)}
          {". Ưu tiên khớp tên đường; phường dùng để hỗ trợ tìm. Kết quả phải nằm trong quận đã chọn; ranh giới phường có thể chưa được xác minh."}
        </p> : null}
      {view.scopeUnavailable && view.district ? <div className="search-scope-choice">
        <button type="button" disabled={!view.canSearch} onClick={()=>view.searchDistrict()}>Tìm trong quận {view.district} (không giới hạn phường)</button>
        <p>Chỉ mở rộng khi bạn bấm nút này. Địa chỉ gốc được giữ nguyên; kết quả vẫn cần kiểm tra ghim.</p>
      </div> : null}
      {view.districtScope ? <p role="status">Đang dùng phạm vi quận {view.district}; chưa đối chiếu ranh giới phường {view.ward || "đã nhập"}.</p> : null}
      {view.scopeConflict ? <p role="alert" className="search-error">{view.scopeConflict}</p> : null}
      {view.busy ? <p role="status" data-sp-b9243b48="">
          {"Đang tìm các vị trí phù hợp…"}
        </p> : null}
      {view.error ? <p role="alert" className="search-error" data-sp-b9243b48="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}
        </p> : null}
      {view.error ? <button type="button" disabled={!view.canSearch} onClick={$event => {
        return view.search?.($event);
      }} data-sp-b9243b48="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.retryRemaining ? "Thử lại sau " + view.retryRemaining + " giây" : "Thử lại tìm vị trí")}
        </button> : null}
      {view.status ? <p role="status" data-sp-b9243b48="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.status)}
        </p> : null}
      {view.candidates.length ? <fieldset className="search-results" data-sp-b9243b48="">
          <legend data-sp-b9243b48="">
            {"Các vị trí đề xuất"}
          </legend>
          {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.candidates, candidate => <label key={candidate.id} className={classNames(["search-result", {
          chosen: view.selected === candidate.id
        }])} data-sp-b9243b48="">
              <input type="radio" name="geocoding-result" checked={view.selected === candidate.id} disabled={view.disabled} onChange={$event => {
            view.preview(candidate);
          }} data-sp-b9243b48="" />
              <span data-sp-b9243b48="">
                <strong data-sp-b9243b48="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(candidate.formattedAddress)}
                </strong>
                <small data-sp-b9243b48="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.accuracyLabel(candidate))}
                </small>
                <small data-sp-b9243b48="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(candidate.attribution)}
                </small>
              </span>
            </label>)}
        </fieldset> : null}
      {view.candidates.some(candidate => candidate.provider === "GEOAPIFY") ? <p className="source-links" data-sp-b9243b48="">
          <a href="https://www.geoapify.com/" target="_blank" rel="noopener noreferrer" data-sp-b9243b48="">
            {"Powered by Geoapify"}
          </a>
          {" · "}
          <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer" data-sp-b9243b48="">
            {"© OpenStreetMap contributors"}
          </a>
        </p> : null}
      {view.candidates.some(candidate => candidate.provider === "GOOGLE") ? <p className="source-links" data-sp-b9243b48="">
          {"Google Maps · Gợi ý chỉ hiển thị trên Google; không sao chép vào bản nháp hoặc bản đồ OSM."}
        </p> : null}
    </div></>;
});
