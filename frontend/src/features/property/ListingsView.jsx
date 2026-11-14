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
import { ref, computed } from "../../shared/state/store.js";
import ListingFilters from "./ListingFilters.jsx";
import ListingCard from "./ListingCard.jsx";
import { useListingFilters } from "./useListingFilters.js";
import { usePublicListings } from "./usePublicListings.js";
import { useComparison } from "../../shared/hooks/useComparison.js";
import { sortOptions } from "./listingFilters.js";
import { price } from "./property.js";
import { LegacyState, LegacyPager } from "../../shared/lib/legacy.js";
import "./ListingsView.css";
function setup(__props) {
  const search = useListingFilters(),
    compare = useComparison(),
    viewMode = ref("grid");
  const state = usePublicListings(() => search.filters.value);
  const averagePrice = computed(() => {
    const rows = state.items;
    if (
      !rows.length ||
      new Set(rows.map((p) => `${p.transactionType}:${p.priceUnit}`)).size !== 1
    )
      return "—";
    const values = rows.map((p) => String(p.priceExact ?? p.price));
    if (values.some((value) => !/^\d+(?:\.\d{1,2})?$/.test(value))) return "—";
    const total = values.reduce((sum, value) => {
        const [whole, fraction = ""] = value.split(".");
        return sum + BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0"));
      }, 0n),
      cents = total / BigInt(rows.length);
    return price({
      priceExact:
        String(cents / 100n) + "." + String(cents % 100n).padStart(2, "0"),
      priceUnit: rows[0].priceUnit,
    });
  });
  return {
    ref,
    computed,
    ListingFilters,
    ListingCard,
    useListingFilters,
    usePublicListings,
    useComparison,
    sortOptions,
    price,
    LegacyState,
    LegacyPager,
    search,
    compare,
    viewMode,
    state,
    averagePrice,
  };
}
export default React.forwardRef(function ListingsView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="ListingsView"
      {...mergeProps({
        className: "collection-v3",
        "data-sp-16d61e40": "",
      })}
    >
      <div
        {...mergeProps({
          className: "page-width",
          "data-sp-16d61e40": "",
        })}
      >
        <div
          {...mergeProps({
            className: "collection-intro",
            "data-sp-16d61e40": "",
          })}
        >
          <p
            {...mergeProps({
              className: "eyebrow",
              "data-sp-16d61e40": "",
            })}
          >
            {"SMARTPROP / PROPERTY COLLECTION"}
          </p>
          <h1
            {...mergeProps({
              "data-sp-16d61e40": "",
            })}
          >
            {"Không gian sống "}
            <span
              {...mergeProps({
                "data-sp-16d61e40": "",
              })}
            >
              {"dành riêng cho bạn."}
            </span>
          </h1>
          <p
            {...mergeProps({
              "data-sp-16d61e40": "",
            })}
          >
            {
              "Tìm kiếm tin công khai, so sánh lựa chọn và khám phá vị trí trên bản đồ."
            }
          </p>
        </div>
        <ListingFilters
          {...mergeProps({
            modelValue: ctx.search.filters.value,
            onUpdateModelValue: ($event) => {
              return ctx.search.set?.($event);
            },
            "data-sp-16d61e40": "",
          })}
        />
        <div
          {...mergeProps({
            className: "collection-stats",
            "data-sp-16d61e40": "",
          })}
        >

          <p
            {...mergeProps({
              "data-sp-16d61e40": "",
            })}
          >
            {"Giá chào trung bình của trang: "}
            <strong
              {...mergeProps({
                "data-sp-16d61e40": "",
              })}
            >
              {display(ctx.averagePrice)}
            </strong>
            <small
              {...mergeProps({
                "data-sp-16d61e40": "",
              })}
            >
              {
                "Chỉ tính khi cùng hình thức và đơn vị giá; không phải giá thị trường."
              }
            </small>
          </p>
        </div>
        <div
          {...mergeProps({
            className: "collection-toolbar",
            "data-sp-16d61e40": "",
          })}
        >
          <p
            {...mergeProps({
              "data-sp-16d61e40": "",
            })}
          >
            <strong
              {...mergeProps({
                "data-sp-16d61e40": "",
              })}
            >
              {display(ctx.state.totalElements)}
            </strong>
            {" tin phù hợp"}
            {ctx.search.filters.value.district ? (
              <span
                {...mergeProps({
                  "data-sp-16d61e40": "",
                })}
              >
                {" · "}
                {display(ctx.search.filters.value.district)}
              </span>
            ) : null}
          </p>
          <div
            {...mergeProps({
              className: "view-buttons",
              "aria-label": "Cách hiển thị",
              "data-sp-16d61e40": "",
            })}
          >
            <button
              {...mergeProps({
                type: "button",
                "aria-pressed": ctx.viewMode === "grid",
                onClick: ($event) => {
                  ctx.viewMode = "grid";
                },
                "data-sp-16d61e40": "",
              })}
            >
              {"▦ Lưới"}
            </button>
            <button
              {...mergeProps({
                type: "button",
                "aria-pressed": ctx.viewMode === "list",
                onClick: ($event) => {
                  ctx.viewMode = "list";
                },
                "data-sp-16d61e40": "",
              })}
            >
              {"☷ Danh sách"}
            </button>
          </div>
          <label
            {...mergeProps({
              "data-sp-16d61e40": "",
            })}
          >
            {"Sắp xếp"}
            <select
              {...mergeProps({
                value: ctx.search.filters.value.sort,
                onChange: ($event) => {
                  ctx.search.patch({
                    sort: $event.target.value,
                  });
                },
                "data-sp-16d61e40": "",
              })}
            >
              {renderList(ctx.sortOptions, (label, key) => (
                <option
                  key={key}
                  {...mergeProps({
                    value: key,
                    "data-sp-16d61e40": "",
                  })}
                >
                  {display(label)}
                </option>
              ))}
            </select>
          </label>
          <button
            {...mergeProps({
              type: "button",
              className: "clear-filter",
              onClick: ($event) => {
                return ctx.search.reset?.($event);
              },
              "data-sp-16d61e40": "",
            })}
          >
            {"Xóa bộ lọc"}
          </button>
        </div>
        <LegacyState
          {...mergeProps({
            state: ctx.state,
            "data-sp-16d61e40": "",
          })}
        />
        {ctx.state.items.length ? (
          <div
            {...mergeProps({
              className: ["collection-grid", {
                "list-mode": ctx.viewMode === "list",
              }],
              
              "data-sp-16d61e40": "",
            })}
          >
            {renderList(ctx.state.items, (property) => (
              <ListingCard
                key={property.id}
                {...mergeProps({
                  property: property,
                  list: ctx.viewMode === "list",
                  "data-sp-16d61e40": "",
                })}
              >
                <RouterLink
                  {...mergeProps({
                    to: ctx.search.link("/map", {
                      propertyId: property.id,
                    }),
                    className: "on-map",
                    "data-sp-16d61e40": "",
                  })}
                >
                  {"⌖ Bản đồ"}
                </RouterLink>
                <button
                  {...mergeProps({
                    type: "button",
                    className: "compare-button",
                    "aria-pressed": ctx.compare.has(property.id),
                    onClick: ($event) => {
                      ctx.compare.toggle(property);
                    },
                    "data-sp-16d61e40": "",
                  })}
                >
                  {display(
                    ctx.compare.has(property.id) ? "✓ Đã chọn" : "+ So sánh",
                  )}
                </button>
              </ListingCard>
            ))}
          </div>
        ) : null}
        {!ctx.state.busy && !ctx.state.error && !ctx.state.items.length ? (
          <div
            {...mergeProps({
              className: "empty",
              "data-sp-16d61e40": "",
            })}
          >
            <h2
              {...mergeProps({
                "data-sp-16d61e40": "",
              })}
            >
              {"Chưa tìm thấy bất động sản"}
            </h2>
            <p
              {...mergeProps({
                "data-sp-16d61e40": "",
              })}
            >
              {"Hãy thử thay đổi khu vực hoặc điều kiện tìm kiếm."}
            </p>
            <button
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  return ctx.search.reset?.($event);
                },
                "data-sp-16d61e40": "",
              })}
            >
              {"Xóa bộ lọc"}
            </button>
          </div>
        ) : null}
        {ctx.compare.notice.value ? (
          <p
            {...mergeProps({
              role: "status",
              className: "notice",
              "data-sp-16d61e40": "",
            })}
          >
            {display(ctx.compare.notice.value)}
          </p>
        ) : null}
        <LegacyPager
          {...mergeProps({
            state: ctx.state,
            "data-sp-16d61e40": "",
          })}
        />
      </div>
    </div>,
  ]);
});
