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
import { computed } from "../../shared/state/store.js";
import PrivateImage from "../../shared/components/PrivateImage.jsx";
import {
  price,
  compactPrice,
  displayDecimal,
  types,
  states,
} from "./property.js";
import "./ListingCard.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    property: {
      type: Object,
      required: true,
    },
    own: Boolean,
    list: Boolean,
  });
  const detail = computed(() => ({
    path: "/listing/" + props.property.id,
    query: props.own
      ? {
          own: "1",
        }
      : {},
  }));
  const cover = computed(
    () =>
      (
        props.property.images?.find((image) => image.cover) ||
        props.property.images?.[0]
      )?.url,
  );
  const imageCount = computed(() => props.property.images?.length || 1);
  const fullAddress = computed(() => {
    const parts = [
      props.property.address,
      props.property.ward,
      props.property.district,
    ].filter(Boolean);
    if (parts.length) return parts.join(", ");
    return (
      [props.property.district, props.property.city]
        .filter(Boolean)
        .join(", ") || "Đà Nẵng"
    );
  });
  const area = computed(() =>
    displayDecimal(props.property.areaSqmExact ?? props.property.areaSqm),
  );
  const unitPriceText = computed(() => {
    const pr = Number(props.property.priceExact ?? props.property.price ?? 0);
    const ar = Number(
      props.property.areaSqmExact ?? props.property.areaSqm ?? 0,
    );
    if (
      pr > 0 &&
      ar > 0 &&
      props.property.transactionType === "SALE" &&
      props.property.priceUnit === "TOTAL"
    ) {
      const perSqm = Math.round(pr / ar);
      if (perSqm >= 1000000) {
        return `~ ${(perSqm / 1000000).toLocaleString("vi-VN", {
          maximumFractionDigits: 1,
        })} tr/m²`;
      }
      return `~ ${perSqm.toLocaleString("vi-VN")} đ/m²`;
    }
    return null;
  });
  return {
    computed,
    PrivateImage,
    price,
    compactPrice,
    displayDecimal,
    types,
    states,
    props,
    detail,
    cover,
    imageCount,
    fullAddress,
    area,
    unitPriceText,
  };
}
export default React.forwardRef(function ListingCard(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <article
      {...mergeProps({
        className: ["property-card", {
          "property-card-list": ctx.list,
        }],
        
        "data-sp-d0ec4fcb": "",
      })}
    >
      <RouterLink
        {...mergeProps({
          to: ctx.detail,
          className: "property-main",
          "aria-label": "Xem chi tiết " + ctx.property.title,
          "data-sp-d0ec4fcb": "",
        })}
      >
        <div
          {...mergeProps({
            className: "property-image",
            "data-sp-d0ec4fcb": "",
          })}
        >
          <PrivateImage
            {...mergeProps({
              src: ctx.cover,
              alt: ctx.property.title,
              "data-sp-d0ec4fcb": "",
            })}
          />
          <div
            {...mergeProps({
              className: "image-top-tags",
              "data-sp-d0ec4fcb": "",
            })}
          >
            <span
              {...mergeProps({
                className: ["badge-transaction", ctx.property.transactionType === "RENT" ? "rent" : "sale"],
                
                "data-sp-d0ec4fcb": "",
              })}
            >
              {display(
                ctx.own
                  ? ctx.states[ctx.property.status]
                  : ctx.property.transactionType === "SALE"
                    ? "Bán"
                    : "Cho thuê",
              )}
            </span>
            <span
              {...mergeProps({
                className: "badge-type",
                "data-sp-d0ec4fcb": "",
              })}
            >
              {display(
                ctx.types[ctx.property.propertyType] ||
                  ctx.property.propertyType,
              )}
            </span>
          </div>
          <div
            {...mergeProps({
              className: "image-bottom-tags",
              "data-sp-d0ec4fcb": "",
            })}
          >
            {ctx.imageCount > 1 ? (
              <span
                {...mergeProps({
                  className: "badge-photo-count",
                  "data-sp-d0ec4fcb": "",
                })}
              >
                <svg
                  {...mergeProps({
                    width: "12",
                    height: "12",
                    viewBox: "0 0 24 24",
                    fill: "none",
                    stroke: "currentColor",
                    strokeWidth: "2.2",
                    "data-sp-d0ec4fcb": "",
                  })}
                >
                  <path
                    {...mergeProps({
                      d: "M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z",
                      "data-sp-d0ec4fcb": "",
                    })}
                  />
                  <circle
                    {...mergeProps({
                      cx: "12",
                      cy: "13",
                      r: "4",
                      "data-sp-d0ec4fcb": "",
                    })}
                  />
                </svg>{" "}
                {display(ctx.imageCount)}
                {" ảnh "}
              </span>
            ) : null}
          </div>
        </div>
        <div
          {...mergeProps({
            className: "property-body",
            "data-sp-d0ec4fcb": "",
          })}
        >
          <h3
            {...mergeProps({
              className: "property-title",
              title: ctx.property.title,
              "data-sp-d0ec4fcb": "",
            })}
          >
            {display(ctx.property.title)}
          </h3>
          <div
            {...mergeProps({
              className: "property-metrics",
              "data-sp-d0ec4fcb": "",
            })}
          >
            <div
              {...mergeProps({
                className: "price-container",
                "data-sp-d0ec4fcb": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "main-price",
                  title: ctx.price(ctx.property),
                  "data-sp-d0ec4fcb": "",
                })}
              >
                {display(ctx.compactPrice(ctx.property))}
              </span>
              {ctx.unitPriceText ? (
                <span
                  {...mergeProps({
                    className: "unit-price",
                    "data-sp-d0ec4fcb": "",
                  })}
                >
                  {display(ctx.unitPriceText)}
                </span>
              ) : null}
            </div>
            <div
              {...mergeProps({
                className: "area-container",
                "aria-label": "Diện tích " + ctx.area + " m²",
                "data-sp-d0ec4fcb": "",
              })}
            >
              <svg
                {...mergeProps({
                  width: "13",
                  height: "13",
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  strokeWidth: "2",
                  strokeLinecap: "round",
                  strokeLinejoin: "round",
                  "data-sp-d0ec4fcb": "",
                })}
              >
                <path
                  {...mergeProps({
                    d: "M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M3 3l6 6m12-6-6 6M3 21l6-6m12 6-6-6",
                    "data-sp-d0ec4fcb": "",
                  })}
                />
              </svg>
              <span
                {...mergeProps({
                  "data-sp-d0ec4fcb": "",
                })}
              >
                {display(ctx.area)}
                {" m²"}
              </span>
            </div>
          </div>
          <p
            {...mergeProps({
              className: "property-location",
              title: ctx.fullAddress,
              "data-sp-d0ec4fcb": "",
            })}
          >
            <svg
              {...mergeProps({
                width: "14",
                height: "14",
                viewBox: "0 0 24 24",
                fill: "none",
                stroke: "currentColor",
                strokeWidth: "2",
                strokeLinecap: "round",
                strokeLinejoin: "round",
                "data-sp-d0ec4fcb": "",
              })}
            >
              <path
                {...mergeProps({
                  d: "M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z",
                  "data-sp-d0ec4fcb": "",
                })}
              />
              <circle
                {...mergeProps({
                  cx: "12",
                  cy: "10",
                  r: "2.5",
                  "data-sp-d0ec4fcb": "",
                })}
              />
            </svg>
            <span
              {...mergeProps({
                "data-sp-d0ec4fcb": "",
              })}
            >
              {display(ctx.fullAddress)}
            </span>
          </p>
          <div
            {...mergeProps({
              className: "property-specs",
              "data-sp-d0ec4fcb": "",
            })}
          >
            {ctx.property.direction ? (
              <span
                {...mergeProps({
                  className: "spec-pill",
                  "data-sp-d0ec4fcb": "",
                })}
              >
                {" 🧭 Hướng "}
                {display(ctx.property.direction)}
              </span>
            ) : null}
            {ctx.property.bedrooms > 0 ? (
              <span
                {...mergeProps({
                  className: "spec-pill",
                  "data-sp-d0ec4fcb": "",
                })}
              >
                {" 🛏️ "}
                <strong
                  {...mergeProps({
                    "data-sp-d0ec4fcb": "",
                  })}
                >
                  {display(ctx.property.bedrooms)}
                </strong>
                {" PN "}
              </span>
            ) : null}
            {ctx.property.bathrooms > 0 ? (
              <span
                {...mergeProps({
                  className: "spec-pill",
                  "data-sp-d0ec4fcb": "",
                })}
              >
                {" 🚿 "}
                <strong
                  {...mergeProps({
                    "data-sp-d0ec4fcb": "",
                  })}
                >
                  {display(ctx.property.bathrooms)}
                </strong>
                {" PT "}
              </span>
            ) : null}
            {ctx.property.propertyType === "LAND" ? (
              <span
                {...mergeProps({
                  className: "spec-pill land-tag",
                  "data-sp-d0ec4fcb": "",
                })}
              >
                {" 📑 Sổ đỏ sẵn sàng "}
              </span>
            ) : null}
          </div>
        </div>
      </RouterLink>
      <div
        {...mergeProps({
          className: "property-actions",
          "data-sp-d0ec4fcb": "",
        })}
      >
        <RouterLink
          {...mergeProps({
            to: ctx.detail,
            className: "detail-link",
            "data-sp-d0ec4fcb": "",
          })}
        >
          {"Xem chi tiết ↗"}
        </RouterLink>
        {ctx.$children ?? null}
      </div>
    </article>,
  ]);
});
