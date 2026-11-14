import React from "react";
import {
  useSetup,
  propsForSetup,
  emitForProps,
  exposeForSetup,
} from "../../shared/state/store.js";
import {
  mergeProps,
  bindRef,
  renderList,
  display,
  modelProps,
  rootProps,
  Teleport,
} from "../../shared/components/rendering.js";
import { RouterLink, RouterView } from "../../shared/routing/router.jsx";
import { computed, ref } from "../../shared/state/store.js";
import { useRoute } from "../../shared/routing/router.jsx";
import { usePost } from "./legacyPost.js";
import {
  postSteps,
  propertyOptions,
  priceInput,
  areaInput,
  formatDecimal,
  hasRooms,
  locationConfirmed,
} from "./postForm.js";
import { districts } from "../map/districts.js";
import { administrativeHints } from "../map/geocoding.js";
import PostStepNav from "./PostStepNav.jsx";
import PostValidationSummary from "./PostValidationSummary.jsx";
import GooglePropertyLocation from "../map/GooglePropertyLocation.jsx";
import PrivateImage from "../../shared/components/PrivateImage.jsx";
import PostValuationPanel from "../prediction/PostValuationPanel.jsx";
import ImageScanSection from "./ImageScanSection.jsx";
import ImageAnalysisSection from "./ImageAnalysisSection.jsx";
import "./PostView.css";
function setup(__props) {
  const route = useRoute(),
    editor = usePost();
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
    editAgain,
  } = editor;
  const step = computed(
      () => postSteps.find((s) => s.path === route.path)?.step || 3,
    ),
    fileInput = ref(null),
    showValuation = ref(false);
  const priceText = computed(() => formatDecimal(priceInput(draft.price))),
    areaText = computed(() => formatDecimal(areaInput(draft.area)));
  const unitText = computed(() =>
    draft.transactionType === "Bán"
      ? ""
      : {
          PER_MONTH: "/ tháng",
          PER_YEAR: "/ năm",
          PER_DAY: "/ ngày",
          TOTAL: "trọn kỳ thuê",
        }[draft.rentUnit],
  );
  const currentTitle = computed(() => postSteps[step.value - 1].label);
  const locked = computed(() => state.busy || !state.loaded || state.loadError);
  const addressHints = computed(() =>
    administrativeHints(
      draft,
      districts.filter((d) => d !== "Tất cả"),
    ),
  );
  const addressSyncNotice = ref("");
  function synchronizeAddressFields() {
    if (locked.value) return;
    const hints = administrativeHints(
      draft,
      districts.filter((d) => d !== "Tất cả"),
    );
    if (!draft.ward && hints.ward) draft.ward = hints.ward;
    if (!draft.district && hints.district) draft.district = hints.district;
    addressSyncNotice.value =
      "Giữ phạm vi địa bàn bạn đã chọn khi sửa địa chỉ. Nếu tên phường/quận trong địa chỉ khác bộ lọc, hãy điều chỉnh một trong hai trước khi tìm; hệ thống không tự mở rộng phạm vi.";
  }
  function applyAddressHints() {
    if (locked.value) return;
    const hints = addressHints.value;
    if (!draft.district && hints.district) draft.district = hints.district;
    if (!draft.ward && hints.ward) draft.ward = hints.ward;
  }
  const cover = computed(
    () => images.value.find((e) => e.key === coverKey.value) || images.value[0],
  );
  const amenityOptions = [
    "Máy lạnh",
    "Tủ lạnh",
    "Máy giặt",
    "Giường",
    "Sofa",
    "Tivi",
    "Bàn ăn",
    "Ban công",
    "Chỗ để xe",
  ];
  function pickFiles(event) {
    chooseFiles(event.target.files || []);
    event.target.value = "";
  }
  function dropFiles(event) {
    if (!locked.value) chooseFiles(event.dataTransfer.files);
  }
  function toggleAmenity(value) {
    draft.selectedAmenities = draft.selectedAmenities.includes(value)
      ? draft.selectedAmenities.filter((v) => v !== value)
      : [...draft.selectedAmenities, value];
  }
  return {
    computed,
    ref,
    useRoute,
    usePost,
    postSteps,
    propertyOptions,
    priceInput,
    areaInput,
    formatDecimal,
    hasRooms,
    locationConfirmed,
    districts,
    administrativeHints,
    PostStepNav,
    PostValidationSummary,
    GooglePropertyLocation,
    PrivateImage,
    PostValuationPanel,
    ImageScanSection,
    ImageAnalysisSection,
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
    chooseFiles,
    removeImage,
    moveImage,
    chooseCover,
    selectLocation,
    clearLocation,
    confirmLocation,
    checkResult,
    reviewVersion,
    editAgain,
    step,
    fileInput,
    showValuation,
    priceText,
    areaText,
    unitText,
    currentTitle,
    locked,
    addressHints,
    addressSyncNotice,
    synchronizeAddressFields,
    applyAddressHints,
    cover,
    amenityOptions,
    pickFiles,
    dropFiles,
    toggleAmenity,
  };
}
export default React.forwardRef(function PostView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="PostView"
      {...mergeProps({
        className: "posting-page",
        "data-sp-b5d4ccf8": "",
      })}
    >
      <div
        {...mergeProps({
          className: "posting-main",
          "data-sp-b5d4ccf8": "",
        })}
      >
        <div
          {...mergeProps({
            className: "posting-title",
            "data-sp-b5d4ccf8": "",
          })}
        >
          <div
            {...mergeProps({
              "data-sp-b5d4ccf8": "",
            })}
          >
            <p
              {...mergeProps({
                className: "eyebrow",
                "data-sp-b5d4ccf8": "",
              })}
            >
              {"ĐĂNG BÁN / CHO THUÊ"}
            </p>
            <h1
              {...mergeProps({
                "data-sp-b5d4ccf8": "",
              })}
            >
              {display(ctx.managed ? "Chỉnh sửa tin đăng" : "Tạo tin đăng mới")}
            </h1>
            <p
              {...mergeProps({
                "data-sp-b5d4ccf8": "",
              })}
            >
              {"Thông tin rõ ràng, hình ảnh thực tế và vị trí do bạn xác nhận."}
            </p>
          </div>
          <span
            {...mergeProps({
              className: "step-badge",
              "data-sp-b5d4ccf8": "",
            })}
          >
            {"Bước "}
            {display(ctx.step)}
            {" / 3"}
          </span>
        </div>
        <PostStepNav
          {...mergeProps({
            current: ctx.step,
            busy: ctx.state.busy,
            "data-sp-b5d4ccf8": "",
          })}
        />
        <PostValidationSummary
          {...mergeProps({
            issues: ctx.state.issues,
            "data-sp-b5d4ccf8": "",
          })}
        />
        {ctx.state.error ? (
          <div
            {...mergeProps({
              className: "posting-alert error",
              role: "alert",
              "data-sp-b5d4ccf8": "",
            })}
          >
            <strong
              {...mergeProps({
                "data-sp-b5d4ccf8": "",
              })}
            >
              {"Chưa hoàn tất thao tác"}
            </strong>
            <p
              {...mergeProps({
                "data-sp-b5d4ccf8": "",
              })}
            >
              {display(ctx.state.error)}
            </p>
            {ctx.state.conflict ? (
              <button
                {...mergeProps({
                  type: "button",
                  disabled: ctx.state.busy,
                  onClick: ($event) => {
                    return ctx.reviewVersion?.($event);
                  },
                  "data-sp-b5d4ccf8": "",
                })}
              >
                {"Đối chiếu phiên bản máy chủ"}
              </button>
            ) : null}
            {ctx.state.uncertainCreate || ctx.state.uncertainUpload ? (
              <button
                {...mergeProps({
                  type: "button",
                  disabled: ctx.state.busy,
                  onClick: ($event) => {
                    return ctx.checkResult?.($event);
                  },
                  "data-sp-b5d4ccf8": "",
                })}
              >
                {"Đối chiếu kết quả"}
              </button>
            ) : null}
            {ctx.state.loadError ? (
              <button
                {...mergeProps({
                  type: "button",
                  disabled: ctx.state.busy,
                  onClick: ($event) => {
                    ctx.editor.initialize(ctx.route.query.edit);
                  },
                  "data-sp-b5d4ccf8": "",
                })}
              >
                {"Thử tải lại tin"}
              </button>
            ) : null}
          </div>
        ) : null}
        {ctx.state.notice && !ctx.state.complete ? (
          <p
            {...mergeProps({
              role: "status",
              className: "posting-alert notice",
              "data-sp-b5d4ccf8": "",
            })}
          >
            {display(ctx.state.notice)}
          </p>
        ) : null}
        {ctx.state.localSaveError ? (
          <p
            {...mergeProps({
              role: "status",
              className: "posting-alert error",
              "data-sp-b5d4ccf8": "",
            })}
          >
            {
              "Trình duyệt chưa giữ được bản nháp. Nội dung vẫn ở tab này; hãy lưu nháp tài khoản khi đủ thông tin và vị trí."
            }
          </p>
        ) : null}
        {ctx.state.complete ? (
          <section
            {...mergeProps({
              className: "posting-success",
              role: "status",
              "data-sp-b5d4ccf8": "",
            })}
          >
            <span
              {...mergeProps({
                className: "success-symbol",
                "data-sp-b5d4ccf8": "",
              })}
            >
              {"✓"}
            </span>
            <p
              {...mergeProps({
                className: "eyebrow",
                "data-sp-b5d4ccf8": "",
              })}
            >
              {"ĐÃ GỬI DUYỆT"}
            </p>
            <h2
              {...mergeProps({
                "data-sp-b5d4ccf8": "",
              })}
            >
              {"Tin của bạn đã được tiếp nhận"}
            </h2>
            <p
              {...mergeProps({
                "data-sp-b5d4ccf8": "",
              })}
            >
              {display(ctx.managed?.property.title)}
            </p>
            <p
              {...mergeProps({
                "data-sp-b5d4ccf8": "",
              })}
            >
              {"Trạng thái trên máy chủ: "}
              <strong
                {...mergeProps({
                  "data-sp-b5d4ccf8": "",
                })}
              >
                {display(
                  ctx.managed?.property.status === "PENDING"
                    ? "Chờ duyệt"
                    : ctx.managed?.property.status === "PUBLISHED"
                      ? "Đã được duyệt"
                      : ctx.managed?.property.status,
                )}
              </strong>
              {". Tin chỉ hiển thị công khai khi được quản trị viên phê duyệt."}
            </p>
            <div
              {...mergeProps({
                className: "success-actions",
                "data-sp-b5d4ccf8": "",
              })}
            >
              <RouterLink
                {...mergeProps({
                  className: "primary-button",
                  to: "/my-listing",
                  "data-sp-b5d4ccf8": "",
                })}
              >
                {"Đến tin đăng của tôi"}
              </RouterLink>
              <button
                {...mergeProps({
                  type: "button",
                  className: "secondary-button",
                  onClick: ($event) => {
                    return ctx.editAgain?.($event);
                  },
                  "data-sp-b5d4ccf8": "",
                })}
              >
                {"Chỉnh sửa lại"}
              </button>
              <button
                {...mergeProps({
                  type: "button",
                  className: "text-button",
                  onClick: ($event) => {
                    return ctx.startNew?.($event);
                  },
                  "data-sp-b5d4ccf8": "",
                })}
              >
                {"Tạo tin khác"}
              </button>
            </div>
          </section>
        ) : (
          <div
            {...mergeProps({
              className: "posting-layout",
              "data-sp-b5d4ccf8": "",
            })}
          >
            <form
              {...mergeProps({
                className: "posting-form",
                noValidate: true,
                onSubmit: ($event) => {
                  $event.preventDefault();
                  ctx.step < 3 && ctx.goNext();
                },
                "data-sp-b5d4ccf8": "",
              })}
            >
              <fieldset
                {...mergeProps({
                  disabled: ctx.locked,
                  "data-sp-b5d4ccf8": "",
                })}
              >
                {ctx.step === 1 ? (
                  <React.Fragment {...mergeProps({})}>
                    <section
                      {...mergeProps({
                        className: "posting-card",
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          className: "card-heading",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            className: "section-number",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {"01"}
                        </span>
                        <div
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <h2
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Thông tin & giá"}
                          </h2>
                          <p
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {
                              "Bắt đầu với nhu cầu và thông tin chính của bất động sản."
                            }
                          </p>
                        </div>
                      </div>
                      <div
                        {...mergeProps({
                          className: "field",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            id: "transaction-label",
                            className: "field-label",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {"Nhu cầu "}
                          <span
                            {...mergeProps({
                              className: "required",
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"*"}
                          </span>
                        </span>
                        <div
                          {...mergeProps({
                            id: "post-transactionType",
                            className: "transaction-options",
                            role: "group",
                            "aria-labelledby": "transaction-label",
                            tabIndex: "-1",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {renderList(["Bán", "Cho thuê"], (value) => (
                            <button
                              key={value}
                              {...mergeProps({
                                type: "button",
                                "aria-pressed":
                                  ctx.draft.transactionType === value,
                                className: {
                                  selected: ctx.draft.transactionType === value,
                                },
                                onClick: ($event) => {
                                  ctx.draft.transactionType = value;
                                },
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {display(
                                value === "Bán" ? "Đăng bán" : "Cho thuê",
                              )}
                            </button>
                          ))}
                        </div>
                      </div>
                      <label
                        {...mergeProps({
                          className: "field",
                          htmlFor: "post-propertyType",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {"Loại bất động sản "}
                          <span
                            {...mergeProps({
                              className: "required",
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"*"}
                          </span>
                        </span>
                        <select
                          {...mergeProps(
                            {
                              id: "post-propertyType",
                              "data-sp-b5d4ccf8": "",
                            },
                            modelProps(
                              ctx.draft.propertyType,
                              ($value) => {
                                ctx.draft.propertyType = $value;
                              },
                              {
                                kind: "text",
                                value: "on",
                                number: false,
                                multiple: false,
                              },
                            ),
                          )}
                        >
                          {renderList(ctx.propertyOptions, (option) => (
                            <option
                              key={option.value}
                              {...mergeProps({
                                value: option.value,
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {display(option.label)}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label
                        {...mergeProps({
                          className: "field",
                          htmlFor: "post-title",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {"Tiêu đề tin đăng "}
                          <span
                            {...mergeProps({
                              className: "required",
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"*"}
                          </span>
                        </span>
                        <input
                          {...mergeProps(
                            {
                              id: "post-title",
                              maxLength: "255",
                              placeholder:
                                "Ví dụ: Bán căn hộ 2 phòng ngủ, ban công thoáng tại Hải Châu",
                              autoComplete: "off",
                              "data-sp-b5d4ccf8": "",
                            },
                            modelProps(
                              ctx.draft.title,
                              ($value) => {
                                ctx.draft.title = $value;
                              },
                              {
                                kind: "text",
                                value: "on",
                                number: false,
                                multiple: false,
                              },
                            ),
                          )}
                        />
                        <small
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {display(ctx.draft.title.length)}
                          {
                            " / 255 ký tự · Nêu điểm nổi bật, tránh viết toàn bộ bằng chữ in hoa."
                          }
                        </small>
                      </label>
                      <div
                        {...mergeProps({
                          className: "field-grid",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <label
                          {...mergeProps({
                            className: "field",
                            htmlFor: "post-area",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Diện tích "}
                            <span
                              {...mergeProps({
                                className: "required",
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"*"}
                            </span>
                          </span>
                          <div
                            {...mergeProps({
                              className: "input-unit",
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            <input
                              {...mergeProps(
                                {
                                  id: "post-area",
                                  inputMode: "decimal",
                                  placeholder: "86,3",
                                  "data-sp-b5d4ccf8": "",
                                },
                                modelProps(
                                  ctx.draft.area,
                                  ($value) => {
                                    ctx.draft.area = $value;
                                  },
                                  {
                                    kind: "text",
                                    value: "on",
                                    number: false,
                                    multiple: false,
                                  },
                                ),
                              )}
                            />
                            <span
                              {...mergeProps({
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"m²"}
                            </span>
                          </div>
                          {ctx.areaInput(ctx.draft.area) !== null ? (
                            <small
                              {...mergeProps({
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {display(ctx.areaText)}
                              {" m²"}
                            </small>
                          ) : null}
                        </label>
                        <label
                          {...mergeProps({
                            className: "field",
                            htmlFor: "post-price",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {display(
                              ctx.draft.transactionType === "Bán"
                                ? "Giá bán"
                                : "Giá thuê",
                            )}{" "}
                            <span
                              {...mergeProps({
                                className: "required",
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"*"}
                            </span>
                          </span>
                          <div
                            {...mergeProps({
                              className: "input-unit",
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            <input
                              {...mergeProps(
                                {
                                  id: "post-price",
                                  inputMode: "decimal",
                                  placeholder: "Ví dụ: 2,5 tỷ hoặc 12.000.000",
                                  "data-sp-b5d4ccf8": "",
                                },
                                modelProps(
                                  ctx.draft.price,
                                  ($value) => {
                                    ctx.draft.price = $value;
                                  },
                                  {
                                    kind: "text",
                                    value: "on",
                                    number: false,
                                    multiple: false,
                                  },
                                ),
                              )}
                            />
                            <span
                              {...mergeProps({
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"VND"}
                            </span>
                          </div>
                          {ctx.priceInput(ctx.draft.price) !== null ? (
                            <small
                              {...mergeProps({
                                className: "exact-value",
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {display(ctx.priceText)}
                              {" VND "}
                              {display(ctx.unitText)}
                            </small>
                          ) : (
                            <small
                              {...mergeProps({
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"Nhập VND hoặc ghi rõ triệu/tỷ; ví dụ 2,5 tỷ."}
                            </small>
                          )}
                        </label>
                      </div>
                      {ctx.draft.transactionType === "Cho thuê" ? (
                        <label
                          {...mergeProps({
                            className: "field",
                            htmlFor: "post-priceUnit",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Đơn vị giá thuê "}
                            <span
                              {...mergeProps({
                                className: "required",
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"*"}
                            </span>
                          </span>
                          <select
                            {...mergeProps(
                              {
                                id: "post-priceUnit",
                                "data-sp-b5d4ccf8": "",
                              },
                              modelProps(
                                ctx.draft.rentUnit,
                                ($value) => {
                                  ctx.draft.rentUnit = $value;
                                },
                                {
                                  kind: "text",
                                  value: "on",
                                  number: false,
                                  multiple: false,
                                },
                              ),
                            )}
                          >
                            <option
                              {...mergeProps({
                                value: "PER_MONTH",
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"VND / tháng"}
                            </option>
                            <option
                              {...mergeProps({
                                value: "PER_YEAR",
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"VND / năm"}
                            </option>
                            <option
                              {...mergeProps({
                                value: "PER_DAY",
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"VND / ngày"}
                            </option>
                            <option
                              {...mergeProps({
                                value: "TOTAL",
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"VND / trọn kỳ thuê"}
                            </option>
                          </select>
                        </label>
                      ) : null}
                      {ctx.hasRooms(ctx.draft.propertyType) ? (
                        <div
                          {...mergeProps({
                            className: "field-grid optional-rooms",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <label
                            {...mergeProps({
                              className: "field",
                              htmlFor: "post-bedrooms",
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            <span
                              {...mergeProps({
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"Phòng ngủ "}
                              <small
                                {...mergeProps({
                                  "data-sp-b5d4ccf8": "",
                                })}
                              >
                                {"Tùy chọn"}
                              </small>
                            </span>
                            <input
                              {...mergeProps(
                                {
                                  id: "post-bedrooms",
                                  type: "number",
                                  min: "0",
                                  max: "32767",
                                  step: "1",
                                  placeholder: "Không cung cấp",
                                  "data-sp-b5d4ccf8": "",
                                },
                                modelProps(
                                  ctx.draft.bedrooms,
                                  ($value) => {
                                    ctx.draft.bedrooms = $value;
                                  },
                                  {
                                    kind: "number",
                                    value: "on",
                                    number: false,
                                    multiple: false,
                                  },
                                ),
                              )}
                            />
                          </label>
                          <label
                            {...mergeProps({
                              className: "field",
                              htmlFor: "post-bathrooms",
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            <span
                              {...mergeProps({
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"Phòng tắm "}
                              <small
                                {...mergeProps({
                                  "data-sp-b5d4ccf8": "",
                                })}
                              >
                                {"Tùy chọn"}
                              </small>
                            </span>
                            <input
                              {...mergeProps(
                                {
                                  id: "post-bathrooms",
                                  type: "number",
                                  min: "0",
                                  max: "32767",
                                  step: "1",
                                  placeholder: "Không cung cấp",
                                  "data-sp-b5d4ccf8": "",
                                },
                                modelProps(
                                  ctx.draft.bathrooms,
                                  ($value) => {
                                    ctx.draft.bathrooms = $value;
                                  },
                                  {
                                    kind: "number",
                                    value: "on",
                                    number: false,
                                    multiple: false,
                                  },
                                ),
                              )}
                            />
                          </label>
                        </div>
                      ) : null}
                    </section>
                  </React.Fragment>
                ) : ctx.step === 2 ? (
                  <React.Fragment {...mergeProps({})}>
                    <section
                      {...mergeProps({
                        id: "post-images",
                        tabIndex: "-1",
                        className: "posting-card",
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          className: "card-heading",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            className: "section-number",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {"02"}
                        </span>
                        <div
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <h2
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Ảnh bất động sản"}
                          </h2>
                          <p
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {
                              "Ảnh rõ ràng giúp người xem hiểu đúng bất động sản."
                            }
                          </p>
                        </div>
                        <span
                          {...mergeProps({
                            className: "count-badge",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {display(ctx.imageCount)}
                          {" / 30"}
                        </span>
                      </div>
                      <div
                        {...mergeProps({
                          className: "upload-zone",
                          onDragOver: ($event) => {
                            $event.preventDefault();
                            undefined;
                          },
                          onDrop: ($event) => {
                            $event.preventDefault();
                            return ctx.dropFiles?.($event);
                          },
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            className: "upload-symbol",
                            "aria-hidden": "true",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {"↑"}
                        </span>
                        <h3
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {"Chọn nhiều ảnh hoặc kéo ảnh vào đây"}
                        </h3>
                        <p
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {"JPEG/PNG · tối đa 10 MB/ảnh · tối đa 30 ảnh"}
                        </p>
                        <button
                          {...mergeProps({
                            type: "button",
                            className: "secondary-button",
                            onClick: ($event) => {
                              ctx.fileInput?.click();
                            },
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {"Chọn ảnh từ thiết bị"}
                        </button>
                        <input
                          {...mergeProps({
                            ref: bindRef(ctx, "fileInput"),
                            className: "visually-hidden",
                            type: "file",
                            accept: "image/jpeg,image/png",
                            multiple: true,
                            "aria-label": "Tải ảnh bất động sản",
                            onChange: ($event) => {
                              return ctx.pickFiles?.($event);
                            },
                            "data-sp-b5d4ccf8": "",
                          })}
                        />
                      </div>
                      <p
                        {...mergeProps({
                          className: "field-help",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        {
                          "Lưu nháp không bắt buộc ảnh; gửi duyệt cần ít nhất 1 ảnh. Ảnh tối đa 12000 px mỗi chiều và 40 triệu pixel. Chỉ đăng ảnh bạn có quyền sử dụng."
                        }
                      </p>
                      {ctx.images.length ? (
                        <div
                          {...mergeProps({
                            className: "photo-grid",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {renderList(ctx.images, (entry, index) => (
                            <article
                              key={entry.key}
                              {...mergeProps({
                                className: "photo-card",
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              <div
                                {...mergeProps({
                                  className: "photo-image",
                                  "data-sp-b5d4ccf8": "",
                                })}
                              >
                                {entry.server ? (
                                  <PrivateImage
                                    {...mergeProps({
                                      src: entry.server.url,
                                      alt: "Ảnh bất động sản " + (index + 1),
                                      "data-sp-b5d4ccf8": "",
                                    })}
                                  />
                                ) : (
                                  <img
                                    {...mergeProps({
                                      src: entry.preview,
                                      alt: entry.file.name,
                                      "data-sp-b5d4ccf8": "",
                                    })}
                                  />
                                )}
                                {ctx.coverKey === entry.key ? (
                                  <span
                                    {...mergeProps({
                                      className: "cover-badge",
                                      "data-sp-b5d4ccf8": "",
                                    })}
                                  >
                                    {"Ảnh đại diện"}
                                  </span>
                                ) : null}
                                <span
                                  {...mergeProps({
                                    className: "upload-badge",
                                    "data-sp-b5d4ccf8": "",
                                  })}
                                >
                                  {display(
                                    entry.server ? "Đã tải" : "Chưa tải",
                                  )}
                                </span>
                              </div>
                              <p
                                {...mergeProps({
                                  className: "photo-name",
                                  "data-sp-b5d4ccf8": "",
                                })}
                              >
                                {display(
                                  entry.file?.name || "Ảnh " + (index + 1),
                                )}
                              </p>
                              <button
                                {...mergeProps({
                                  type: "button",
                                  className: "cover-button",
                                  "aria-pressed": ctx.coverKey === entry.key,
                                  onClick: ($event) => {
                                    ctx.chooseCover(entry.key);
                                  },
                                  "data-sp-b5d4ccf8": "",
                                })}
                              >
                                {display(
                                  ctx.coverKey === entry.key
                                    ? "✓ Ảnh đại diện"
                                    : "Chọn làm đại diện",
                                )}
                              </button>
                              <div
                                {...mergeProps({
                                  className: "photo-actions",
                                  "data-sp-b5d4ccf8": "",
                                })}
                              >
                                <button
                                  {...mergeProps({
                                    type: "button",
                                    disabled: index === 0,
                                    "aria-label":
                                      "Đưa ảnh " + (index + 1) + " lên trước",
                                    onClick: ($event) => {
                                      ctx.moveImage(entry.key, -1);
                                    },
                                    "data-sp-b5d4ccf8": "",
                                  })}
                                >
                                  {"↑ Lên"}
                                </button>
                                <button
                                  {...mergeProps({
                                    type: "button",
                                    disabled: index === ctx.images.length - 1,
                                    "aria-label":
                                      "Đưa ảnh " + (index + 1) + " xuống sau",
                                    onClick: ($event) => {
                                      ctx.moveImage(entry.key, 1);
                                    },
                                    "data-sp-b5d4ccf8": "",
                                  })}
                                >
                                  {"↓ Xuống"}
                                </button>
                                <button
                                  {...mergeProps({
                                    type: "button",
                                    "aria-label": "Xóa ảnh " + (index + 1),
                                    className: "delete-image",
                                    onClick: ($event) => {
                                      ctx.removeImage(entry.key);
                                    },
                                    "data-sp-b5d4ccf8": "",
                                  })}
                                >
                                  {"Xóa"}
                                </button>
                              </div>
                            </article>
                          ))}
                        </div>
                      ) : null}
                      {ctx.managed?.property.id ? (
                        <>
                          <ImageScanSection propertyId={ctx.managed.property.id} compact />
                          <ImageAnalysisSection propertyId={ctx.managed.property.id} compact />
                        </>
                      ) : ctx.images.length ? (
                        <p className="field-help">
                          {"Ảnh sẽ được kiểm tra trùng tự động sau khi bạn lưu nháp. Không cần mở trang kiểm tra riêng."}
                        </p>
                      ) : null}
                    </section>
                    <section
                      {...mergeProps({
                        className: "posting-card",
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          className: "card-heading",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <div
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <h2
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Địa chỉ & vị trí"}
                          </h2>
                          <p
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {
                              "Nhập địa chỉ thực tế, chọn ghim rồi xác nhận vị trí."
                            }
                          </p>
                        </div>
                      </div>
                      <label
                        {...mergeProps({
                          className: "field",
                          htmlFor: "post-address",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {"Địa chỉ đầy đủ "}
                          <span
                            {...mergeProps({
                              className: "required",
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"*"}
                          </span>
                        </span>
                        <input
                          {...mergeProps(
                            {
                              id: "post-address",
                              onChange: ($event) => {
                                return ctx.synchronizeAddressFields?.($event);
                              },
                              autoComplete: "street-address",
                              maxLength: "4000",
                              placeholder: "Số nhà, đường, phường và thành phố",
                              "data-sp-b5d4ccf8": "",
                            },
                            modelProps(
                              ctx.draft.address,
                              ($value) => {
                                ctx.draft.address = $value;
                              },
                              {
                                kind: "text",
                                value: "on",
                                number: false,
                                multiple: false,
                              },
                            ),
                          )}
                        />
                        <small
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {
                            "Nhập số nhà, tên đường, phường và thành phố."
                          }
                        </small>
                      </label>
                      {ctx.addressSyncNotice ? (
                        <p
                          {...mergeProps({
                            role: "status",
                            className: "field-help",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {display(ctx.addressSyncNotice)}
                        </p>
                      ) : null}
                      <div
                        {...mergeProps({
                          className: "field-grid three",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <label
                          {...mergeProps({
                            className: "field",
                            htmlFor: "post-city",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Thành phố"}
                          </span>
                          <select
                            {...mergeProps(
                              {
                                id: "post-city",
                                "data-sp-b5d4ccf8": "",
                              },
                              modelProps(
                                ctx.draft.city,
                                ($value) => {
                                  ctx.draft.city = $value;
                                },
                                {
                                  kind: "text",
                                  value: "on",
                                  number: false,
                                  multiple: false,
                                },
                              ),
                            )}
                          >
                            <option
                              {...mergeProps({
                                value: "Da Nang",
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"Đà Nẵng"}
                            </option>
                            {ctx.draft.city && ctx.draft.city !== "Da Nang" ? (
                              <option
                                {...mergeProps({
                                  value: ctx.draft.city,
                                  "data-sp-b5d4ccf8": "",
                                })}
                              >
                                {display(ctx.draft.city)}
                              </option>
                            ) : null}
                          </select>
                        </label>
                        <label
                          {...mergeProps({
                            className: "field",
                            htmlFor: "post-district",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Quận/huyện "}
                            <small
                              {...mergeProps({
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"Tùy chọn"}
                            </small>
                          </span>
                          <select
                            {...mergeProps(
                              {
                                id: "post-district",
                                "data-sp-b5d4ccf8": "",
                              },
                              modelProps(
                                ctx.draft.district,
                                ($value) => {
                                  ctx.draft.district = $value;
                                },
                                {
                                  kind: "text",
                                  value: "on",
                                  number: false,
                                  multiple: false,
                                },
                              ),
                            )}
                          >
                            <option
                              {...mergeProps({
                                value: "",
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"Chọn khu vực"}
                            </option>
                            {renderList(
                              ctx.districts.filter((d) => d !== "Tất cả"),
                              (district) => (
                                <option
                                  key={district}
                                  {...mergeProps({
                                    "data-sp-b5d4ccf8": "",
                                  })}
                                >
                                  {display(district)}
                                </option>
                              ),
                            )}
                            {ctx.draft.district &&
                            !ctx.districts.includes(ctx.draft.district) ? (
                              <option
                                {...mergeProps({
                                  value: ctx.draft.district,
                                  "data-sp-b5d4ccf8": "",
                                })}
                              >
                                {display(ctx.draft.district)}
                              </option>
                            ) : null}
                          </select>
                        </label>
                        <label
                          {...mergeProps({
                            className: "field",
                            htmlFor: "post-ward",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Phường/xã "}
                            <small
                              {...mergeProps({
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"Tùy chọn"}
                            </small>
                          </span>
                          <input
                            {...mergeProps(
                              {
                                id: "post-ward",
                                maxLength: "100",
                                placeholder: "Phường/xã",
                                "data-sp-b5d4ccf8": "",
                              },
                              modelProps(
                                ctx.draft.ward,
                                ($value) => {
                                  ctx.draft.ward = $value;
                                },
                                {
                                  kind: "text",
                                  value: "on",
                                  number: false,
                                  multiple: false,
                                },
                              ),
                            )}
                          />
                        </label>
                      </div>
                      {ctx.addressHints.district || ctx.addressHints.ward ? (
                        <div
                          {...mergeProps({
                            className:
                              "mt-4 rounded-xl border border-brand-line bg-brand-cream p-4 text-sm",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <p
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Gợi ý từ địa chỉ bạn nhập: "}
                            <strong
                              {...mergeProps({
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {display(
                                [
                                  ctx.addressHints.district,
                                  ctx.addressHints.ward,
                                ]
                                  .filter(Boolean)
                                  .join(" · "),
                              )}
                            </strong>
                            {
                              ". Đây là tên trong nội dung bạn nhập, chưa xác minh địa giới cũ/mới."
                            }
                          </p>
                          <button
                            {...mergeProps({
                              type: "button",
                              className: "secondary-button mt-3",
                              disabled: ctx.locked,
                              onClick: ($event) => {
                                return ctx.applyAddressHints?.($event);
                              },
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Điền các trường còn trống"}
                          </button>
                        </div>
                      ) : null}
                      <GooglePropertyLocation
                        {...mergeProps({
                          address: ctx.draft.address,
                          city: ctx.draft.city,
                          district: ctx.draft.district,
                          ward: ctx.draft.ward,
                          latitude: ctx.draft.latitude,
                          longitude: ctx.draft.longitude,
                          confirmed: ctx.locationConfirmed(ctx.draft),
                          disabled: ctx.locked,
                          onSelect: ($event) => {
                            return ctx.selectLocation?.($event);
                          },
                          onInvalidate: ($event) => {
                            return ctx.clearLocation?.($event);
                          },
                          onConfirm: ($event) => {
                            return ctx.confirmLocation?.($event);
                          },
                          "data-sp-b5d4ccf8": "",
                        })}
                      />
                    </section>
                  </React.Fragment>
                ) : (
                  <React.Fragment {...mergeProps({})}>
                    <section
                      {...mergeProps({
                        className: "posting-card",
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          className: "card-heading",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            className: "section-number",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {"03"}
                        </span>
                        <div
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <h2
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Mô tả & liên hệ"}
                          </h2>
                          <p
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {
                              "Bổ sung thông tin để người quan tâm dễ liên hệ với bạn."
                            }
                          </p>
                        </div>
                      </div>
                      <label
                        {...mergeProps({
                          className: "field",
                          htmlFor: "post-description",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {"Mô tả bất động sản "}
                          <small
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Tùy chọn"}
                          </small>
                        </span>
                        <textarea
                          {...mergeProps(
                            {
                              id: "post-description",
                              rows: "5",
                              maxLength: "20000",
                              placeholder:
                                "Mô tả không gian, hiện trạng, tiện ích và điều kiện bán hoặc cho thuê…",
                              "data-sp-b5d4ccf8": "",
                            },
                            modelProps(
                              ctx.draft.description,
                              ($value) => {
                                ctx.draft.description = $value;
                              },
                              {
                                kind: "text",
                                value: "on",
                                number: false,
                                multiple: false,
                              },
                            ),
                          )}
                        />
                        <small
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {display(ctx.draft.description.length)}
                          {" / 20000 ký tự"}
                        </small>
                      </label>
                      <div
                        {...mergeProps({
                          className: "field-grid",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <label
                          {...mergeProps({
                            className: "field",
                            htmlFor: "post-contactName",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Tên liên hệ "}
                            <small
                              {...mergeProps({
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"Tùy chọn"}
                            </small>
                          </span>
                          <input
                            {...mergeProps(
                              {
                                id: "post-contactName",
                                autoComplete: "name",
                                maxLength: "150",
                                placeholder: "Tên người liên hệ",
                                "data-sp-b5d4ccf8": "",
                              },
                              modelProps(
                                ctx.draft.contactName,
                                ($value) => {
                                  ctx.draft.contactName = $value;
                                },
                                {
                                  kind: "text",
                                  value: "on",
                                  number: false,
                                  multiple: false,
                                },
                              ),
                            )}
                          />
                        </label>
                        <label
                          {...mergeProps({
                            className: "field",
                            htmlFor: "post-phone",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Số điện thoại "}
                            <small
                              {...mergeProps({
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"Tùy chọn"}
                            </small>
                          </span>
                          <input
                            {...mergeProps(
                              {
                                id: "post-phone",
                                type: "tel",
                                autoComplete: "tel",
                                maxLength: "30",
                                placeholder: "Số điện thoại liên hệ",
                                "data-sp-b5d4ccf8": "",
                              },
                              modelProps(
                                ctx.draft.phone,
                                ($value) => {
                                  ctx.draft.phone = $value;
                                },
                                {
                                  kind: "tel",
                                  value: "on",
                                  number: false,
                                  multiple: false,
                                },
                              ),
                            )}
                          />
                        </label>
                      </div>
                      <label
                        {...mergeProps({
                          className: "field",
                          htmlFor: "post-contact",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {"Email liên hệ "}
                          <small
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Tùy chọn"}
                          </small>
                        </span>
                        <input
                          {...mergeProps(
                            {
                              id: "post-contact",
                              type: "email",
                              autoComplete: "email",
                              maxLength: "254",
                              placeholder: "Email người liên hệ",
                              "data-sp-b5d4ccf8": "",
                            },
                            modelProps(
                              ctx.draft.contact,
                              ($value) => {
                                ctx.draft.contact = $value;
                              },
                              {
                                kind: "email",
                                value: "on",
                                number: false,
                                multiple: false,
                              },
                            ),
                          )}
                        />
                      </label>
                      <p
                        {...mergeProps({
                          className: "field-help",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        {
                          "Thông tin liên hệ được gợi sẵn từ tài khoản và có thể chỉnh sửa. Chỉ cung cấp thông tin bạn có quyền sử dụng."
                        }
                      </p>
                    </section>
                    <details
                      {...mergeProps({
                        className: "posting-card extra-information",
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      <summary
                        {...mergeProps({
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        {"Thêm thông tin "}
                        <span
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {"Tùy chọn"}
                        </span>
                      </summary>
                      <div
                        {...mergeProps({
                          className: "field-grid three",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <label
                          {...mergeProps({
                            className: "field",
                            htmlFor: "post-direction",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Hướng nhà"}
                          </span>
                          <select
                            {...mergeProps(
                              {
                                id: "post-direction",
                                "data-sp-b5d4ccf8": "",
                              },
                              modelProps(
                                ctx.draft.direction,
                                ($value) => {
                                  ctx.draft.direction = $value;
                                },
                                {
                                  kind: "text",
                                  value: "on",
                                  number: false,
                                  multiple: false,
                                },
                              ),
                            )}
                          >
                            <option
                              {...mergeProps({
                                value: "",
                                "data-sp-b5d4ccf8": "",
                              })}
                            >
                              {"Không cung cấp"}
                            </option>
                            {renderList(
                              [
                                "Đông",
                                "Tây",
                                "Nam",
                                "Bắc",
                                "Đông Bắc",
                                "Đông Nam",
                                "Tây Bắc",
                                "Tây Nam",
                              ],
                              (value) => (
                                <option
                                  key={value}
                                  {...mergeProps({
                                    "data-sp-b5d4ccf8": "",
                                  })}
                                >
                                  {display(value)}
                                </option>
                              ),
                            )}
                          </select>
                        </label>
                        <label
                          {...mergeProps({
                            className: "field",
                            htmlFor: "post-floor",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Thông tin tầng"}
                          </span>
                          <input
                            {...mergeProps(
                              {
                                id: "post-floor",
                                maxLength: "30",
                                placeholder: "Ví dụ: Tầng 5 / 3 tầng",
                                "data-sp-b5d4ccf8": "",
                              },
                              modelProps(
                                ctx.draft.floor,
                                ($value) => {
                                  ctx.draft.floor = $value;
                                },
                                {
                                  kind: "text",
                                  value: "on",
                                  number: false,
                                  multiple: false,
                                },
                              ),
                            )}
                          />
                        </label>
                        <label
                          {...mergeProps({
                            className: "field",
                            htmlFor: "post-block",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Tòa / block"}
                          </span>
                          <input
                            {...mergeProps(
                              {
                                id: "post-block",
                                maxLength: "50",
                                placeholder: "Tòa / block",
                                "data-sp-b5d4ccf8": "",
                              },
                              modelProps(
                                ctx.draft.block,
                                ($value) => {
                                  ctx.draft.block = $value;
                                },
                                {
                                  kind: "text",
                                  value: "on",
                                  number: false,
                                  multiple: false,
                                },
                              ),
                            )}
                          />
                        </label>
                      </div>
                      <div
                        {...mergeProps({
                          id: "post-declaredAmenities",
                          tabIndex: "-1",
                          className: "amenities",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            className: "field-label",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {"Tiện ích & nội thất"}
                        </span>
                        {renderList(ctx.amenityOptions, (value) => (
                          <label
                            key={value}
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            <input
                              {...mergeProps({
                                type: "checkbox",
                                checked:
                                  ctx.draft.selectedAmenities.includes(value),
                                onChange: ($event) => {
                                  ctx.toggleAmenity(value);
                                },
                                "data-sp-b5d4ccf8": "",
                              })}
                            />
                            {display(value)}
                          </label>
                        ))}
                      </div>
                    </details>
                    <section
                      {...mergeProps({
                        className: "posting-card preview-card",
                        "aria-label": "Xem trước tin đăng",
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          className: "card-heading",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <div
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <h2
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Xem trước thông tin"}
                          </h2>
                          <p
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Kiểm tra lại trước khi gửi quản trị viên duyệt."}
                          </p>
                        </div>
                      </div>
                      <div
                        {...mergeProps({
                          className: "preview-summary",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        {ctx.cover ? (
                          <div
                            {...mergeProps({
                              className: "preview-photo",
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {ctx.cover.server ? (
                              <PrivateImage
                                {...mergeProps({
                                  src: ctx.cover.server.url,
                                  alt: "Ảnh đại diện xem trước",
                                  "data-sp-b5d4ccf8": "",
                                })}
                              />
                            ) : (
                              <img
                                {...mergeProps({
                                  src: ctx.cover.preview,
                                  alt: "Ảnh đại diện xem trước",
                                  "data-sp-b5d4ccf8": "",
                                })}
                              />
                            )}
                          </div>
                        ) : null}
                        <div
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              className: "preview-type",
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {display(ctx.draft.transactionType)}
                            {" · "}
                            {display(ctx.draft.propertyType)}
                          </span>
                          <h3
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {display(ctx.draft.title || "Chưa có tiêu đề")}
                          </h3>
                          <p
                            {...mergeProps({
                              className: "preview-price",
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {display(ctx.priceText)}
                            {" VND "}
                            {display(ctx.unitText)}
                          </p>
                          <p
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {display(ctx.areaText)}
                            {" m²"}
                            {ctx.hasRooms(ctx.draft.propertyType) &&
                            ctx.draft.bedrooms ? (
                              <span
                                {...mergeProps({
                                  "data-sp-b5d4ccf8": "",
                                })}
                              >
                                {" · "}
                                {display(ctx.draft.bedrooms)}
                                {" phòng ngủ"}
                              </span>
                            ) : null}
                          </p>
                          <p
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {display(ctx.draft.address || "Chưa có địa chỉ")}
                          </p>
                        </div>
                      </div>
                      <dl
                        {...mergeProps({
                          className: "preview-details",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <div
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <dt
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Ảnh"}
                          </dt>
                          <dd
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {display(ctx.imageCount)}
                            {" ảnh · "}
                            {display(
                              ctx.images.filter((e) => !e.server).length,
                            )}
                            {" ảnh chưa tải"}
                          </dd>
                        </div>
                        <div
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <dt
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Vị trí"}
                          </dt>
                          <dd
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {display(
                              ctx.locationConfirmed(ctx.draft)
                                ? "Đã xác nhận ghim"
                                : "Chưa xác nhận vị trí",
                            )}
                          </dd>
                        </div>
                        <div
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          <dt
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Liên hệ"}
                          </dt>
                          <dd
                            {...mergeProps({
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {display(
                              [
                                ctx.draft.contactName,
                                ctx.draft.phone,
                                ctx.draft.contact,
                              ]
                                .filter(Boolean)
                                .join(" · ") || "Chưa cung cấp",
                            )}
                          </dd>
                        </div>
                      </dl>
                      {ctx.draft.description ? (
                        <p
                          {...mergeProps({
                            className: "description-preview",
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {display(ctx.draft.description)}
                        </p>
                      ) : null}
                      <div
                        {...mergeProps({
                          className: "legal-note",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <p
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {
                            "Hồ sơ pháp lý không bắt buộc trong form cơ bản. Hồ sơ được quản lý riêng và chỉ có kết quả xác minh sau khi được kiểm duyệt."
                          }
                        </p>
                        {ctx.managed ? (
                          <RouterLink
                            {...mergeProps({
                              to:
                                "/account/properties/" +
                                ctx.managed.property.id +
                                "/legal-documents",
                              "data-sp-b5d4ccf8": "",
                            })}
                          >
                            {"Quản lý hồ sơ pháp lý riêng tư ↗"}
                          </RouterLink>
                        ) : null}
                      </div>
                      <label
                        {...mergeProps({
                          id: "post-consent",
                          className: "consent",
                          tabIndex: "-1",
                          "data-sp-b5d4ccf8": "",
                        })}
                      >
                        <input
                          {...mergeProps(
                            {
                              type: "checkbox",
                              "data-sp-b5d4ccf8": "",
                            },
                            modelProps(
                              ctx.draft.accepted,
                              ($value) => {
                                ctx.draft.accepted = $value;
                              },
                              {
                                kind: "checkbox",
                                value: "on",
                                number: false,
                                multiple: false,
                              },
                            ),
                          )}
                        />
                        <span
                          {...mergeProps({
                            "data-sp-b5d4ccf8": "",
                          })}
                        >
                          {
                            "Tôi xác nhận có quyền đăng nội dung, hình ảnh và chịu trách nhiệm về tính chính xác của thông tin này."
                          }
                        </span>
                      </label>
                    </section>
                  </React.Fragment>
                )}
              </fieldset>
              <div
                {...mergeProps({
                  className: "posting-actions",
                  "data-sp-b5d4ccf8": "",
                })}
              >
                <button
                  {...mergeProps({
                    type: "button",
                    className: "secondary-button back-button",
                    disabled: ctx.locked || ctx.step === 1,
                    onClick: ($event) => {
                      ctx.goStep(ctx.step - 1);
                    },
                    "data-sp-b5d4ccf8": "",
                  })}
                >
                  {"← Quay lại"}
                </button>
                <button
                  {...mergeProps({
                    type: "button",
                    className: "secondary-button save-button",
                    disabled: ctx.locked,
                    onClick: ($event) => {
                      ctx.saveDraft(false);
                    },
                    "data-sp-b5d4ccf8": "",
                  })}
                >
                  {display(ctx.state.busy ? "Đang xử lý…" : "Lưu nháp")}
                </button>
                {ctx.step < 3 ? (
                  <button
                    {...mergeProps({
                      type: "submit",
                      className: "primary-button",
                      disabled: ctx.locked,
                      "data-sp-b5d4ccf8": "",
                    })}
                  >
                    {"Tiếp tục →"}
                  </button>
                ) : (
                  <button
                    {...mergeProps({
                      type: "button",
                      className: "primary-button",
                      disabled: ctx.locked,
                      onClick: ($event) => {
                        ctx.saveDraft(true);
                      },
                      "data-sp-b5d4ccf8": "",
                    })}
                  >
                    {display(ctx.state.busy ? "Đang xử lý…" : "Gửi duyệt")}
                  </button>
                )}
              </div>
              <p
                {...mergeProps({
                  className: "save-explanation",
                  "data-sp-b5d4ccf8": "",
                })}
              >
                {
                  "Nháp tài khoản cần đủ thông tin cơ bản và vị trí đã xác nhận. Nội dung chưa đủ điều kiện chỉ được giữ trên trình duyệt, không được báo là đã lưu máy chủ."
                }
              </p>
            </form>
            <aside
              {...mergeProps({
                className: "posting-sidebar",
                "data-sp-b5d4ccf8": "",
              })}
            >
              <section
                {...mergeProps({
                  className: "sidebar-card",
                  "data-sp-b5d4ccf8": "",
                })}
              >
                <p
                  {...mergeProps({
                    className: "eyebrow",
                    "data-sp-b5d4ccf8": "",
                  })}
                >
                  {"TIN ĐĂNG CỦA BẠN"}
                </p>
                <h2
                  {...mergeProps({
                    "data-sp-b5d4ccf8": "",
                  })}
                >
                  {display(ctx.currentTitle)}
                </h2>
                <dl
                  {...mergeProps({
                    "data-sp-b5d4ccf8": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      "data-sp-b5d4ccf8": "",
                    })}
                  >
                    <dt
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {"Nhu cầu"}
                    </dt>
                    <dd
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {display(ctx.draft.transactionType)}
                    </dd>
                  </div>
                  <div
                    {...mergeProps({
                      "data-sp-b5d4ccf8": "",
                    })}
                  >
                    <dt
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {"Loại"}
                    </dt>
                    <dd
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {display(ctx.draft.propertyType)}
                    </dd>
                  </div>
                  <div
                    {...mergeProps({
                      "data-sp-b5d4ccf8": "",
                    })}
                  >
                    <dt
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {"Diện tích"}
                    </dt>
                    <dd
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {display(ctx.areaText)}
                      {" m²"}
                    </dd>
                  </div>
                  <div
                    {...mergeProps({
                      "data-sp-b5d4ccf8": "",
                    })}
                  >
                    <dt
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {"Giá"}
                    </dt>
                    <dd
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {display(ctx.priceText)}
                      {" VND "}
                      {display(ctx.unitText)}
                    </dd>
                  </div>
                  <div
                    {...mergeProps({
                      "data-sp-b5d4ccf8": "",
                    })}
                  >
                    <dt
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {"Hình ảnh"}
                    </dt>
                    <dd
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {display(ctx.imageCount)}
                      {" / 30 ảnh"}
                    </dd>
                  </div>
                  <div
                    {...mergeProps({
                      "data-sp-b5d4ccf8": "",
                    })}
                  >
                    <dt
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {"Vị trí"}
                    </dt>
                    <dd
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {display(
                        ctx.locationConfirmed(ctx.draft)
                          ? "Đã xác nhận"
                          : "Chưa xác nhận",
                      )}
                    </dd>
                  </div>
                </dl>
                <div
                  {...mergeProps({
                    className: "draft-status",
                    "data-sp-b5d4ccf8": "",
                  })}
                >
                  <strong
                    {...mergeProps({
                      "data-sp-b5d4ccf8": "",
                    })}
                  >
                    {display(
                      ctx.managed
                        ? "Nháp tài khoản đã có mã tin"
                        : "Nháp trên trình duyệt",
                    )}
                  </strong>
                  {ctx.managed ? (
                    <p
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {display(
                        ctx.dirty
                          ? "Còn thay đổi trong form cần lưu."
                          : "Thông tin hiện tại khớp nháp trên máy chủ.",
                      )}
                    </p>
                  ) : (
                    <p
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {"Nội dung chưa được lưu vào tài khoản."}
                    </p>
                  )}
                  {ctx.state.savedAt ? (
                    <p
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {"Lưu tài khoản gần nhất: "}
                      {display(
                        new Date(ctx.state.savedAt).toLocaleTimeString("vi-VN"),
                      )}
                    </p>
                  ) : null}
                </div>
                <p
                  {...mergeProps({
                    className: "sidebar-note",
                    "data-sp-b5d4ccf8": "",
                  })}
                >
                  {
                    "Gửi duyệt không tự công khai tin. Bạn có thể theo dõi kết quả tại Tin đăng của tôi."
                  }
                </p>
              </section>
              {ctx.step === 1 ? (
                <details
                  {...mergeProps({
                    className: "valuation-optional",
                    onToggle: ($event) => {
                      ctx.showValuation = $event.target.open;
                    },
                    "data-sp-b5d4ccf8": "",
                  })}
                >
                  <summary
                    {...mergeProps({
                      "data-sp-b5d4ccf8": "",
                    })}
                  >
                    {"Giá tham khảo "}
                    <span
                      {...mergeProps({
                        "data-sp-b5d4ccf8": "",
                      })}
                    >
                      {"Tùy chọn"}
                    </span>
                  </summary>
                  {ctx.showValuation ? (
                    <PostValuationPanel
                      {...mergeProps({
                        draft: ctx.draft,
                        "data-sp-b5d4ccf8": "",
                      })}
                    />
                  ) : null}
                </details>
              ) : null}
            </aside>
          </div>
        )}
      </div>
    </div>,
  ]);
});
