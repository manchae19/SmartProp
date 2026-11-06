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
  reactive,
  ref,
  watch,
  onMounted,
  onBeforeUnmount,
} from "../../shared/state/store.js";
import { api } from "../auth/api.js";
import {
  categoryFor,
  valuationInput,
  createPreviewState,
  exactVnd,
} from "./valuation.js";
function setup(__props) {
  const props = propsForSetup(__props, {
    draft: {
      type: Object,
      required: true,
    },
  });
  const options = ref(null),
    optionsError = ref(""),
    loading = ref(false);
  const state = reactive({
    busy: false,
    result: null,
    error: "",
  });
  const preview = createPreviewState(
    (body) =>
      api("/properties/valuation-preview", {
        method: "POST",
        body,
      }),
    state,
  );
  let disposed = false;
  const locations = computed(
    () =>
      options.value?.categories?.find(
        (c) => c.category === categoryFor(props.draft.propertyType),
      )?.locations || [],
  );
  const location = computed(() =>
    locations.value.includes(props.draft.valuationLocation)
      ? props.draft.valuationLocation
      : "",
  );
  const input = computed(() => valuationInput(props.draft, location.value));
  function pickDistrict() {
    const district =
      props.draft.district === "Hoà Vang" ? "Hòa Vang" : props.draft.district;
    if (!locations.value.includes(props.draft.valuationLocation))
      props.draft.valuationLocation = locations.value.includes(district)
        ? district
        : "";
  }
  watch([locations, () => props.draft.district], pickDistrict, {
    immediate: true,
  });
  watch(
    () =>
      JSON.stringify([
        input.value,
        props.draft.propertyType,
        props.draft.district,
        props.draft.price,
        props.draft.address,
        props.draft.latitude,
        props.draft.longitude,
      ]),
    () => preview.invalidate(),
    {
      flush: "sync",
    },
  );
  async function loadOptions() {
    loading.value = true;
    optionsError.value = "";
    try {
      const value = await api("/properties/valuation-options");
      if (!disposed) options.value = value;
    } catch (e) {
      if (!disposed) optionsError.value = e.message;
    } finally {
      if (!disposed) loading.value = false;
    }
  }
  onMounted(loadOptions);
  onBeforeUnmount(() => {
    disposed = true;
    preview.dispose();
  });
  const featureLabels = {
    areaSqm: "Diện tích (m²)",
    locationFeature: "Khu vực",
    rooms: "Phòng ngủ",
    floors: "Số tầng",
    access_type: "Đường tiếp cận",
    house_subtype: "Kiểu nhà",
  };
  const missingLabel = (value) =>
    ({
      ...featureLabels,
      ward_source: "Phường/xã",
      access_type: "Đường tiếp cận",
      house_subtype: "Kiểu nhà",
    })[value] || value;
  const featureValue = (value) =>
    ({
      alley: "Trong kiệt/hẻm",
      frontage: "Mặt tiền",
      villa: "Biệt thự",
      house_c4: "Nhà cấp 4",
    })[value] || value;
  return {
    computed,
    reactive,
    ref,
    watch,
    onMounted,
    onBeforeUnmount,
    api,
    categoryFor,
    valuationInput,
    createPreviewState,
    exactVnd,
    props,
    options,
    optionsError,
    loading,
    state,
    preview,
    disposed,
    locations,
    location,
    input,
    pickDistrict,
    loadOptions,
    featureLabels,
    missingLabel,
    featureValue,
  };
}
export default React.forwardRef(function PostValuationPanel(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section data-ui-view="PostValuationPanel"
      {...mergeProps({
        "data-testid": "valuation-panel",
        className: "bg-[var(--ui-soft)] text-brand-navy rounded-[22px] p-6",
      })}
    >
      <h2
        {...mergeProps({
          className: "text-xs tracking-[0.18em] text-brand-navy/60",
        })}
      >
        {"GIÁ THAM CHIẾU XGBOOST · v6"}
      </h2>
      <div
        {...mergeProps({
          "data-testid": "valuation-price",
          "aria-live": "polite",
          className: "text-xl font-light mt-3 break-words",
        })}
      >
        {display(
          ctx.state.result?.available
            ? ctx.exactVnd(ctx.state.result.predictedAskingPriceVnd)
            : "—",
        )}
      </div>
      <p
        {...mergeProps({
          className: "text-xs text-brand-navy/70 mt-2",
        })}
      >
        {"Giá rao ước tính; giá chào của bạn được giữ nguyên."}
      </p>
      <label
        {...mergeProps({
          className: "block mt-5 text-xs",
        })}
      >
        {"Khu vực tham khảo "}
        <select
          {...mergeProps({
            "data-testid": "valuation-location",
            value: ctx.location,
            onChange: ($event) => {
              ctx.draft.valuationLocation = $event.target.value;
            },
            className: "mt-2 w-full bg-brand-card text-[var(--ui-accent)] rounded-lg p-2",
            disabled: ctx.loading || !ctx.locations.length,
          })}
        >
          <option
            {...mergeProps({
              value: "",
            })}
          >
            {"Chọn đúng khu vực"}
          </option>
          {renderList(ctx.locations, (item) => (
            <option
              key={item}
              {...mergeProps({
                value: item,
              })}
            >
              {display(item)}
            </option>
          ))}
        </select>
      </label>
      <p
        {...mergeProps({
          className: "text-xs text-brand-navy/60 mt-2",
        })}
      >
        {
          "Địa bàn theo dữ liệu model. Hãy chọn khu vực tương ứng với địa chỉ thực tế."
        }
      </p>
      {ctx.optionsError ? (
        <p
          {...mergeProps({
            role: "status",
            className: "mt-3 text-xs text-[var(--ui-warning-text)]",
          })}
        >
          {display(ctx.optionsError)}{" "}
          <button
            {...mergeProps({
              type: "button",
              className: "underline",
              onClick: ($event) => {
                return ctx.loadOptions?.($event);
              },
            })}
          >
            {"Thử lại"}
          </button>
        </p>
      ) : ctx.input.reason ? (
        <p
          {...mergeProps({
            className: "mt-3 text-xs text-brand-navy/80",
          })}
        >
          {display(ctx.input.reason)}
        </p>
      ) : null}
      <button
        {...mergeProps({
          type: "button",
          "data-testid": "valuation-preview",
          disabled:
            ctx.loading || ctx.state.busy || !ctx.options || !!ctx.input.reason,
          onClick: ($event) => {
            ctx.preview.preview(ctx.input.body);
          },
          className:
            "mt-4 w-full rounded-full border border-brand-line/40 py-2 text-xs disabled:opacity-50",
        })}
      >
        {display(ctx.state.busy ? "Đang tính…" : "Xem giá tham khảo")}
      </button>
      {ctx.state.error ? (
        <p
          {...mergeProps({
            role: "status",
            className: "mt-3 text-xs text-[var(--ui-warning-text)]",
          })}
        >
          {display(ctx.state.error)}
        </p>
      ) : null}
      {ctx.state.result && !ctx.state.result.available ? (
        <p
          {...mergeProps({
            role: "status",
            className: "mt-3 text-xs",
          })}
        >
          {display(ctx.state.result.reason)}
        </p>
      ) : null}
      {ctx.state.result?.available ? (
        <div
          {...mergeProps({
            className: "mt-5 border-t border-brand-line/10 pt-4 text-xs space-y-2",
          })}
        >
          <h3
            {...mergeProps({
              className: "font-semibold",
            })}
          >
            {"Thông tin model đã dùng"}
          </h3>
          {renderList(ctx.state.result.featuresUsed, (value, key) => (
            <p key={key} {...mergeProps({})}>
              {display(ctx.featureLabels[key] || key)}
              {": "}
              {display(ctx.featureValue(value))}
            </p>
          ))}
          {ctx.state.result.missingFeatures?.length ? (
            <p {...mergeProps({})}>
              {"Chưa có: "}
              {display(
                ctx.state.result.missingFeatures
                  .map(ctx.missingLabel)
                  .join(", "),
              )}
            </p>
          ) : null}
          {renderList(ctx.state.result.warnings, (warning, index) => (
            <p
              key={index}
              {...mergeProps({
                className: "text-[var(--ui-warning-text)]",
              })}
            >
              {display(warning)}
            </p>
          ))}
        </div>
      ) : null}
      <p
        {...mergeProps({
          className: "mt-5 text-xs text-brand-navy/60 leading-relaxed",
        })}
      >
        {
          "Thông tin tham khảo, không phải kết quả thẩm định chính thức. Không có kết quả vẫn có thể lưu hoặc gửi tin."
        }
      </p>
    </section>,
  ]);
});
