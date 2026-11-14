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
  ref,
  computed,
  onBeforeUnmount,
  watch,
} from "../../shared/state/store.js";
import { useRoute } from "../../shared/routing/router.jsx";
import { useComparison } from "../../shared/hooks/useComparison.js";
import { api } from "../auth/api.js";
import { isPublicProperty } from "./usePublicListings.js";
import { price, compactPrice, types, states } from "./property.js";
import PrivateImage from "../../shared/components/PrivateImage.jsx";
import BrowseTileMap from "../map/BrowseTileMap.jsx";
import "./ComparisonTray.css";
function setup(__props) {
  const route = useRoute();
  const compare = useComparison();
  const dialog = ref(null);
  const busy = ref(false);
  const error = ref("");
  const showOnlyDiff = ref(false);
  const showMap = ref(true);
  const visible = computed(() =>
    ["/home", "/listings", "/map"].includes(route.path),
  );
  const mixed = computed(
    () =>
      new Set(
        compare.items.value.map((p) => `${p.transactionType}:${p.priceUnit}`),
      ).size > 1,
  );
  let sequence = 0;
  async function open() {
    const run = ++sequence;
    busy.value = true;
    error.value = "";
    const originals = [...compare.items.value];
    const result = await Promise.allSettled(
      originals.map((p) =>
        api("/properties/" + encodeURIComponent(p.id), {
          authenticated: false,
        }),
      ),
    );
    if (run !== sequence) return;
    busy.value = false;
    if (
      compare.items.value.map((p) => p.id).join("|") !==
      originals.map((p) => p.id).join("|")
    ) {
      error.value =
        "Lựa chọn đã thay đổi trong lúc kiểm tra. Hãy bấm so sánh lại.";
      return;
    }
    if (
      result.some((r) => r.status === "rejected" && r.reason?.status !== 404)
    ) {
      error.value =
        "Chưa xác minh được trạng thái mới nhất của các tin. Hãy thử lại.";
      return;
    }
    const current = result.flatMap((r) =>
      r.status === "fulfilled" && isPublicProperty(r.value) ? [r.value] : [],
    );
    compare.replace(current);
    if (current.length !== originals.length) {
      error.value =
        "Đã bỏ tin không còn công khai. Hãy chọn ít nhất 2 tin hợp lệ.";
      return;
    }
    if (current.length < 2) return;
    dialog.value.showModal();
  }
  function close() {
    dialog.value?.close();
  }
  watch(
    () => route.fullPath,
    () => {
      sequence++;
      busy.value = false;
      close();
    },
  );
  onBeforeUnmount(() => {
    sequence++;
    close();
  });

  // Helper methods for calculations & visuals
  function cover(p) {
    return (p.images?.find((i) => i.cover) || p.images?.[0])?.url;
  }
  function getNumericPrice(p) {
    const raw = Number(p.priceExact ?? p.price ?? 0);
    return Number.isFinite(raw) ? raw : 0;
  }
  function getNumericArea(p) {
    const raw = Number(p.areaSqmExact ?? p.areaSqm ?? 0);
    return Number.isFinite(raw) ? raw : 0;
  }
  function getUnitPricePerSqm(p) {
    const pr = getNumericPrice(p);
    const ar = getNumericArea(p);
    if (
      pr > 0 &&
      ar > 0 &&
      p.transactionType === "SALE" &&
      p.priceUnit === "TOTAL"
    ) {
      return Math.round(pr / ar);
    }
    return null;
  }
  function formatUnitPrice(p) {
    const u = getUnitPricePerSqm(p);
    if (!u) return "—";
    const million = (u / 1000000).toLocaleString("vi-VN", {
      maximumFractionDigits: 1,
    });
    return `${million} tr/m²`;
  }
  function calculateDistanceKm(lat1, lon1, lat2, lon2) {
    if (lat1 == null || lon1 == null || lat2 == null || lon2 == null)
      return null;
    const y1 = Number(lat1),
      x1 = Number(lon1),
      y2 = Number(lat2),
      x2 = Number(lon2);
    if (
      !Number.isFinite(y1) ||
      !Number.isFinite(x1) ||
      !Number.isFinite(y2) ||
      !Number.isFinite(x2)
    )
      return null;
    const R = 6371; // km
    const dLat = ((y2 - y1) * Math.PI) / 180;
    const dLon = ((x2 - x1) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((y1 * Math.PI) / 180) *
        Math.cos((y2 * Math.PI) / 180) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const d = R * c;
    return d < 1 ? `${Math.round(d * 1000)} m` : `${d.toFixed(1)} km`;
  }

  // Visual comparisons
  const metricsComparison = computed(() => {
    const items = compare.items.value;
    if (items.length < 2) return null;

    // 1. Price
    const prices = items.map(getNumericPrice);
    const maxPrice = Math.max(...prices) || 1;
    const priceBars = items.map((p) => ({
      id: p.id,
      pct: Math.max(10, Math.round((getNumericPrice(p) / maxPrice) * 100)),
      label: compactPrice(p),
      isLowest:
        getNumericPrice(p) === Math.min(...prices) &&
        prices.some((v) => v !== prices[0]),
    }));

    // 2. Unit Price
    const units = items.map(getUnitPricePerSqm).filter(Boolean);
    let unitBars = [];
    if (units.length === items.length) {
      const maxUnit = Math.max(...units) || 1;
      const minUnit = Math.min(...units);
      unitBars = items.map((p) => {
        const u = getUnitPricePerSqm(p);
        return {
          id: p.id,
          pct: Math.max(10, Math.round((u / maxUnit) * 100)),
          label: formatUnitPrice(p),
          isLowest: u === minUnit && minUnit !== maxUnit,
          savingPct:
            u === minUnit && minUnit !== maxUnit
              ? Math.round(((maxUnit - minUnit) / maxUnit) * 100)
              : 0,
        };
      });
    }

    // 3. Area
    const areas = items.map(getNumericArea);
    const maxArea = Math.max(...areas) || 1;
    const areaBars = items.map((p) => ({
      id: p.id,
      pct: Math.max(10, Math.round((getNumericArea(p) / maxArea) * 100)),
      label: `${p.areaSqmExact ?? p.areaSqm} m²`,
      isLargest:
        getNumericArea(p) === maxArea && areas.some((v) => v !== areas[0]),
    }));

    // 4. Distance (if 2 properties)
    let distance = null;
    if (items.length === 2 && items[0].latitude && items[1].latitude) {
      distance = calculateDistanceKm(
        items[0].latitude,
        items[0].longitude,
        items[1].latitude,
        items[1].longitude,
      );
    }
    return {
      priceBars,
      unitBars,
      areaBars,
      distance,
    };
  });

  // Smart highlights per property
  function getPropertyHighlights(p) {
    const items = compare.items.value;
    if (items.length < 2) return [];
    const badges = [];
    const prices = items.map(getNumericPrice);
    const units = items.map(getUnitPricePerSqm).filter(Boolean);
    const areas = items.map(getNumericArea);
    if (
      prices.length > 1 &&
      getNumericPrice(p) === Math.min(...prices) &&
      new Set(prices).size > 1
    ) {
      badges.push({
        text: "Giá tổng tốt nhất",
        type: "best-price",
      });
    }
    const u = getUnitPricePerSqm(p);
    if (
      units.length === items.length &&
      u === Math.min(...units) &&
      new Set(units).size > 1
    ) {
      badges.push({
        text: "Đơn giá/m² tối ưu",
        type: "best-unit",
      });
    }
    if (
      areas.length > 1 &&
      getNumericArea(p) === Math.max(...areas) &&
      new Set(areas).size > 1
    ) {
      badges.push({
        text: "Diện tích lớn nhất",
        type: "best-area",
      });
    }
    if (
      p.bedrooms &&
      items.some((other) => (other.bedrooms || 0) < p.bedrooms)
    ) {
      badges.push({
        text: `${p.bedrooms} phòng ngủ`,
        type: "highlight",
      });
    }
    return badges;
  }

  // Amenities Union
  const allAmenities = computed(() => {
    const set = new Set();
    for (const p of compare.items.value) {
      if (Array.isArray(p.declaredAmenities)) {
        for (const a of p.declaredAmenities) {
          if (a && typeof a === "string" && a.trim()) set.add(a.trim());
        }
      }
    }
    return Array.from(set);
  });

  // Grouped Criteria Matrix
  const criteriaGroups = computed(() => {
    const groups = [
      {
        name: "Tài chính & Hiệu quả",
        icon: "💰",
        rows: [
          {
            label: "Tổng giá chào",
            isDiff: (items) =>
              new Set(items.map((p) => getNumericPrice(p))).size > 1,
            render: (p) => ({
              highlight: true,
              text: compactPrice(p),
              sub: price(p),
            }),
          },
          {
            label: "Đơn giá / m²",
            isDiff: (items) =>
              new Set(items.map((p) => getUnitPricePerSqm(p))).size > 1,
            render: (p) => ({
              text: formatUnitPrice(p),
              highlight: false,
            }),
          },
        ],
      },
      {
        name: "Vị trí & Quy hoạch",
        icon: "📍",
        rows: [
          {
            label: "Quận / Huyện",
            isDiff: (items) =>
              new Set(items.map((p) => p.district || "")).size > 1,
            render: (p) => ({
              text: p.district || "—",
            }),
          },
          {
            label: "Tuyến đường & Phường",
            isDiff: (items) =>
              new Set(items.map((p) => `${p.address}-${p.ward}`)).size > 1,
            render: (p) => ({
              text: [p.address, p.ward].filter(Boolean).join(", ") || "—",
            }),
          },
          {
            label: "Hướng phong thủy",
            isDiff: (items) =>
              new Set(items.map((p) => p.direction || "")).size > 1,
            render: (p) => ({
              text: p.direction ? `🧭 Hướng ${p.direction}` : "—",
            }),
          },
        ],
      },
      {
        name: "Quy mô & Thiết kế",
        icon: "📐",
        rows: [
          {
            label: "Loại hình BĐS",
            isDiff: (items) =>
              new Set(items.map((p) => p.propertyType)).size > 1,
            render: (p) => ({
              text: types[p.propertyType] || p.propertyType,
            }),
          },
          {
            label: "Diện tích đất / sàn",
            isDiff: (items) =>
              new Set(items.map((p) => getNumericArea(p))).size > 1,
            render: (p) => ({
              text: `${p.areaSqmExact ?? p.areaSqm} m²`,
            }),
          },
          {
            label: "Số phòng ngủ",
            isDiff: (items) =>
              new Set(items.map((p) => p.bedrooms ?? "")).size > 1,
            render: (p) => ({
              text: p.bedrooms != null ? `${p.bedrooms} phòng ngủ` : "—",
            }),
          },
          {
            label: "Số phòng tắm / WC",
            isDiff: (items) =>
              new Set(items.map((p) => p.bathrooms ?? "")).size > 1,
            render: (p) => ({
              text: p.bathrooms != null ? `${p.bathrooms} phòng tắm` : "—",
            }),
          },
          {
            label: "Số tầng kết cấu",
            isDiff: (items) =>
              new Set(items.map((p) => p.floor ?? "")).size > 1,
            render: (p) => ({
              text: p.floor != null ? `${p.floor} tầng` : "—",
            }),
          },
        ],
      },
    ];
    if (!showOnlyDiff.value) return groups;
    return groups
      .map((g) => ({
        ...g,
        rows: g.rows.filter((r) => r.isDiff(compare.items.value)),
      }))
      .filter((g) => g.rows.length > 0);
  });

  // Map points for BrowseTileMap
  const mapPoints = computed(() => {
    return compare.items.value
      .filter(
        (p) =>
          Number.isFinite(Number(p.latitude)) &&
          Number.isFinite(Number(p.longitude)),
      )
      .map((p) => ({
        id: p.id,
        latitude: Number(p.latitude),
        longitude: Number(p.longitude),
        title: p.title,
        transactionType: p.transactionType,
        priceExact: p.priceExact,
        price: p.price,
        priceUnit: p.priceUnit,
      }));
  });
  return {
    ref,
    computed,
    onBeforeUnmount,
    watch,
    useRoute,
    useComparison,
    api,
    isPublicProperty,
    price,
    compactPrice,
    types,
    states,
    PrivateImage,
    BrowseTileMap,
    route,
    compare,
    dialog,
    busy,
    error,
    showOnlyDiff,
    showMap,
    visible,
    mixed,
    sequence,
    open,
    close,
    cover,
    getNumericPrice,
    getNumericArea,
    getUnitPricePerSqm,
    formatUnitPrice,
    calculateDistanceKm,
    metricsComparison,
    getPropertyHighlights,
    allAmenities,
    criteriaGroups,
    mapPoints,
  };
}
export default React.forwardRef(function ComparisonTray(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    ctx.visible && ctx.compare.items.value.length ? (
      <aside
        {...mergeProps({
          className: "comparison-tray",
          "aria-label": "Các tin đã chọn để so sánh",
          "data-sp-f380b3c4": "",
        })}
      >
        <div
          {...mergeProps({
            className: "tray-items",
            "data-sp-f380b3c4": "",
          })}
        >
          <div
            {...mergeProps({
              className: "tray-count-badge",
              "data-sp-f380b3c4": "",
            })}
          >
            <svg
              {...mergeProps({
                width: "16",
                height: "16",
                viewBox: "0 0 24 24",
                fill: "none",
                stroke: "currentColor",
                strokeWidth: "2",
                strokeLinecap: "round",
                strokeLinejoin: "round",
                "data-sp-f380b3c4": "",
              })}
            >
              <path
                {...mergeProps({
                  d: "M16 3h5v5M4 20L21 3m0 13v5h-5M4 4l5 5",
                  "data-sp-f380b3c4": "",
                })}
              />
            </svg>
            <strong
              {...mergeProps({
                "data-sp-f380b3c4": "",
              })}
            >
              {"So sánh "}
              {display(ctx.compare.items.value.length)}
              {"/3"}
            </strong>
          </div>
          {renderList(ctx.compare.items.value, (item) => (
            <div
              key={item.id}
              {...mergeProps({
                className: "tray-chip",
                "data-sp-f380b3c4": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "chip-thumb",
                  "data-sp-f380b3c4": "",
                })}
              >
                <PrivateImage
                  {...mergeProps({
                    src: ctx.cover(item),
                    alt: item.title,
                    "data-sp-f380b3c4": "",
                  })}
                />
              </div>
              <span
                {...mergeProps({
                  className: "chip-title",
                  title: item.title,
                  "data-sp-f380b3c4": "",
                })}
              >
                {display(item.title)}
              </span>
              <button
                {...mergeProps({
                  type: "button",
                  disabled: ctx.busy,
                  "aria-label": "Bỏ so sánh " + item.title,
                  className: "chip-remove",
                  onClick: ($event) => {
                    ctx.compare.toggle(item);
                  },
                  "data-sp-f380b3c4": "",
                })}
              >
                {"×"}
              </button>
            </div>
          ))}
        </div>
        <div
          {...mergeProps({
            className: "tray-actions",
            "data-sp-f380b3c4": "",
          })}
        >
          <button
            {...mergeProps({
              type: "button",
              className: "btn-clear",
              disabled: ctx.busy,
              onClick: ($event) => {
                return ctx.compare.clear?.($event);
              },
              "data-sp-f380b3c4": "",
            })}
          >
            {"Xóa hết"}
          </button>
          <button
            {...mergeProps({
              type: "button",
              className: "btn-compare primary",
              disabled: ctx.busy || ctx.compare.items.value.length < 2,
              onClick: ($event) => {
                return ctx.open?.($event);
              },
              "data-sp-f380b3c4": "",
            })}
          >
            {display(
              ctx.busy
                ? "Đang kiểm tra…"
                : `So sánh ngay (${ctx.compare.items.value.length}) ↗`,
            )}
          </button>
        </div>
        {ctx.compare.notice.value || ctx.error ? (
          <p
            {...mergeProps({
              className: "tray-status",
              role: "status",
              "data-sp-f380b3c4": "",
            })}
          >
            {display(ctx.error || ctx.compare.notice.value)}
          </p>
        ) : null}
      </aside>
    ) : null,
    <dialog data-ui-view="ComparisonTray"
      {...mergeProps({
        ref: bindRef(ctx, "dialog"),
        className: "comparison-dialog",
        "aria-labelledby": "compare-heading",
        onClick: ($event) => {
          return ((event) => {
            if (event.target === ctx.dialog) ctx.close();
          })?.($event);
        },
        "data-sp-f380b3c4": "",
      })}
    >
      <div
        {...mergeProps({
          className: "dialog-inner",
          "data-sp-f380b3c4": "",
        })}
      >
        <header
          {...mergeProps({
            className: "dialog-header",
            "data-sp-f380b3c4": "",
          })}
        >
          <div
            {...mergeProps({
              "data-sp-f380b3c4": "",
            })}
          >
            <div
              {...mergeProps({
                className: "dialog-badge",
                "data-sp-f380b3c4": "",
              })}
            >
              {"SMARTPROP / BỘ SO SÁNH TRỰC QUAN"}
            </div>
            <h2
              {...mergeProps({
                id: "compare-heading",
                "data-sp-f380b3c4": "",
              })}
            >
              {"So sánh bất động sản"}
            </h2>
            <p
              {...mergeProps({
                className: "dialog-subtitle",
                "data-sp-f380b3c4": "",
              })}
            >
              {
                "Phân tích đa chiều về giá cả, đơn giá/m², quy mô và vị trí địa lý tương quan"
              }
            </p>
          </div>
          <div
            {...mergeProps({
              className: "dialog-controls",
              "data-sp-f380b3c4": "",
            })}
          >
            <label
              {...mergeProps({
                className: ["toggle-btn", {
                  active: ctx.showOnlyDiff,
                }],
                
                "data-sp-f380b3c4": "",
              })}
            >
              <input
                {...mergeProps(
                  {
                    type: "checkbox",
                    "data-sp-f380b3c4": "",
                  },
                  modelProps(
                    ctx.showOnlyDiff,
                    ($value) => {
                      ctx.showOnlyDiff = $value;
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
                  "data-sp-f380b3c4": "",
                })}
              >
                {"⚡ Chỉ xem điểm khác biệt"}
              </span>
            </label>
            {ctx.mapPoints.length ? (
              <button
                {...mergeProps({
                  type: "button",
                  className: ["btn-map-toggle", {
                    active: ctx.showMap,
                  }],
                  
                  onClick: ($event) => {
                    ctx.showMap = !ctx.showMap;
                  },
                  "data-sp-f380b3c4": "",
                })}
              >
                {" 🗺️ "}
                {display(ctx.showMap ? "Ẩn bản đồ" : "Xem bản đồ vị trí")}
              </button>
            ) : null}
            <button
              {...mergeProps({
                type: "button",
                className: "btn-close",
                "aria-label": "Đóng so sánh",
                onClick: ($event) => {
                  return ctx.close?.($event);
                },
                "data-sp-f380b3c4": "",
              })}
            >
              {"✕"}
            </button>
          </div>
        </header>
        {ctx.mixed ? (
          <div
            {...mergeProps({
              className: "mixed-note",
              "data-sp-f380b3c4": "",
            })}
          >
            {" ⚠️ "}
            <strong
              {...mergeProps({
                "data-sp-f380b3c4": "",
              })}
            >
              {"Lưu ý:"}
            </strong>
            {
              " Các tin có hình thức giao dịch hoặc đơn vị tính khác nhau (Bán vs Cho thuê). Hệ thống không so sánh trực tiếp tổng giá bán với giá thuê theo kỳ. "
            }
          </div>
        ) : null}
        {ctx.metricsComparison ? (
          <section
            {...mergeProps({
              className: "metrics-dashboard",
              "data-sp-f380b3c4": "",
            })}
          >
            <h3
              {...mergeProps({
                className: "section-title",
                "data-sp-f380b3c4": "",
              })}
            >
              {"📊 Trực quan hóa tương quan chỉ số"}
            </h3>
            <div
              {...mergeProps({
                className: "metrics-grid",
                "data-sp-f380b3c4": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "metric-card",
                  "data-sp-f380b3c4": "",
                })}
              >
                <div
                  {...mergeProps({
                    className: "metric-head",
                    "data-sp-f380b3c4": "",
                  })}
                >
                  <span
                    {...mergeProps({
                      className: "metric-name",
                      "data-sp-f380b3c4": "",
                    })}
                  >
                    {"Tổng giá chào"}
                  </span>
                  <span
                    {...mergeProps({
                      className: "metric-sub",
                      "data-sp-f380b3c4": "",
                    })}
                  >
                    {"Thấp nhất là lợi thế"}
                  </span>
                </div>
                <div
                  {...mergeProps({
                    className: "metric-bars",
                    "data-sp-f380b3c4": "",
                  })}
                >
                  {renderList(ctx.metricsComparison.priceBars, (b, idx) => (
                    <div
                      key={b.id}
                      {...mergeProps({
                        className: "bar-row",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      <span
                        {...mergeProps({
                          className: ["bar-index", "prop-idx-" + idx],
                          
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        {"Căn "}
                        {display(idx + 1)}
                      </span>
                      <div
                        {...mergeProps({
                          className: "bar-track",
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        <div
                          {...mergeProps({
                            className: ["bar-fill", [
                              "fill-" + idx,
                              {
                                best: b.isLowest,
                              },
                            ]],
                            
                            style: {
                              width: b.pct + "%",
                            },
                            "data-sp-f380b3c4": "",
                          })}
                        />
                      </div>
                      <span
                        {...mergeProps({
                          className: "bar-val",
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        {display(b.label)}
                      </span>
                      {b.isLowest ? (
                        <span
                          {...mergeProps({
                            className: "bar-badge green",
                            "data-sp-f380b3c4": "",
                          })}
                        >
                          {"✓ Giá tốt"}
                        </span>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
              {ctx.metricsComparison.unitBars.length ? (
                <div
                  {...mergeProps({
                    className: "metric-card",
                    "data-sp-f380b3c4": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className: "metric-head",
                      "data-sp-f380b3c4": "",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className: "metric-name",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      {"Đơn giá trên mỗi m²"}
                    </span>
                    <span
                      {...mergeProps({
                        className: "metric-sub",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      {"Đo lường độ đắt / rẻ thực tế"}
                    </span>
                  </div>
                  <div
                    {...mergeProps({
                      className: "metric-bars",
                      "data-sp-f380b3c4": "",
                    })}
                  >
                    {renderList(ctx.metricsComparison.unitBars, (b, idx) => (
                      <div
                        key={b.id}
                        {...mergeProps({
                          className: "bar-row",
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            className: ["bar-index", "prop-idx-" + idx],
                            
                            "data-sp-f380b3c4": "",
                          })}
                        >
                          {"Căn "}
                          {display(idx + 1)}
                        </span>
                        <div
                          {...mergeProps({
                            className: "bar-track",
                            "data-sp-f380b3c4": "",
                          })}
                        >
                          <div
                            {...mergeProps({
                              className: ["bar-fill", [
                                "fill-" + idx,
                                {
                                  best: b.isLowest,
                                },
                              ]],
                              
                              style: {
                                width: b.pct + "%",
                              },
                              "data-sp-f380b3c4": "",
                            })}
                          />
                        </div>
                        <span
                          {...mergeProps({
                            className: "bar-val",
                            "data-sp-f380b3c4": "",
                          })}
                        >
                          {display(b.label)}
                        </span>
                        {b.isLowest && b.savingPct > 0 ? (
                          <span
                            {...mergeProps({
                              className: "bar-badge green",
                              "data-sp-f380b3c4": "",
                            })}
                          >
                            {"Tiết kiệm "}
                            {display(b.savingPct)}
                            {"%"}
                          </span>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
              <div
                {...mergeProps({
                  className: "metric-card",
                  "data-sp-f380b3c4": "",
                })}
              >
                <div
                  {...mergeProps({
                    className: "metric-head",
                    "data-sp-f380b3c4": "",
                  })}
                >
                  <span
                    {...mergeProps({
                      className: "metric-name",
                      "data-sp-f380b3c4": "",
                    })}
                  >
                    {"Diện tích sử dụng"}
                  </span>
                  <span
                    {...mergeProps({
                      className: "metric-sub",
                      "data-sp-f380b3c4": "",
                    })}
                  >
                    {"Không gian sống"}
                  </span>
                </div>
                <div
                  {...mergeProps({
                    className: "metric-bars",
                    "data-sp-f380b3c4": "",
                  })}
                >
                  {renderList(ctx.metricsComparison.areaBars, (b, idx) => (
                    <div
                      key={b.id}
                      {...mergeProps({
                        className: "bar-row",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      <span
                        {...mergeProps({
                          className: ["bar-index", "prop-idx-" + idx],
                          
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        {"Căn "}
                        {display(idx + 1)}
                      </span>
                      <div
                        {...mergeProps({
                          className: "bar-track",
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        <div
                          {...mergeProps({
                            className: ["bar-fill", [
                              "fill-" + idx,
                              {
                                best: b.isLargest,
                              },
                            ]],
                            
                            style: {
                              width: b.pct + "%",
                            },
                            "data-sp-f380b3c4": "",
                          })}
                        />
                      </div>
                      <span
                        {...mergeProps({
                          className: "bar-val",
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        {display(b.label)}
                      </span>
                      {b.isLargest ? (
                        <span
                          {...mergeProps({
                            className: "bar-badge gold",
                            "data-sp-f380b3c4": "",
                          })}
                        >
                          {"Rộng nhất"}
                        </span>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
              {ctx.metricsComparison.distance ? (
                <div
                  {...mergeProps({
                    className: "metric-card distance-card",
                    "data-sp-f380b3c4": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className: "metric-head",
                      "data-sp-f380b3c4": "",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className: "metric-name",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      {"Khoảng cách địa lý"}
                    </span>
                    <span
                      {...mergeProps({
                        className: "metric-sub",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      {"Giữa 2 bất động sản"}
                    </span>
                  </div>
                  <div
                    {...mergeProps({
                      className: "distance-content",
                      "data-sp-f380b3c4": "",
                    })}
                  >
                    <div
                      {...mergeProps({
                        className: "distance-icon",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      {"📍 ⟷ 📍"}
                    </div>
                    <div
                      {...mergeProps({
                        className: "distance-number",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      {display(ctx.metricsComparison.distance)}
                    </div>
                    <p
                      {...mergeProps({
                        className: "distance-desc",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      {
                        "Khoảng cách đường chim bay giữa 2 vị trí trên bản đồ Đà Nẵng"
                      }
                    </p>
                  </div>
                </div>
              ) : null}
            </div>
          </section>
        ) : null}
        {ctx.showMap && ctx.mapPoints.length ? (
          <section
            {...mergeProps({
              className: "map-section",
              "data-sp-f380b3c4": "",
            })}
          >
            <div
              {...mergeProps({
                className: "map-header",
                "data-sp-f380b3c4": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "map-title",
                  "data-sp-f380b3c4": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "pin-symbol",
                    "data-sp-f380b3c4": "",
                  })}
                >
                  {"📍"}
                </span>
                <strong
                  {...mergeProps({
                    "data-sp-f380b3c4": "",
                  })}
                >
                  {"Bản đồ so sánh vị trí địa lý tương quan"}
                </strong>
                <span
                  {...mergeProps({
                    className: "map-hint",
                    "data-sp-f380b3c4": "",
                  })}
                >
                  {"Đã ghim "}
                  {display(ctx.mapPoints.length)}
                  {" bất động sản trên cùng bản đồ"}
                </span>
              </div>
            </div>
            <div
              {...mergeProps({
                className: "map-viewport-wrapper",
                "data-sp-f380b3c4": "",
              })}
            >
              <BrowseTileMap
                {...mergeProps({
                  points: ctx.mapPoints,
                  "data-sp-f380b3c4": "",
                })}
              />
            </div>
          </section>
        ) : null}
        <section
          {...mergeProps({
            className: "table-container",
            "data-sp-f380b3c4": "",
          })}
        >
          <h3
            {...mergeProps({
              className: "section-title",
              "data-sp-f380b3c4": "",
            })}
          >
            {"📋 Bảng ma trận so sánh chi tiết"}
          </h3>
          <div
            {...mergeProps({
              className: "table-scroll",
              tabIndex: "0",
              role: "region",
              "aria-label": "Bảng so sánh chi tiết, cuộn ngang để xem thêm",
              "data-sp-f380b3c4": "",
            })}
          >
            <table
              {...mergeProps({
                className: "comparison-table",
                "data-sp-f380b3c4": "",
              })}
            >
              <thead
                {...mergeProps({
                  "data-sp-f380b3c4": "",
                })}
              >
                <tr
                  {...mergeProps({
                    "data-sp-f380b3c4": "",
                  })}
                >
                  <th
                    {...mergeProps({
                      scope: "col",
                      className: "corner-header",
                      "data-sp-f380b3c4": "",
                    })}
                  >
                    <div
                      {...mergeProps({
                        className: "criteria-header-box",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      <span
                        {...mergeProps({
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        {"Tiêu chí so sánh"}
                      </span>
                      {ctx.showOnlyDiff ? (
                        <small
                          {...mergeProps({
                            "data-sp-f380b3c4": "",
                          })}
                        >
                          {"Đang lọc điểm khác"}
                        </small>
                      ) : null}
                    </div>
                  </th>
                  {renderList(ctx.compare.items.value, (p, idx) => (
                    <th
                      key={p.id}
                      {...mergeProps({
                        scope: "col",
                        className: "property-col-header",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          className: "prop-card-header",
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        <div
                          {...mergeProps({
                            className: "card-badge-row",
                            "data-sp-f380b3c4": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              className: ["card-num-pill", "bg-idx-" + idx],
                              
                              "data-sp-f380b3c4": "",
                            })}
                          >
                            {"Căn "}
                            {display(idx + 1)}
                          </span>
                          <span
                            {...mergeProps({
                              className: "card-type-pill",
                              "data-sp-f380b3c4": "",
                            })}
                          >
                            {display(
                              ctx.types[p.propertyType] || p.propertyType,
                            )}
                          </span>
                          <button
                            {...mergeProps({
                              type: "button",
                              className: "btn-remove-col",
                              title: "Bỏ so sánh " + p.title,
                              onClick: ($event) => {
                                ctx.compare.toggle(p);
                              },
                              "data-sp-f380b3c4": "",
                            })}
                          >
                            {"×"}
                          </button>
                        </div>
                        <div
                          {...mergeProps({
                            className: "card-img-box",
                            "data-sp-f380b3c4": "",
                          })}
                        >
                          <PrivateImage
                            {...mergeProps({
                              src: ctx.cover(p),
                              alt: p.title,
                              "data-sp-f380b3c4": "",
                            })}
                          />
                          <span
                            {...mergeProps({
                              className: "card-tag",
                              "data-sp-f380b3c4": "",
                            })}
                          >
                            {display(
                              p.transactionType === "RENT" ? "Cho thuê" : "Bán",
                            )}
                          </span>
                        </div>
                        <div
                          {...mergeProps({
                            className: "card-info-box",
                            "data-sp-f380b3c4": "",
                          })}
                        >
                          <RouterLink
                            {...mergeProps({
                              to: "/listing/" + p.id,
                              className: "card-title-link",
                              title: p.title,
                              onClick: ($event) => {
                                return ctx.close?.($event);
                              },
                              "data-sp-f380b3c4": "",
                            })}
                          >
                            {display(p.title)}
                            {" ↗ "}
                          </RouterLink>
                          <div
                            {...mergeProps({
                              className: "card-price-row",
                              "data-sp-f380b3c4": "",
                            })}
                          >
                            <strong
                              {...mergeProps({
                                className: "card-price-compact",
                                "data-sp-f380b3c4": "",
                              })}
                            >
                              {display(ctx.compactPrice(p))}
                            </strong>
                            <span
                              {...mergeProps({
                                className: "card-price-full",
                                "data-sp-f380b3c4": "",
                              })}
                            >
                              {display(ctx.price(p))}
                            </span>
                          </div>
                        </div>
                        <div
                          {...mergeProps({
                            className: "card-advantages",
                            "data-sp-f380b3c4": "",
                          })}
                        >
                          {renderList(ctx.getPropertyHighlights(p), (badge) => (
                            <span
                              key={badge.text}
                              {...mergeProps({
                                className: ["advantage-pill", badge.type],
                                
                                "data-sp-f380b3c4": "",
                              })}
                            >
                              {" ★ "}
                              {display(badge.text)}
                            </span>
                          ))}
                        </div>
                        <RouterLink
                          {...mergeProps({
                            to: "/listing/" + p.id,
                            className: "btn-view-detail",
                            onClick: ($event) => {
                              return ctx.close?.($event);
                            },
                            "data-sp-f380b3c4": "",
                          })}
                        >
                          {" Xem chi tiết tin ↗ "}
                        </RouterLink>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody
                {...mergeProps({
                  "data-sp-f380b3c4": "",
                })}
              >
                {renderList(ctx.criteriaGroups, (group) => (
                  <React.Fragment key={group.name} {...mergeProps({})}>
                    <tr
                      {...mergeProps({
                        className: "group-header-row",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      <th
                        {...mergeProps({
                          colSpan: ctx.compare.items.value.length + 1,
                          scope: "colgroup",
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            className: "group-icon",
                            "data-sp-f380b3c4": "",
                          })}
                        >
                          {display(group.icon)}
                        </span>
                        <span
                          {...mergeProps({
                            className: "group-title",
                            "data-sp-f380b3c4": "",
                          })}
                        >
                          {display(group.name)}
                        </span>
                      </th>
                    </tr>
                    {renderList(group.rows, (row) => (
                      <tr
                        key={row.label}
                        {...mergeProps({
                          className: "data-row",
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        <th
                          {...mergeProps({
                            scope: "row",
                            className: "row-label",
                            "data-sp-f380b3c4": "",
                          })}
                        >
                          {display(row.label)}
                        </th>
                        {renderList(ctx.compare.items.value, (p) => (
                          <td
                            key={p.id}
                            {...mergeProps({
                              className: "row-cell",
                              "data-sp-f380b3c4": "",
                            })}
                          >
                            {row.render(p).sub ? (
                              <div
                                {...mergeProps({
                                  className: "cell-price-box",
                                  "data-sp-f380b3c4": "",
                                })}
                              >
                                <strong
                                  {...mergeProps({
                                    className: "cell-main-price",
                                    "data-sp-f380b3c4": "",
                                  })}
                                >
                                  {display(row.render(p).text)}
                                </strong>
                                <small
                                  {...mergeProps({
                                    className: "cell-sub-price",
                                    "data-sp-f380b3c4": "",
                                  })}
                                >
                                  {display(row.render(p).sub)}
                                </small>
                              </div>
                            ) : (
                              <span
                                {...mergeProps({
                                  className: ["cell-text", {
                                    "text-highlight": row.render(p).highlight,
                                  }],
                                  
                                  "data-sp-f380b3c4": "",
                                })}
                              >
                                {display(row.render(p).text)}
                              </span>
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </React.Fragment>
                ))}
                {ctx.allAmenities.length ? (
                  <tr
                    {...mergeProps({
                      className: "group-header-row",
                      "data-sp-f380b3c4": "",
                    })}
                  >
                    <th
                      {...mergeProps({
                        colSpan: ctx.compare.items.value.length + 1,
                        scope: "colgroup",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      <span
                        {...mergeProps({
                          className: "group-icon",
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        {"✨"}
                      </span>
                      <span
                        {...mergeProps({
                          className: "group-title",
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        {"Tiện ích khai báo & Điểm nổi bật"}
                      </span>
                    </th>
                  </tr>
                ) : null}
                {renderList(ctx.allAmenities, (amenity) => (
                  <tr
                    key={amenity}
                    {...mergeProps({
                      className: "data-row",
                      "data-sp-f380b3c4": "",
                    })}
                  >
                    <th
                      {...mergeProps({
                        scope: "row",
                        className: "row-label",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      {display(amenity)}
                    </th>
                    {renderList(ctx.compare.items.value, (p) => (
                      <td
                        key={p.id}
                        {...mergeProps({
                          className: "row-cell",
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        {p.declaredAmenities?.includes(amenity) ? (
                          <span
                            {...mergeProps({
                              className: "amenity-pill has",
                              "data-sp-f380b3c4": "",
                            })}
                          >
                            {" ✓ Có sẵn "}
                          </span>
                        ) : (
                          <span
                            {...mergeProps({
                              className: "amenity-pill missing",
                              "data-sp-f380b3c4": "",
                            })}
                          >
                            {" — Chưa có "}
                          </span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
                <tr
                  {...mergeProps({
                    className: "group-header-row",
                    "data-sp-f380b3c4": "",
                  })}
                >
                  <th
                    {...mergeProps({
                      colSpan: ctx.compare.items.value.length + 1,
                      scope: "colgroup",
                      "data-sp-f380b3c4": "",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className: "group-icon",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      {"🛡️"}
                    </span>
                    <span
                      {...mergeProps({
                        className: "group-title",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      {"Pháp lý & Giấy tờ"}
                    </span>
                  </th>
                </tr>
                <tr
                  {...mergeProps({
                    className: "data-row",
                    "data-sp-f380b3c4": "",
                  })}
                >
                  <th
                    {...mergeProps({
                      scope: "row",
                      className: "row-label",
                      "data-sp-f380b3c4": "",
                    })}
                  >
                    {"Tình trạng pháp lý"}
                  </th>
                  {renderList(ctx.compare.items.value, (p) => (
                    <td
                      key={p.id}
                      {...mergeProps({
                        className: "row-cell",
                        "data-sp-f380b3c4": "",
                      })}
                    >
                      <span
                        {...mergeProps({
                          className: "legal-badge",
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        {"Sổ đỏ / Sổ hồng chính chủ"}
                      </span>
                      <small
                        {...mergeProps({
                          className: "legal-note",
                          "data-sp-f380b3c4": "",
                        })}
                      >
                        {"Xem hồ sơ công khai tại trang chi tiết tin đăng"}
                      </small>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </section>
        <footer
          {...mergeProps({
            className: "dialog-footer",
            "data-sp-f380b3c4": "",
          })}
        >
          <p
            {...mergeProps({
              className: "dialog-disclaimer",
              "data-sp-f380b3c4": "",
            })}
          >
            {
              " * Thông tin, hình ảnh và giá chào do người đăng cung cấp. SmartProp hỗ trợ công cụ so sánh trực quan độc lập nhằm giúp bạn đưa ra quyết định tối ưu nhất. "
            }
          </p>
          <button
            {...mergeProps({
              type: "button",
              className: "btn-close-bottom",
              onClick: ($event) => {
                return ctx.close?.($event);
              },
              "data-sp-f380b3c4": "",
            })}
          >
            {"Đóng bảng so sánh"}
          </button>
        </footer>
      </div>
    </dialog>,
  ]);
});
