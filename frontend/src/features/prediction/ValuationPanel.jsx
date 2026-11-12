import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { buildValuationPayload, createValuationClient, featureLabels, formatPrice, locationLabel, warningLabel } from "./valuation.js";
import { session, errorText } from "../auth/api.js";
import { createHistoryClient } from "./history.js";
import "./ValuationPanel.css";
function useValuationPanelState(inputProps, forwardedRef) {
  inputProps = {
    initialInput: (() => ({}))(),
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const props = {
    initialInput: (() => ({}))(),
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [history] = useState(() => createHistoryClient());
  const [saving] = useState(() => createStateStore(false)),
    [saved] = useState(() => createStateStore(false)),
    [saveError] = useState(() => createStateStore(""));
  useSyncExternalStore(saveError.subscribe, saveError.getSnapshot);
  useSyncExternalStore(saved.subscribe, saved.getSnapshot);
  useSyncExternalStore(saving.subscribe, saving.getSnapshot);
  const _resultInputRef = useRef(undefined),
    _saveKeyRef = useRef(undefined);
  const [client] = useState(() => createValuationClient());
  const [options] = useState(() => createStateStore(null));
  useSyncExternalStore(options.subscribe, options.getSnapshot);
  const [optionsLoading] = useState(() => createStateStore(false));
  useSyncExternalStore(optionsLoading.subscribe, optionsLoading.getSnapshot);
  const [optionsError] = useState(() => createStateStore(""));
  useSyncExternalStore(optionsError.subscribe, optionsError.getSnapshot);
  const [predicting] = useState(() => createStateStore(false));
  useSyncExternalStore(predicting.subscribe, predicting.getSnapshot);
  const [predictionError] = useState(() => createStateStore(""));
  useSyncExternalStore(predictionError.subscribe, predictionError.getSnapshot);
  const [result] = useState(() => createStateStore(null));
  useSyncExternalStore(result.subscribe, result.getSnapshot);
  const [form] = useState(() => createStateStore({}));
  useSyncExternalStore(form.subscribe, form.getSnapshot);
  const _optionsControllerRef = useRef(undefined);
  const _predictionControllerRef = useRef(undefined);
  const _generationRef = useRef(0);
  const getLocations = () => options.getSnapshot()?.categories.find(item => item.category === form.getSnapshot().category)?.locations ?? [];
  const getLegacyLocations = () => getLocations().filter(value => !value.startsWith("new_unit:"));
  const getExpandedLocations = () => getLocations().filter(value => value.startsWith("new_unit:"));
  const displayLocation = value => locationLabel(value, options.getSnapshot()?.location_labels);
  const getIsHouse = () => form.getSnapshot().category === "Nhà ở";
  const getIsApartment = () => form.getSnapshot().category === "Căn hộ chung cư";
  const getHasRooms = () => form.getSnapshot().category !== "Đất nền";
  const getMissingLabels = () => result.getSnapshot()?.missing_features.map(key => featureLabels[key] ?? "Thông tin bổ sung") ?? [];
  const getUsedFeatures = () => {
    if (!result.getSnapshot()) return [];
    return Object.entries(result.getSnapshot().features_used).filter(([, value]) => value !== null).map(([key, value]) => {
      if (key === "area_sqm") value = `${value} m²`;
      if (key === "location_feature") value = displayLocation(value);
      if (key === "ward_source") value = String(form.getSnapshot().ward ?? "").trim() || value;
      if (key === "access_type") value = options.getSnapshot().access_types[value];
      if (key === "house_subtype") value = options.getSnapshot().house_subtypes[value];
      return {
        label: featureLabels[key],
        value
      };
    });
  };
  function invalidate() {
    _generationRef.current++;
    _predictionControllerRef.current?.abort();
    result.set(null);
    predictionError.set("");
    predicting.set(false);
    saved.set(false);
    saving.set(false);
    saveError.set("");
    _resultInputRef.current = null;
    _saveKeyRef.current = null;
  }
  const _watched = form.getSnapshot();
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
    const result = invalidate(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  const _watched2 = (() => _props.current.initialInput)();
  const _previous2 = useRef(_watched2),
    _initialized2 = useRef(false);
  useEffect(() => {
    const previousValue = _previous2.current;
    _previous2.current = _watched2;
    let dispose;
    _initialized2.current = true;
    const result = (input => {
      invalidate();
      form.edit(draftValue => Object.assign(draftValue, {
        category: "Nhà ở",
        area_sqm: "",
        location_feature: "",
        ward: "",
        rooms: "",
        floors: "",
        access_type: "",
        house_subtype: ""
      }, input));
    })(_watched2, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched2)]);
  const _watched3 = (() => form.getSnapshot().category)();
  const _previous3 = useRef(_watched3),
    _initialized3 = useRef(false);
  useEffect(() => {
    const previousValue = _previous3.current;
    _previous3.current = _watched3;
    let dispose;
    if (!_initialized3.current) {
      _initialized3.current = true;
      return;
    }
    const result = (() => {
      if (!getHasRooms()) form.edit(draftValue => draftValue["rooms"] = "");
      if (!getIsHouse()) {
        form.edit(draftValue => draftValue["floors"] = "");
        form.edit(draftValue => draftValue["house_subtype"] = "");
      }
      if (getIsApartment()) form.edit(draftValue => draftValue["access_type"] = "");
      if (options.getSnapshot() && !getLocations().includes(form.getSnapshot().location_feature)) form.edit(draftValue => draftValue["location_feature"] = "");
    })(_watched3, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched3)]);
  async function loadOptions() {
    invalidate();
    _optionsControllerRef.current?.abort();
    const controller = new AbortController();
    _optionsControllerRef.current = controller;
    optionsLoading.set(true);
    optionsError.set("");
    try {
      const data = await client.getOptions({
        signal: controller.signal
      });
      if (controller.signal.aborted) return;
      options.set(data);
      _propsLatest.current.onOptionsLoaded?.(data.location_labels ?? {});
      if (!getLocations().includes(form.getSnapshot().location_feature)) form.edit(draftValue => draftValue["location_feature"] = "");
    } catch (error) {
      if (!controller.signal.aborted) optionsError.set(error.message);
    } finally {
      if (_optionsControllerRef.current === controller) optionsLoading.set(false);
    }
  }
  async function estimate() {
    invalidate();
    if (!options.getSnapshot()) return;
    let payload;
    try {
      payload = buildValuationPayload(form.getSnapshot(), options.getSnapshot());
    } catch (error) {
      predictionError.set(error.message);
      return;
    }
    const current = _generationRef.current;
    const controller = new AbortController();
    _predictionControllerRef.current = controller;
    predicting.set(true);
    try {
      const prediction = await client.predict(payload, {
        signal: controller.signal
      });
      if (current === _generationRef.current && !controller.signal.aborted) {
        result.set(prediction);
        _resultInputRef.current = payload;
        _saveKeyRef.current = globalThis.crypto.randomUUID();
      }
    } catch (error) {
      if (current === _generationRef.current && !controller.signal.aborted) predictionError.set(error.message);
    } finally {
      if (current === _generationRef.current) predicting.set(false);
    }
  }
  async function saveResult() {
    if (!_resultInputRef.current || !session.getSnapshot().token || saving.getSnapshot() || saved.getSnapshot()) return;
    const current = _generationRef.current,
      token = session.getSnapshot().token;
    saving.set(true);
    saveError.set("");
    try {
      await history.save(_resultInputRef.current, _saveKeyRef.current);
      if (current === _generationRef.current && token === session.getSnapshot().token) {
        saved.set(true);
        _propsLatest.current.onSaved?.();
      }
    } catch (error) {
      if (current === _generationRef.current && token === session.getSnapshot().token) saveError.set(errorText(error));
    } finally {
      if (current === _generationRef.current && token === session.getSnapshot().token) saving.set(false);
    }
  }
  const _watched4 = (() => session.getSnapshot().token)();
  const _previous4 = useRef(_watched4),
    _initialized4 = useRef(false);
  useEffect(() => {
    const previousValue = _previous4.current;
    _previous4.current = _watched4;
    let dispose;
    if (!_initialized4.current) {
      _initialized4.current = true;
      return;
    }
    const result = (() => {
      saved.set(false);
      saveError.set("");
      saving.set(false);
    })(_watched4, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched4)]);
  useEffect(() => {
    const result = loadOptions();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  useEffect(() => () => (() => {
    _generationRef.current++;
    _optionsControllerRef.current?.abort();
    _predictionControllerRef.current?.abort();
  })(), []);
  return {
    ...inputProps,
    formatPrice,
    warningLabel,
    session: session.getSnapshot(),
    saving: saving.getSnapshot(),
    saved: saved.getSnapshot(),
    saveError: saveError.getSnapshot(),
    options: options.getSnapshot(),
    optionsLoading: optionsLoading.getSnapshot(),
    optionsError: optionsError.getSnapshot(),
    predicting: predicting.getSnapshot(),
    predictionError: predictionError.getSnapshot(),
    result: result.getSnapshot(),
    form: form.getSnapshot(),
    legacyLocations: getLegacyLocations(),
    expandedLocations: getExpandedLocations(),
    displayLocation,
    isHouse: getIsHouse(),
    isApartment: getIsApartment(),
    hasRooms: getHasRooms(),
    missingLabels: getMissingLabels(),
    usedFeatures: getUsedFeatures(),
    loadOptions,
    estimate,
    saveResult,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["initialInput", "demo", "historyEnabled", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateForm: form.edit
  };
}
export default React.forwardRef(function ValuationPanel(props, ref) {
  const view = useValuationPanelState(props, ref);
  return <><section data-ui-view="ValuationPanel" aria-labelledby="valuation-heading" data-sp-018bbc28="" {...view.rootAttributes} className={classNames(["valuation-panel bg-[var(--ui-soft)] text-brand-navy rounded-[24px] p-6 md:p-8 shadow-sm", view.rootAttributes.className])}>
      <div className="flex flex-wrap items-start justify-between gap-3" data-sp-018bbc28="">
        <div data-sp-018bbc28="">
          <p className="text-xs text-brand-navy/60 uppercase tracking-widest" data-sp-018bbc28="">
            {"Định giá tham chiếu · XGBoost v6"}
          </p>
          <h2 id="valuation-heading" className="text-2xl font-semibold mt-2" data-sp-018bbc28="">
            {"Ước tính giá rao"}
          </h2>
        </div>
        {view.demo ? <span className="rounded-full bg-brand-card/10 px-3 py-1 text-xs text-brand-navy/80" data-sp-018bbc28="">
            {"Tin minh họa"}
          </span> : null}
      </div>
      <p className="text-sm text-brand-navy/70 mt-3 leading-6" data-sp-018bbc28="">
        {"Nhập thông tin hiện có. Các trường chưa rõ có thể để trống; kết quả được tính từ thông tin trong form này."}
      </p>
      {view.optionsLoading ? <p role="status" className="mt-5 text-sm text-brand-navy/80" data-sp-018bbc28="">
          {"Đang tải địa bàn được hỗ trợ…"}
        </p> : view.optionsError ? <div role="alert" className="mt-5 rounded-xl bg-brand-card/10 p-4" data-sp-018bbc28="">
          <p data-sp-018bbc28="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.optionsError)}
          </p>
          <button type="button" className="mt-3 underline underline-offset-4" onClick={$event => {
          return view.loadOptions?.($event);
        }} data-sp-018bbc28="">
            {"Thử kết nối lại"}
          </button>
        </div> : view.options ? <form className="mt-6" noValidate={true} onSubmit={$event => {
        $event.preventDefault();
        return view.estimate?.($event);
      }} data-sp-018bbc28="">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4" data-sp-018bbc28="">
            <label className="block text-sm" data-sp-018bbc28="">
              {"Loại bất động sản "}
              <span aria-hidden="true" data-sp-018bbc28="">
                {"*"}
              </span>
              <select required={true} className="valuation-input mt-2" data-sp-018bbc28="" value={view.form.category ?? ""} onChange={event => ($value => {
              view.updateForm(draftValue => draftValue.category = $value);
            })(event.target.value)}>
                {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.options.categories, item => <option key={item.category} value={item.category} data-sp-018bbc28="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.category)}
                  </option>)}
              </select>
            </label>
            <label className="block text-sm" data-sp-018bbc28="">
              {"Địa bàn "}
              <span aria-hidden="true" data-sp-018bbc28="">
                {"*"}
              </span>
              <select required={true} className="valuation-input mt-2" data-sp-018bbc28="" value={view.form.location_feature ?? ""} onChange={event => ($value => {
              view.updateForm(draftValue => draftValue.location_feature = $value);
            })(event.target.value)}>
                <option disabled={true} value="" data-sp-018bbc28="">
                  {"Chọn địa bàn"}
                </option>
                {view.legacyLocations.length ? <optgroup label="Quận/huyện cũ" data-sp-018bbc28="">
                    {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.legacyLocations, location => <option key={location} value={location} data-sp-018bbc28="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.displayLocation(location))}
                      </option>)}
                  </optgroup> : null}
                {view.expandedLocations.length ? <optgroup label="Địa bàn mở rộng trong dữ liệu" data-sp-018bbc28="">
                    {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.expandedLocations, location => <option key={location} value={location} data-sp-018bbc28="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.displayLocation(location))}
                      </option>)}
                  </optgroup> : null}
              </select>
            </label>
            <label className="block text-sm" data-sp-018bbc28="">
              {"Diện tích (m²) "}
              <span aria-hidden="true" data-sp-018bbc28="">
                {"*"}
              </span>
              <input type="number" min="20" max="1000" step="any" inputMode="decimal" required={true} className="valuation-input mt-2" placeholder="Ví dụ: 80" data-sp-018bbc28="" value={view.form.area_sqm ?? ""} onChange={event => ($value => {
              view.updateForm(draftValue => draftValue.area_sqm = $value);
            })(event.target.value)} />
              <span className="block mt-1 text-xs text-brand-navy/60" data-sp-018bbc28="">
                {"Từ 20 đến 1.000 m²"}
              </span>
            </label>
            <label className="block text-sm" data-sp-018bbc28="">
              {"Phường/xã theo tin "}
              <span className="text-brand-navy/70" data-sp-018bbc28="">
                {"· tùy chọn"}
              </span>
              <input maxLength="100" className="valuation-input mt-2" placeholder="Để trống nếu chưa rõ" data-sp-018bbc28="" value={view.form.ward ?? ""} onChange={event => ($value => {
              view.updateForm(draftValue => draftValue.ward = $value);
            })(event.target.value)} />
              <span className="block mt-1 text-xs text-brand-navy/60" data-sp-018bbc28="">
                {"Bổ sung nếu địa chỉ tin nêu rõ; có thể để trống."}
              </span>
            </label>
            {view.hasRooms ? <label className="block text-sm" data-sp-018bbc28="">
                {"Phòng ngủ "}
                <span className="text-brand-navy/70" data-sp-018bbc28="">
                  {"· tùy chọn"}
                </span>
                <input type="number" min="1" max="30" step="1" inputMode="numeric" className="valuation-input mt-2" placeholder="Chưa rõ" data-sp-018bbc28="" value={view.form.rooms ?? ""} onChange={event => ($value => {
              view.updateForm(draftValue => draftValue.rooms = $value);
            })(event.target.value)} />
              </label> : null}
            {view.isHouse ? <label className="block text-sm" data-sp-018bbc28="">
                {"Số tầng nhà "}
                <span className="text-brand-navy/70" data-sp-018bbc28="">
                  {"· tùy chọn"}
                </span>
                <input type="number" min="1" max="20" step="any" inputMode="decimal" className="valuation-input mt-2" placeholder="Chưa rõ" data-sp-018bbc28="" value={view.form.floors ?? ""} onChange={event => ($value => {
              view.updateForm(draftValue => draftValue.floors = $value);
            })(event.target.value)} />
              </label> : null}
            {!view.isApartment ? <label className="block text-sm" data-sp-018bbc28="">
                {"Lối vào "}
                <span className="text-brand-navy/70" data-sp-018bbc28="">
                  {"· tùy chọn"}
                </span>
                <select className="valuation-input mt-2" data-sp-018bbc28="" value={view.form.access_type ?? ""} onChange={event => ($value => {
              view.updateForm(draftValue => draftValue.access_type = $value);
            })(event.target.value)}>
                  <option value="" data-sp-018bbc28="">
                    {"Chưa rõ"}
                  </option>
                  {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.options.access_types, (label, value) => <option key={value} value={value} data-sp-018bbc28="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(label)}
                    </option>)}
                </select>
              </label> : null}
            {view.isHouse ? <label className="block text-sm" data-sp-018bbc28="">
                {"Loại nhà chi tiết "}
                <span className="text-brand-navy/70" data-sp-018bbc28="">
                  {"· tùy chọn"}
                </span>
                <select className="valuation-input mt-2" data-sp-018bbc28="" value={view.form.house_subtype ?? ""} onChange={event => ($value => {
              view.updateForm(draftValue => draftValue.house_subtype = $value);
            })(event.target.value)}>
                  <option value="" data-sp-018bbc28="">
                    {"Chưa rõ"}
                  </option>
                  {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.options.house_subtypes, (label, value) => <option key={value} value={value} data-sp-018bbc28="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(label)}
                    </option>)}
                </select>
              </label> : null}
          </div>
          <button type="submit" disabled={view.predicting} className="mt-6 rounded-full bg-brand-card px-6 py-3 text-sm font-semibold text-[var(--ui-accent)] hover:bg-[var(--ui-surface)] disabled:opacity-60 disabled:cursor-wait transition" data-sp-018bbc28="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.predicting ? "Đang ước tính…" : "Ước tính giá rao")}
          </button>
        </form> : null}
      <div aria-live="polite" aria-atomic="true" className="mt-5" data-sp-018bbc28="">
        {view.predicting ? <p role="status" className="text-sm text-brand-navy/80" data-sp-018bbc28="">
            {"Mô hình đang tính giá từ thông tin đã nhập…"}
          </p> : null}
        {view.predictionError ? <p role="alert" className="rounded-xl bg-[var(--ui-surface)] p-4 text-sm text-[var(--ui-ink)]" data-sp-018bbc28="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.predictionError)}
          </p> : null}
        {view.result ? <div className="border-t border-brand-line/20 pt-6" data-testid="valuation-result" data-sp-018bbc28="">
            <p className="text-sm text-brand-navy/70" data-sp-018bbc28="">
              {"Giá rao ước tính"}
            </p>
            <p className="text-3xl sm:text-4xl font-semibold mt-2" data-testid="estimated-price" data-sp-018bbc28="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.formatPrice(view.result.predicted_asking_price_vnd))}
            </p>
            <p className="text-sm text-brand-navy/70 mt-2" data-sp-018bbc28="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(new Intl.NumberFormat("vi-VN").format(view.result.predicted_asking_price_vnd))}
              {" đồng · Tổng giá bất động sản"}
            </p>
            {view.historyEnabled && !view.demo ? <div className="mt-4" data-sp-018bbc28="">
                {view.session.token ? <button type="button" disabled={view.saving || view.saved} className="rounded-full border border-brand-line/40 px-4 py-2 text-sm disabled:opacity-60" onClick={$event => {
              return view.saveResult?.($event);
            }} data-sp-018bbc28="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.saved ? "Đã lưu kết quả" : view.saving ? "Đang lưu…" : "Lưu kết quả")}
                  </button> : <SiteLink to="/login?next=/valuation" className="text-sm underline" data-sp-018bbc28="">
                    {"Đăng nhập để lưu kết quả"}
                  </SiteLink>}
                {view.saveError ? <p role="alert" className="mt-3 text-sm text-[var(--ui-ink)]" data-sp-018bbc28="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.saveError)}
                  </p> : null}
              </div> : null}
            <h3 className="font-medium text-sm mt-6" data-sp-018bbc28="">
              {"Thông tin đã dùng"}
            </h3>
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-3" data-sp-018bbc28="">
              {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.usedFeatures, feature => <div key={feature.label} className="rounded-xl bg-brand-card/10 p-3" data-sp-018bbc28="">
                  <dt className="text-xs text-brand-navy/60" data-sp-018bbc28="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(feature.label)}
                  </dt>
                  <dd className="text-sm mt-1" data-sp-018bbc28="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(feature.value)}
                  </dd>
                </div>)}
            </dl>
            {view.missingLabels.length ? <p className="text-sm text-brand-navy/80 mt-4" data-sp-018bbc28="">
                {"Thông tin còn thiếu: "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.missingLabels.join(", "))}
                {"."}
              </p> : null}
            {view.result.warnings.length ? <ul className="list-disc pl-5 mt-3 space-y-2 text-sm text-[var(--ui-ink)]" data-sp-018bbc28="">
                {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.result.warnings, warning => <li key={warning} data-sp-018bbc28="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.warningLabel(warning))}
                  </li>)}
              </ul> : null}
          </div> : null}
      </div>
      <p className="mt-6 text-xs text-brand-navy/60 leading-5" data-sp-018bbc28="">
        {"Giá rao ước tính để tham khảo. Mô hình chưa sử dụng tọa độ tài sản và khoảng cách tới tiện ích; kết quả chưa được xác minh bằng giá giao dịch."}
      </p>
    </section></>;
});
