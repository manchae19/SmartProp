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
import { ref, watch } from "../../shared/state/store.js";
import { api } from "../auth/api.js";
import { types } from "../property/property.js";
function setup(__props) {
  const props = propsForSetup(__props, {
    district: String,
  });
  const summary = ref(null);
  const busy = ref(false);
  const error = ref("");
  const type = ref("");
  let sequence = 0;
  async function load() {
    const run = ++sequence;
    busy.value = true;
    error.value = "";
    summary.value = null;
    try {
      const query = new URLSearchParams({
        transactionType: "SALE",
        priceUnit: "TOTAL",
      });
      if (props.district) query.set("district", props.district);
      if (type.value) query.set("propertyType", type.value);
      const result = await api("/properties/market-summary?" + query, {
        authenticated: false,
      });
      if (run === sequence) summary.value = result;
    } catch {
      if (run === sequence)
        error.value = "Chưa tải được giá chào hiện tại. Vui lòng thử lại.";
    } finally {
      if (run === sequence) busy.value = false;
    }
  }
  watch(() => [props.district, type.value], load, {
    immediate: true,
  });
  const price = (value) =>
    value == null
      ? "—"
      : Number(value).toLocaleString("vi-VN", {
          maximumFractionDigits: 0,
        });
  return {
    ref,
    watch,
    api,
    types,
    props,
    summary,
    busy,
    error,
    type,
    sequence,
    load,
    price,
  };
}
export default React.forwardRef(function MarketSummary(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section
      {...mergeProps({
        id: "market-current",
        "aria-labelledby": "market-current-heading",
        className: "bg-[var(--ui-surface)] pb-14 text-[var(--ui-accent)] md:pb-20",
      })}
    >
      <div
        {...mergeProps({
          className: "mx-auto max-w-7xl px-5 lg:px-8",
        })}
      >
        <div
          {...mergeProps({
            className:
              "rounded-3xl border border-[var(--ui-border)] bg-brand-card p-5 md:p-7",
            "aria-busy": ctx.busy,
          })}
        >
          <div
            {...mergeProps({
              className: "flex flex-wrap items-start justify-between gap-5",
            })}
          >
            <div
              {...mergeProps({
                className: "max-w-2xl",
              })}
            >
              <p
                {...mergeProps({
                  className:
                    "text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-accent)]",
                })}
              >
                {"Dữ liệu từ SmartProp"}
              </p>
              <h2
                {...mergeProps({
                  id: "market-current-heading",
                  className: "mt-2 text-xl font-semibold md:text-2xl",
                })}
              >
                {"Giá chào hiện tại trên SmartProp"}
              </h2>
              <p
                {...mergeProps({
                  className: "mt-2 text-sm leading-6 text-[var(--ui-accent)]",
                })}
              >
                {" Tin bán được duyệt còn hiệu lực"}
                {ctx.district ? (
                  <span {...mergeProps({})}>
                    {" tại "}
                    {display(ctx.district)}
                  </span>
                ) : null}
                {
                  " · VND / tổng giá. Đây là giá chào, chưa có dữ liệu lịch sử hoặc giá giao dịch. "
                }
              </p>
            </div>
            <label
              {...mergeProps({
                className:
                  "flex w-full flex-col gap-2 text-sm font-medium sm:w-auto",
              })}
            >
              {" Loại bất động sản "}
              <select
                {...mergeProps(
                  {
                    className:
                      "min-h-11 rounded-xl border border-[var(--ui-border)] bg-brand-card px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ui-border)]",
                  },
                  modelProps(
                    ctx.type,
                    ($value) => {
                      ctx.type = $value;
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
                  })}
                >
                  {"Tất cả"}
                </option>
                {renderList(ctx.types, (label, key) => (
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
          </div>
          {ctx.busy ? (
            <p
              {...mergeProps({
                role: "status",
                className: "mt-6 text-sm text-[var(--ui-accent)]",
              })}
            >
              {"Đang tải thống kê…"}
            </p>
          ) : null}
          {ctx.error ? (
            <p
              {...mergeProps({
                role: "alert",
                className:
                  "mt-6 rounded-xl bg-[var(--ui-error-bg)] p-4 text-sm text-[var(--ui-error-text)]",
              })}
            >
              {display(ctx.error)}{" "}
              <button
                {...mergeProps({
                  type: "button",
                  onClick: ($event) => {
                    return ctx.load?.($event);
                  },
                  className:
                    "ml-2 cursor-pointer rounded font-semibold underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2",
                })}
              >
                {"Thử lại"}
              </button>
            </p>
          ) : null}
          {ctx.summary ? (
            <div
              {...mergeProps({
                className: "mt-6 grid gap-4 md:grid-cols-3",
              })}
            >
              <div
                {...mergeProps({
                  className: "min-w-0 rounded-2xl bg-[var(--ui-surface)] p-5",
                })}
              >
                <p
                  {...mergeProps({
                    className: "text-sm text-[var(--ui-accent)]",
                  })}
                >
                  {"Tin phù hợp"}
                </p>
                <strong
                  {...mergeProps({
                    className: "mt-2 block text-3xl font-bold",
                  })}
                >
                  {display(ctx.summary.overall.count)}
                </strong>
              </div>
              <div
                {...mergeProps({
                  className: "min-w-0 rounded-2xl bg-[var(--ui-surface)] p-5",
                })}
              >
                <p
                  {...mergeProps({
                    className: "text-sm text-[var(--ui-accent)]",
                  })}
                >
                  {"Giá chào trung bình"}
                </p>
                <strong
                  {...mergeProps({
                    className: "mt-2 block text-xl font-semibold wrap-anywhere",
                  })}
                >
                  {display(ctx.price(ctx.summary.overall.averageAskingPrice))}{" "}
                  <span
                    {...mergeProps({
                      className: "text-sm font-medium",
                    })}
                  >
                    {"VND"}
                  </span>
                </strong>
              </div>
              <div
                {...mergeProps({
                  className: "min-w-0 rounded-2xl bg-[var(--ui-surface)] p-5",
                })}
              >
                <p
                  {...mergeProps({
                    className: "text-sm text-[var(--ui-accent)]",
                  })}
                >
                  {"Giá chào theo tổng diện tích"}
                </p>
                <strong
                  {...mergeProps({
                    className: "mt-2 block text-xl font-semibold wrap-anywhere",
                  })}
                >
                  {display(
                    ctx.price(ctx.summary.overall.weightedAskingPricePerSqm),
                  )}{" "}
                  <span
                    {...mergeProps({
                      className: "text-sm font-medium",
                    })}
                  >
                    {"VND/m²"}
                  </span>
                </strong>
              </div>
            </div>
          ) : null}
          {ctx.summary?.overall.count === 0 ? (
            <p
              {...mergeProps({
                className: "mt-5 text-sm text-[var(--ui-accent)]",
              })}
            >
              {"Chưa có tin đủ điều kiện để thống kê."}
            </p>
          ) : null}
          {ctx.summary?.byDistrict?.length ? (
            <ul
              {...mergeProps({
                className: "mt-5 grid gap-3 md:grid-cols-3",
              })}
            >
              {renderList(ctx.summary.byDistrict, (group) => (
                <li
                  key={group.key}
                  {...mergeProps({
                    className:
                      "rounded-xl border border-[var(--ui-border)] p-4 text-sm leading-6 text-[var(--ui-accent)]",
                  })}
                >
                  <strong
                    {...mergeProps({
                      className: "block font-semibold text-[var(--ui-accent)]",
                    })}
                  >
                    {display(group.key || "Chưa xác định khu vực")}
                  </strong>{" "}
                  {display(group.amounts.count)}
                  {" tin · "}
                  {display(ctx.price(group.amounts.weightedAskingPricePerSqm))}
                  {" VND/m² "}
                </li>
              ))}
            </ul>
          ) : null}
          {ctx.summary?.districtsTruncated ? (
            <p
              {...mergeProps({
                className: "mt-4 text-sm text-[var(--ui-accent)]",
              })}
            >
              {"Danh sách thống kê khu vực đã được giới hạn bởi server."}
            </p>
          ) : null}
        </div>
      </div>
    </section>,
  ]);
});
