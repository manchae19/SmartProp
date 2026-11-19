import { classNames, chainHandlers } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef, useEffect } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { useRouteState } from "../../app/navigation.jsx";
import { usePostEditor } from "./usePostEditor.js";
import { postSteps, propertyOptions, priceInput, areaInput, formatDecimal, hasRooms, locationConfirmed } from "./postForm.js";
import { districts } from "../map/districts.js";
import { administrativeHints, addressComponents } from "../map/geocoding.js";
import PostStepNav from "./PostStepNav.jsx";
import PostValidationSummary from "./PostValidationSummary.jsx";
import GooglePropertyLocation from "../map/GooglePropertyLocation.jsx";
import PrivateImage from "../../shared/components/PrivateImage.jsx";
import PostValuationPanel from "../prediction/PostValuationPanel.jsx";
import "./PostView.css";
function usePostViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const route = useRouteState(),
    editor = usePostEditor();
  const _editorLatest = useRef(editor);
  _editorLatest.current = editor;
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  const {
    draft,
    state,
    managed,
    images,
    coverKey,
    imageCount,
    dirty,
    goStep,
    goNext,
    saveDraft,
    startNew,
    chooseFiles,
    removeImage,
    moveImage,
    chooseCover,
    selectLocation,
    clearLocation,
    confirmLocation,
    checkResult,
    reviewVersion,
    editAgain
  } = editor;
  const getStep = () => postSteps.find(s => s.path === _routeLatest.current.path)?.step || 3,
    [fileInput] = useState(() => createStateStore(null)),
    [showValuation] = useState(() => createStateStore(false));
  useSyncExternalStore(showValuation.subscribe, showValuation.getSnapshot);
  useSyncExternalStore(fileInput.subscribe, fileInput.getSnapshot);
  const getPriceText = () => formatDecimal(priceInput(draft.price)),
    getAreaText = () => formatDecimal(areaInput(draft.area));
  const getUnitText = () => draft.transactionType === "Bán" ? "" : {
    PER_MONTH: "/ tháng",
    PER_YEAR: "/ năm",
    PER_DAY: "/ ngày",
    TOTAL: "trọn kỳ thuê"
  }[draft.rentUnit];
  const getCurrentTitle = () => postSteps[getStep() - 1].label;
  const getLocked = () => state.busy || !state.loaded || state.loadError;
  const getAddressHints = () => administrativeHints(draft, districts.filter(d => d !== "Tất cả"));
  const [addressSyncNotice] = useState(() => createStateStore(""));
  useSyncExternalStore(addressSyncNotice.subscribe, addressSyncNotice.getSnapshot);
  function synchronizeAddressFields() {
    const current = _editorLatest.current;
    if (current.state.busy || !current.state.loaded || current.state.loadError) return;
    const hints = administrativeHints(current.draft, districts.slice(1));
    if (!hints.district && !hints.ward) return;
    current.updateDraft(value => {
      if (hints.district) {
        value.district = hints.district;
        if (!hints.ward) value.ward = addressComponents(current.draft).wards[0] || '';
      }
      if (hints.ward) value.ward = hints.ward;
      value.latitude = '';
      value.longitude = '';
      value.confirmedLocation = '';
    });
    addressSyncNotice.set('Đã tự cập nhật phường/quận theo địa chỉ bạn nhập. Hãy tìm và xác nhận lại vị trí.');
  }
  useEffect(() => {
    addressSyncNotice.set('');
    const timer = setTimeout(synchronizeAddressFields, 500);
    return () => clearTimeout(timer);
  }, [draft.address, state.loaded]);
  const getCover = () => images.find(e => e.key === coverKey) || images[0];
  const amenityOptions = ["Máy lạnh", "Tủ lạnh", "Máy giặt", "Giường", "Sofa", "Tivi", "Bàn ăn", "Ban công", "Chỗ để xe"];
  function pickFiles(event) {
    chooseFiles(event.target.files || []);
    event.target.value = "";
  }
  function dropFiles(event) {
    if (!getLocked()) chooseFiles(event.dataTransfer.files);
  }
  function toggleAmenity(value) {
    _editorLatest.current.updateDraft(draftValue => draftValue["selectedAmenities"] = draft.selectedAmenities.includes(value) ? draft.selectedAmenities.filter(v => v !== value) : [...draft.selectedAmenities, value]);
  }
  return {
    ...inputProps,
    propertyOptions,
    priceInput,
    areaInput,
    hasRooms,
    locationConfirmed,
    districts,
    route,
    editor,
    draft,
    state,
    managed,
    images,
    coverKey,
    imageCount,
    dirty,
    goStep,
    goNext,
    saveDraft,
    startNew,
    removeImage,
    moveImage,
    chooseCover,
    selectLocation,
    clearLocation,
    confirmLocation,
    checkResult,
    reviewVersion,
    editAgain,
    step: getStep(),
    fileInput: fileInput.getSnapshot(),
    showValuation: showValuation.getSnapshot(),
    priceText: getPriceText(),
    areaText: getAreaText(),
    unitText: getUnitText(),
    currentTitle: getCurrentTitle(),
    locked: getLocked(),
    addressHints: getAddressHints(),
    addressSyncNotice: addressSyncNotice.getSnapshot(),
    synchronizeAddressFields,
    cover: getCover(),
    amenityOptions,
    pickFiles,
    dropFiles,
    toggleAmenity,
    updateFileInputValue: fileInput.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateDraft: editor.updateDraft,
    updateShowValuationValue: showValuation.set
  };
}
export default React.forwardRef(function PostView(props, ref) {
  const view = usePostViewState(props, ref);
  return <><div data-ui-view="PostView" data-sp-b5d4ccf8="" {...view.rootAttributes} className={classNames(["posting-page", view.rootAttributes.className])}>
      <div className="posting-main" data-sp-b5d4ccf8="">
        <div className="posting-title" data-sp-b5d4ccf8="">
          <div data-sp-b5d4ccf8="">
            <p className="eyebrow" data-sp-b5d4ccf8="">
              {"ĐĂNG BÁN / CHO THUÊ"}
            </p>
            <h1 data-sp-b5d4ccf8="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.managed ? "Chỉnh sửa tin đăng" : "Tạo tin đăng mới")}
            </h1>
            <p data-sp-b5d4ccf8="">
              {"Thông tin rõ ràng, hình ảnh thực tế và vị trí do bạn xác nhận."}
            </p>
          </div>
          <span className="step-badge" data-sp-b5d4ccf8="">
            {"Bước "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.step)}
            {" / 3"}
          </span>
        </div>
        <PostStepNav current={view.step} busy={view.state.busy} data-sp-b5d4ccf8="" />
        <PostValidationSummary issues={view.state.issues} data-sp-b5d4ccf8="" />
        {view.state.error ? <div className="posting-alert error" role="alert" data-sp-b5d4ccf8="">
            <strong data-sp-b5d4ccf8="">
              {"Chưa hoàn tất thao tác"}
            </strong>
            <p data-sp-b5d4ccf8="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.error)}
            </p>
            {view.state.conflict ? <button type="button" disabled={view.state.busy} onClick={$event => {
            return view.reviewVersion?.($event);
          }} data-sp-b5d4ccf8="">
                {"Đối chiếu phiên bản máy chủ"}
              </button> : null}
            {view.state.uncertainCreate || view.state.uncertainUpload ? <button type="button" disabled={view.state.busy} onClick={$event => {
            return view.checkResult?.($event);
          }} data-sp-b5d4ccf8="">
                {"Đối chiếu kết quả"}
              </button> : null}
            {view.state.loadError ? <button type="button" disabled={view.state.busy} onClick={$event => {
            view.editor.initialize(view.route.query.edit);
          }} data-sp-b5d4ccf8="">
                {"Thử tải lại tin"}
              </button> : null}
          </div> : null}
        {view.state.notice && !view.state.complete ? <p role="status" className="posting-alert notice" data-sp-b5d4ccf8="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.notice)}
          </p> : null}
        {view.state.localSaveError ? <p role="status" className="posting-alert error" data-sp-b5d4ccf8="">
            {"Trình duyệt chưa giữ được bản nháp. Nội dung vẫn ở tab này; hãy lưu nháp tài khoản khi đủ thông tin và vị trí."}
          </p> : null}
        {view.state.complete ? <section className="posting-success" role="status" data-sp-b5d4ccf8="">
            <span className="success-symbol" data-sp-b5d4ccf8="">
              {"✓"}
            </span>
            <p className="eyebrow" data-sp-b5d4ccf8="">
              {"ĐÃ GỬI DUYỆT"}
            </p>
            <h2 data-sp-b5d4ccf8="">
              {"Tin của bạn đã được tiếp nhận"}
            </h2>
            <p data-sp-b5d4ccf8="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.managed?.property.title)}
            </p>
            <p data-sp-b5d4ccf8="">
              {"Trạng thái trên máy chủ: "}
              <strong data-sp-b5d4ccf8="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.managed?.property.status === "PENDING" ? "Chờ duyệt" : view.managed?.property.status === "PUBLISHED" ? "Đã được duyệt" : view.managed?.property.status)}
              </strong>
              {". Tin chỉ hiển thị công khai khi được quản trị viên phê duyệt."}
            </p>
            <div className="success-actions" data-sp-b5d4ccf8="">
              <SiteLink className="primary-button" to="/my-listing" data-sp-b5d4ccf8="">
                {"Đến tin đăng của tôi"}
              </SiteLink>
              <button type="button" className="secondary-button" onClick={$event => {
              return view.editAgain?.($event);
            }} data-sp-b5d4ccf8="">
                {"Chỉnh sửa lại"}
              </button>
              <button type="button" className="text-button" onClick={$event => {
              return view.startNew?.($event);
            }} data-sp-b5d4ccf8="">
                {"Tạo tin khác"}
              </button>
            </div>
          </section> : <div className="posting-layout" data-sp-b5d4ccf8="">
            <form className="posting-form" noValidate={true} onSubmit={$event => {
            $event.preventDefault();
            view.step < 3 && view.goNext();
          }} data-sp-b5d4ccf8="">
              <fieldset disabled={view.locked} data-sp-b5d4ccf8="">
                {view.step === 1 ? <React.Fragment>
                    <section className="posting-card" data-sp-b5d4ccf8="">
                      <div className="card-heading" data-sp-b5d4ccf8="">
                        <span className="section-number" data-sp-b5d4ccf8="">
                          {"01"}
                        </span>
                        <div data-sp-b5d4ccf8="">
                          <h2 data-sp-b5d4ccf8="">
                            {"Thông tin & giá"}
                          </h2>
                          <p data-sp-b5d4ccf8="">
                            {"Bắt đầu với nhu cầu và thông tin chính của bất động sản."}
                          </p>
                        </div>
                      </div>
                      <div className="field" data-sp-b5d4ccf8="">
                        <span id="transaction-label" className="field-label" data-sp-b5d4ccf8="">
                          {"Nhu cầu "}
                          <span className="required" data-sp-b5d4ccf8="">
                            {"*"}
                          </span>
                        </span>
                        <div id="post-transactionType" className="transaction-options" role="group" aria-labelledby="transaction-label" tabIndex="-1" data-sp-b5d4ccf8="">
                          {((items, render) => typeof items === "number" ? Array.from({
                        length: Math.max(0, items)
                      }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(["Bán", "Cho thuê"], value => <button key={value} type="button" aria-pressed={view.draft.transactionType === value} className={classNames({
                        selected: view.draft.transactionType === value
                      })} onClick={$event => {
                        view.updateDraft(draftValue => draftValue.transactionType = value);
                      }} data-sp-b5d4ccf8="">
                              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(value === "Bán" ? "Đăng bán" : "Cho thuê")}
                            </button>)}
                        </div>
                      </div>
                      <label className="field" htmlFor="post-propertyType" data-sp-b5d4ccf8="">
                        <span data-sp-b5d4ccf8="">
                          {"Loại bất động sản "}
                          <span className="required" data-sp-b5d4ccf8="">
                            {"*"}
                          </span>
                        </span>
                        <select id="post-propertyType" data-sp-b5d4ccf8="" value={view.draft.propertyType ?? ""} onChange={event => ($value => {
                      view.updateDraft(draftValue => draftValue.propertyType = $value);
                    })(event.target.value)}>
                          {((items, render) => typeof items === "number" ? Array.from({
                        length: Math.max(0, items)
                      }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.propertyOptions, option => <option key={option.value} value={option.value} data-sp-b5d4ccf8="">
                              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(option.label)}
                            </option>)}
                        </select>
                      </label>
                      <label className="field" htmlFor="post-title" data-sp-b5d4ccf8="">
                        <span data-sp-b5d4ccf8="">
                          {"Tiêu đề tin đăng "}
                          <span className="required" data-sp-b5d4ccf8="">
                            {"*"}
                          </span>
                        </span>
                        <input id="post-title" maxLength="255" placeholder="Ví dụ: Bán căn hộ 2 phòng ngủ, ban công thoáng tại Hải Châu" autoComplete="off" data-sp-b5d4ccf8="" value={view.draft.title ?? ""} onChange={event => ($value => {
                      view.updateDraft(draftValue => draftValue.title = $value);
                    })(event.target.value)} />
                        <small data-sp-b5d4ccf8="">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.draft.title.length)}
                          {" / 255 ký tự · Nêu điểm nổi bật, tránh viết toàn bộ bằng chữ in hoa."}
                        </small>
                      </label>
                      <div className="field-grid" data-sp-b5d4ccf8="">
                        <label className="field" htmlFor="post-area" data-sp-b5d4ccf8="">
                          <span data-sp-b5d4ccf8="">
                            {"Diện tích "}
                            <span className="required" data-sp-b5d4ccf8="">
                              {"*"}
                            </span>
                          </span>
                          <div className="input-unit" data-sp-b5d4ccf8="">
                            <input id="post-area" inputMode="decimal" placeholder="86,3" data-sp-b5d4ccf8="" value={view.draft.area ?? ""} onChange={event => ($value => {
                          view.updateDraft(draftValue => draftValue.area = $value);
                        })(event.target.value)} />
                            <span data-sp-b5d4ccf8="">
                              {"m²"}
                            </span>
                          </div>
                          {view.areaInput(view.draft.area) !== null ? <small data-sp-b5d4ccf8="">
                              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.areaText)}
                              {" m²"}
                            </small> : null}
                        </label>
                        <label className="field" htmlFor="post-price" data-sp-b5d4ccf8="">
                          <span data-sp-b5d4ccf8="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.draft.transactionType === "Bán" ? "Giá bán" : "Giá thuê")}{" "}
                            <span className="required" data-sp-b5d4ccf8="">
                              {"*"}
                            </span>
                          </span>
                          <div className="input-unit" data-sp-b5d4ccf8="">
                            <input id="post-price" inputMode="decimal" placeholder="Ví dụ: 2,5 tỷ hoặc 12.000.000" data-sp-b5d4ccf8="" value={view.draft.price ?? ""} onChange={event => ($value => {
                          view.updateDraft(draftValue => draftValue.price = $value);
                        })(event.target.value)} />
                            <span data-sp-b5d4ccf8="">
                              {"VND"}
                            </span>
                          </div>
                          {view.priceInput(view.draft.price) !== null ? <small className="exact-value" data-sp-b5d4ccf8="">
                              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.priceText)}
                              {" VND "}
                              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.unitText)}
                            </small> : <small data-sp-b5d4ccf8="">
                              {"Nhập VND hoặc ghi rõ triệu/tỷ; ví dụ 2,5 tỷ."}
                            </small>}
                        </label>
                      </div>
                      {view.draft.transactionType === "Cho thuê" ? <label className="field" htmlFor="post-priceUnit" data-sp-b5d4ccf8="">
                          <span data-sp-b5d4ccf8="">
                            {"Đơn vị giá thuê "}
                            <span className="required" data-sp-b5d4ccf8="">
                              {"*"}
                            </span>
                          </span>
                          <select id="post-priceUnit" data-sp-b5d4ccf8="" value={view.draft.rentUnit ?? ""} onChange={event => ($value => {
                      view.updateDraft(draftValue => draftValue.rentUnit = $value);
                    })(event.target.value)}>
                            <option value="PER_MONTH" data-sp-b5d4ccf8="">
                              {"VND / tháng"}
                            </option>
                            <option value="PER_YEAR" data-sp-b5d4ccf8="">
                              {"VND / năm"}
                            </option>
                            <option value="PER_DAY" data-sp-b5d4ccf8="">
                              {"VND / ngày"}
                            </option>
                            <option value="TOTAL" data-sp-b5d4ccf8="">
                              {"VND / trọn kỳ thuê"}
                            </option>
                          </select>
                        </label> : null}
                      {view.hasRooms(view.draft.propertyType) ? <div className="field-grid optional-rooms" data-sp-b5d4ccf8="">
                          <label className="field" htmlFor="post-bedrooms" data-sp-b5d4ccf8="">
                            <span data-sp-b5d4ccf8="">
                              {"Phòng ngủ "}
                              <small data-sp-b5d4ccf8="">
                                {"Tùy chọn"}
                              </small>
                            </span>
                            <input id="post-bedrooms" type="number" min="0" max="32767" step="1" placeholder="Không cung cấp" data-sp-b5d4ccf8="" value={view.draft.bedrooms ?? ""} onChange={event => ($value => {
                        view.updateDraft(draftValue => draftValue.bedrooms = $value);
                      })(event.target.value)} />
                          </label>
                          <label className="field" htmlFor="post-bathrooms" data-sp-b5d4ccf8="">
                            <span data-sp-b5d4ccf8="">
                              {"Phòng tắm "}
                              <small data-sp-b5d4ccf8="">
                                {"Tùy chọn"}
                              </small>
                            </span>
                            <input id="post-bathrooms" type="number" min="0" max="32767" step="1" placeholder="Không cung cấp" data-sp-b5d4ccf8="" value={view.draft.bathrooms ?? ""} onChange={event => ($value => {
                        view.updateDraft(draftValue => draftValue.bathrooms = $value);
                      })(event.target.value)} />
                          </label>
                        </div> : null}
                    </section>
                  </React.Fragment> : view.step === 2 ? <React.Fragment>
                    <section id="post-images" tabIndex="-1" className="posting-card" data-sp-b5d4ccf8="">
                      <div className="card-heading" data-sp-b5d4ccf8="">
                        <span className="section-number" data-sp-b5d4ccf8="">
                          {"02"}
                        </span>
                        <div data-sp-b5d4ccf8="">
                          <h2 data-sp-b5d4ccf8="">
                            {"Ảnh bất động sản"}
                          </h2>
                          <p data-sp-b5d4ccf8="">
                            {"Ảnh rõ ràng giúp người xem hiểu đúng bất động sản."}
                          </p>
                        </div>
                        <span className="count-badge" data-sp-b5d4ccf8="">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.imageCount)}
                          {" / 30"}
                        </span>
                      </div>
                      <div className="upload-zone" onDragOver={$event => {
                    $event.preventDefault();
                    undefined;
                  }} onDrop={$event => {
                    $event.preventDefault();
                    return view.dropFiles?.($event);
                  }} data-sp-b5d4ccf8="">
                        <span className="upload-symbol" aria-hidden="true" data-sp-b5d4ccf8="">
                          {"↑"}
                        </span>
                        <h3 data-sp-b5d4ccf8="">
                          {"Chọn nhiều ảnh hoặc kéo ảnh vào đây"}
                        </h3>
                        <p data-sp-b5d4ccf8="">
                          {"JPEG/PNG · tối đa 10 MB/ảnh · tối đa 30 ảnh"}
                        </p>
                        <button type="button" className="secondary-button" onClick={$event => {
                      view.fileInput?.click();
                    }} data-sp-b5d4ccf8="">
                          {"Chọn ảnh từ thiết bị"}
                        </button>
                        <input ref={view.updateFileInputValue} className="visually-hidden" type="file" accept="image/jpeg,image/png" multiple={true} aria-label="Tải ảnh bất động sản" onChange={$event => {
                      return view.pickFiles?.($event);
                    }} data-sp-b5d4ccf8="" />
                      </div>
                      <p className="field-help" data-sp-b5d4ccf8="">
                        {"Lưu nháp không bắt buộc ảnh; gửi duyệt cần ít nhất 1 ảnh. Ảnh tối đa 12000 px mỗi chiều và 40 triệu pixel. Chỉ đăng ảnh bạn có quyền sử dụng."}
                      </p>
                      {view.images.length ? <div className="photo-grid" data-sp-b5d4ccf8="">
                          {((items, render) => typeof items === "number" ? Array.from({
                      length: Math.max(0, items)
                    }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.images, (entry, index) => <article key={entry.key} className="photo-card" data-sp-b5d4ccf8="">
                              <div className="photo-image" data-sp-b5d4ccf8="">
                                {entry.server ? <PrivateImage src={entry.server.url} alt={"Ảnh bất động sản " + (index + 1)} data-sp-b5d4ccf8="" /> : <img src={entry.preview} alt={entry.file.name} data-sp-b5d4ccf8="" />}
                                {view.coverKey === entry.key ? <span className="cover-badge" data-sp-b5d4ccf8="">
                                    {"Ảnh đại diện"}
                                  </span> : null}
                                <span className="upload-badge" data-sp-b5d4ccf8="">
                                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(entry.server ? "Đã tải" : "Chưa tải")}
                                </span>
                              </div>
                              <p className="photo-name" data-sp-b5d4ccf8="">
                                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(entry.file?.name || "Ảnh " + (index + 1))}
                              </p>
                              <button type="button" className="cover-button" aria-pressed={view.coverKey === entry.key} onClick={$event => {
                        view.chooseCover(entry.key);
                      }} data-sp-b5d4ccf8="">
                                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.coverKey === entry.key ? "✓ Ảnh đại diện" : "Chọn làm đại diện")}
                              </button>
                              <div className="photo-actions" data-sp-b5d4ccf8="">
                                <button type="button" disabled={index === 0} aria-label={"Đưa ảnh " + (index + 1) + " lên trước"} onClick={$event => {
                          view.moveImage(entry.key, -1);
                        }} data-sp-b5d4ccf8="">
                                  {"↑ Lên"}
                                </button>
                                <button type="button" disabled={index === view.images.length - 1} aria-label={"Đưa ảnh " + (index + 1) + " xuống sau"} onClick={$event => {
                          view.moveImage(entry.key, 1);
                        }} data-sp-b5d4ccf8="">
                                  {"↓ Xuống"}
                                </button>
                                <button type="button" aria-label={"Xóa ảnh " + (index + 1)} className="delete-image" onClick={$event => {
                          view.removeImage(entry.key);
                        }} data-sp-b5d4ccf8="">
                                  {"Xóa"}
                                </button>
                              </div>
                            </article>)}
                        </div> : null}
                    </section>
                    <section className="posting-card" data-sp-b5d4ccf8="">
                      <div className="card-heading" data-sp-b5d4ccf8="">
                        <div data-sp-b5d4ccf8="">
                          <h2 data-sp-b5d4ccf8="">
                            {"Địa chỉ & vị trí"}
                          </h2>
                          <p data-sp-b5d4ccf8="">
                            {"Nhập địa chỉ thực tế, chọn ghim rồi xác nhận vị trí."}
                          </p>
                        </div>
                      </div>
                      <label className="field" htmlFor="post-address" data-sp-b5d4ccf8="">
                        <span data-sp-b5d4ccf8="">
                          {"Địa chỉ đầy đủ "}
                          <span className="required" data-sp-b5d4ccf8="">
                            {"*"}
                          </span>
                        </span>
                        <input id="post-address" autoComplete="street-address" maxLength="4000" placeholder="Số nhà, đường, phường và thành phố" data-sp-b5d4ccf8="" value={view.draft.address ?? ""} onBlur={view.synchronizeAddressFields} onChange={event => {
                      view.updateDraft(value => { value.address = event.target.value; });
                    }} />
                        <small data-sp-b5d4ccf8="">
                          {"Nhập số nhà, tên đường, phường và thành phố."}
                        </small>
                      </label>
                      {view.addressSyncNotice ? <p role="status" className="field-help" data-sp-b5d4ccf8="">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.addressSyncNotice)}
                        </p> : null}
                      <div className="field-grid three" data-sp-b5d4ccf8="">
                        <label className="field" htmlFor="post-city" data-sp-b5d4ccf8="">
                          <span data-sp-b5d4ccf8="">
                            {"Thành phố"}
                          </span>
                          <select id="post-city" data-sp-b5d4ccf8="" value={view.draft.city ?? ""} onChange={event => ($value => {
                        view.updateDraft(draftValue => draftValue.city = $value);
                      })(event.target.value)}>
                            <option value="Da Nang" data-sp-b5d4ccf8="">
                              {"Đà Nẵng"}
                            </option>
                            {view.draft.city && view.draft.city !== "Da Nang" ? <option value={view.draft.city} data-sp-b5d4ccf8="">
                                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.draft.city)}
                              </option> : null}
                          </select>
                        </label>
                        <label className="field" htmlFor="post-district" data-sp-b5d4ccf8="">
                          <span data-sp-b5d4ccf8="">
                            {"Quận/huyện "}
                            <small data-sp-b5d4ccf8="">
                              {"Tùy chọn"}
                            </small>
                          </span>
                          <select id="post-district" data-sp-b5d4ccf8="" value={view.draft.district ?? ""} onChange={event => ($value => {
                        view.updateDraft(draftValue => draftValue.district = $value);
                      })(event.target.value)}>
                            <option value="" data-sp-b5d4ccf8="">
                              {"Chọn khu vực"}
                            </option>
                            {((items, render) => typeof items === "number" ? Array.from({
                          length: Math.max(0, items)
                        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.districts.filter(d => d !== "Tất cả"), district => <option key={district} data-sp-b5d4ccf8="">
                                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(district)}
                                </option>)}
                            {view.draft.district && !view.districts.includes(view.draft.district) ? <option value={view.draft.district} data-sp-b5d4ccf8="">
                                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.draft.district)}
                              </option> : null}
                          </select>
                        </label>
                        <label className="field" htmlFor="post-ward" data-sp-b5d4ccf8="">
                          <span data-sp-b5d4ccf8="">
                            {"Phường/xã "}
                            <small data-sp-b5d4ccf8="">
                              {"Tùy chọn"}
                            </small>
                          </span>
                          <input id="post-ward" maxLength="100" placeholder="Phường/xã" data-sp-b5d4ccf8="" value={view.draft.ward ?? ""} onChange={event => ($value => {
                        view.updateDraft(draftValue => draftValue.ward = $value);
                      })(event.target.value)} />
                        </label>
                      </div>
                      {view.addressHints.district || view.addressHints.ward ? <div className="mt-4 rounded-xl border border-brand-line bg-brand-cream p-4 text-sm" data-sp-b5d4ccf8="">
                          <p data-sp-b5d4ccf8="">
                            {"Gợi ý từ địa chỉ bạn nhập: "}
                            <strong data-sp-b5d4ccf8="">
                              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))([view.addressHints.district, view.addressHints.ward].filter(Boolean).join(" · "))}
                            </strong>
                            {". Đây là tên trong nội dung bạn nhập, chưa xác minh địa giới cũ/mới."}
                          </p>

                        </div> : null}
                      <GooglePropertyLocation address={view.draft.address} city={view.draft.city} district={view.draft.district} ward={view.draft.ward} latitude={view.draft.latitude} longitude={view.draft.longitude} confirmed={view.locationConfirmed(view.draft)} disabled={view.locked} onSelect={$event => {
                    return view.selectLocation?.($event);
                  }} onInvalidate={$event => {
                    return view.clearLocation?.($event);
                  }} onConfirm={$event => {
                    return view.confirmLocation?.($event);
                  }} data-sp-b5d4ccf8="" />
                    </section>
                  </React.Fragment> : <React.Fragment>
                    <section className="posting-card" data-sp-b5d4ccf8="">
                      <div className="card-heading" data-sp-b5d4ccf8="">
                        <span className="section-number" data-sp-b5d4ccf8="">
                          {"03"}
                        </span>
                        <div data-sp-b5d4ccf8="">
                          <h2 data-sp-b5d4ccf8="">
                            {"Mô tả & liên hệ"}
                          </h2>
                          <p data-sp-b5d4ccf8="">
                            {"Bổ sung thông tin để người quan tâm dễ liên hệ với bạn."}
                          </p>
                        </div>
                      </div>
                      <label className="field" htmlFor="post-description" data-sp-b5d4ccf8="">
                        <span data-sp-b5d4ccf8="">
                          {"Mô tả bất động sản "}
                          <small data-sp-b5d4ccf8="">
                            {"Tùy chọn"}
                          </small>
                        </span>
                        <textarea id="post-description" rows="5" maxLength="20000" placeholder="Mô tả không gian, hiện trạng, tiện ích và điều kiện bán hoặc cho thuê…" data-sp-b5d4ccf8="" value={view.draft.description ?? ""} onChange={event => ($value => {
                      view.updateDraft(draftValue => draftValue.description = $value);
                    })(event.target.value)} />
                        <small data-sp-b5d4ccf8="">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.draft.description.length)}
                          {" / 20000 ký tự"}
                        </small>
                      </label>
                      <div className="field-grid" data-sp-b5d4ccf8="">
                        <label className="field" htmlFor="post-contactName" data-sp-b5d4ccf8="">
                          <span data-sp-b5d4ccf8="">
                            {"Tên liên hệ "}
                            <small data-sp-b5d4ccf8="">
                              {"Tùy chọn"}
                            </small>
                          </span>
                          <input id="post-contactName" autoComplete="name" maxLength="150" placeholder="Tên người liên hệ" data-sp-b5d4ccf8="" value={view.draft.contactName ?? ""} onChange={event => ($value => {
                        view.updateDraft(draftValue => draftValue.contactName = $value);
                      })(event.target.value)} />
                        </label>
                        <label className="field" htmlFor="post-phone" data-sp-b5d4ccf8="">
                          <span data-sp-b5d4ccf8="">
                            {"Số điện thoại "}
                            <small data-sp-b5d4ccf8="">
                              {"Tùy chọn"}
                            </small>
                          </span>
                          <input id="post-phone" type="tel" autoComplete="tel" maxLength="30" placeholder="Số điện thoại liên hệ" data-sp-b5d4ccf8="" value={view.draft.phone ?? ""} onChange={event => ($value => {
                        view.updateDraft(draftValue => draftValue.phone = $value);
                      })(event.target.value)} />
                        </label>
                      </div>
                      <label className="field" htmlFor="post-contact" data-sp-b5d4ccf8="">
                        <span data-sp-b5d4ccf8="">
                          {"Email liên hệ "}
                          <small data-sp-b5d4ccf8="">
                            {"Tùy chọn"}
                          </small>
                        </span>
                        <input id="post-contact" type="email" autoComplete="email" maxLength="254" placeholder="Email người liên hệ" data-sp-b5d4ccf8="" value={view.draft.contact ?? ""} onChange={event => ($value => {
                      view.updateDraft(draftValue => draftValue.contact = $value);
                    })(event.target.value)} />
                      </label>
                      <p className="field-help" data-sp-b5d4ccf8="">
                        {"Thông tin liên hệ được gợi sẵn từ tài khoản và có thể chỉnh sửa. Chỉ cung cấp thông tin bạn có quyền sử dụng."}
                      </p>
                    </section>
                    <details className="posting-card extra-information" data-sp-b5d4ccf8="">
                      <summary data-sp-b5d4ccf8="">
                        {"Thêm thông tin "}
                        <span data-sp-b5d4ccf8="">
                          {"Tùy chọn"}
                        </span>
                      </summary>
                      <div className="field-grid three" data-sp-b5d4ccf8="">
                        <label className="field" htmlFor="post-direction" data-sp-b5d4ccf8="">
                          <span data-sp-b5d4ccf8="">
                            {"Hướng nhà"}
                          </span>
                          <select id="post-direction" data-sp-b5d4ccf8="" value={view.draft.direction ?? ""} onChange={event => ($value => {
                        view.updateDraft(draftValue => draftValue.direction = $value);
                      })(event.target.value)}>
                            <option value="" data-sp-b5d4ccf8="">
                              {"Không cung cấp"}
                            </option>
                            {((items, render) => typeof items === "number" ? Array.from({
                          length: Math.max(0, items)
                        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(["Đông", "Tây", "Nam", "Bắc", "Đông Bắc", "Đông Nam", "Tây Bắc", "Tây Nam"], value => <option key={value} data-sp-b5d4ccf8="">
                                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(value)}
                                </option>)}
                          </select>
                        </label>
                        <label className="field" htmlFor="post-floor" data-sp-b5d4ccf8="">
                          <span data-sp-b5d4ccf8="">
                            {"Thông tin tầng"}
                          </span>
                          <input id="post-floor" maxLength="30" placeholder="Ví dụ: Tầng 5 / 3 tầng" data-sp-b5d4ccf8="" value={view.draft.floor ?? ""} onChange={event => ($value => {
                        view.updateDraft(draftValue => draftValue.floor = $value);
                      })(event.target.value)} />
                        </label>
                        <label className="field" htmlFor="post-block" data-sp-b5d4ccf8="">
                          <span data-sp-b5d4ccf8="">
                            {"Tòa / block"}
                          </span>
                          <input id="post-block" maxLength="50" placeholder="Tòa / block" data-sp-b5d4ccf8="" value={view.draft.block ?? ""} onChange={event => ($value => {
                        view.updateDraft(draftValue => draftValue.block = $value);
                      })(event.target.value)} />
                        </label>
                      </div>
                      <div id="post-declaredAmenities" tabIndex="-1" className="amenities" data-sp-b5d4ccf8="">
                        <span className="field-label" data-sp-b5d4ccf8="">
                          {"Tiện ích & nội thất"}
                        </span>
                        {((items, render) => typeof items === "number" ? Array.from({
                      length: Math.max(0, items)
                    }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.amenityOptions, value => <label key={value} data-sp-b5d4ccf8="">
                            <input type="checkbox" checked={view.draft.selectedAmenities.includes(value)} onChange={$event => {
                        view.toggleAmenity(value);
                      }} data-sp-b5d4ccf8="" />
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(value)}
                          </label>)}
                      </div>
                    </details>
                    <section className="posting-card preview-card" aria-label="Xem trước tin đăng" data-sp-b5d4ccf8="">
                      <div className="card-heading" data-sp-b5d4ccf8="">
                        <div data-sp-b5d4ccf8="">
                          <h2 data-sp-b5d4ccf8="">
                            {"Xem trước thông tin"}
                          </h2>
                          <p data-sp-b5d4ccf8="">
                            {"Kiểm tra lại trước khi gửi quản trị viên duyệt."}
                          </p>
                        </div>
                      </div>
                      <div className="preview-summary" data-sp-b5d4ccf8="">
                        {view.cover ? <div className="preview-photo" data-sp-b5d4ccf8="">
                            {view.cover.server ? <PrivateImage src={view.cover.server.url} alt="Ảnh đại diện xem trước" data-sp-b5d4ccf8="" /> : <img src={view.cover.preview} alt="Ảnh đại diện xem trước" data-sp-b5d4ccf8="" />}
                          </div> : null}
                        <div data-sp-b5d4ccf8="">
                          <span className="preview-type" data-sp-b5d4ccf8="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.draft.transactionType)}
                            {" · "}
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.draft.propertyType)}
                          </span>
                          <h3 data-sp-b5d4ccf8="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.draft.title || "Chưa có tiêu đề")}
                          </h3>
                          <p className="preview-price" data-sp-b5d4ccf8="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.priceText)}
                            {" VND "}
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.unitText)}
                          </p>
                          <p data-sp-b5d4ccf8="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.areaText)}
                            {" m²"}
                            {view.hasRooms(view.draft.propertyType) && view.draft.bedrooms ? <span data-sp-b5d4ccf8="">
                                {" · "}
                                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.draft.bedrooms)}
                                {" phòng ngủ"}
                              </span> : null}
                          </p>
                          <p data-sp-b5d4ccf8="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.draft.address || "Chưa có địa chỉ")}
                          </p>
                        </div>
                      </div>
                      <dl className="preview-details" data-sp-b5d4ccf8="">
                        <div data-sp-b5d4ccf8="">
                          <dt data-sp-b5d4ccf8="">
                            {"Ảnh"}
                          </dt>
                          <dd data-sp-b5d4ccf8="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.imageCount)}
                            {" ảnh · "}
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.images.filter(e => !e.server).length)}
                            {" ảnh chưa tải"}
                          </dd>
                        </div>
                        <div data-sp-b5d4ccf8="">
                          <dt data-sp-b5d4ccf8="">
                            {"Vị trí"}
                          </dt>
                          <dd data-sp-b5d4ccf8="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.locationConfirmed(view.draft) ? "Đã xác nhận ghim" : "Chưa xác nhận vị trí")}
                          </dd>
                        </div>
                        <div data-sp-b5d4ccf8="">
                          <dt data-sp-b5d4ccf8="">
                            {"Liên hệ"}
                          </dt>
                          <dd data-sp-b5d4ccf8="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))([view.draft.contactName, view.draft.phone, view.draft.contact].filter(Boolean).join(" · ") || "Chưa cung cấp")}
                          </dd>
                        </div>
                      </dl>
                      {view.draft.description ? <p className="description-preview" data-sp-b5d4ccf8="">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.draft.description)}
                        </p> : null}
                      <div className="legal-note" data-sp-b5d4ccf8="">
                        <p data-sp-b5d4ccf8="">
                          {"Hồ sơ pháp lý không bắt buộc trong form cơ bản. Hồ sơ được quản lý riêng và chỉ có kết quả xác minh sau khi được kiểm duyệt."}
                        </p>
                        {view.managed ? <SiteLink to={"/account/properties/" + view.managed.property.id + "/legal-documents"} data-sp-b5d4ccf8="">
                            {"Quản lý hồ sơ pháp lý riêng tư ↗"}
                          </SiteLink> : null}
                      </div>
                      <label id="post-consent" className="consent" tabIndex="-1" data-sp-b5d4ccf8="">
                        <input type="checkbox" data-sp-b5d4ccf8="" checked={Array.isArray(view.draft.accepted) ? view.draft.accepted.includes("on") : !!view.draft.accepted} onChange={event => ($value => {
                      view.updateDraft(draftValue => draftValue.accepted = $value);
                    })(Array.isArray(view.draft.accepted) ? event.target.checked ? [...view.draft.accepted, "on"] : view.draft.accepted.filter(item => item !== "on") : event.target.checked)} />
                        <span data-sp-b5d4ccf8="">
                          {"Tôi xác nhận có quyền đăng nội dung, hình ảnh và chịu trách nhiệm về tính chính xác của thông tin này."}
                        </span>
                      </label>
                    </section>
                  </React.Fragment>}
              </fieldset>
              <div className="posting-actions" data-sp-b5d4ccf8="">
                <button type="button" className="secondary-button back-button" disabled={view.locked || view.step === 1} onClick={$event => {
                view.goStep(view.step - 1);
              }} data-sp-b5d4ccf8="">
                  {"← Quay lại"}
                </button>
                <button type="button" className="secondary-button save-button" disabled={view.locked} onClick={$event => {
                view.saveDraft(false);
              }} data-sp-b5d4ccf8="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.busy ? "Đang xử lý…" : "Lưu nháp")}
                </button>
                {view.step < 3 ? <button type="submit" className="primary-button" disabled={view.locked} data-sp-b5d4ccf8="">
                    {"Tiếp tục →"}
                  </button> : <button type="button" className="primary-button" disabled={view.locked} onClick={$event => {
                view.saveDraft(true);
              }} data-sp-b5d4ccf8="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.busy ? "Đang xử lý…" : "Gửi duyệt")}
                  </button>}
              </div>
              <p className="save-explanation" data-sp-b5d4ccf8="">
                {"Nháp tài khoản cần đủ thông tin cơ bản và vị trí đã xác nhận. Nội dung chưa đủ điều kiện chỉ được giữ trên trình duyệt, không được báo là đã lưu máy chủ."}
              </p>
            </form>
            <aside className="posting-sidebar" data-sp-b5d4ccf8="">
              <section className="sidebar-card" data-sp-b5d4ccf8="">
                <p className="eyebrow" data-sp-b5d4ccf8="">
                  {"TIN ĐĂNG CỦA BẠN"}
                </p>
                <h2 data-sp-b5d4ccf8="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentTitle)}
                </h2>
                <dl data-sp-b5d4ccf8="">
                  <div data-sp-b5d4ccf8="">
                    <dt data-sp-b5d4ccf8="">
                      {"Nhu cầu"}
                    </dt>
                    <dd data-sp-b5d4ccf8="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.draft.transactionType)}
                    </dd>
                  </div>
                  <div data-sp-b5d4ccf8="">
                    <dt data-sp-b5d4ccf8="">
                      {"Loại"}
                    </dt>
                    <dd data-sp-b5d4ccf8="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.draft.propertyType)}
                    </dd>
                  </div>
                  <div data-sp-b5d4ccf8="">
                    <dt data-sp-b5d4ccf8="">
                      {"Diện tích"}
                    </dt>
                    <dd data-sp-b5d4ccf8="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.areaText)}
                      {" m²"}
                    </dd>
                  </div>
                  <div data-sp-b5d4ccf8="">
                    <dt data-sp-b5d4ccf8="">
                      {"Giá"}
                    </dt>
                    <dd data-sp-b5d4ccf8="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.priceText)}
                      {" VND "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.unitText)}
                    </dd>
                  </div>
                  <div data-sp-b5d4ccf8="">
                    <dt data-sp-b5d4ccf8="">
                      {"Hình ảnh"}
                    </dt>
                    <dd data-sp-b5d4ccf8="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.imageCount)}
                      {" / 30 ảnh"}
                    </dd>
                  </div>
                  <div data-sp-b5d4ccf8="">
                    <dt data-sp-b5d4ccf8="">
                      {"Vị trí"}
                    </dt>
                    <dd data-sp-b5d4ccf8="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.locationConfirmed(view.draft) ? "Đã xác nhận" : "Chưa xác nhận")}
                    </dd>
                  </div>
                </dl>
                <div className="draft-status" data-sp-b5d4ccf8="">
                  <strong data-sp-b5d4ccf8="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.managed ? "Nháp tài khoản đã có mã tin" : "Nháp trên trình duyệt")}
                  </strong>
                  {view.managed ? <p data-sp-b5d4ccf8="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.dirty ? "Còn thay đổi trong form cần lưu." : "Thông tin hiện tại khớp nháp trên máy chủ.")}
                    </p> : <p data-sp-b5d4ccf8="">
                      {"Nội dung chưa được lưu vào tài khoản."}
                    </p>}
                  {view.state.savedAt ? <p data-sp-b5d4ccf8="">
                      {"Lưu tài khoản gần nhất: "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(new Date(view.state.savedAt).toLocaleTimeString("vi-VN"))}
                    </p> : null}
                </div>
                <p className="sidebar-note" data-sp-b5d4ccf8="">
                  {"Gửi duyệt không tự công khai tin. Bạn có thể theo dõi kết quả tại Tin đăng của tôi."}
                </p>
              </section>
              {view.step === 1 ? <details className="valuation-optional" onToggle={$event => {
              view.updateShowValuationValue($event.target.open);
            }} data-sp-b5d4ccf8="">
                  <summary data-sp-b5d4ccf8="">
                    {"Giá tham khảo "}
                    <span data-sp-b5d4ccf8="">
                      {"Tùy chọn"}
                    </span>
                  </summary>
                  {view.showValuation ? <PostValuationPanel draft={view.draft} data-sp-b5d4ccf8="" onDraftChange={value => view.updateDraft(draft => Object.assign(draft, value))} /> : null}
                </details> : null}
            </aside>
          </div>}
      </div>
    </div></>;
});
