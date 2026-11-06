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
import { ref, watch, nextTick, useId } from "../../shared/state/store.js";
import { districts } from "../map/districts.js";
import {
  propertyTypes,
  normalizeFilters,
  filterError,
  sortOptions,
} from "./listingFilters.js";
function setup(__props) {
  const props = propsForSetup(__props, {
    modelValue: {
      type: Object,
      required: true,
    },
  });
  const emit = emitForProps(__props, ["update:modelValue", "search"]);
  const draft = ref({}),
    expanded = ref(false),
    error = ref(""),
    errorNode = ref(null),
    panelId = useId();
  watch(
    () => props.modelValue,
    (value) => {
      draft.value = {
        ...value,
      };
      error.value = "";
    },
    {
      immediate: true,
      deep: true,
    },
  );
  async function apply() {
    error.value = filterError(draft.value);
    if (error.value) {
      expanded.value = true;
      await nextTick();
      errorNode.value?.focus();
      return;
    }
    emit("update:modelValue", normalizeFilters(draft.value));
    emit("search");
  }
  function transaction(value) {
    draft.value.transactionType = value;
    apply();
  }
  function reset() {
    draft.value = {};
    apply();
  }
  exposeForSetup({
    expand: () => {
      expanded.value = true;
    },
  });
  return {
    ref,
    watch,
    nextTick,
    useId,
    districts,
    propertyTypes,
    normalizeFilters,
    filterError,
    sortOptions,
    props,
    emit,
    draft,
    expanded,
    error,
    errorNode,
    panelId,
    apply,
    transaction,
    reset,
  };
}
export default React.forwardRef(function ListingFilters(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <form
      {...mergeProps({
        className:
          "listing-filters rounded-panel border border-brand-line bg-brand-card p-4 shadow-sm sm:p-6",
        "aria-label": "Tìm kiếm bất động sản",
        onSubmit: ($event) => {
          $event.preventDefault();
          return ctx.apply?.($event);
        },
      })}
    >
      <div
        {...mergeProps({
          className: "mb-5 flex flex-wrap items-center justify-between gap-3",
        })}
      >
        <div
          {...mergeProps({
            className:
              "filter-tabs inline-flex flex-wrap gap-1 rounded-full bg-brand-surface p-1",
            role: "group",
            "aria-label": "Hình thức giao dịch",
          })}
        >
          {renderList(
            {
              "": "Tất cả",
              SALE: "Bán",
              RENT: "Cho thuê",
            },
            (label, key) => (
              <button
                key={key}
                {...mergeProps({
                  type: "button",
                  "aria-pressed": (ctx.draft.transactionType || "") === key,
                  className: ["min-h-11 rounded-full px-4 py-2 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-gold sm:px-6", (ctx.draft.transactionType || "") === key
                      ? "bg-brand-raised text-brand-navy shadow-sm"
                      : "text-brand-muted hover:bg-brand-card"],
                  
                  onClick: ($event) => {
                    ctx.transaction(key);
                  },
                })}
              >
                {display(label)}
              </button>
            ),
          )}
          {ctx.$children ?? null}
        </div>
        <button
          {...mergeProps({
            type: "button",
            className: "advanced-toggle sp-button sp-button-secondary",
            "aria-expanded": ctx.expanded,
            "aria-controls": ctx.panelId,
            onClick: ($event) => {
              ctx.expanded = !ctx.expanded;
            },
          })}
        >
          {display(ctx.expanded ? "Thu gọn bộ lọc" : "Bộ lọc nâng cao")}
          <svg
            {...mergeProps({
              className: ["size-4 transition-transform motion-reduce:transition-none", {
                "rotate-180": ctx.expanded,
              }],
              
              viewBox: "0 0 24 24",
              fill: "none",
              stroke: "currentColor",
              strokeWidth: "1.7",
              "aria-hidden": "true",
            })}
          >
            <path
              {...mergeProps({
                d: "m6 9 6 6 6-6",
              })}
            />
          </svg>
        </button>
      </div>
      <div
        {...mergeProps({
          className:
            "quick-fields grid items-end gap-3 min-[360px]:grid-cols-2 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)_auto]",
        })}
      >
        <label
          {...mergeProps({
            className: "keyword sp-field min-[360px]:col-span-2 lg:col-span-1",
          })}
        >
          {"Từ khóa"}
          <input
            {...mergeProps(
              {
                name: "keyword",
                className: "sp-input",
                maxLength: "200",
                placeholder: "Tên tin, địa chỉ, khu vực…",
                type: "search",
              },
              modelProps(
                ctx.draft.keyword,
                ($value) => {
                  ctx.draft.keyword = $value;
                },
                {
                  kind: "search",
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
            className: "sp-field",
          })}
        >
          {"Khu vực"}
          <select
            {...mergeProps(
              {
                name: "district",
                className: "sp-input",
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
                value: undefined,
              })}
            >
              {"Tất cả khu vực"}
            </option>
            {renderList(
              ctx.districts.filter((d) => d !== "Tất cả"),
              (district) => (
                <option key={district} {...mergeProps({})}>
                  {display(district)}
                </option>
              ),
            )}
          </select>
        </label>
        <label
          {...mergeProps({
            className: "sp-field",
          })}
        >
          {"Loại bất động sản"}
          <select
            {...mergeProps(
              {
                name: "propertyType",
                className: "sp-input",
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
            <option
              {...mergeProps({
                value: undefined,
              })}
            >
              {"Tất cả loại hình"}
            </option>
            {renderList(ctx.propertyTypes, (label, key) => (
              <option
                key={key}
                {...mergeProps({
                  value: key,
                })}
              >
                {display(label)}
              </option>
            ))}
          </select>
        </label>
        <button
          {...mergeProps({
            className:
              "search-button sp-button sp-button-primary min-[360px]:col-span-2 lg:col-span-1",
            type: "submit",
          })}
        >
          <svg
            {...mergeProps({
              className: "size-4",
              viewBox: "0 0 24 24",
              fill: "none",
              stroke: "currentColor",
              strokeWidth: "1.7",
              "aria-hidden": "true",
            })}
          >
            <circle
              {...mergeProps({
                cx: "10.5",
                cy: "10.5",
                r: "6.5",
              })}
            />
            <path
              {...mergeProps({
                d: "m16 16 5 5",
              })}
            />
          </svg>
          {"Tìm kiếm"}
        </button>
      </div>
      <div
        {...mergeProps(
          {
            id: ctx.panelId,
            className:
              "advanced-fields mt-6 grid gap-4 border-t border-brand-line pt-5 sm:grid-cols-2 lg:grid-cols-3",
          },
          {
            style: {
              display: ctx.expanded ? undefined : "none",
            },
          },
        )}
      >
        <p
          {...mergeProps({
            className:
              "filter-help text-xs leading-6 text-brand-muted sm:col-span-2 lg:col-span-3",
          })}
        >
          {
            "Giá nhập bằng VND, theo đơn vị giá niêm yết của từng tin: tổng giá / tháng / năm / ngày. Bộ lọc áp dụng trên toàn bộ danh sách."
          }
        </p>
        <label
          {...mergeProps({
            className: "sp-field",
          })}
        >
          {"Giá tối thiểu (VND)"}
          <input
            {...mergeProps(
              {
                name: "minPrice",
                className: "sp-input",
                type: "text",
                inputMode: "decimal",
                placeholder: "Ví dụ: 2000000000",
              },
              modelProps(
                ctx.draft.minPrice,
                ($value) => {
                  ctx.draft.minPrice = $value;
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
            className: "sp-field",
          })}
        >
          {"Giá tối đa (VND)"}
          <input
            {...mergeProps(
              {
                name: "maxPrice",
                className: "sp-input",
                type: "text",
                inputMode: "decimal",
                placeholder: "Không giới hạn",
              },
              modelProps(
                ctx.draft.maxPrice,
                ($value) => {
                  ctx.draft.maxPrice = $value;
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
            className: "sp-field",
          })}
        >
          {"Diện tích tối thiểu (m²)"}
          <input
            {...mergeProps(
              {
                name: "minArea",
                className: "sp-input",
                type: "number",
                min: "0",
                step: "0.01",
              },
              modelProps(
                ctx.draft.minArea,
                ($value) => {
                  ctx.draft.minArea = $value;
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
            className: "sp-field",
          })}
        >
          {"Diện tích tối đa (m²)"}
          <input
            {...mergeProps(
              {
                name: "maxArea",
                className: "sp-input",
                type: "number",
                min: "0",
                step: "0.01",
              },
              modelProps(
                ctx.draft.maxArea,
                ($value) => {
                  ctx.draft.maxArea = $value;
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
            className: "sp-field",
          })}
        >
          {"Phòng ngủ tối thiểu"}
          <select
            {...mergeProps(
              {
                name: "bedrooms",
                className: "sp-input",
              },
              modelProps(
                ctx.draft.bedrooms,
                ($value) => {
                  ctx.draft.bedrooms = $value;
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
                value: undefined,
              })}
            >
              {"Không giới hạn"}
            </option>
            {renderList(5, (n) => (
              <option
                key={n}
                {...mergeProps({
                  value: String(n),
                })}
              >
                {display(n)}
                {"+"}
              </option>
            ))}
          </select>
        </label>
        <label
          {...mergeProps({
            className: "sp-field",
          })}
        >
          {"Sắp xếp"}
          <select
            {...mergeProps(
              {
                name: "sort",
                className: "sp-input",
              },
              modelProps(
                ctx.draft.sort,
                ($value) => {
                  ctx.draft.sort = $value;
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
            {renderList(ctx.sortOptions, (label, key) => (
              <option
                key={key}
                {...mergeProps({
                  value: key,
                })}
              >
                {display(label)}
              </option>
            ))}
          </select>
        </label>
        {ctx.draft.city ? (
          <label
            {...mergeProps({
              className: "sp-field",
            })}
          >
            {"Thành phố"}
            <input
              {...mergeProps(
                {
                  className: "sp-input",
                  name: "city",
                  maxLength: "100",
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
            />
          </label>
        ) : null}
        {ctx.draft.ward ? (
          <label
            {...mergeProps({
              className: "sp-field",
            })}
          >
            {"Phường / xã"}
            <input
              {...mergeProps(
                {
                  className: "sp-input",
                  name: "ward",
                  maxLength: "100",
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
        ) : null}
        <div
          {...mergeProps({
            className:
              "advanced-actions flex flex-wrap justify-end gap-3 sm:col-span-2 lg:col-span-3",
          })}
        >
          <button
            {...mergeProps({
              type: "submit",
              className: "sp-button sp-button-primary",
            })}
          >
            {"Áp dụng bộ lọc"}
          </button>
        </div>
      </div>
      <div
        {...mergeProps({
          className: "mt-4 flex flex-wrap items-center justify-between gap-3",
        })}
      >
        <p
          {...mergeProps({
            className: "text-xs leading-6 text-brand-muted",
          })}
        >
          {"Có thể kết hợp hình thức, khu vực và loại hình."}
        </p>
        <button
          {...mergeProps({
            type: "button",
            className:
              "reset-filters min-h-11 rounded-control px-2 text-xs font-semibold text-brand-accent underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-brand-gold",
            onClick: ($event) => {
              return ctx.reset?.($event);
            },
          })}
        >
          {"Xóa bộ lọc"}
        </button>
      </div>
      {ctx.error ? (
        <p
          {...mergeProps({
            ref: bindRef(ctx, "errorNode"),
            role: "alert",
            tabIndex: "-1",
            className:
              "filter-error mt-4 rounded-control bg-[var(--ui-error-bg)] p-4 text-sm leading-6 text-[var(--ui-error-text)] focus-visible:outline-2 focus-visible:outline-red-700",
          })}
        >
          {display(ctx.error)}
        </p>
      ) : null}
    </form>,
  ]);
});
