import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
function usePriceTrendChartState(inputProps, forwardedRef) {
  inputProps = {
    history: (() => ({
      labels: [],
      land: [],
      house: [],
      apartment: []
    }))(),
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    history: (() => ({
      labels: [],
      land: [],
      house: [],
      apartment: []
    }))(),
    ...inputProps
  };

  // Toggle series visibility
  const _props = useRef(props);
  _props.current = props;
  const [visibleSeries] = useState(() => createStateStore({
    land: true,
    house: true,
    apartment: true
  }));
  useSyncExternalStore(visibleSeries.subscribe, visibleSeries.getSnapshot);
  const seriesConfig = {
    land: {
      key: "land",
      name: "Đất nền đô thị",
      color: "var(--ui-chart-1)",
      // Slate theme chart series
      dotColor: "var(--ui-chart-1)",
      gradientFrom: "var(--ui-chart-1-soft)",
      gradientTo: "transparent"
    },
    house: {
      key: "house",
      name: "Nhà phố & Biệt thự",
      color: "var(--ui-chart-2)",
      // Muted contrasting series
      dotColor: "var(--ui-chart-2)",
      gradientFrom: "var(--ui-chart-2-soft)",
      gradientTo: "transparent"
    },
    apartment: {
      key: "apartment",
      name: "Căn hộ cao cấp",
      color: "var(--ui-chart-3)",
      // Muted contrasting series
      dotColor: "var(--ui-chart-3)",
      gradientFrom: "var(--ui-chart-3-soft)",
      gradientTo: "transparent"
    }
  };
  const timeRanges = ["Tất cả (2024–2026)", "2 năm gần nhất", "1 năm gần nhất"];
  const [activeRange] = useState(() => createStateStore("Tất cả (2024–2026)"));
  useSyncExternalStore(activeRange.subscribe, activeRange.getSnapshot);
  const getFilteredLabels = () => {
    const all = _props.current.history?.labels || [];
    if (activeRange.getSnapshot() === "1 năm gần nhất") return all.slice(-4);
    if (activeRange.getSnapshot() === "2 năm gần nhất") return all.slice(-8);
    return all;
  };
  const getFilteredData = () => {
    const count = getFilteredLabels().length;
    return {
      land: (_props.current.history?.land || []).slice(-count),
      house: (_props.current.history?.house || []).slice(-count),
      apartment: (_props.current.history?.apartment || []).slice(-count)
    };
  };
  const [hoveredIndex] = useState(() => createStateStore(null));

  // SVG Chart Geometry
  useSyncExternalStore(hoveredIndex.subscribe, hoveredIndex.getSnapshot);
  const svgWidth = 860;
  const svgHeight = 320;
  const padding = {
    top: 32,
    right: 32,
    bottom: 44,
    left: 56
  };
  const getChartMetrics = () => {
    const labels = getFilteredLabels();
    if (!labels.length) return {
      min: 0,
      max: 200,
      series: [],
      yTicks: []
    };
    let allVals = [];
    if (visibleSeries.getSnapshot().land) allVals.push(...getFilteredData().land);
    if (visibleSeries.getSnapshot().house) allVals.push(...getFilteredData().house);
    if (visibleSeries.getSnapshot().apartment) allVals.push(...getFilteredData().apartment);
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
      const val = Math.round(min + i / tickCount * delta);
      const y = padding.top + chartH - i / tickCount * chartH;
      yTicks.push({
        y,
        value: val
      });
    }
    const series = Object.entries(seriesConfig).map(([key, cfg]) => {
      const vals = getFilteredData()[key] || [];
      const isVisible = visibleSeries.getSnapshot()[key];
      if (!isVisible || !vals.length) return {
        ...cfg,
        points: [],
        pathD: "",
        areaD: "",
        isVisible: false
      };
      const points = vals.map((val, idx) => {
        const x = padding.left + idx / Math.max(1, vals.length - 1) * chartW;
        const y = padding.top + chartH - (val - min) / delta * chartH;
        return {
          x,
          y,
          value: val,
          label: labels[idx]
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
        isVisible: true
      };
    });
    return {
      min,
      max,
      series,
      yTicks
    };
  };
  function toggleSeries(key) {
    visibleSeries.edit(draftValue => draftValue[key] = !visibleSeries.getSnapshot()[key]);
  }
  return {
    ...inputProps,
    visibleSeries: visibleSeries.getSnapshot(),
    seriesConfig,
    timeRanges,
    activeRange: activeRange.getSnapshot(),
    filteredLabels: getFilteredLabels(),
    hoveredIndex: hoveredIndex.getSnapshot(),
    svgWidth,
    svgHeight,
    padding,
    chartMetrics: getChartMetrics(),
    toggleSeries,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["history", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateActiveRangeValue: activeRange.set,
    updateHoveredIndexValue: hoveredIndex.set
  };
}
export default React.forwardRef(function PriceTrendChart(props, ref) {
  const view = usePriceTrendChartState(props, ref);
  return <><div {...view.rootAttributes} className={classNames(["market-price-chart rounded-3xl bg-brand-card p-6 sm:p-8 border border-[var(--ui-border)] shadow-2xs", view.rootAttributes.className])}>
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-5 pb-6 border-b border-[var(--ui-border)]">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--ui-accent)] mb-2">
            {" CHỈ SỐ ĐỊNH LƯỢNG · LỊCH SỬ ĐƠN GIÁ "}
          </p>
          <h3 className="text-xl sm:text-2xl font-semibold text-[var(--ui-accent)] tracking-tight">
            {" Biến động mặt bằng giá "}
            <span className="text-[var(--ui-accent)]">
              {"theo thời gian."}
            </span>
          </h3>
          <p className="text-xs text-[var(--ui-accent)] mt-1.5 leading-relaxed">
            {" Đơn giá trung bình chuẩn hóa theo quý của 3 phân khúc chủ đạo · Đơn vị tính: "}
            <strong className="text-[var(--ui-accent)]">
              {"Triệu VNĐ/m²"}
            </strong>
          </p>
        </div>
        <div className="chart-time-selector inline-flex items-center gap-1 bg-[var(--ui-surface)] p-1.5 rounded-full border border-[var(--ui-border)] self-start lg:self-auto text-xs">
          {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.timeRanges, range => <button key={range} type="button" aria-pressed={view.activeRange === range} onClick={$event => {
            view.updateActiveRangeValue(range);
            view.updateHoveredIndexValue(null);
          }} className={classNames(["px-3.5 py-1.5 rounded-full font-semibold transition-all cursor-pointer", view.activeRange === range ? "bg-[var(--ui-soft)] text-[var(--ui-ink)] shadow-xs" : "text-[var(--ui-accent)] hover:text-[var(--ui-accent)]"])}>
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(range)}
            </button>)}
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-4 pt-5 pb-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="text-xs text-[var(--ui-muted)] font-semibold mr-1">
            {"Phân khúc hiển thị:"}
          </span>
          {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.seriesConfig, (cfg, key) => <button key={key} type="button" aria-pressed={!!view.visibleSeries[key]} onClick={$event => {
            view.toggleSeries(key);
          }} className={classNames(["chart-segment inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-xs font-semibold transition-all cursor-pointer", view.visibleSeries[key] ? "bg-[var(--ui-surface)] border-[var(--ui-border)] text-[var(--ui-accent)] shadow-2xs" : "bg-brand-card border-[var(--ui-border)] text-[var(--ui-muted)] opacity-55 line-through"])}>
              <span className="w-2.5 h-2.5 rounded-full" style={{
              backgroundColor: cfg.color
            }} />
              <span>{(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(cfg.name)}</span>
            </button>)}
        </div>
        <span className="text-[11px] text-[var(--ui-muted)] italic">
          {" Rê chuột trên biểu đồ để đối chiếu đơn giá từng quý "}
        </span>
      </div>
      <p className="price-data-note">Lịch sử giá tham khảo cấu hình sẵn; chưa được đối chiếu với dữ liệu giao dịch đã kiểm chứng.</p>
      <div className="chart-canvas relative">
      <div className="chart-scroll relative w-full overflow-x-auto mt-2">
        <div className="min-w-[680px]">
          <svg viewBox={`0 0 ${view.svgWidth} ${view.svgHeight}`} className="w-full h-auto overflow-visible select-none">
            <defs>
              {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.chartMetrics.series, s => <linearGradient key={"grad-" + s.key} id={"grad-" + s.key} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={s.color} stopOpacity="0.14" />
                  <stop offset="100%" stopColor={s.color} stopOpacity="0.0" />
                </linearGradient>)}
            </defs>
            <g className="grid-lines">
              {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.chartMetrics.yTicks, tick => <React.Fragment key={tick.y}>
                  <line x1={view.padding.left} y1={tick.y} x2={view.svgWidth - view.padding.right} y2={tick.y} stroke="var(--ui-border)" strokeWidth="1" strokeDasharray="4,4" />
                  <text x={view.padding.left - 14} y={tick.y + 4} textAnchor="end" className="text-[11px] fill-[var(--ui-muted)] font-semibold">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(tick.value)}
                  </text>
                </React.Fragment>)}
            </g>
            {view.hoveredIndex !== null ? <React.Fragment>
                {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.chartMetrics.series, s => <line key={"guide-" + s.key} x1={s.points[view.hoveredIndex].x} y1={view.padding.top} x2={s.points[view.hoveredIndex].x} y2={view.svgHeight - view.padding.bottom} stroke="var(--ui-chart-2)" strokeWidth="1.5" strokeDasharray="3,3" style={{
                display: s.isVisible && s.points[view.hoveredIndex] ? undefined : "none"
              }} />)}
              </React.Fragment> : null}
            {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.chartMetrics.series, s => <g key={s.key}>
                {s.isVisible && s.areaD ? <path d={s.areaD} fill={`url(#grad-${s.key})`} className="transition-all duration-300" /> : null}
                {s.isVisible && s.pathD ? <path d={s.pathD} fill="none" stroke={s.color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="transition-all duration-300" /> : null}
              </g>)}
            {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.filteredLabels, (lbl, idx) => <g key={idx}>
                <text x={view.padding.left + idx / Math.max(1, view.filteredLabels.length - 1) * (view.svgWidth - view.padding.left - view.padding.right)} y={view.svgHeight - 12} textAnchor="middle" className={classNames(["text-[11px] font-semibold transition", view.hoveredIndex === idx ? "fill-[var(--ui-accent)] font-bold" : "fill-[var(--ui-muted)]"])}>
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(lbl)}
                </text>
                <rect tabIndex={0} role="button" aria-describedby={view.hoveredIndex === idx ? "market-price-tooltip" : undefined} aria-label={"Xem đơn giá " + lbl} onFocus={() => view.updateHoveredIndexValue(idx)} onBlur={() => view.updateHoveredIndexValue(null)} x={view.padding.left + idx / Math.max(1, view.filteredLabels.length - 1) * (view.svgWidth - view.padding.left - view.padding.right) - 25} y={view.padding.top} width="50" height={view.svgHeight - view.padding.top - view.padding.bottom} fill="transparent" className="cursor-pointer" onMouseEnter={$event => {
                view.updateHoveredIndexValue(idx);
              }} onMouseLeave={$event => {
                view.updateHoveredIndexValue(null);
              }} />
                {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.chartMetrics.series, s => <React.Fragment key={s.key}>
                    {s.isVisible && s.points[idx] ? <circle cx={s.points[idx].x} cy={s.points[idx].y} r={view.hoveredIndex === idx ? 6.5 : 4} fill="var(--ui-surface)" stroke={s.color} strokeWidth={view.hoveredIndex === idx ? 3.5 : 2.5} className="transition-all duration-150 pointer-events-none" /> : null}
                  </React.Fragment>)}
              </g>)}
          </svg>
        </div>
      </div>
          {view.hoveredIndex !== null ? <div id="market-price-tooltip" role="tooltip" className="chart-tooltip absolute pointer-events-none z-20 transition-all duration-100" style={{
            "--tooltip-x": `${Math.min(78, Math.max(12, view.hoveredIndex / Math.max(1, view.filteredLabels.length - 1) * 100))}%`,
            top: "14px"
          }}>
              <div className="bg-[var(--ui-soft)]/95 backdrop-blur-md text-brand-navy p-4 rounded-2xl shadow-xl border border-[var(--ui-border)]/35 text-xs min-w-[220px]">
                <p className="font-bold text-[var(--ui-ink)] pb-2 mb-2.5 border-b border-brand-line/12 flex items-center justify-between gap-4">
                  <span>
                    {"Kỳ thống kê: "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.filteredLabels[view.hoveredIndex])}
                  </span>
                  <span className="text-[10px] text-[var(--ui-success-text)] font-semibold uppercase tracking-wider">
                    {"Chuẩn hóa"}
                  </span>
                </p>
                <div className="space-y-2">
                  {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.chartMetrics.series, s => <div key={s.key} className="flex items-center justify-between gap-4" style={{
                  display: s.isVisible && s.points[view.hoveredIndex] ? undefined : "none"
                }}>
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full border border-brand-line/40" style={{
                      backgroundColor: s.color
                    }} />
                        <span className="text-brand-navy/80">
                          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(s.name)}
                        </span>
                      </div>
                      <span className="font-bold text-brand-navy">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(s.points[view.hoveredIndex].value)}
                        {" tr/m²"}
                      </span>
                    </div>)}
                </div>
              </div>
            </div> : null}
      </div>
    </div></>;
});
