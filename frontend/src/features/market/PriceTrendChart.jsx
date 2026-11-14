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
  const props = propsForSetup(__props, {
    history: {
      type: Object,
      required: true,
      default: () => ({
        labels: [],
        land: [],
        house: [],
        apartment: [],
      }),
    },
  });

  // Toggle series visibility
  const visibleSeries = ref({
    land: true,
    house: true,
    apartment: true,
  });
  const seriesConfig = {
    land: {
      key: "land",
      name: "Đất nền đô thị",
      color: "var(--ui-chart-1)",
      // Slate theme chart series
      dotColor: "var(--ui-chart-1)",
      gradientFrom: "var(--ui-chart-1-soft)",
      gradientTo: "transparent",
    },
    house: {
      key: "house",
      name: "Nhà phố & Biệt thự",
      color: "var(--ui-chart-2)",
      // Muted contrasting series
      dotColor: "var(--ui-chart-2)",
      gradientFrom: "var(--ui-chart-2-soft)",
      gradientTo: "transparent",
    },
    apartment: {
      key: "apartment",
      name: "Căn hộ cao cấp",
      color: "var(--ui-chart-3)",
      // Muted contrasting series
      dotColor: "var(--ui-chart-3)",
      gradientFrom: "var(--ui-chart-3-soft)",
      gradientTo: "transparent",
    },
  };
  const timeRanges = ["Tất cả (2024–2026)", "2 năm gần nhất", "1 năm gần nhất"];
  const activeRange = ref("Tất cả (2024–2026)");
  const filteredLabels = computed(() => {
    const all = props.history?.labels || [];
    if (activeRange.value === "1 năm gần nhất") return all.slice(-4);
    if (activeRange.value === "2 năm gần nhất") return all.slice(-8);
    return all;
  });
  const filteredData = computed(() => {
    const count = filteredLabels.value.length;
    return {
      land: (props.history?.land || []).slice(-count),
      house: (props.history?.house || []).slice(-count),
      apartment: (props.history?.apartment || []).slice(-count),
    };
  });
  const hoveredIndex = ref(null);

  // SVG Chart Geometry
  const svgWidth = 860;
  const svgHeight = 320;
  const padding = {
    top: 32,
    right: 32,
    bottom: 44,
    left: 56,
  };
  const chartMetrics = computed(() => {
    const labels = filteredLabels.value;
    if (!labels.length)
      return {
        min: 0,
        max: 200,
        series: [],
        yTicks: [],
      };
    let allVals = [];
    if (visibleSeries.value.land) allVals.push(...filteredData.value.land);
    if (visibleSeries.value.house) allVals.push(...filteredData.value.house);
    if (visibleSeries.value.apartment)
      allVals.push(...filteredData.value.apartment);
    if (!allVals.length) allVals = [50, 150];
    const rawMin = Math.min(...allVals);
    const rawMax = Math.max(...allVals);
    const range = rawMax - rawMin || 1;
    const min = Math.max(0, Math.floor((rawMin - range * 0.12) / 10) * 10);
    const max = Math.ceil((rawMax + range * 0.12) / 10) * 10;
    const delta = max - min || 1;
    const chartW = svgWidth - padding.left - padding.right;
    const chartH = svgHeight - padding.top - padding.bottom;
    const tickCount = 4;
    const yTicks = [];
    for (let i = 0; i <= tickCount; i++) {
      const val = Math.round(min + (i / tickCount) * delta);
      const y = padding.top + chartH - (i / tickCount) * chartH;
      yTicks.push({
        y,
        value: val,
      });
    }
    const series = Object.entries(seriesConfig).map(([key, cfg]) => {
      const vals = filteredData.value[key] || [];
      const isVisible = visibleSeries.value[key];
      if (!isVisible || !vals.length)
        return {
          ...cfg,
          points: [],
          pathD: "",
          areaD: "",
          isVisible: false,
        };
      const points = vals.map((val, idx) => {
        const x = padding.left + (idx / Math.max(1, vals.length - 1)) * chartW;
        const y = padding.top + chartH - ((val - min) / delta) * chartH;
        return {
          x,
          y,
          value: val,
          label: labels[idx],
        };
      });
      let pathD = `M ${points[0].x} ${points[0].y}`;
      for (let i = 0; i < points.length - 1; i++) {
        const p0 = points[i];
        const p1 = points[i + 1];
        const cpX = (p0.x + p1.x) / 2;
        pathD += ` C ${cpX} ${p0.y}, ${cpX} ${p1.y}, ${p1.x} ${p1.y}`;
      }
      const baseLineY = padding.top + chartH;
      const areaD = `${pathD} L ${points[points.length - 1].x} ${baseLineY} L ${points[0].x} ${baseLineY} Z`;
      return {
        ...cfg,
        points,
        pathD,
        areaD,
        isVisible: true,
      };
    });
    return {
      min,
      max,
      series,
      yTicks,
    };
  });
  function toggleSeries(key) {
    visibleSeries.value[key] = !visibleSeries.value[key];
  }
  return {
    ref,
    computed,
    props,
    visibleSeries,
    seriesConfig,
    timeRanges,
    activeRange,
    filteredLabels,
    filteredData,
    hoveredIndex,
    svgWidth,
    svgHeight,
    padding,
    chartMetrics,
    toggleSeries,
  };
}
export default React.forwardRef(function PriceTrendChart(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div
      {...mergeProps({
        className:
          "rounded-3xl bg-brand-card p-6 sm:p-8 border border-[var(--ui-border)] shadow-2xs",
      })}
    >
      <div
        {...mergeProps({
          className:
            "flex flex-col lg:flex-row lg:items-end justify-between gap-5 pb-6 border-b border-[var(--ui-border)]",
        })}
      >
        <div {...mergeProps({})}>
          <p
            {...mergeProps({
              className:
                "text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--ui-accent)] mb-2",
            })}
          >
            {" CHỈ SỐ ĐỊNH LƯỢNG · LỊCH SỬ ĐƠN GIÁ "}
          </p>
          <h3
            {...mergeProps({
              className:
                "text-xl sm:text-2xl font-semibold text-[var(--ui-accent)] tracking-tight",
            })}
          >
            {" Biến động mặt bằng giá "}
            <span
              {...mergeProps({
                className: "text-[var(--ui-accent)]",
              })}
            >
              {"theo thời gian."}
            </span>
          </h3>
          <p
            {...mergeProps({
              className: "text-xs text-[var(--ui-accent)] mt-1.5 leading-relaxed",
            })}
          >
            {
              " Đơn giá trung bình chuẩn hóa theo quý của 3 phân khúc chủ đạo · Đơn vị tính: "
            }
            <strong
              {...mergeProps({
                className: "text-[var(--ui-accent)]",
              })}
            >
              {"Triệu VNĐ/m²"}
            </strong>
          </p>
        </div>
        <div
          {...mergeProps({
            className:
              "inline-flex items-center gap-1 bg-[var(--ui-surface)] p-1.5 rounded-full border border-[var(--ui-border)] self-start lg:self-auto text-xs",
          })}
        >
          {renderList(ctx.timeRanges, (range) => (
            <button
              key={range}
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  ctx.activeRange = range;
                  ctx.hoveredIndex = null;
                },
                className: ["px-3.5 py-1.5 rounded-full font-semibold transition-all cursor-pointer", ctx.activeRange === range
                    ? "bg-[var(--ui-soft)] text-[var(--ui-ink)] shadow-xs"
                    : "text-[var(--ui-accent)] hover:text-[var(--ui-accent)]"],
                
              })}
            >
              {display(range)}
            </button>
          ))}
        </div>
      </div>
      <div
        {...mergeProps({
          className:
            "flex flex-wrap items-center justify-between gap-4 pt-5 pb-3",
        })}
      >
        <div
          {...mergeProps({
            className: "flex flex-wrap items-center gap-2.5",
          })}
        >
          <span
            {...mergeProps({
              className: "text-xs text-[var(--ui-muted)] font-semibold mr-1",
            })}
          >
            {"Phân khúc hiển thị:"}
          </span>
          {renderList(ctx.seriesConfig, (cfg, key) => (
            <button
              key={key}
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  ctx.toggleSeries(key);
                },
                className: ["inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-xs font-semibold transition-all cursor-pointer", ctx.visibleSeries[key]
                  ? "bg-[var(--ui-surface)] border-[var(--ui-border)] text-[var(--ui-accent)] shadow-2xs"
                  : "bg-brand-card border-[var(--ui-border)] text-[var(--ui-muted)] opacity-55 line-through"],
                
              })}
            >
              <span
                {...mergeProps({
                  className: "w-2.5 h-2.5 rounded-full",
                  style: {
                    backgroundColor: cfg.color,
                  },
                })}
              />
              <span {...mergeProps({})}>{display(cfg.name)}</span>
            </button>
          ))}
        </div>
        <span
          {...mergeProps({
            className: "text-[11px] text-[var(--ui-muted)] italic",
          })}
        >
          {" Rê chuột trên biểu đồ để đối chiếu đơn giá từng quý "}
        </span>
      </div>
      <div
        {...mergeProps({
          className: "relative w-full overflow-x-auto mt-2",
        })}
      >
        <div
          {...mergeProps({
            className: "min-w-[680px]",
          })}
        >
          <svg
            {...mergeProps({
              viewBox: `0 0 ${ctx.svgWidth} ${ctx.svgHeight}`,
              className: "w-full h-auto overflow-visible select-none",
            })}
          >
            <defs {...mergeProps({})}>
              {renderList(ctx.chartMetrics.series, (s) => (
                <linearGradient
                  key={"grad-" + s.key}
                  {...mergeProps({
                    id: "grad-" + s.key,
                    x1: "0",
                    y1: "0",
                    x2: "0",
                    y2: "1",
                  })}
                >
                  <stop
                    {...mergeProps({
                      offset: "0%",
                      stopColor: s.color,
                      stopOpacity: "0.14",
                    })}
                  />
                  <stop
                    {...mergeProps({
                      offset: "100%",
                      stopColor: s.color,
                      stopOpacity: "0.0",
                    })}
                  />
                </linearGradient>
              ))}
            </defs>
            <g
              {...mergeProps({
                className: "grid-lines",
              })}
            >
              {renderList(ctx.chartMetrics.yTicks, (tick) => (
                <React.Fragment key={tick.y} {...mergeProps({})}>
                  <line
                    {...mergeProps({
                      x1: ctx.padding.left,
                      y1: tick.y,
                      x2: ctx.svgWidth - ctx.padding.right,
                      y2: tick.y,
                      stroke: "var(--ui-border)",
                      strokeWidth: "1",
                      strokeDasharray: "4,4",
                    })}
                  />
                  <text
                    {...mergeProps({
                      x: ctx.padding.left - 14,
                      y: tick.y + 4,
                      textAnchor: "end",
                      className: "text-[11px] fill-[var(--ui-muted)] font-semibold",
                    })}
                  >
                    {display(tick.value)}
                  </text>
                </React.Fragment>
              ))}
            </g>
            {ctx.hoveredIndex !== null ? (
              <React.Fragment {...mergeProps({})}>
                {renderList(ctx.chartMetrics.series, (s) => (
                  <line
                    key={"guide-" + s.key}
                    {...mergeProps(
                      {
                        x1: s.points[ctx.hoveredIndex].x,
                        y1: ctx.padding.top,
                        x2: s.points[ctx.hoveredIndex].x,
                        y2: ctx.svgHeight - ctx.padding.bottom,
                        stroke: "var(--ui-chart-2)",
                        strokeWidth: "1.5",
                        strokeDasharray: "3,3",
                      },
                      {
                        style: {
                          display:
                            s.isVisible && s.points[ctx.hoveredIndex]
                              ? undefined
                              : "none",
                        },
                      },
                    )}
                  />
                ))}
              </React.Fragment>
            ) : null}
            {renderList(ctx.chartMetrics.series, (s) => (
              <g key={s.key} {...mergeProps({})}>
                {s.isVisible && s.areaD ? (
                  <path
                    {...mergeProps({
                      d: s.areaD,
                      fill: `url(#grad-${s.key})`,
                      className: "transition-all duration-300",
                    })}
                  />
                ) : null}
                {s.isVisible && s.pathD ? (
                  <path
                    {...mergeProps({
                      d: s.pathD,
                      fill: "none",
                      stroke: s.color,
                      strokeWidth: "3",
                      strokeLinecap: "round",
                      strokeLinejoin: "round",
                      className: "transition-all duration-300",
                    })}
                  />
                ) : null}
              </g>
            ))}
            {renderList(ctx.filteredLabels, (lbl, idx) => (
              <g key={idx} {...mergeProps({})}>
                <text
                  {...mergeProps({
                    x:
                      ctx.padding.left +
                      (idx / Math.max(1, ctx.filteredLabels.length - 1)) *
                        (ctx.svgWidth - ctx.padding.left - ctx.padding.right),
                    y: ctx.svgHeight - 12,
                    textAnchor: "middle",
                    className: ["text-[11px] font-semibold transition", ctx.hoveredIndex === idx
                        ? "fill-[var(--ui-accent)] font-bold"
                        : "fill-[var(--ui-muted)]"],
                    
                  })}
                >
                  {display(lbl)}
                </text>
                <rect
                  {...mergeProps({
                    x:
                      ctx.padding.left +
                      (idx / Math.max(1, ctx.filteredLabels.length - 1)) *
                        (ctx.svgWidth - ctx.padding.left - ctx.padding.right) -
                      25,
                    y: ctx.padding.top,
                    width: "50",
                    height:
                      ctx.svgHeight - ctx.padding.top - ctx.padding.bottom,
                    fill: "transparent",
                    className: "cursor-pointer",
                    onMouseEnter: ($event) => {
                      ctx.hoveredIndex = idx;
                    },
                    onMouseLeave: ($event) => {
                      ctx.hoveredIndex = null;
                    },
                  })}
                />
                {renderList(ctx.chartMetrics.series, (s) => (
                  <React.Fragment key={s.key} {...mergeProps({})}>
                    {s.isVisible && s.points[idx] ? (
                      <circle
                        {...mergeProps({
                          cx: s.points[idx].x,
                          cy: s.points[idx].y,
                          r: ctx.hoveredIndex === idx ? 6.5 : 4,
                          fill: "var(--ui-surface)",
                          stroke: s.color,
                          strokeWidth: ctx.hoveredIndex === idx ? 3.5 : 2.5,
                          className:
                            "transition-all duration-150 pointer-events-none",
                        })}
                      />
                    ) : null}
                  </React.Fragment>
                ))}
              </g>
            ))}
          </svg>
          {ctx.hoveredIndex !== null ? (
            <div
              {...mergeProps({
                className:
                  "absolute pointer-events-none z-20 transition-all duration-100",
                style: {
                  left: `${Math.min(78, Math.max(12, (ctx.hoveredIndex / Math.max(1, ctx.filteredLabels.length - 1)) * 100))}%`,
                  top: "14px",
                },
              })}
            >
              <div
                {...mergeProps({
                  className:
                    "bg-[var(--ui-soft)]/95 backdrop-blur-md text-brand-navy p-4 rounded-2xl shadow-xl border border-[var(--ui-border)]/35 text-xs min-w-[220px]",
                })}
              >
                <p
                  {...mergeProps({
                    className:
                      "font-bold text-[var(--ui-ink)] pb-2 mb-2.5 border-b border-brand-line/12 flex items-center justify-between gap-4",
                  })}
                >
                  <span {...mergeProps({})}>
                    {"Kỳ thống kê: "}
                    {display(ctx.filteredLabels[ctx.hoveredIndex])}
                  </span>
                  <span
                    {...mergeProps({
                      className:
                        "text-[10px] text-[var(--ui-success-text)] font-semibold uppercase tracking-wider",
                    })}
                  >
                    {"Chuẩn hóa"}
                  </span>
                </p>
                <div
                  {...mergeProps({
                    className: "space-y-2",
                  })}
                >
                  {renderList(ctx.chartMetrics.series, (s) => (
                    <div
                      key={s.key}
                      {...mergeProps(
                        {
                          className: "flex items-center justify-between gap-4",
                        },
                        {
                          style: {
                            display:
                              s.isVisible && s.points[ctx.hoveredIndex]
                                ? undefined
                                : "none",
                          },
                        },
                      )}
                    >
                      <div
                        {...mergeProps({
                          className: "flex items-center gap-2",
                        })}
                      >
                        <span
                          {...mergeProps({
                            className:
                              "w-2.5 h-2.5 rounded-full border border-brand-line/40",
                            style: {
                              backgroundColor: s.color,
                            },
                          })}
                        />
                        <span
                          {...mergeProps({
                            className: "text-brand-navy/80",
                          })}
                        >
                          {display(s.name)}
                        </span>
                      </div>
                      <span
                        {...mergeProps({
                          className: "font-bold text-brand-navy",
                        })}
                      >
                        {display(s.points[ctx.hoveredIndex].value)}
                        {" tr/m²"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>,
  ]);
});
