import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { api } from "../auth/api.js";
import { categoryFor, valuationInput, createPreviewState, exactVnd } from "./valuation.js";
function usePostValuationPanelState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [options] = useState(() => createStateStore(null)),
    [optionsError] = useState(() => createStateStore("")),
    [loading] = useState(() => createStateStore(false));
  useSyncExternalStore(loading.subscribe, loading.getSnapshot);
  useSyncExternalStore(optionsError.subscribe, optionsError.getSnapshot);
  useSyncExternalStore(options.subscribe, options.getSnapshot);
  const [state] = useState(() => createStateStore({
    busy: false,
    result: null,
    error: ""
  }));
  useSyncExternalStore(state.subscribe, state.getSnapshot);
  const [preview] = useState(() => createPreviewState(body => api("/properties/valuation-preview", {
    method: "POST",
    body
  }), state));
  const _disposedRef = useRef(false);
  const getLocations = () => options.getSnapshot()?.categories?.find(c => c.category === categoryFor(_props.current.draft.propertyType))?.locations || [];
  const getLocation = () => getLocations().includes(_props.current.draft.valuationLocation) ? _props.current.draft.valuationLocation : "";
  const getInput = () => valuationInput(_props.current.draft, getLocation());
  function pickDistrict() {
    const district = _props.current.draft.district === "Hoà Vang" ? "Hòa Vang" : _props.current.draft.district;
    if (!getLocations().includes(_props.current.draft.valuationLocation)) _props.current.onDraftChange?.({
      ..._props.current.draft,
      valuationLocation: getLocations().includes(district) ? district : ""
    });
  }
  const _watched = [getLocations(), (() => _props.current.draft.district)()];
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    _initialized.current = true;
    const result = pickDistrict(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  const _watched2 = (() => JSON.stringify([getInput(), _props.current.draft.propertyType, _props.current.draft.district, _props.current.draft.price, _props.current.draft.address, _props.current.draft.latitude, _props.current.draft.longitude]))();
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
    const result = (() => preview.invalidate())(_watched2, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched2)]);
  async function loadOptions() {
    loading.set(true);
    optionsError.set("");
    try {
      const value = await api("/properties/valuation-options");
      if (!_disposedRef.current) options.set(value);
    } catch (e) {
      if (!_disposedRef.current) optionsError.set(e.message);
    } finally {
      if (!_disposedRef.current) loading.set(false);
    }
  }
  useEffect(() => {
    const result = loadOptions();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  useEffect(() => () => (() => {
    _disposedRef.current = true;
    preview.dispose();
  })(), []);
  const featureLabels = {
    areaSqm: "Diện tích (m²)",
    locationFeature: "Khu vực",
    rooms: "Phòng ngủ",
    floors: "Số tầng",
    access_type: "Đường tiếp cận",
    house_subtype: "Kiểu nhà"
  };
  const missingLabel = value => ({
    ...featureLabels,
    ward_source: "Phường/xã",
    access_type: "Đường tiếp cận",
    house_subtype: "Kiểu nhà"
  })[value] || value;
  const featureValue = value => ({
    alley: "Trong kiệt/hẻm",
    frontage: "Mặt tiền",
    villa: "Biệt thự",
    house_c4: "Nhà cấp 4"
  })[value] || value;
  return {
    ...inputProps,
    exactVnd,
    options: options.getSnapshot(),
    optionsError: optionsError.getSnapshot(),
    loading: loading.getSnapshot(),
    state: state.getSnapshot(),
    preview,
    locations: getLocations(),
    location: getLocation(),
    input: getInput(),
    loadOptions,
    featureLabels,
    missingLabel,
    featureValue,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["draft", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function PostValuationPanel(props, ref) {
  const view = usePostValuationPanelState(props, ref);
  return <><section data-ui-view="PostValuationPanel" data-testid="valuation-panel" {...view.rootAttributes} className={classNames(["bg-[var(--ui-soft)] text-brand-navy rounded-[22px] p-6", view.rootAttributes.className])}>
      <h2 className="text-xs tracking-[0.18em] text-brand-navy/60">
        {"GIÁ THAM CHIẾU XGBOOST · v6"}
      </h2>
      <div data-testid="valuation-price" aria-live="polite" className="text-xl font-light mt-3 break-words">
        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.result?.available ? view.exactVnd(view.state.result.predictedAskingPriceVnd) : "—")}
      </div>
      <p className="text-xs text-brand-navy/70 mt-2">
        {"Giá rao ước tính; giá chào của bạn được giữ nguyên."}
      </p>
      <label className="block mt-5 text-xs">
        {"Khu vực tham khảo "}
        <select data-testid="valuation-location" value={view.location} onChange={$event => {
          view.onDraftChange?.({
            ...view.draft,
            valuationLocation: $event.target.value
          });
        }} className="mt-2 w-full bg-brand-card text-[var(--ui-accent)] rounded-lg p-2" disabled={view.loading || !view.locations.length}>
          <option value="">
            {"Chọn đúng khu vực"}
          </option>
          {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.locations, item => <option key={item} value={item}>
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item)}
            </option>)}
        </select>
      </label>
      <p className="text-xs text-brand-navy/60 mt-2">
        {"Địa bàn theo dữ liệu model. Hãy chọn khu vực tương ứng với địa chỉ thực tế."}
      </p>
      {view.optionsError ? <p role="status" className="mt-3 text-xs text-[var(--ui-warning-text)]">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.optionsError)}{" "}
          <button type="button" className="underline" onClick={$event => {
          return view.loadOptions?.($event);
        }}>
            {"Thử lại"}
          </button>
        </p> : view.input.reason ? <p className="mt-3 text-xs text-brand-navy/80">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.input.reason)}
        </p> : null}
      <button type="button" data-testid="valuation-preview" disabled={view.loading || view.state.busy || !view.options || !!view.input.reason} onClick={$event => {
        view.preview.preview(view.input.body);
      }} className="mt-4 w-full rounded-full border border-brand-line/40 py-2 text-xs disabled:opacity-50">
        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.busy ? "Đang tính…" : "Xem giá tham khảo")}
      </button>
      {view.state.error ? <p role="status" className="mt-3 text-xs text-[var(--ui-warning-text)]">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.error)}
        </p> : null}
      {view.state.result && !view.state.result.available ? <p role="status" className="mt-3 text-xs">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.result.reason)}
        </p> : null}
      {view.state.result?.available ? <div className="mt-5 border-t border-brand-line/10 pt-4 text-xs space-y-2">
          <h3 className="font-semibold">
            {"Thông tin model đã dùng"}
          </h3>
          {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.state.result.featuresUsed, (value, key) => <p key={key}>
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.featureLabels[key] || key)}
              {": "}
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.featureValue(value))}
            </p>)}
          {view.state.result.missingFeatures?.length ? <p>
              {"Chưa có: "}
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.result.missingFeatures.map(view.missingLabel).join(", "))}
            </p> : null}
          {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.state.result.warnings, (warning, index) => <p key={index} className="text-[var(--ui-warning-text)]">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(warning)}
            </p>)}
        </div> : null}
      <p className="mt-5 text-xs text-brand-navy/60 leading-relaxed">
        {"Thông tin tham khảo, không phải kết quả thẩm định chính thức. Không có kết quả vẫn có thể lưu hoặc gửi tin."}
      </p>
    </section></>;
});
