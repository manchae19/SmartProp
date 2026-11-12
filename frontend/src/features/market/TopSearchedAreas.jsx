import { classNames, chainHandlers } from "../../shared/lib/ui.js";
import React, { useRef } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { useAppNavigation } from "../../app/navigation.jsx";
import { DISTRICT_PROFILES } from "./marketData.js";
function useTopSearchedAreasState(inputProps, forwardedRef) {
  inputProps = {
    currentSlug: "",
    eyebrow: "XU HƯỚNG TÌM KIẾM · ĐÀ NẴNG",
    mode: "market",
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    currentSlug: "",
    eyebrow: "XU HƯỚNG TÌM KIẾM · ĐÀ NẴNG",
    mode: "market",
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const router = useAppNavigation();

  // Ordered by search popularity (viewsCount)
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  const getOrderedDistricts = () => {
    const all = [DISTRICT_PROFILES["Sơn Trà"], DISTRICT_PROFILES["Hải Châu"], DISTRICT_PROFILES["Ngũ Hành Sơn"], DISTRICT_PROFILES["Liên Chiểu"], DISTRICT_PROFILES["Cẩm Lệ"], DISTRICT_PROFILES["Thanh Khê"]].filter(Boolean);

    // If currentSlug is provided and matches one of the top 5, we can either keep Top 5 or rotate so all 5 other districts show
    if (_props.current.currentSlug) {
      const others = all.filter(d => d.slug !== _props.current.currentSlug);
      if (others.length === 5) return others;
    }
    return all.slice(0, 5);
  };
  const getFeaturedDistrict = () => getOrderedDistricts()[0] || null;
  const getSecondaryDistricts = () => getOrderedDistricts().slice(1, 5);
  function handleSelect(district) {
    _propsLatest.current.onSelectDistrict?.(district.slug);
    if (_props.current.mode === "listings") {
      _routerLatest.current.push({
        path: "/listings",
        query: {
          district: district.shortName
        }
      });
    } else {
      _routerLatest.current.push({
        path: `/market/${district.slug}`
      });
      window.scrollTo({
        top: 0,
        behavior: "smooth"
      });
    }
  }
  return {
    ...inputProps,
    featuredDistrict: getFeaturedDistrict(),
    secondaryDistricts: getSecondaryDistricts(),
    handleSelect,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["currentSlug", "eyebrow", "mode", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function TopSearchedAreas(props, ref) {
  const view = useTopSearchedAreasState(props, ref);
  return <><div {...view.rootAttributes} className={classNames(["top-searched-areas", view.rootAttributes.className])}>
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--ui-accent)] mb-2">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.eyebrow)}
          </p>
          <h2 className="text-2xl sm:text-3xl font-semibold text-[var(--ui-accent)] tracking-tight">
            {" Khu vực được tìm kiếm "}
            <span className="text-[var(--ui-accent)]">
              {"nhiều nhất."}
            </span>
          </h2>
        </div>
        <SiteLink to="/listings" className="inline-flex items-center gap-2 text-xs font-bold text-[var(--ui-accent)] hover:text-[var(--ui-accent)] transition self-start sm:self-auto">
          <span>{"Khám phá toàn bộ tin đăng Đà Nẵng"}</span>
          <span aria-hidden="true">
            {"→"}
          </span>
        </SiteLink>
      </div>
      {view.featuredDistrict ? <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
          <article onClick={$event => {
          view.handleSelect(view.featuredDistrict);
        }} role="button" tabIndex="0" onKeyDown={chainHandlers($event => {
          if ($event.key !== "Enter") return;
          $event.preventDefault();
          view.handleSelect(view.featuredDistrict);
        }, $event => {
          if ($event.key !== " ") return;
          $event.preventDefault();
          view.handleSelect(view.featuredDistrict);
        })} aria-label={`${view.featuredDistrict.name}, Đà Nẵng - ${view.featuredDistrict.viewsCount} lượt xem`} className="lg:col-span-6 relative min-h-[340px] sm:min-h-[400px] lg:h-[468px] rounded-[22px] overflow-hidden cursor-pointer group shadow-md border border-[var(--ui-border)] select-none">
            <img src={view.featuredDistrict.image} alt={view.featuredDistrict.name} loading="lazy" className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-105" />
            <div className="absolute inset-0 bg-gradient-to-t from-[var(--ui-soft)]/90 via-[var(--ui-soft)]/25 to-brand-cream/15 transition-opacity duration-300 group-hover:from-[var(--ui-soft)]/95" aria-hidden="true" />
            <div className="absolute top-4 left-4 z-10 flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-[var(--ui-surface)]/95 backdrop-blur-md text-[var(--ui-ink)] text-xs font-bold shadow-md border border-[var(--ui-border)]">
                <svg className="size-3.5 text-[var(--ui-muted)] shrink-0" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 23c-4.97 0-9-3.58-9-8 0-3.19 2.13-6.02 4.5-7.86.37-.29.91-.03.91.44 0 1.18.47 2.26 1.29 3.01.29.27.76.11.83-.28.36-2.06 1.68-4.58 4.13-6.15.39-.25.9.06.86.52-.12 1.46.38 2.86 1.38 3.92 2.41 2.55 4.1 5.13 4.1 8.4 0 4.42-4.03 8-9 8z" />
                </svg>
                <span>
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.featuredDistrict.viewsCount)}
                  {" lượt xem"}
                </span>
              </span>
            </div>
            <div className="absolute top-4 right-4 z-10">
              <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-[var(--ui-soft)]/85 backdrop-blur-md text-[var(--ui-ink)] text-xs font-bold border border-[var(--ui-border)]/35">
                <span>
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.featuredDistrict.macro.avgPricePerM2)}
                </span>
                <span className="text-[var(--ui-success-text)] ml-1">
                  {"▲ "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.featuredDistrict.macro.priceGrowthYoY)}
                </span>
              </span>
            </div>
            <div className="absolute inset-x-0 bottom-0 p-6 sm:p-7 z-10 flex items-end justify-between gap-4">
              <div>
                <h3 className="text-2xl sm:text-[26px] font-bold text-brand-navy tracking-tight leading-tight group-hover:text-[var(--ui-ink)] transition-colors">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.featuredDistrict.name)}
                  {", Đà Nẵng "}
                </h3>
                <p className="text-xs sm:text-sm text-brand-navy/90 font-medium mt-1.5">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.featuredDistrict.activeListingsCount)}
                  {" bất động sản đang bán "}
                </p>
              </div>
              <span className="w-10 h-10 rounded-full bg-brand-card/15 backdrop-blur-md border border-brand-line/25 text-brand-navy flex items-center justify-center group-hover:bg-[var(--ui-soft)] group-hover:text-[var(--ui-accent)] group-hover:border-[var(--ui-border)] transition-all shrink-0">
                {" ↗ "}
              </span>
            </div>
          </article>
          <div className="lg:col-span-6 grid grid-cols-1 sm:grid-cols-2 gap-5">
            {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.secondaryDistricts, item => <article key={item.id} onClick={$event => {
            view.handleSelect(item);
          }} role="button" tabIndex="0" onKeyDown={chainHandlers($event => {
            if ($event.key !== "Enter") return;
            $event.preventDefault();
            view.handleSelect(item);
          }, $event => {
            if ($event.key !== " ") return;
            $event.preventDefault();
            view.handleSelect(item);
          })} aria-label={`${item.name}, Đà Nẵng - ${item.viewsCount} lượt xem`} className="relative h-[224px] rounded-[20px] overflow-hidden cursor-pointer group shadow-sm border border-[var(--ui-border)] select-none">
                <img src={item.image} alt={item.name} loading="lazy" className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-105" />
                <div className="absolute inset-0 bg-gradient-to-t from-[var(--ui-soft)]/90 via-[var(--ui-soft)]/25 to-brand-cream/10 transition-opacity duration-300 group-hover:from-[var(--ui-soft)]/95" aria-hidden="true" />
                <div className="absolute top-3.5 left-3.5 z-10">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-[var(--ui-surface)]/95 backdrop-blur-md text-[var(--ui-ink)] text-[11px] font-bold shadow-sm border border-[var(--ui-border)]">
                    <svg className="size-3 text-[var(--ui-muted)] shrink-0" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 23c-4.97 0-9-3.58-9-8 0-3.19 2.13-6.02 4.5-7.86.37-.29.91-.03.91.44 0 1.18.47 2.26 1.29 3.01.29.27.76.11.83-.28.36-2.06 1.68-4.58 4.13-6.15.39-.25.9.06.86.52-.12 1.46.38 2.86 1.38 3.92 2.41 2.55 4.1 5.13 4.1 8.4 0 4.42-4.03 8-9 8z" />
                    </svg>
                    <span>
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.viewsCount)}
                      {" lượt xem"}
                    </span>
                  </span>
                </div>
                <div className="absolute top-3.5 right-3.5 z-10">
                  <span className="px-2.5 py-1 rounded-lg bg-[var(--ui-soft)]/80 backdrop-blur-md text-[var(--ui-ink)] text-[10px] font-bold border border-brand-line/15">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.macro.avgPricePerM2)}
                  </span>
                </div>
                <div className="absolute inset-x-0 bottom-0 p-4 sm:p-5 z-10 flex items-end justify-between gap-2">
                  <div>
                    <h3 className="text-base sm:text-[17px] font-bold text-brand-navy tracking-tight leading-snug group-hover:text-[var(--ui-ink)] transition-colors">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.name)}
                      {", Đà Nẵng "}
                    </h3>
                    <p className="text-xs text-brand-navy/85 font-medium mt-0.5">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.activeListingsCount)}
                      {" bất động sản đang bán "}
                    </p>
                  </div>
                  <span className="w-8 h-8 rounded-full bg-brand-card/15 backdrop-blur-md border border-brand-line/20 text-brand-navy text-xs flex items-center justify-center group-hover:bg-[var(--ui-soft)] group-hover:text-[var(--ui-accent)] transition-all shrink-0">
                    {" ↗ "}
                  </span>
                </div>
              </article>)}
          </div>
        </div> : null}
    </div></>;
});
