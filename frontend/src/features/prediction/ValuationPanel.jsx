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
import {
  computed,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from "../../shared/state/store.js";
import {
  buildValuationPayload,
  createValuationClient,
  featureLabels,
  formatPrice,
  locationLabel,
  warningLabel,
} from "./valuation.js";
import { session, errorText } from "../auth/api.js";
import { createHistoryClient } from "./history.js";
import {
  missingFeatureLabels,
  normalizeShapFactors,
  v13AssumptionNotes,
} from "./valuationPresentation.js";
import { normalizeQuickAddress, parseQuickAddress } from "./quickAddress.js";
import "./ValuationPanel.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    initialInput: {
      type: Object,
      default: () => ({}),
    },
    demo: Boolean,
    historyEnabled: Boolean,
  });
  const emit = emitForProps(__props, ["saved", "options-loaded"]);
  const history = createHistoryClient();
  const saving = ref(false),
    saved = ref(false),
    saveError = ref("");
  let resultInput, saveKey;
  const client = createValuationClient();
  const options = ref(null);
  const optionsLoading = ref(false);
  const optionsError = ref("");
  const predicting = ref(false);
  const predictionError = ref("");
  const result = ref(null);
  const v13 = ref(null);
  const v13Loading = ref(false);
  const v13Error = ref("");
  const quickAddressInput = ref("");
  const quickAddressFeedback = ref("");
  const form = reactive({});
  let optionsController;
  let predictionController;
  let generation = 0;
  const locations = computed(
    () =>
      options.value?.categories.find((item) => item.category === form.category)
        ?.locations ?? [],
  );
  const legacyLocations = computed(() =>
    locations.value.filter((value) => !value.startsWith("new_unit:")),
  );
  const expandedLocations = computed(() =>
    locations.value.filter((value) => value.startsWith("new_unit:")),
  );
  const displayLocation = (value) =>
    locationLabel(value, options.value?.location_labels);
  function applyQuickAddress() {
    const text = String(quickAddressInput.value ?? "").trim();
    if (!text) {
      quickAddressFeedback.value = "Nhập địa chỉ trước khi điền nhanh.";
      return;
    }
    const parsed = parseQuickAddress(text);
    if (!parsed?.district) {
      quickAddressFeedback.value =
        "Chưa nhận diện được quận/huyện. Vui lòng chọn Địa bàn thủ công.";
      return;
    }
    const target = normalizeQuickAddress(parsed.district);
    const matched = locations.value.find((location) => {
      const label = normalizeQuickAddress(displayLocation(location));
      return label === target || label.includes(target) || normalizeQuickAddress(location) === target;
    });
    if (!matched) {
      quickAddressFeedback.value = `Đã nhận diện ${parsed.district} nhưng địa bàn chưa được hỗ trợ cho loại BĐS này. Vui lòng chọn thủ công.`;
      return;
    }
    form.location_feature = matched;
    if (parsed.ward) form.ward = parsed.ward;
    quickAddressFeedback.value = `Đã điền: ${displayLocation(matched)}${parsed.ward ? ` · Phường ${parsed.ward}` : ""}. Vui lòng kiểm tra lại trước khi ước tính.`;
  }
  const isHouse = computed(() => form.category === "Nhà ở");
  const isApartment = computed(() => form.category === "Căn hộ chung cư");
  const hasRooms = computed(() => form.category !== "Đất nền");
  const missingLabels = computed(
    () =>
      result.value?.missing_features.map(
        (key) => featureLabels[key] ?? "Thông tin bổ sung",
      ) ?? [],
  );
  const usedFeatures = computed(() => {
    if (!result.value) return [];
    return Object.entries(result.value.features_used)
      .filter(([, value]) => value !== null)
      .map(([key, value]) => {
        if (key === "area_sqm") value = `${value} m²`;
        if (key === "location_feature") value = displayLocation(value);
        if (key === "ward_source")
          value = String(form.ward ?? "").trim() || value;
        if (key === "access_type") value = options.value.access_types[value];
        if (key === "house_subtype")
          value = options.value.house_subtypes[value];
        return {
          label: featureLabels[key],
          value,
        };
      });
  });
  const v6Shap = computed(() =>
    normalizeShapFactors(result.value?.shap_explanation, result.value?.features_used),
  );
  const v13Shap = computed(() =>
    normalizeShapFactors(v13.value?.shap_explanation, v13.value?.features_used),
  );
  const v13MissingLabels = computed(() =>
    missingFeatureLabels(v13.value?.missing_features ?? []),
  );
  const v13Assumptions = computed(() =>
    v13AssumptionNotes(v13.value?.features_used ?? {}),
  );
  async function previewV13() {
    if (!resultInput || v13Loading.value) return
    v13Loading.value = true
    v13Error.value = ""
    try {
      v13.value = await client.predictV13(resultInput)
    } catch (error) {
      v13Error.value = error.message || "Không tải được dự đoán V1.3."
    } finally {
      v13Loading.value = false
    }
  }
  function invalidate() {
    generation++;
    predictionController?.abort();
    result.value = null;
    v13.value = null;
    v13Error.value = "";
    v13Loading.value = false;
    predictionError.value = "";
    predicting.value = false;
    saved.value = false;
    saving.value = false;
    saveError.value = "";
    resultInput = null;
    saveKey = null;
  }
  watch(form, invalidate, {
    deep: true,
    flush: "sync",
  });
  watch(
    () => props.initialInput,
    (input) => {
      invalidate();
      Object.assign(
        form,
        {
          category: "Nhà ở",
          area_sqm: "",
          location_feature: "",
          ward: "",
          rooms: "",
          floors: "",
          access_type: "",
          house_subtype: "",
        },
        input,
      );
    },
    {
      immediate: true,
    },
  );
  watch(
    () => form.category,
    () => {
      if (!hasRooms.value) form.rooms = "";
      if (!isHouse.value) {
        form.floors = "";
        form.house_subtype = "";
      }
      if (isApartment.value) form.access_type = "";
      if (options.value && !locations.value.includes(form.location_feature))
        form.location_feature = "";
    },
  );
  async function loadOptions() {
    invalidate();
    optionsController?.abort();
    const controller = new AbortController();
    optionsController = controller;
    optionsLoading.value = true;
    optionsError.value = "";
    try {
      const data = await client.getOptions({
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      options.value = data;
      emit("options-loaded", data.location_labels ?? {});
      if (!locations.value.includes(form.location_feature))
        form.location_feature = "";
    } catch (error) {
      if (!controller.signal.aborted) optionsError.value = error.message;
    } finally {
      if (optionsController === controller) optionsLoading.value = false;
    }
  }
  async function estimate() {
    invalidate();
    if (!options.value) return;
    let payload;
    try {
      payload = buildValuationPayload(form, options.value);
    } catch (error) {
      predictionError.value = error.message;
      return;
    }
    const current = generation;
    const controller = new AbortController();
    predictionController = controller;
    predicting.value = true;
    try {
      const prediction = await client.predict(payload, {
        signal: controller.signal,
      });
      if (current === generation && !controller.signal.aborted) {
        result.value = prediction;
        resultInput = payload;
        saveKey = globalThis.crypto.randomUUID();
      }
    } catch (error) {
      if (current === generation && !controller.signal.aborted)
        predictionError.value = error.message;
    } finally {
      if (current === generation) predicting.value = false;
    }
  }
  async function saveResult() {
    if (!resultInput || !session.token || saving.value || saved.value) return;
    const current = generation,
      token = session.token;
    saving.value = true;
    saveError.value = "";
    try {
      await history.save(resultInput, saveKey);
      if (current === generation && token === session.token) {
        saved.value = true;
        emit("saved");
      }
    } catch (error) {
      if (current === generation && token === session.token)
        saveError.value = errorText(error);
    } finally {
      if (current === generation && token === session.token)
        saving.value = false;
    }
  }
  watch(
    () => session.token,
    () => {
      saved.value = false;
      saveError.value = "";
      saving.value = false;
    },
  );
  onMounted(loadOptions);
  onBeforeUnmount(() => {
    generation++;
    optionsController?.abort();
    predictionController?.abort();
  });
  return {
    computed,
    onBeforeUnmount,
    onMounted,
    reactive,
    ref,
    watch,
    buildValuationPayload,
    createValuationClient,
    featureLabels,
    formatPrice,
    locationLabel,
    warningLabel,
    session,
    errorText,
    createHistoryClient,
    props,
    emit,
    history,
    saving,
    saved,
    saveError,
    resultInput,
    saveKey,
    client,
    options,
    optionsLoading,
    optionsError,
    predicting,
    predictionError,
    result,
    v13,
    v13Loading,
    v13Error,
    previewV13,
    quickAddressInput,
    quickAddressFeedback,
    applyQuickAddress,
    form,
    optionsController,
    predictionController,
    generation,
    locations,
    legacyLocations,
    expandedLocations,
    displayLocation,
    isHouse,
    isApartment,
    hasRooms,
    missingLabels,
    usedFeatures,
    v6Shap,
    v13Shap,
    v13MissingLabels,
    v13Assumptions,
    invalidate,
    loadOptions,
    estimate,
    saveResult,
  };
}
export default React.forwardRef(function ValuationPanel(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section data-ui-view="ValuationPanel"
      {...mergeProps({
        className:
          "valuation-panel bg-[var(--ui-soft)] text-brand-navy rounded-[24px] p-6 md:p-8 shadow-sm",
        "aria-labelledby": "valuation-heading",
        "data-sp-018bbc28": "",
      })}
    >
      <div
        {...mergeProps({
          className: "flex flex-wrap items-start justify-between gap-3",
          "data-sp-018bbc28": "",
        })}
      >
        <div
          {...mergeProps({
            "data-sp-018bbc28": "",
          })}
        >
          <p
            {...mergeProps({
              className: "text-xs text-brand-navy/60 uppercase tracking-widest",
              "data-sp-018bbc28": "",
            })}
          >
            {"Định giá tham chiếu · XGBoost v6"}
          </p>
          <h2
            {...mergeProps({
              id: "valuation-heading",
              className: "text-2xl font-semibold mt-2",
              "data-sp-018bbc28": "",
            })}
          >
            {"Ước tính giá rao"}
          </h2>
        </div>
        {ctx.demo ? (
          <span
            {...mergeProps({
              className:
                "rounded-full bg-brand-card/10 px-3 py-1 text-xs text-brand-navy/80",
              "data-sp-018bbc28": "",
            })}
          >
            {"Tin minh họa"}
          </span>
        ) : null}
      </div>
      <p
        {...mergeProps({
          className: "text-sm text-brand-navy/70 mt-3 leading-6",
          "data-sp-018bbc28": "",
        })}
      >
        {
          "Nhập thông tin hiện có. Các trường chưa rõ có thể để trống; kết quả được tính từ thông tin trong form này."
        }
      </p>
      {ctx.optionsLoading ? (
        <p
          {...mergeProps({
            role: "status",
            className: "mt-5 text-sm text-brand-navy/80",
            "data-sp-018bbc28": "",
          })}
        >
          {"Đang tải địa bàn được hỗ trợ…"}
        </p>
      ) : ctx.optionsError ? (
        <div
          {...mergeProps({
            role: "alert",
            className: "mt-5 rounded-xl bg-brand-card/10 p-4",
            "data-sp-018bbc28": "",
          })}
        >
          <p
            {...mergeProps({
              "data-sp-018bbc28": "",
            })}
          >
            {display(ctx.optionsError)}
          </p>
          <button
            {...mergeProps({
              type: "button",
              className: "mt-3 underline underline-offset-4",
              onClick: ($event) => {
                return ctx.loadOptions?.($event);
              },
              "data-sp-018bbc28": "",
            })}
          >
            {"Thử kết nối lại"}
          </button>
        </div>
      ) : ctx.options ? (
        <form
          {...mergeProps({
            className: "mt-6",
            noValidate: true,
            onSubmit: ($event) => {
              $event.preventDefault();
              return ctx.estimate?.($event);
            },
            "data-sp-018bbc28": "",
          })}
        >
          <div
            className="mb-5 rounded-2xl border border-brand-line/30 bg-[var(--ui-surface)] p-4"
            data-testid="valuation-quick-address"
          >
            <label className="block text-sm font-medium" htmlFor="valuation-quick-address-input">
              {"Điền nhanh từ địa chỉ"}
            </label>
            <p className="mt-1 text-xs text-brand-navy/60">
              {"Nhập số nhà, đường, phường/quận để điền Địa bàn và Phường/xã. Không lấy vị trí thiết bị và không tạo tọa độ."}
            </p>
            <div className="mt-2 flex flex-col gap-2 sm:flex-row">
              <input
                {...mergeProps(
                  {
                    id: "valuation-quick-address-input",
                    type: "text",
                    className: "valuation-input flex-1",
                    placeholder: "Ví dụ: 120 Bạch Đằng, Phường Hải Châu 1, Quận Hải Châu",
                    "data-testid": "valuation-quick-address-input",
                  },
                  modelProps(
                    ctx.quickAddressInput,
                    ($value) => {
                      ctx.quickAddressInput = $value;
                    },
                    { kind: "text", value: "on", number: false, multiple: false },
                  ),
                )}
              />
              <button
                type="button"
                className="rounded-full border border-brand-line/40 px-4 py-2 text-sm"
                data-testid="valuation-quick-address-apply"
                onClick={() => ctx.applyQuickAddress()}
              >
                {"Điền địa bàn"}
              </button>
            </div>
            {ctx.quickAddressFeedback ? (
              <p className="mt-2 text-xs text-brand-navy/75" role="status" data-testid="valuation-quick-address-feedback">
                {display(ctx.quickAddressFeedback)}
              </p>
            ) : null}
          </div>
          <div
            {...mergeProps({
              className: "grid grid-cols-1 sm:grid-cols-2 gap-4",
              "data-sp-018bbc28": "",
            })}
          >
            <label
              {...mergeProps({
                className: "block text-sm",
                "data-sp-018bbc28": "",
              })}
            >
              {"Loại bất động sản "}
              <span
                {...mergeProps({
                  "aria-hidden": "true",
                  "data-sp-018bbc28": "",
                })}
              >
                {"*"}
              </span>
              <select
                {...mergeProps(
                  {
                    required: true,
                    className: "valuation-input mt-2",
                    "data-sp-018bbc28": "",
                  },
                  modelProps(
                    ctx.form.category,
                    ($value) => {
                      ctx.form.category = $value;
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
                {renderList(ctx.options.categories, (item) => (
                  <option
                    key={item.category}
                    {...mergeProps({
                      value: item.category,
                      "data-sp-018bbc28": "",
                    })}
                  >
                    {display(item.category)}
                  </option>
                ))}
              </select>
            </label>
            <label
              {...mergeProps({
                className: "block text-sm",
                "data-sp-018bbc28": "",
              })}
            >
              {"Địa bàn "}
              <span
                {...mergeProps({
                  "aria-hidden": "true",
                  "data-sp-018bbc28": "",
                })}
              >
                {"*"}
              </span>
              <select
                {...mergeProps(
                  {
                    required: true,
                    className: "valuation-input mt-2",
                    "data-sp-018bbc28": "",
                  },
                  modelProps(
                    ctx.form.location_feature,
                    ($value) => {
                      ctx.form.location_feature = $value;
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
                    disabled: true,
                    value: "",
                    "data-sp-018bbc28": "",
                  })}
                >
                  {"Chọn địa bàn"}
                </option>
                {ctx.legacyLocations.length ? (
                  <optgroup
                    {...mergeProps({
                      label: "Quận/huyện cũ",
                      "data-sp-018bbc28": "",
                    })}
                  >
                    {renderList(ctx.legacyLocations, (location) => (
                      <option
                        key={location}
                        {...mergeProps({
                          value: location,
                          "data-sp-018bbc28": "",
                        })}
                      >
                        {display(ctx.displayLocation(location))}
                      </option>
                    ))}
                  </optgroup>
                ) : null}
                {ctx.expandedLocations.length ? (
                  <optgroup
                    {...mergeProps({
                      label: "Địa bàn mở rộng trong dữ liệu",
                      "data-sp-018bbc28": "",
                    })}
                  >
                    {renderList(ctx.expandedLocations, (location) => (
                      <option
                        key={location}
                        {...mergeProps({
                          value: location,
                          "data-sp-018bbc28": "",
                        })}
                      >
                        {display(ctx.displayLocation(location))}
                      </option>
                    ))}
                  </optgroup>
                ) : null}
              </select>
            </label>
            <label
              {...mergeProps({
                className: "block text-sm",
                "data-sp-018bbc28": "",
              })}
            >
              {"Diện tích (m²) "}
              <span
                {...mergeProps({
                  "aria-hidden": "true",
                  "data-sp-018bbc28": "",
                })}
              >
                {"*"}
              </span>
              <input
                {...mergeProps(
                  {
                    type: "number",
                    min: "20",
                    max: "1000",
                    step: "any",
                    inputMode: "decimal",
                    required: true,
                    className: "valuation-input mt-2",
                    placeholder: "Ví dụ: 80",
                    "data-sp-018bbc28": "",
                  },
                  modelProps(
                    ctx.form.area_sqm,
                    ($value) => {
                      ctx.form.area_sqm = $value;
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
              <span
                {...mergeProps({
                  className: "block mt-1 text-xs text-brand-navy/60",
                  "data-sp-018bbc28": "",
                })}
              >
                {"Từ 20 đến 1.000 m²"}
              </span>
            </label>
            <label
              {...mergeProps({
                className: "block text-sm",
                "data-sp-018bbc28": "",
              })}
            >
              {"Phường/xã theo tin "}
              <span
                {...mergeProps({
                  className: "text-brand-navy/70",
                  "data-sp-018bbc28": "",
                })}
              >
                {"· tùy chọn"}
              </span>
              <input
                {...mergeProps(
                  {
                    maxLength: "100",
                    className: "valuation-input mt-2",
                    placeholder: "Để trống nếu chưa rõ",
                    "data-sp-018bbc28": "",
                  },
                  modelProps(
                    ctx.form.ward,
                    ($value) => {
                      ctx.form.ward = $value;
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
                  className: "block mt-1 text-xs text-brand-navy/60",
                  "data-sp-018bbc28": "",
                })}
              >
                {"Bổ sung nếu địa chỉ tin nêu rõ; có thể để trống."}
              </span>
            </label>
            {ctx.hasRooms ? (
              <label
                {...mergeProps({
                  className: "block text-sm",
                  "data-sp-018bbc28": "",
                })}
              >
                {"Phòng ngủ "}
                <span
                  {...mergeProps({
                    className: "text-brand-navy/70",
                    "data-sp-018bbc28": "",
                  })}
                >
                  {"· tùy chọn"}
                </span>
                <input
                  {...mergeProps(
                    {
                      type: "number",
                      min: "1",
                      max: "30",
                      step: "1",
                      inputMode: "numeric",
                      className: "valuation-input mt-2",
                      placeholder: "Chưa rõ",
                      "data-sp-018bbc28": "",
                    },
                    modelProps(
                      ctx.form.rooms,
                      ($value) => {
                        ctx.form.rooms = $value;
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
            ) : null}
            {ctx.isHouse ? (
              <label
                {...mergeProps({
                  className: "block text-sm",
                  "data-sp-018bbc28": "",
                })}
              >
                {"Số tầng nhà "}
                <span
                  {...mergeProps({
                    className: "text-brand-navy/70",
                    "data-sp-018bbc28": "",
                  })}
                >
                  {"· tùy chọn"}
                </span>
                <input
                  {...mergeProps(
                    {
                      type: "number",
                      min: "1",
                      max: "20",
                      step: "any",
                      inputMode: "decimal",
                      className: "valuation-input mt-2",
                      placeholder: "Chưa rõ",
                      "data-sp-018bbc28": "",
                    },
                    modelProps(
                      ctx.form.floors,
                      ($value) => {
                        ctx.form.floors = $value;
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
            ) : null}
            {!ctx.isApartment ? (
              <label
                {...mergeProps({
                  className: "block text-sm",
                  "data-sp-018bbc28": "",
                })}
              >
                {"Lối vào "}
                <span
                  {...mergeProps({
                    className: "text-brand-navy/70",
                    "data-sp-018bbc28": "",
                  })}
                >
                  {"· tùy chọn"}
                </span>
                <select
                  {...mergeProps(
                    {
                      className: "valuation-input mt-2",
                      "data-sp-018bbc28": "",
                    },
                    modelProps(
                      ctx.form.access_type,
                      ($value) => {
                        ctx.form.access_type = $value;
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
                      "data-sp-018bbc28": "",
                    })}
                  >
                    {"Chưa rõ"}
                  </option>
                  {renderList(ctx.options.access_types, (label, value) => (
                    <option
                      key={value}
                      {...mergeProps({
                        value: value,
                        "data-sp-018bbc28": "",
                      })}
                    >
                      {display(label)}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            {ctx.isHouse ? (
              <label
                {...mergeProps({
                  className: "block text-sm",
                  "data-sp-018bbc28": "",
                })}
              >
                {"Loại nhà chi tiết "}
                <span
                  {...mergeProps({
                    className: "text-brand-navy/70",
                    "data-sp-018bbc28": "",
                  })}
                >
                  {"· tùy chọn"}
                </span>
                <select
                  {...mergeProps(
                    {
                      className: "valuation-input mt-2",
                      "data-sp-018bbc28": "",
                    },
                    modelProps(
                      ctx.form.house_subtype,
                      ($value) => {
                        ctx.form.house_subtype = $value;
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
                      "data-sp-018bbc28": "",
                    })}
                  >
                    {"Chưa rõ"}
                  </option>
                  {renderList(ctx.options.house_subtypes, (label, value) => (
                    <option
                      key={value}
                      {...mergeProps({
                        value: value,
                        "data-sp-018bbc28": "",
                      })}
                    >
                      {display(label)}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>
          <button
            {...mergeProps({
              type: "submit",
              disabled: ctx.predicting,
              className:
                "mt-6 rounded-full bg-brand-card px-6 py-3 text-sm font-semibold text-[var(--ui-accent)] hover:bg-[var(--ui-surface)] disabled:opacity-60 disabled:cursor-wait transition",
              "data-sp-018bbc28": "",
            })}
          >
            {display(ctx.predicting ? "Đang ước tính…" : "Ước tính giá rao")}
          </button>
        </form>
      ) : null}
      <div
        {...mergeProps({
          "aria-live": "polite",
          "aria-atomic": "true",
          className: "mt-5",
          "data-sp-018bbc28": "",
        })}
      >
        {ctx.predicting ? (
          <p
            {...mergeProps({
              role: "status",
              className: "text-sm text-brand-navy/80",
              "data-sp-018bbc28": "",
            })}
          >
            {"Mô hình đang tính giá từ thông tin đã nhập…"}
          </p>
        ) : null}
        {ctx.predictionError ? (
          <p
            {...mergeProps({
              role: "alert",
              className: "rounded-xl bg-[var(--ui-surface)] p-4 text-sm text-[var(--ui-ink)]",
              "data-sp-018bbc28": "",
            })}
          >
            {display(ctx.predictionError)}
          </p>
        ) : null}
        {ctx.result ? (
          <div
            {...mergeProps({
              className: "border-t border-brand-line/20 pt-6",
              "data-testid": "valuation-result",
              "data-sp-018bbc28": "",
            })}
          >
            <p
              {...mergeProps({
                className: "text-sm text-brand-navy/70",
                "data-sp-018bbc28": "",
              })}
            >
              {"Giá rao ước tính · "}
              {display(String(ctx.result.model_version).toUpperCase())}
            </p>
            <p
              {...mergeProps({
                className: "text-3xl sm:text-4xl font-semibold mt-2",
                "data-testid": "estimated-price",
                "data-sp-018bbc28": "",
              })}
            >
              {display(ctx.formatPrice(ctx.result.predicted_asking_price_vnd))}
            </p>
            <p
              {...mergeProps({
                className: "text-sm text-brand-navy/70 mt-2",
                "data-sp-018bbc28": "",
              })}
            >
              {display(
                new Intl.NumberFormat("vi-VN").format(
                  ctx.result.predicted_asking_price_vnd,
                ),
              )}
              {" đồng · Tổng giá bất động sản"}
            </p>
            <p className="mt-2 text-xs text-brand-navy/60" data-testid="v6-band">
              {"API V6 hiện chỉ trả giá ước tính, không trả khoảng giá; V1.3 preview có khoảng giá riêng bên dưới."}
            </p>
            <p className="mt-1 text-xs text-brand-navy/55" data-testid="v6-governance">
              {"V6 đang là luồng chính · nguồn đánh giá: development validation 299 mẫu; chưa có holdout độc lập."}
            </p>
            {ctx.historyEnabled && !ctx.demo ? (
              <div
                {...mergeProps({
                  className: "mt-4",
                  "data-sp-018bbc28": "",
                })}
              >
                {ctx.session.token ? (
                  <button
                    {...mergeProps({
                      type: "button",
                      disabled: ctx.saving || ctx.saved,
                      className:
                        "rounded-full border border-brand-line/40 px-4 py-2 text-sm disabled:opacity-60",
                      onClick: ($event) => {
                        return ctx.saveResult?.($event);
                      },
                      "data-sp-018bbc28": "",
                    })}
                  >
                    {display(
                      ctx.saved
                        ? "Đã lưu kết quả"
                        : ctx.saving
                          ? "Đang lưu…"
                          : "Lưu kết quả",
                    )}
                  </button>
                ) : (
                  <RouterLink
                    {...mergeProps({
                      to: "/login?next=/valuation",
                      className: "text-sm underline",
                      "data-sp-018bbc28": "",
                    })}
                  >
                    {"Đăng nhập để lưu kết quả"}
                  </RouterLink>
                )}
                {ctx.saveError ? (
                  <p
                    {...mergeProps({
                      role: "alert",
                      className: "mt-3 text-sm text-[var(--ui-ink)]",
                      "data-sp-018bbc28": "",
                    })}
                  >
                    {display(ctx.saveError)}
                  </p>
                ) : null}
              </div>
            ) : null}
            <div
              data-testid="v6-shap"
              className="mt-6 rounded-2xl border border-brand-line/30 bg-[var(--ui-surface)] p-4"
            >
              <h3 className="text-sm font-medium">{"Giải thích yếu tố ảnh hưởng · V6"}</h3>
              {ctx.v6Shap.length ? (
                <ul className="mt-3 space-y-2" data-testid="v6-shap-factors">
                  {ctx.v6Shap.map((factor) => (
                    <li
                      key={`${factor.feature_name}:${factor.shap_value}`}
                      className="flex items-start justify-between gap-3 text-sm"
                    >
                      <span>{display(factor.displayLabel)}</span>
                      <strong className={factor.direction === "increase" ? "text-emerald-700" : "text-rose-700"}>
                        {display(factor.displayImpact)}
                      </strong>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-sm text-brand-navy/70">
                  {"Mô hình V6 không trả SHAP cho kết quả này."}
                </p>
              )}
              <p className="mt-3 text-xs leading-5 text-brand-navy/60">
                {"SHAP là đóng góp vào dự đoán của model, không phải quan hệ nhân quả. Các đặc trưng đang thiếu hoặc không áp dụng được ghi chú ngay trên nhãn."}
              </p>
            </div>
            <div
              {...mergeProps({
                className:
                  "mt-6 rounded-2xl border border-brand-line/30 bg-[var(--ui-surface)] p-4",
                "data-testid": "v1-3-preview",
                "data-sp-018bbc28": "",
              })}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">
                    {"AI V1.3 · Xem trước thử nghiệm"}
                  </p>
                  <p className="mt-1 text-xs text-brand-navy/70">
                    {
                      "Kết quả tham khảo từ mô hình V1.3, không thay thế định giá V6."
                    }
                  </p>
                  <p className="mt-1 text-[11px] text-brand-navy/55" data-testid="v1-3-governance">
                    {"Nguồn đánh giá: dev-test 4.403 mẫu (không phải blind); MAE ≈3,77 tỷ; MAPE ≈19,8%. Không lấy trung bình với V6."}
                  </p>
                </div>
                <button
                  type="button"
                  disabled={ctx.v13Loading}
                  onClick={() => ctx.previewV13()}
                  className="rounded-full border border-brand-line/40 px-4 py-2 text-sm disabled:opacity-60"
                >
                  {display(
                    ctx.v13
                      ? "Tính lại V1.3"
                      : ctx.v13Loading
                        ? "Đang tính…"
                        : "Xem dự đoán V1.3",
                  )}
                </button>
              </div>
              {ctx.v13Error ? (
                <p role="alert" className="mt-3 text-sm text-[var(--ui-ink)]">
                  {display(ctx.v13Error)}
                </p>
              ) : null}
              {ctx.v13 ? (
                <div className="mt-4 space-y-3" data-testid="v1-3-details">
                <dl
                  className="grid gap-2 text-sm"
                  data-testid="v1-3-result"
                >
                  <div>
                    <dt className="text-brand-navy/60">{"Giá V1.3"}</dt>
                    <dd className="font-medium">
                      {display(
                        ctx.formatPrice(ctx.v13.predicted_asking_price_vnd),
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-brand-navy/60">{"Khoảng giá"}</dt>
                    <dd>{display(ctx.v13.price_band)}</dd>
                  </div>
                  <div>
                    <dt className="text-brand-navy/60">{"Phiên bản"}</dt>
                    <dd>
                      {display(ctx.v13.model_version)}
                      {" · "}
                      {display(ctx.v13.status)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-brand-navy/60">{"Lưu ý"}</dt>
                    <dd className="text-xs text-brand-navy/70">
                      {display(ctx.v13.disclaimer)}
                    </dd>
                  </div>
                </dl>
                {ctx.v13MissingLabels.length ? (
                  <p className="mt-3 text-xs text-brand-navy/75" data-testid="v1-3-missing">
                    {"Thông tin còn thiếu: "}
                    {display(ctx.v13MissingLabels.join(", "))}
                    {"."}
                  </p>
                ) : null}
                {ctx.v13Assumptions.length ? (
                  <div className="mt-3 rounded-xl border border-amber-300/60 bg-amber-50 p-3" data-testid="v1-3-assumptions">
                    <p className="text-xs font-medium text-amber-900">{"Giả định của adapter V1.3"}</p>
                    <ul className="mt-1 list-disc pl-4 text-xs leading-5 text-amber-900/90">
                      {ctx.v13Assumptions.map((note) => (
                        <li key={note}>{display(note)}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                <div className="mt-4 border-t border-brand-line/20 pt-3" data-testid="v1-3-shap">
                  <p className="text-xs font-medium">{"Giải thích yếu tố ảnh hưởng · V1.3"}</p>
                  {ctx.v13Shap.length ? (
                    <ul className="mt-2 space-y-2" data-testid="v1-3-shap-factors">
                      {ctx.v13Shap.map((factor) => (
                        <li
                          key={`${factor.feature_name}:${factor.shap_value}`}
                          className="flex items-start justify-between gap-3 text-sm"
                        >
                          <span>{display(factor.displayLabel)}</span>
                          <strong className={factor.direction === "increase" ? "text-emerald-700" : "text-rose-700"}>
                            {display(factor.displayImpact)}
                          </strong>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-xs text-brand-navy/70">
                      {"Mô hình V1.3 không trả SHAP cho kết quả này."}
                    </p>
                  )}
                  <p className="mt-2 text-xs leading-5 text-brand-navy/60">
                    {"SHAP là đóng góp vào dự đoán, không phải quan hệ nhân quả. Nhãn “đang thiếu/không có trong input” là trạng thái của model, không phải giá trị thực của bất động sản."}
                  </p>
                </div>
                </div>
              ) : null}
            </div>
            <h3
              {...mergeProps({
                className: "font-medium text-sm mt-6",
                "data-sp-018bbc28": "",
              })}
            >
              {"Thông tin đã dùng"}
            </h3>
            <dl
              {...mergeProps({
                className: "grid grid-cols-2 sm:grid-cols-3 gap-3 mt-3",
                "data-sp-018bbc28": "",
              })}
            >
              {renderList(ctx.usedFeatures, (feature) => (
                <div
                  key={feature.label}
                  {...mergeProps({
                    className: "rounded-xl bg-brand-card/10 p-3",
                    "data-sp-018bbc28": "",
                  })}
                >
                  <dt
                    {...mergeProps({
                      className: "text-xs text-brand-navy/60",
                      "data-sp-018bbc28": "",
                    })}
                  >
                    {display(feature.label)}
                  </dt>
                  <dd
                    {...mergeProps({
                      className: "text-sm mt-1",
                      "data-sp-018bbc28": "",
                    })}
                  >
                    {display(feature.value)}
                  </dd>
                </div>
              ))}
            </dl>
            {ctx.missingLabels.length ? (
              <p
                {...mergeProps({
                  className: "text-sm text-brand-navy/80 mt-4",
                  "data-sp-018bbc28": "",
                })}
              >
                {"Thông tin còn thiếu: "}
                {display(ctx.missingLabels.join(", "))}
                {"."}
              </p>
            ) : null}
            {ctx.result.warnings.length ? (
              <ul
                {...mergeProps({
                  className:
                    "list-disc pl-5 mt-3 space-y-2 text-sm text-[var(--ui-ink)]",
                  "data-sp-018bbc28": "",
                })}
              >
                {renderList(ctx.result.warnings, (warning) => (
                  <li
                    key={warning}
                    {...mergeProps({
                      "data-sp-018bbc28": "",
                    })}
                  >
                    {display(ctx.warningLabel(warning))}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </div>
      <p
        {...mergeProps({
          className: "mt-6 text-xs text-brand-navy/60 leading-5",
          "data-sp-018bbc28": "",
        })}
      >
        {
          "Giá rao ước tính để tham khảo. Mô hình chưa sử dụng tọa độ tài sản và khoảng cách tới tiện ích; kết quả chưa được xác minh bằng giá giao dịch."
        }
      </p>
    </section>,
  ]);
});
