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
function setup(__props) {
  // Dữ liệu giả lập để trình diễn giao diện; chưa kết nối API thị trường.
  const marketType = ref("Tất cả");
  const marketPeriod = ref(12);
  const marketTypes = [
    {
      name: "Căn hộ",
      color: "#8BB5CA",
      values: [36, 37, 38, 37, 39, 40, 41, 40, 42, 43, 44, 46],
    },
    {
      name: "Nhà phố",
      color: "#a5dbdc",
      values: [54, 55, 54, 57, 58, 59, 61, 60, 62, 65, 66, 68],
    },
    {
      name: "Đất nền",
      color: "#9ABFAE",
      values: [42, 43, 42, 44, 45, 44, 46, 48, 47, 49, 50, 52],
    },
  ];
  const marketDistrictData = [
    {
      name: "Hải Châu",
      prices: {
        "Căn hộ": 52,
        "Nhà phố": 80,
        "Đất nền": 60,
      },
    },
    {
      name: "Sơn Trà",
      prices: {
        "Căn hộ": 48,
        "Nhà phố": 69,
        "Đất nền": 54,
      },
    },
    {
      name: "Ngũ Hành Sơn",
      prices: {
        "Căn hộ": 44,
        "Nhà phố": 61,
        "Đất nền": 49,
      },
    },
    {
      name: "Cẩm Lệ",
      prices: {
        "Căn hộ": 32,
        "Nhà phố": 48,
        "Đất nền": 38,
      },
    },
  ];
  const visibleMarketSeries = computed(() =>
    marketType.value === "Tất cả"
      ? marketTypes
      : marketTypes.filter((item) => item.name === marketType.value),
  );
  const marketSummary = computed(() => {
    const series = visibleMarketSeries.value;
    const first =
      series.reduce(
        (sum, item) => sum + item.values[12 - marketPeriod.value],
        0,
      ) / series.length;
    const last =
      series.reduce((sum, item) => sum + item.values[11], 0) / series.length;
    return {
      price: last,
      change: ((last - first) / first) * 100,
    };
  });
  const marketDistricts = computed(() =>
    marketDistrictData
      .map((item) => ({
        name: item.name,
        price:
          marketType.value === "Tất cả"
            ? Object.values(item.prices).reduce(
                (sum, price) => sum + price,
                0,
              ) / 3
            : item.prices[marketType.value],
      }))
      .sort((a, b) => b.price - a.price),
  );
  const marketChart = computed(() => {
    const start = 12 - marketPeriod.value;
    const series = visibleMarketSeries.value;
    const values = series.flatMap((item) => item.values.slice(start));
    const low = Math.floor((Math.min(...values) - 5) / 10) * 10;
    const high = Math.ceil((Math.max(...values) + 5) / 10) * 10;
    const x = (index) => 52 + (index * 650) / (marketPeriod.value - 1);
    const y = (value) => 245 - ((value - low) / (high - low)) * 205;
    return {
      lines: series.map((item) => ({
        name: item.name,
        color: item.color,
        points: item.values
          .slice(start)
          .map((value, index) => `${x(index)},${y(value)}`)
          .join(" "),
        latest: item.values[11],
      })),
      grid: Array.from(
        {
          length: 5,
        },
        (_, i) => ({
          value: low + ((high - low) * i) / 4,
          y: y(low + ((high - low) * i) / 4),
        }),
      ),
      labels: Array.from(
        {
          length: marketPeriod.value,
        },
        (_, i) => ({
          text: `T${start + i + 1}`,
          x: x(i),
        }),
      ),
    };
  });
  return {
    ref,
    computed,
    marketType,
    marketPeriod,
    marketTypes,
    marketDistrictData,
    visibleMarketSeries,
    marketSummary,
    marketDistricts,
    marketChart,
  };
}
export default React.forwardRef(function MarketIntelligence(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section
      {...mergeProps({
        id: "market-demo",
        "aria-labelledby": "market-heading",
        className: "bg-[var(--ui-surface)] py-14 text-[var(--ui-accent)] md:py-20",
      })}
    >
      <div
        {...mergeProps({
          className: "mx-auto max-w-7xl px-5 lg:px-8",
        })}
      >
        <div
          {...mergeProps({
            className: "flex flex-wrap items-end justify-between gap-6",
          })}
        >
          <div {...mergeProps({})}>
            <p
              {...mergeProps({
                className:
                  "mb-3 text-xs font-bold uppercase tracking-[0.3em] text-[var(--ui-accent)]",
              })}
            >
              {" Market Intelligence "}
            </p>
            <h2
              {...mergeProps({
                id: "market-heading",
                className:
                  "text-3xl font-semibold leading-tight sm:text-4xl md:text-5xl",
              })}
            >
              {" Dữ liệu kể "}
              <span
                {...mergeProps({
                  className: "text-[var(--ui-accent)]",
                })}
              >
                {"câu chuyện thị trường."}
              </span>
            </h2>
            <p
              {...mergeProps({
                className: "mt-4 max-w-2xl text-sm leading-7 text-[var(--ui-accent)]",
              })}
            >
              {
                " Khám phá xu hướng giá căn hộ, nhà phố và đất nền tại Đà Nẵng. "
              }
              <span
                {...mergeProps({
                  className: "ml-1 inline-block font-semibold text-[var(--ui-accent)]",
                })}
              >
                {"Dữ liệu mô phỏng."}
              </span>
            </p>
          </div>
          <div
            {...mergeProps({
              className: "flex flex-wrap gap-2",
              role: "group",
              "aria-label": "Lọc loại hình bất động sản",
            })}
          >
            {renderList(["Tất cả", "Căn hộ", "Nhà phố", "Đất nền"], (item) => (
              <button
                key={item}
                {...mergeProps({
                  type: "button",
                  onClick: ($event) => {
                    ctx.marketType = item;
                  },
                  "aria-pressed": ctx.marketType === item,
                  className: ["cursor-pointer rounded-full border px-4 py-2.5 text-xs font-bold transition focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--ui-border)]", ctx.marketType === item
                      ? "border-[var(--ui-border)] bg-[var(--ui-soft)] text-brand-navy"
                      : "border-[var(--ui-border)] bg-brand-card text-[var(--ui-accent)] hover:border-[var(--ui-border)]"],
                  
                })}
              >
                {display(item)}
              </button>
            ))}
          </div>
        </div>
        <div
          {...mergeProps({
            className: "mt-9 grid gap-4 sm:grid-cols-3",
          })}
        >
          <div
            {...mergeProps({
              className: "rounded-2xl border border-[var(--ui-border)] bg-brand-card p-6",
            })}
          >
            <p
              {...mergeProps({
                className: "text-xs font-semibold text-[var(--ui-accent)]",
              })}
            >
              {" Giá trung bình theo loại hình "}
            </p>
            <p
              {...mergeProps({
                className: "mt-3 text-3xl font-bold text-[var(--ui-accent)]",
              })}
            >
              {display(ctx.marketSummary.price.toFixed(1))}{" "}
              <span
                {...mergeProps({
                  className: "text-sm font-medium",
                })}
              >
                {"triệu/m²"}
              </span>
            </p>
          </div>
          <div
            {...mergeProps({
              className: "rounded-2xl border border-[var(--ui-border)] bg-brand-card p-6",
            })}
          >
            <p
              {...mergeProps({
                className: "text-xs font-semibold text-[var(--ui-accent)]",
              })}
            >
              {" Biến động trong kỳ "}
            </p>
            <p
              {...mergeProps({
                className: ["mt-3 text-3xl font-bold", ctx.marketSummary.change >= 0
                    ? "text-[var(--ui-success-text)]"
                    : "text-[var(--ui-error-text)]"],
                
              })}
            >
              {display(ctx.marketSummary.change >= 0 ? "+" : "")}
              {display(ctx.marketSummary.change.toFixed(1))}
              {"% "}
            </p>
          </div>
          <div
            {...mergeProps({
              className: "rounded-2xl border border-[var(--ui-border)] bg-brand-card p-6",
            })}
          >
            <p
              {...mergeProps({
                className: "text-xs font-semibold text-[var(--ui-accent)]",
              })}
            >
              {" Phạm vi phân tích "}
            </p>
            <p
              {...mergeProps({
                className: "mt-3 text-3xl font-bold text-[var(--ui-accent)]",
              })}
            >
              {" 4 "}
              <span
                {...mergeProps({
                  className: "text-sm font-medium",
                })}
              >
                {"khu vực"}
              </span>
            </p>
          </div>
        </div>
        <div
          {...mergeProps({
            className:
              "mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)]",
          })}
        >
          <div
            {...mergeProps({
              className:
                "min-w-0 rounded-3xl border border-[var(--ui-border)] bg-brand-card p-5 shadow-sm md:p-7",
            })}
          >
            <div
              {...mergeProps({
                className: "flex flex-wrap items-center justify-between gap-4",
              })}
            >
              <div {...mergeProps({})}>
                <h3
                  {...mergeProps({
                    className: "text-xl font-bold",
                  })}
                >
                  {" Xu hướng giá theo loại hình "}
                </h3>
                <p
                  {...mergeProps({
                    className: "mt-1 text-xs text-[var(--ui-accent)]",
                  })}
                >
                  {" Đơn vị: triệu đồng/m² "}
                </p>
              </div>
              <div
                {...mergeProps({
                  className: "flex gap-2",
                  role: "group",
                  "aria-label": "Khoảng thời gian thống kê",
                })}
              >
                {renderList([3, 6, 12], (period) => (
                  <button
                    key={period}
                    {...mergeProps({
                      type: "button",
                      onClick: ($event) => {
                        ctx.marketPeriod = period;
                      },
                      "aria-pressed": ctx.marketPeriod === period,
                      className: ["cursor-pointer rounded-full px-3 py-2.5 text-xs font-bold transition focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--ui-border)]", ctx.marketPeriod === period
                          ? "bg-[var(--ui-soft)] text-[var(--ui-accent)]"
                          : "bg-[var(--ui-surface)] text-[var(--ui-accent)] hover:bg-[var(--ui-surface)]"],
                      
                    })}
                  >
                    {display(period)}
                    {" tháng "}
                  </button>
                ))}
              </div>
            </div>
            <div
              {...mergeProps({
                className: "mt-6 w-full overflow-x-auto overscroll-x-contain",
              })}
            >
              <svg
                {...mergeProps({
                  viewBox: "0 0 750 295",
                  role: "img",
                  "aria-label":
                    "Biểu đồ đường xu hướng giá bất động sản minh họa",
                  className: "block w-full min-w-[420px]",
                })}
              >
                {renderList(ctx.marketChart.grid, (tick) => (
                  <g key={tick.value} {...mergeProps({})}>
                    <line
                      {...mergeProps({
                        x1: "52",
                        y1: tick.y,
                        x2: "702",
                        y2: tick.y,
                        stroke: "#d3e4e9",
                        strokeDasharray: "4 5",
                      })}
                    />
                    <text
                      {...mergeProps({
                        x: "43",
                        y: tick.y + 4,
                        textAnchor: "end",
                        fill: "#64748B",
                        fontSize: "12",
                      })}
                    >
                      {display(tick.value.toFixed(0))}
                    </text>
                  </g>
                ))}
                {renderList(ctx.marketChart.labels, (label) => (
                  <g key={label.text} {...mergeProps({})}>
                    <text
                      {...mergeProps({
                        x: label.x,
                        y: "275",
                        textAnchor: "middle",
                        fill: "#64748B",
                        fontSize: "12",
                      })}
                    >
                      {display(label.text)}
                    </text>
                  </g>
                ))}
                {renderList(ctx.marketChart.lines, (line) => (
                  <polyline
                    key={line.name}
                    {...mergeProps({
                      points: line.points,
                      fill: "none",
                      stroke: line.color,
                      strokeWidth: "3.5",
                      strokeLinecap: "round",
                      strokeLinejoin: "round",
                    })}
                  />
                ))}
              </svg>
            </div>
            <div
              {...mergeProps({
                className: "mt-3 flex flex-wrap gap-x-6 gap-y-3",
              })}
            >
              {renderList(ctx.marketChart.lines, (line) => (
                <div
                  key={line.name}
                  {...mergeProps({
                    className: "flex items-center gap-2 text-xs text-[var(--ui-accent)]",
                  })}
                >
                  <span
                    {...mergeProps({
                      className: "h-2.5 w-2.5 rounded-full",
                      style: {
                        backgroundColor: line.color,
                      },
                    })}
                  />
                  <span {...mergeProps({})}>
                    {display(line.name)}
                    {": "}
                    <strong
                      {...mergeProps({
                        className: "text-[var(--ui-accent)]",
                      })}
                    >
                      {display(line.latest)}
                      {" triệu/m² "}
                    </strong>
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div
            {...mergeProps({
              className:
                "rounded-3xl bg-[var(--ui-soft)] p-6 text-brand-navy shadow-sm md:p-8",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-ink)]",
              })}
            >
              {" District Comparison "}
            </p>
            <h3
              {...mergeProps({
                className: "mt-3 text-2xl font-semibold",
              })}
            >
              {" Giá theo khu vực "}
            </h3>
            <p
              {...mergeProps({
                className: "mt-2 text-xs leading-6 text-brand-navy/60",
              })}
            >
              {" Giá trung bình tham khảo · triệu đồng/m² "}
            </p>
            <div
              {...mergeProps({
                className: "mt-7 space-y-6",
              })}
            >
              {renderList(ctx.marketDistricts, (district) => (
                <div key={district.name} {...mergeProps({})}>
                  <div
                    {...mergeProps({
                      className:
                        "mb-2 flex items-center justify-between gap-3 text-sm",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className: "font-medium",
                      })}
                    >
                      {display(district.name)}
                    </span>
                    <span
                      {...mergeProps({
                        className: "font-bold text-[var(--ui-ink)]",
                      })}
                    >
                      {display(district.price.toFixed(1))}
                    </span>
                  </div>
                  <div
                    {...mergeProps({
                      className: "h-2 overflow-hidden rounded-full bg-brand-card/15",
                    })}
                  >
                    <div
                      {...mergeProps({
                        className:
                          "h-full rounded-full bg-[var(--ui-soft)] transition-all duration-300",
                        style: {
                          width: `${(district.price / 90) * 100}%`,
                        },
                      })}
                    />
                  </div>
                </div>
              ))}
            </div>
            <p
              {...mergeProps({
                className:
                  "mt-8 border-t border-brand-line/15 pt-5 text-xs leading-6 text-brand-navy/60",
              })}
            >
              {
                " Dữ liệu mô phỏng phục vụ trình diễn giao diện, không phải báo cáo giá thực tế hay tư vấn đầu tư. "
              }
            </p>
          </div>
        </div>
      </div>
    </section>,
  ]);
});
