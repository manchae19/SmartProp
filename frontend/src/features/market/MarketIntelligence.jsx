import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
function useMarketIntelligenceState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  // Dữ liệu giả lập để trình diễn giao diện; chưa kết nối API thị trường.
  const [marketType] = useState(() => createStateStore("Tất cả"));
  useSyncExternalStore(marketType.subscribe, marketType.getSnapshot);
  const [marketPeriod] = useState(() => createStateStore(12));
  useSyncExternalStore(marketPeriod.subscribe, marketPeriod.getSnapshot);
  const marketTypes = [{
    name: "Căn hộ",
    color: "#8BB5CA",
    values: [36, 37, 38, 37, 39, 40, 41, 40, 42, 43, 44, 46]
  }, {
    name: "Nhà phố",
    color: "#a5dbdc",
    values: [54, 55, 54, 57, 58, 59, 61, 60, 62, 65, 66, 68]
  }, {
    name: "Đất nền",
    color: "#9ABFAE",
    values: [42, 43, 42, 44, 45, 44, 46, 48, 47, 49, 50, 52]
  }];
  const marketDistrictData = [{
    name: "Hải Châu",
    prices: {
      "Căn hộ": 52,
      "Nhà phố": 80,
      "Đất nền": 60
    }
  }, {
    name: "Sơn Trà",
    prices: {
      "Căn hộ": 48,
      "Nhà phố": 69,
      "Đất nền": 54
    }
  }, {
    name: "Ngũ Hành Sơn",
    prices: {
      "Căn hộ": 44,
      "Nhà phố": 61,
      "Đất nền": 49
    }
  }, {
    name: "Cẩm Lệ",
    prices: {
      "Căn hộ": 32,
      "Nhà phố": 48,
      "Đất nền": 38
    }
  }];
  const getVisibleMarketSeries = () => marketType.getSnapshot() === "Tất cả" ? marketTypes : marketTypes.filter(item => item.name === marketType.getSnapshot());
  const getMarketSummary = () => {
    const series = getVisibleMarketSeries();
    const first = series.reduce((sum, item) => sum + item.values[12 - marketPeriod.getSnapshot()], 0) / series.length;
    const last = series.reduce((sum, item) => sum + item.values[11], 0) / series.length;
    return {
      price: last,
      change: (last - first) / first * 100
    };
  };
  const getMarketDistricts = () => marketDistrictData.map(item => ({
    name: item.name,
    price: marketType.getSnapshot() === "Tất cả" ? Object.values(item.prices).reduce((sum, price) => sum + price, 0) / 3 : item.prices[marketType.getSnapshot()]
  })).sort((a, b) => b.price - a.price);
  const getMarketChart = () => {
    const start = 12 - marketPeriod.getSnapshot();
    const series = getVisibleMarketSeries();
    const values = series.flatMap(item => item.values.slice(start));
    const low = Math.floor((Math.min(...values) - 5) / 10) * 10;
    const high = Math.ceil((Math.max(...values) + 5) / 10) * 10;
    const x = index => 52 + index * 650 / (marketPeriod.getSnapshot() - 1);
    const y = value => 245 - (value - low) / (high - low) * 205;
    return {
      lines: series.map(item => ({
        name: item.name,
        color: item.color,
        points: item.values.slice(start).map((value, index) => `${x(index)},${y(value)}`).join(" "),
        latest: item.values[11]
      })),
      grid: Array.from({
        length: 5
      }, (_, i) => ({
        value: low + (high - low) * i / 4,
        y: y(low + (high - low) * i / 4)
      })),
      labels: Array.from({
        length: marketPeriod.getSnapshot()
      }, (_, i) => ({
        text: `T${start + i + 1}`,
        x: x(i)
      }))
    };
  };
  return {
    ...inputProps,
    marketType: marketType.getSnapshot(),
    marketPeriod: marketPeriod.getSnapshot(),
    marketSummary: getMarketSummary(),
    marketDistricts: getMarketDistricts(),
    marketChart: getMarketChart(),
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateMarketTypeValue: marketType.set,
    updateMarketPeriodValue: marketPeriod.set
  };
}
export default React.forwardRef(function MarketIntelligence(props, ref) {
  const view = useMarketIntelligenceState(props, ref);
  return <><section id="market-demo" aria-labelledby="market-heading" {...view.rootAttributes} className={classNames(["bg-[var(--ui-surface)] py-14 text-[var(--ui-accent)] md:py-20", view.rootAttributes.className])}>
      <div className="mx-auto max-w-7xl px-5 lg:px-8">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="mb-3 text-xs font-bold uppercase tracking-[0.3em] text-[var(--ui-accent)]">
              {" Market Intelligence "}
            </p>
            <h2 id="market-heading" className="text-3xl font-semibold leading-tight sm:text-4xl md:text-5xl">
              {" Dữ liệu kể "}
              <span className="text-[var(--ui-accent)]">
                {"câu chuyện thị trường."}
              </span>
            </h2>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-[var(--ui-accent)]">
              {" Khám phá xu hướng giá căn hộ, nhà phố và đất nền tại Đà Nẵng. "}
              <span className="ml-1 inline-block font-semibold text-[var(--ui-accent)]">
                {"Dữ liệu mô phỏng."}
              </span>
            </p>
          </div>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Lọc loại hình bất động sản">
            {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(["Tất cả", "Căn hộ", "Nhà phố", "Đất nền"], item => <button key={item} type="button" onClick={$event => {
              view.updateMarketTypeValue(item);
            }} aria-pressed={view.marketType === item} className={classNames(["cursor-pointer rounded-full border px-4 py-2.5 text-xs font-bold transition focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--ui-border)]", view.marketType === item ? "border-[var(--ui-border)] bg-[var(--ui-soft)] text-brand-navy" : "border-[var(--ui-border)] bg-brand-card text-[var(--ui-accent)] hover:border-[var(--ui-border)]"])}>
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item)}
              </button>)}
          </div>
        </div>
        <div className="mt-9 grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-[var(--ui-border)] bg-brand-card p-6">
            <p className="text-xs font-semibold text-[var(--ui-accent)]">
              {" Giá trung bình theo loại hình "}
            </p>
            <p className="mt-3 text-3xl font-bold text-[var(--ui-accent)]">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.marketSummary.price.toFixed(1))}{" "}
              <span className="text-sm font-medium">
                {"triệu/m²"}
              </span>
            </p>
          </div>
          <div className="rounded-2xl border border-[var(--ui-border)] bg-brand-card p-6">
            <p className="text-xs font-semibold text-[var(--ui-accent)]">
              {" Biến động trong kỳ "}
            </p>
            <p className={classNames(["mt-3 text-3xl font-bold", view.marketSummary.change >= 0 ? "text-[var(--ui-success-text)]" : "text-[var(--ui-error-text)]"])}>
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.marketSummary.change >= 0 ? "+" : "")}
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.marketSummary.change.toFixed(1))}
              {"% "}
            </p>
          </div>
          <div className="rounded-2xl border border-[var(--ui-border)] bg-brand-card p-6">
            <p className="text-xs font-semibold text-[var(--ui-accent)]">
              {" Phạm vi phân tích "}
            </p>
            <p className="mt-3 text-3xl font-bold text-[var(--ui-accent)]">
              {" 4 "}
              <span className="text-sm font-medium">
                {"khu vực"}
              </span>
            </p>
          </div>
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.65fr)_minmax(0,1fr)]">
          <div className="min-w-0 rounded-3xl border border-[var(--ui-border)] bg-brand-card p-5 shadow-sm md:p-7">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="text-xl font-bold">
                  {" Xu hướng giá theo loại hình "}
                </h3>
                <p className="mt-1 text-xs text-[var(--ui-accent)]">
                  {" Đơn vị: triệu đồng/m² "}
                </p>
              </div>
              <div className="flex gap-2" role="group" aria-label="Khoảng thời gian thống kê">
                {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))([3, 6, 12], period => <button key={period} type="button" onClick={$event => {
                  view.updateMarketPeriodValue(period);
                }} aria-pressed={view.marketPeriod === period} className={classNames(["cursor-pointer rounded-full px-3 py-2.5 text-xs font-bold transition focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--ui-border)]", view.marketPeriod === period ? "bg-[var(--ui-soft)] text-[var(--ui-accent)]" : "bg-[var(--ui-surface)] text-[var(--ui-accent)] hover:bg-[var(--ui-surface)]"])}>
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(period)}
                    {" tháng "}
                  </button>)}
              </div>
            </div>
            <div className="mt-6 w-full overflow-x-auto overscroll-x-contain">
              <svg viewBox="0 0 750 295" role="img" aria-label="Biểu đồ đường xu hướng giá bất động sản minh họa" className="block w-full min-w-[420px]">
                {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.marketChart.grid, tick => <g key={tick.value}>
                    <line x1="52" y1={tick.y} x2="702" y2={tick.y} stroke="#d3e4e9" strokeDasharray="4 5" />
                    <text x="43" y={tick.y + 4} textAnchor="end" fill="#64748B" fontSize="12">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(tick.value.toFixed(0))}
                    </text>
                  </g>)}
                {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.marketChart.labels, label => <g key={label.text}>
                    <text x={label.x} y="275" textAnchor="middle" fill="#64748B" fontSize="12">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(label.text)}
                    </text>
                  </g>)}
                {((items, render) => typeof items === "number" ? Array.from({
                  length: Math.max(0, items)
                }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.marketChart.lines, line => <polyline key={line.name} points={line.points} fill="none" stroke={line.color} strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />)}
              </svg>
            </div>
            <div className="mt-3 flex flex-wrap gap-x-6 gap-y-3">
              {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.marketChart.lines, line => <div key={line.name} className="flex items-center gap-2 text-xs text-[var(--ui-accent)]">
                  <span className="h-2.5 w-2.5 rounded-full" style={{
                  backgroundColor: line.color
                }} />
                  <span>
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(line.name)}
                    {": "}
                    <strong className="text-[var(--ui-accent)]">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(line.latest)}
                      {" triệu/m² "}
                    </strong>
                  </span>
                </div>)}
            </div>
          </div>
          <div className="rounded-3xl bg-[var(--ui-soft)] p-6 text-brand-navy shadow-sm md:p-8">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-ink)]">
              {" District Comparison "}
            </p>
            <h3 className="mt-3 text-2xl font-semibold">
              {" Giá theo khu vực "}
            </h3>
            <p className="mt-2 text-xs leading-6 text-brand-navy/60">
              {" Giá trung bình tham khảo · triệu đồng/m² "}
            </p>
            <div className="mt-7 space-y-6">
              {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.marketDistricts, district => <div key={district.name}>
                  <div className="mb-2 flex items-center justify-between gap-3 text-sm">
                    <span className="font-medium">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(district.name)}
                    </span>
                    <span className="font-bold text-[var(--ui-ink)]">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(district.price.toFixed(1))}
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-brand-card/15">
                    <div className="h-full rounded-full bg-[var(--ui-soft)] transition-all duration-300" style={{
                    width: `${district.price / 90 * 100}%`
                  }} />
                  </div>
                </div>)}
            </div>
            <p className="mt-8 border-t border-brand-line/15 pt-5 text-xs leading-6 text-brand-navy/60">
              {" Dữ liệu mô phỏng phục vụ trình diễn giao diện, không phải báo cáo giá thực tế hay tư vấn đầu tư. "}
            </p>
          </div>
        </div>
      </div>
    </section></>;
});
