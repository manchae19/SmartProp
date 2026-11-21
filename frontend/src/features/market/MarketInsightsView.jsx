import { classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { useRouteState, useAppNavigation } from "../../app/navigation.jsx";
import { api } from "../auth/api.js";
import { DISTRICT_PROFILES, DISTRICT_LIST, getDistrictProfile } from "./marketData.js";
import { useComparison } from "../../shared/hooks/useComparison.js";
import PriceTrendChart from "./PriceTrendChart.jsx";
import BrowseTileMap from "../map/BrowseTileMap.jsx";
import ListingCard from "../property/ListingCard.jsx";
import TopSearchedAreas from "./TopSearchedAreas.jsx";
import "./MarketInsightsView.css";
function useMarketInsightsViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const route = useRouteState();
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  const router = useAppNavigation();
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  const compare = useComparison();

  // District selection
  const _compareLatest = useRef(compare);
  _compareLatest.current = compare;
  const [selectedDistrictSlug] = useState(() => createStateStore(_routeLatest.current.params.district || "son-tra"));
  useSyncExternalStore(selectedDistrictSlug.subscribe, selectedDistrictSlug.getSnapshot);
  const getCurrentDistrict = () => getDistrictProfile(selectedDistrictSlug.getSnapshot());
  function selectDistrict(slug) {
    selectedDistrictSlug.set(slug);
    _routerLatest.current.push({
      path: `/market/${slug}`
    });
  }
  const _watched = (() => _routeLatest.current.params.district)();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    if (!_initialized.current) {
      _initialized.current = true;
      return;
    }
    const result = (newSlug => {
      if (newSlug) selectedDistrictSlug.set(newSlug);
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);

  // Dynamic unit prices from district history
  const getLatestHousePrice = () => {
    const arr = getCurrentDistrict()?.priceHistory?.house || [];
    return arr.length ? `${arr[arr.length - 1]},0 triệu/m²` : "145,0 triệu/m²";
  };
  const getLatestApartmentPrice = () => {
    const arr = getCurrentDistrict()?.priceHistory?.apartment || [];
    return arr.length ? `${arr[arr.length - 1]},0 triệu/m²` : "62,0 triệu/m²";
  };

  // Real-time properties from database
  const [properties] = useState(() => createStateStore([]));
  useSyncExternalStore(properties.subscribe, properties.getSnapshot);
  const [loadingProperties] = useState(() => createStateStore(false));
  useSyncExternalStore(loadingProperties.subscribe, loadingProperties.getSnapshot);
  const [selectedMapPropertyId] = useState(() => createStateStore(null));
  useSyncExternalStore(selectedMapPropertyId.subscribe, selectedMapPropertyId.getSnapshot);
  async function fetchDistrictProperties() {
    loadingProperties.set(true);
    try {
      const districtName = getCurrentDistrict().shortName;
      const res = await api(`/properties?district=${encodeURIComponent(districtName)}&size=6&limit=8`, {
        authenticated: false
      });
      const items = Array.isArray(res) ? res : res?.items || [];
      properties.set(items);
      selectedMapPropertyId.set(items.find(p => Number.isFinite(Number(p.latitude)) && Number.isFinite(Number(p.longitude)))?.id || null);
    } catch (e) {
      properties.set([]);
      selectedMapPropertyId.set(null);
    } finally {
      loadingProperties.set(false);
    }
  }
  const _watched2 = (() => getCurrentDistrict().id)();
  const _previous2 = useRef(_watched2),
    _initialized2 = useRef(false);
  useEffect(() => {
    const previousValue = _previous2.current;
    _previous2.current = _watched2;
    let dispose;
    _initialized2.current = true;
    const result = (() => {
      fetchDistrictProperties();
    })(_watched2, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched2)]);

  // Points for BrowseTileMap
  const getMapPoints = () => {
    return properties.getSnapshot().filter(p => Number.isFinite(Number(p.latitude)) && Number.isFinite(Number(p.longitude))).map(p => ({
      id: p.id,
      latitude: Number(p.latitude),
      longitude: Number(p.longitude),
      price: p.price,
      priceExact: p.priceExact,
      priceUnit: p.priceUnit,
      transactionType: p.transactionType,
      title: p.title
    }));
  };
  function focusOnDistrictMap(propertyId) {
    selectedMapPropertyId.set(propertyId);
    scrollToSection("overview");
  }

  // In-page navigation tabs
  const [activeSection] = useState(() => createStateStore("overview"));
  useSyncExternalStore(activeSection.subscribe, activeSection.getSnapshot);
  const inPageTabs = [{
    id: "overview",
    number: "01",
    label: "Tổng quan & GIS"
  }, {
    id: "planning",
    number: "02",
    label: "Quy hoạch hạ tầng"
  }, {
    id: "price-trend",
    number: "03",
    label: "Biến động đơn giá"
  }, {
    id: "listings",
    number: "04",
    label: "Bất động sản mở bán"
  }, {
    id: "neighboring",
    number: "05",
    label: "Khu vực tìm kiếm nhiều"
  }];
  function scrollToSection(id) {
    activeSection.set(id);
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
    }
  }
  const _sectionObserverRef = useRef(null);
  useEffect(() => {
    const result = (() => {
      if (typeof IntersectionObserver === "undefined") return;
      _sectionObserverRef.current = new IntersectionObserver(entries => {
        const visible = entries.filter(e => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]?.target?.id) {
          activeSection.set(visible[0].target.id);
        }
      }, {
        rootMargin: "-20% 0px -60% 0px",
        threshold: [0.05, 0.25, 0.5]
      });
      for (const tab of inPageTabs) {
        const el = document.getElementById(tab.id);
        if (el) _sectionObserverRef.current.observe(el);
      }
    })();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  useEffect(() => () => (() => {
    _sectionObserverRef.current?.disconnect();
  })(), []);

  // Accordion toggle state for planning section
  const [expandedPanels] = useState(() => createStateStore({
    planning1: true,
    planning2: true,
    planning3: false
  }));
  useSyncExternalStore(expandedPanels.subscribe, expandedPanels.getSnapshot);
  function togglePanel(panelKey) {
    expandedPanels.edit(draftValue => draftValue[panelKey] = !expandedPanels.getSnapshot()[panelKey]);
  }
  function handleBack() {
    if (window.history.length > 1) {
      _routerLatest.current.back();
    } else {
      _routerLatest.current.push("/listings");
    }
  }
  return {
    ...inputProps,
    DISTRICT_PROFILES,
    DISTRICT_LIST,
    router,
    compare,
    currentDistrict: getCurrentDistrict(),
    selectDistrict,
    latestHousePrice: getLatestHousePrice(),
    latestApartmentPrice: getLatestApartmentPrice(),
    properties: properties.getSnapshot(),
    loadingProperties: loadingProperties.getSnapshot(),
    selectedMapPropertyId: selectedMapPropertyId.getSnapshot(),
    mapPoints: getMapPoints(),
    focusOnDistrictMap,
    activeSection: activeSection.getSnapshot(),
    inPageTabs,
    scrollToSection,
    expandedPanels: expandedPanels.getSnapshot(),
    togglePanel,
    handleBack,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function MarketInsightsView(props, ref) {
  const view = useMarketInsightsViewState(props, ref);
  return <><div data-ui-view="MarketInsightsView" data-sp-f9d979a0="" {...view.rootAttributes} className={classNames(["market-luxury min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)] antialiased selection:bg-[var(--ui-soft)] selection:text-[var(--ui-ink)] pb-20", view.rootAttributes.className])}>
      <div className="max-w-[1280px] mx-auto px-5 sm:px-8 pt-6" data-sp-f9d979a0="">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6" data-sp-f9d979a0="">
          <div className="flex items-center gap-3" data-sp-f9d979a0="">
            <button type="button" onClick={$event => {
              return view.handleBack?.($event);
            }} className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-card text-[var(--ui-accent)] border border-[var(--ui-border)] shadow-2xs hover:bg-[var(--ui-surface)] hover:border-[var(--ui-border)] transition-all cursor-pointer text-xs font-bold group" data-sp-f9d979a0="">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" className="transition-transform group-hover:-translate-x-0.5" data-sp-f9d979a0="">
                <line x1="19" y1="12" x2="5" y2="12" data-sp-f9d979a0="" />
                <polyline points="12 19 5 12 12 5" data-sp-f9d979a0="" />
              </svg>
              <span data-sp-f9d979a0="">
                {"Quay lại"}
              </span>
            </button>
            <nav aria-label="Breadcrumb" className="hidden sm:inline-flex items-center gap-2.5 px-4 py-2 rounded-full bg-brand-card border border-[var(--ui-border)] text-xs font-medium text-[var(--ui-accent)]" data-sp-f9d979a0="">
              <SiteLink to="/" className="hover:text-[var(--ui-accent)] transition" data-sp-f9d979a0="">
                {"Trang chủ"}
              </SiteLink>
              <span className="text-[var(--ui-ink)]" data-sp-f9d979a0="">
                {"/"}
              </span>
              <SiteLink to="/market" className="hover:text-[var(--ui-accent)] transition" data-sp-f9d979a0="">
                {"Dữ liệu thị trường"}
              </SiteLink>
              <span className="text-[var(--ui-ink)]" data-sp-f9d979a0="">
                {"/"}
              </span>
              <span className="text-[var(--ui-accent)] font-bold flex items-center gap-1.5" data-sp-f9d979a0="">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--ui-soft)]" data-sp-f9d979a0="" />{" "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.name)}
              </span>
            </nav>
          </div>
          <div className="flex items-center gap-2.5" data-sp-f9d979a0="">
            <SiteLink to={{
              path: "/listings",
              query: {
                district: view.currentDistrict.shortName
              }
            }} className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-card border border-[var(--ui-border)] hover:border-[var(--ui-border)] text-xs font-bold text-[var(--ui-accent)] transition" data-sp-f9d979a0="">
              <span data-sp-f9d979a0="">
                {"Tin đăng "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.shortName)}
              </span>
              <span aria-hidden="true" data-sp-f9d979a0="">
                {"↗"}
              </span>
            </SiteLink>
            <SiteLink to="/advisor" className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[var(--ui-soft)] text-[var(--ui-ink)] hover:bg-[var(--ui-soft)] text-xs font-bold transition shadow-xs" data-sp-f9d979a0="">
              <span data-sp-f9d979a0="">
                {"Tư vấn đầu tư AI"}
              </span>
              <span aria-hidden="true" data-sp-f9d979a0="">
                {"→"}
              </span>
            </SiteLink>
          </div>
        </div>
        <section className="market-intro-banner relative overflow-hidden rounded-[28px] bg-gradient-to-br from-[var(--ui-soft)] via-[var(--ui-soft)] to-[var(--ui-soft)] text-brand-navy p-7 sm:p-10 lg:p-12 border border-[var(--ui-border)]/30 shadow-xl" data-sp-f9d979a0="">
          <div className="pointer-events-none absolute -right-20 -top-20 h-80 w-80 rounded-full bg-[var(--ui-soft)]/8 blur-3xl" aria-hidden="true" data-sp-f9d979a0="" />
          <div className="pointer-events-none absolute -bottom-24 left-1/3 h-64 w-64 rounded-full bg-[var(--ui-soft)]/10 blur-3xl" aria-hidden="true" data-sp-f9d979a0="" />
          <div className="relative z-10 flex flex-col lg:flex-row lg:items-end justify-between gap-8 pb-8 border-b border-brand-line/12" data-sp-f9d979a0="">
            <div className="max-w-3xl" data-sp-f9d979a0="">
              <div className="inline-flex items-center gap-2.5 text-xs font-bold uppercase tracking-[0.24em] text-[var(--ui-ink)] mb-3" data-sp-f9d979a0="">
                <span data-sp-f9d979a0="">
                  {"⌖"}
                </span>
                <span data-sp-f9d979a0="">
                  {"SMARTPROP MARKET INTELLIGENCE · ĐÀ NẴNG"}
                </span>
              </div>
              <h1 className="text-3xl sm:text-4xl lg:text-[46px] font-semibold tracking-tight leading-[1.14] text-brand-navy" data-sp-f9d979a0="">
                {" Báo cáo thị trường "}
                <span className="text-[var(--ui-ink)] block sm:inline" data-sp-f9d979a0="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.name)}
                  {"."}
                </span>
              </h1>
              <p className="text-sm sm:text-[15px] text-brand-navy/80 mt-3.5 leading-relaxed max-w-2xl" data-sp-f9d979a0="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.tagline)}
              </p>
            </div>
            <div className="flex flex-wrap sm:flex-nowrap items-stretch gap-3 shrink-0" data-sp-f9d979a0="">
              <div className="market-hero-metric px-5 py-4 min-w-[165px]" data-sp-f9d979a0="">
                <p className="text-[11px] uppercase tracking-wider text-brand-navy/65 font-semibold" data-sp-f9d979a0="">
                  {"Đơn giá TB Đất nền"}
                </p>
                <p className="text-xl sm:text-2xl font-bold text-[var(--ui-ink)] mt-1 tracking-tight" data-sp-f9d979a0="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.macro.avgPricePerM2)}
                </p>
                <p className="text-[11px] text-[var(--ui-success-text)] font-semibold mt-1 flex items-center gap-1" data-sp-f9d979a0="">
                  <span data-sp-f9d979a0="">
                    {"▲ "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.macro.priceGrowthYoY)}
                  </span>
                  <span className="text-brand-navy/50 font-normal" data-sp-f9d979a0="">
                    {"so với cùng kỳ"}
                  </span>
                </p>
              </div>
              <div className="market-hero-metric px-5 py-4 min-w-[155px]" data-sp-f9d979a0="">
                <p className="text-[11px] uppercase tracking-wider text-brand-navy/65 font-semibold" data-sp-f9d979a0="">
                  {"Chỉ số thanh khoản"}
                </p>
                <p className="text-xl sm:text-2xl font-bold text-brand-navy mt-1 tracking-tight" data-sp-f9d979a0="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.macro.liquidityRating.split(" ")[0])}{" "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.macro.liquidityRating.split(" ")[1] || "")}
                </p>
                <p className="text-[11px] text-brand-navy/70 mt-1" data-sp-f9d979a0="">
                  {" Cập nhật Quý 4/2026 "}
                </p>
              </div>
            </div>
          </div>
          <div className="relative z-10 pt-6" data-sp-f9d979a0="">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3.5" data-sp-f9d979a0="">
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-brand-navy/60" data-sp-f9d979a0="">
                {" CHỌN QUẬN / KHU VỰC PHÂN TÍCH CHUYÊN SÂU "}
              </p>
              <span className="text-xs text-[var(--ui-ink)]/90 font-medium" data-sp-f9d979a0="">
                {" 6 quận trọng điểm · Dữ liệu chuẩn hóa & AI Valuation V1.3 "}
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5" data-sp-f9d979a0="">
              {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.DISTRICT_LIST, name => <button key={name} type="button" onClick={$event => {
                view.selectDistrict(view.DISTRICT_PROFILES[name].slug);
              }} className={classNames(["group px-4 py-3 rounded-2xl text-left transition-all cursor-pointer border flex flex-col justify-between", view.currentDistrict.shortName === name ? "bg-[var(--ui-soft)] text-[var(--ui-accent)] border-[var(--ui-border)] shadow-lg" : "bg-brand-card/7 text-brand-navy border-brand-line/12 hover:bg-brand-card/14 hover:border-[var(--ui-border)]/50"])} data-sp-f9d979a0="">
                  <div className="flex items-center justify-between gap-2 w-full mb-1" data-sp-f9d979a0="">
                    <span className="text-xs font-bold tracking-tight" data-sp-f9d979a0="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(name)}
                    </span>
                    <span className={classNames(["w-2 h-2 rounded-full transition", view.currentDistrict.shortName === name ? "bg-[var(--ui-soft)]" : "bg-brand-card/25 group-hover:bg-[var(--ui-soft)]"])} data-sp-f9d979a0="" />
                  </div>
                  <span className={classNames(["text-[11px] font-semibold", view.currentDistrict.shortName === name ? "text-[var(--ui-accent)]/80" : "text-brand-navy/65"])} data-sp-f9d979a0="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.DISTRICT_PROFILES[name].macro.avgPricePerM2)}
                  </span>
                </button>)}
            </div>
          </div>
        </section>
        <div className="sticky top-[calc(var(--sp-header-height,64px)+10px)] z-30 my-7" data-sp-f9d979a0="">
          <div className="rounded-full bg-brand-card/95 backdrop-blur-md border border-[var(--ui-border)] shadow-sm p-1.5 flex items-center justify-between gap-1 overflow-x-auto" data-sp-f9d979a0="">
            {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.inPageTabs, tab => <button key={tab.id} type="button" onClick={$event => {
              view.scrollToSection(tab.id);
            }} className={classNames(["flex-1 min-w-fit px-4 py-2.5 rounded-full text-xs font-bold transition-all whitespace-nowrap cursor-pointer flex items-center justify-center gap-2", view.activeSection === tab.id ? "bg-[var(--ui-soft)] text-[var(--ui-ink)] shadow-xs" : "text-[var(--ui-accent)] hover:text-[var(--ui-accent)] hover:bg-[var(--ui-surface)]"])} data-sp-f9d979a0="">
                <span className="text-[10px] opacity-70 font-mono" data-sp-f9d979a0="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(tab.number)}
                </span>
                <span data-sp-f9d979a0="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(tab.label)}
                </span>
              </button>)}
          </div>
        </div>
        <div className="space-y-12" data-sp-f9d979a0="">
          <section id="overview" className="scroll-mt-32 grid grid-cols-1 lg:grid-cols-12 gap-7 items-start" data-sp-f9d979a0="">
            <div className="lg:col-span-7 bg-brand-card rounded-3xl p-6 sm:p-8 border border-[var(--ui-border)] shadow-2xs" data-sp-f9d979a0="">
              <div className="pb-5 mb-6 border-b border-[var(--ui-border)]" data-sp-f9d979a0="">
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--ui-accent)] mb-2" data-sp-f9d979a0="">
                  {" 01 / TỔNG QUAN VĨ MÔ & ĐỊA LÝ "}
                </p>
                <h2 className="text-2xl sm:text-3xl font-semibold text-[var(--ui-accent)] tracking-tight" data-sp-f9d979a0="">
                  {" Bức tranh toàn cảnh "}
                  <span className="text-[var(--ui-accent)]" data-sp-f9d979a0="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.name)}
                    {"."}
                  </span>
                </h2>
              </div>
              <div className="space-y-4 mb-7" data-sp-f9d979a0="">
                <div className="p-5 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)] border-l-4 border-l-[#183e54]" data-sp-f9d979a0="">
                  <div className="flex items-center gap-2 text-xs font-bold text-[var(--ui-accent)] uppercase tracking-wider mb-2" data-sp-f9d979a0="">
                    <svg className="size-4 text-[var(--ui-accent)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-f9d979a0="">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" data-sp-f9d979a0="" />
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" data-sp-f9d979a0="" />
                    </svg>
                    <span data-sp-f9d979a0="">
                      {"Vị trí địa lý & Kết nối giao thông cốt lõi"}
                    </span>
                  </div>
                  <p className="text-xs sm:text-[13px] leading-relaxed text-[var(--ui-accent)]" data-sp-f9d979a0="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.overview)}
                  </p>
                </div>
                <div className="p-5 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)] border-l-4 border-l-[#198692]" data-sp-f9d979a0="">
                  <div className="flex items-center gap-2 text-xs font-bold text-[var(--ui-accent)] uppercase tracking-wider mb-2" data-sp-f9d979a0="">
                    <svg className="size-4 text-[var(--ui-accent)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" data-sp-f9d979a0="">
                      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" data-sp-f9d979a0="" />
                      <polyline points="17 6 23 6 23 12" data-sp-f9d979a0="" />
                    </svg>
                    <span data-sp-f9d979a0="">
                      {"Tiềm năng phát triển & Đặc tính thị trường"}
                    </span>
                  </div>
                  <p className="text-xs sm:text-[13px] leading-relaxed text-[var(--ui-accent)]" data-sp-f9d979a0="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.aiInsights.growthPotential)}
                  </p>
                </div>
              </div>
              <div className="pt-6 border-t border-[var(--ui-border)]" data-sp-f9d979a0="">
                <div className="flex items-center justify-between mb-4" data-sp-f9d979a0="">
                  <p className="text-xs font-bold text-[var(--ui-accent)] uppercase tracking-[0.18em]" data-sp-f9d979a0="">
                    {" CHỈ SỐ VĨ MÔ & MẶT BẰNG ĐƠN GIÁ "}
                  </p>
                  <span className="text-[11px] text-[var(--ui-muted)]" data-sp-f9d979a0="">
                    {"Đơn vị chuẩn hóa theo m²"}
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4" data-sp-f9d979a0="">
                  <div className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]" data-sp-f9d979a0="">
                    <p className="text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider" data-sp-f9d979a0="">
                      {"Diện tích tự nhiên"}
                    </p>
                    <p className="text-lg font-bold text-[var(--ui-accent)] mt-1.5" data-sp-f9d979a0="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.macro.areaKm2)}
                    </p>
                    <p className="text-[11px] text-[var(--ui-muted)] mt-1" data-sp-f9d979a0="">
                      {"Quy hoạch đô thị Đà Nẵng"}
                    </p>
                  </div>
                  <div className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]" data-sp-f9d979a0="">
                    <p className="text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider" data-sp-f9d979a0="">
                      {"Quy mô dân số"}
                    </p>
                    <p className="text-lg font-bold text-[var(--ui-accent)] mt-1.5" data-sp-f9d979a0="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.macro.population)}
                    </p>
                    <p className="text-[11px] text-[var(--ui-accent)] font-semibold mt-1" data-sp-f9d979a0="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.macro.density)}
                    </p>
                  </div>
                  <div className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]" data-sp-f9d979a0="">
                    <p className="text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider" data-sp-f9d979a0="">
                      {"Đơn giá TB Đất nền"}
                    </p>
                    <p className="text-lg font-bold text-[var(--ui-muted)] mt-1.5" data-sp-f9d979a0="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.macro.avgPricePerM2)}
                    </p>
                    <p className="text-[11px] text-[var(--ui-accent)] font-semibold mt-1" data-sp-f9d979a0="">
                      {"▲ "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.macro.priceGrowthYoY)}
                      {" YoY"}
                    </p>
                  </div>
                  <div className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]" data-sp-f9d979a0="">
                    <p className="text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider" data-sp-f9d979a0="">
                      {"Đơn giá TB Nhà phố"}
                    </p>
                    <p className="text-lg font-bold text-[var(--ui-accent)] mt-1.5" data-sp-f9d979a0="">
                      {"~ "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.latestHousePrice)}
                    </p>
                    <p className="text-[11px] text-[var(--ui-muted)] mt-1" data-sp-f9d979a0="">
                      {"Trục thương mại chính"}
                    </p>
                  </div>
                  <div className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]" data-sp-f9d979a0="">
                    <p className="text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider" data-sp-f9d979a0="">
                      {"Đơn giá TB Căn hộ"}
                    </p>
                    <p className="text-lg font-bold text-[var(--ui-accent)] mt-1.5" data-sp-f9d979a0="">
                      {"~ "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.latestApartmentPrice)}
                    </p>
                    <p className="text-[11px] text-[var(--ui-muted)] mt-1" data-sp-f9d979a0="">
                      {"Phân khúc thương mại & biển"}
                    </p>
                  </div>
                  <div className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]" data-sp-f9d979a0="">
                    <p className="text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider" data-sp-f9d979a0="">
                      {"Tin niêm yết công khai"}
                    </p>
                    <p className="text-lg font-bold text-[var(--ui-accent)] mt-1.5" data-sp-f9d979a0="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.properties.length)}
                      {" BĐS"}
                    </p>
                    <p className="text-[11px] text-[var(--ui-accent)] font-semibold mt-1" data-sp-f9d979a0="">
                      {"Thanh khoản: "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.macro.liquidityRating)}
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div className="lg:col-span-5 bg-brand-card rounded-3xl p-5 sm:p-6 border border-[var(--ui-border)] shadow-2xs lg:sticky lg:top-28" data-sp-f9d979a0="">
              <div className="flex items-center justify-between gap-3 mb-4" data-sp-f9d979a0="">
                <div data-sp-f9d979a0="">
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--ui-accent)]" data-sp-f9d979a0="">
                    {"GIS SPATIAL EXPLORER"}
                  </p>
                  <h3 className="text-base font-bold text-[var(--ui-accent)] mt-0.5" data-sp-f9d979a0="">
                    {" Bản đồ phân bố BĐS "}
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.shortName)}
                  </h3>
                </div>
                <span className="text-xs text-[var(--ui-accent)] font-bold bg-[var(--ui-surface)] border border-[var(--ui-border)] px-3 py-1 rounded-full" data-sp-f9d979a0="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.mapPoints.length)}
                  {" ghim tọa độ "}
                </span>
              </div>
              <div className="h-[430px] rounded-2xl overflow-hidden border border-[var(--ui-border)] relative bg-[var(--ui-surface)]" data-sp-f9d979a0="">
                {view.mapPoints.length ? <BrowseTileMap points={view.mapPoints} selectedId={view.selectedMapPropertyId} onSelect={$event => {
                  return (id => view.router.push(`/listing/${id}`))?.($event);
                }} data-sp-f9d979a0="" /> : <div className="w-full h-full flex flex-col items-center justify-center bg-[var(--ui-surface)] text-[var(--ui-accent)] text-xs p-6 text-center" data-sp-f9d979a0="">
                    <p className="font-semibold text-[var(--ui-accent)] mb-1" data-sp-f9d979a0="">
                      {"Đang tải tọa độ không gian..."}
                    </p>
                    <p className="text-[11px] text-[var(--ui-muted)]" data-sp-f9d979a0="">
                      {"Hiển thị các bất động sản có tọa độ xác thực tại "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.name)}
                    </p>
                  </div>}
              </div>
              <div className="mt-4 pt-3 border-t border-[var(--ui-border)] flex items-center justify-between text-xs text-[var(--ui-accent)]" data-sp-f9d979a0="">
                <span data-sp-f9d979a0="">
                  {"Chọn nhãn giá trên bản đồ để mở chi tiết BĐS"}
                </span>
                <SiteLink to={{
                  path: "/map",
                  query: {
                    district: view.currentDistrict.shortName
                  }
                }} className="text-[var(--ui-accent)] hover:text-[var(--ui-accent)] font-bold transition inline-flex items-center gap-1" data-sp-f9d979a0="">
                  <span data-sp-f9d979a0="">
                    {"Mở toàn cảnh GIS"}
                  </span>
                  <span aria-hidden="true" data-sp-f9d979a0="">
                    {"↗"}
                  </span>
                </SiteLink>
              </div>
            </div>
          </section>
          <section id="planning" className="scroll-mt-32 bg-brand-card rounded-3xl p-6 sm:p-8 lg:p-10 border border-[var(--ui-border)] shadow-2xs" data-sp-f9d979a0="">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 mb-7 border-b border-[var(--ui-border)]" data-sp-f9d979a0="">
              <div data-sp-f9d979a0="">
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--ui-accent)] mb-2" data-sp-f9d979a0="">
                  {" 02 / ĐỊNH HƯỚNG QUY HOẠCH ĐÔ THỊ 2030 – 2045 "}
                </p>
                <h2 className="text-2xl sm:text-3xl font-semibold text-[var(--ui-accent)] tracking-tight" data-sp-f9d979a0="">
                  {" Quy hoạch hạ tầng "}
                  <span className="text-[var(--ui-accent)]" data-sp-f9d979a0="">
                    {"& Động lực tăng trưởng."}
                  </span>
                </h2>
              </div>
              <p className="text-xs text-[var(--ui-accent)] max-w-md leading-relaxed" data-sp-f9d979a0="">
                {" Các dự án hạ tầng trọng điểm và định hướng không gian đô thị tác động trực tiếp đến biên độ tăng giá dài hạn tại "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.name)}
                {". "}
              </p>
            </div>
            <div className="space-y-4" data-sp-f9d979a0="">
              <div className="rounded-2xl border border-[var(--ui-border)] overflow-hidden transition-all" data-sp-f9d979a0="">
                <button type="button" onClick={$event => {
                  view.togglePanel("planning1");
                }} className={classNames(["w-full px-6 py-4 flex items-center justify-between text-left text-xs sm:text-sm font-bold cursor-pointer transition-colors", view.expandedPanels.planning1 ? "bg-[var(--ui-soft)] text-brand-navy" : "bg-[var(--ui-surface)] text-[var(--ui-accent)] hover:bg-[var(--ui-surface)]"])} data-sp-f9d979a0="">
                  <div className="flex items-center gap-3.5" data-sp-f9d979a0="">
                    <span className={classNames(["text-xs font-mono px-2.5 py-1 rounded-full border", view.expandedPanels.planning1 ? "border-[var(--ui-border)]/40 text-[var(--ui-ink)] bg-brand-card/8" : "border-[var(--ui-border)] text-[var(--ui-accent)] bg-brand-card"])} data-sp-f9d979a0="">
                      {" 01 "}
                    </span>
                    <span data-sp-f9d979a0="">
                      {"Định hướng phát triển không gian đô thị & thương mại "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.name)}
                    </span>
                  </div>
                  <span className={classNames(["text-xs transition-transform duration-200", [view.expandedPanels.planning1 ? "rotate-180 text-[var(--ui-ink)]" : "text-[var(--ui-accent)]"]])} data-sp-f9d979a0="">
                    {" ▼ "}
                  </span>
                </button>
                <div className="p-6 bg-brand-card text-xs sm:text-[13px] leading-relaxed text-[var(--ui-accent)] space-y-4 border-t border-[var(--ui-border)]" data-sp-f9d979a0="" style={{
                  display: view.expandedPanels.planning1 ? undefined : "none"
                }}>
                  <p data-sp-f9d979a0="">
                    {" Theo Quyết định điều chỉnh Quy hoạch chung TP. Đà Nẵng đến năm 2030, tầm nhìn 2045, "}
                    <strong className="text-[var(--ui-accent)]" data-sp-f9d979a0="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.name)}
                    </strong>
                    {" được định vị là cực tăng trưởng chiến lược với hệ sinh thái "}
                    <strong className="text-[var(--ui-accent)]" data-sp-f9d979a0="">
                      {"đô thị - thương mại dịch vụ - du lịch và cư trú chất lượng cao"}
                    </strong>
                    {". "}
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1" data-sp-f9d979a0="">
                    <div className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]" data-sp-f9d979a0="">
                      <p className="font-bold text-[var(--ui-accent)] mb-1.5" data-sp-f9d979a0="">
                        {"Tái cấu trúc không gian & Trục cảnh quan chủ đạo"}
                      </p>
                      <p className="text-xs text-[var(--ui-accent)] leading-relaxed" data-sp-f9d979a0="">
                        {"Ưu tiên phát triển các tổ hợp thương mại dịch vụ hiện đại, nâng cấp hạ tầng kỹ thuật ngầm hóa và mở rộng không gian công cộng phục vụ cư dân."}
                      </p>
                    </div>
                    <div className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]" data-sp-f9d979a0="">
                      <p className="font-bold text-[var(--ui-accent)] mb-1.5" data-sp-f9d979a0="">
                        {"Kinh tế dịch vụ & Khai thác dòng tiền"}
                      </p>
                      <p className="text-xs text-[var(--ui-accent)] leading-relaxed" data-sp-f9d979a0="">
                        {"Gia tăng mật độ các tuyến phố chuyên doanh, tổ hợp văn phòng - lưu trú cao cấp nhằm tối ưu tỷ suất khai thác cho thuê bất động sản."}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="rounded-2xl border border-[var(--ui-border)] overflow-hidden transition-all" data-sp-f9d979a0="">
                <button type="button" onClick={$event => {
                  view.togglePanel("planning2");
                }} className={classNames(["w-full px-6 py-4 flex items-center justify-between text-left text-xs sm:text-sm font-bold cursor-pointer transition-colors", view.expandedPanels.planning2 ? "bg-[var(--ui-soft)] text-brand-navy" : "bg-[var(--ui-surface)] text-[var(--ui-accent)] hover:bg-[var(--ui-surface)]"])} data-sp-f9d979a0="">
                  <div className="flex items-center gap-3.5" data-sp-f9d979a0="">
                    <span className={classNames(["text-xs font-mono px-2.5 py-1 rounded-full border", view.expandedPanels.planning2 ? "border-[var(--ui-border)]/40 text-[var(--ui-ink)] bg-brand-card/8" : "border-[var(--ui-border)] text-[var(--ui-accent)] bg-brand-card"])} data-sp-f9d979a0="">
                      {" 02 "}
                    </span>
                    <span data-sp-f9d979a0="">
                      {"Danh mục dự án hạ tầng & Giao thông trọng điểm tại "}
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.shortName)}
                    </span>
                  </div>
                  <span className={classNames(["text-xs transition-transform duration-200", [view.expandedPanels.planning2 ? "rotate-180 text-[var(--ui-ink)]" : "text-[var(--ui-accent)]"]])} data-sp-f9d979a0="">
                    {" ▼ "}
                  </span>
                </button>
                <div className="p-6 bg-brand-card border-t border-[var(--ui-border)]" data-sp-f9d979a0="" style={{
                  display: view.expandedPanels.planning2 ? undefined : "none"
                }}>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-sp-f9d979a0="">
                    {((items, render) => typeof items === "number" ? Array.from({
                      length: Math.max(0, items)
                    }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.currentDistrict.infrastructure, item => <div key={item.name} className="p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)] flex flex-col justify-between gap-3" data-sp-f9d979a0="">
                        <div data-sp-f9d979a0="">
                          <span className="text-[10px] font-bold px-2.5 py-1 rounded-full inline-block mb-2.5 bg-brand-card border border-[var(--ui-border)] text-[var(--ui-accent)] uppercase tracking-wider" data-sp-f9d979a0="">
                            {" ● "}
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.status)}
                          </span>
                          <p className="font-bold text-[var(--ui-accent)] text-xs sm:text-[13px] leading-snug" data-sp-f9d979a0="">
                            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.name)}
                          </p>
                        </div>
                        <p className="text-[11px] text-[var(--ui-muted)]" data-sp-f9d979a0="">
                          {"Tác động trực tiếp tới giá trị kết nối khu vực"}
                        </p>
                      </div>)}
                  </div>
                </div>
              </div>
              <div className="rounded-2xl border border-[var(--ui-border)] overflow-hidden transition-all" data-sp-f9d979a0="">
                <button type="button" onClick={$event => {
                  view.togglePanel("planning3");
                }} className={classNames(["w-full px-6 py-4 flex items-center justify-between text-left text-xs sm:text-sm font-bold cursor-pointer transition-colors", view.expandedPanels.planning3 ? "bg-[var(--ui-soft)] text-brand-navy" : "bg-[var(--ui-surface)] text-[var(--ui-accent)] hover:bg-[var(--ui-surface)]"])} data-sp-f9d979a0="">
                  <div className="flex items-center gap-3.5" data-sp-f9d979a0="">
                    <span className={classNames(["text-xs font-mono px-2.5 py-1 rounded-full border", view.expandedPanels.planning3 ? "border-[var(--ui-border)]/40 text-[var(--ui-ink)] bg-brand-card/8" : "border-[var(--ui-border)] text-[var(--ui-accent)] bg-brand-card"])} data-sp-f9d979a0="">
                      {" 03 "}
                    </span>
                    <span data-sp-f9d979a0="">
                      {"Hệ sinh thái tiện ích ngoại khu & Chất lượng sống"}
                    </span>
                  </div>
                  <span className={classNames(["text-xs transition-transform duration-200", [view.expandedPanels.planning3 ? "rotate-180 text-[var(--ui-ink)]" : "text-[var(--ui-accent)]"]])} data-sp-f9d979a0="">
                    {" ▼ "}
                  </span>
                </button>
                <div className="p-6 bg-brand-card text-xs sm:text-[13px] leading-relaxed text-[var(--ui-accent)] border-t border-[var(--ui-border)]" data-sp-f9d979a0="" style={{
                  display: view.expandedPanels.planning3 ? undefined : "none"
                }}>
                  <p data-sp-f9d979a0="">
                    <strong className="text-[var(--ui-accent)]" data-sp-f9d979a0="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.name)}
                    </strong>
                    {" sở hữu mạng lưới tiện ích đô thị hoàn chỉnh trong bán kính 1–3 km: hệ thống trường học liên cấp, bệnh viện & trạm y tế, siêu thị thương mại, công viên cây xanh và các trục giao thông kết nối thẳng ra sân bay quốc tế Đà Nẵng cũng như bãi biển. "}
                  </p>
                </div>
              </div>
            </div>
          </section>
          <section id="price-trend" className="scroll-mt-32 space-y-6" data-sp-f9d979a0="">
            <PriceTrendChart history={view.currentDistrict.priceHistory} data-sp-f9d979a0="" />
            <div className="rounded-3xl p-6 sm:p-8 lg:p-10 bg-gradient-to-br from-[var(--ui-soft)] via-[var(--ui-soft)] to-[var(--ui-soft)] text-brand-navy shadow-xl border border-[var(--ui-border)]/35 relative overflow-hidden" data-sp-f9d979a0="">
              <div className="pointer-events-none absolute -right-16 -bottom-16 h-64 w-64 rounded-full bg-[var(--ui-soft)]/10 blur-3xl" aria-hidden="true" data-sp-f9d979a0="" />
              <div className="relative z-10 flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 mb-6 border-b border-brand-line/12" data-sp-f9d979a0="">
                <div data-sp-f9d979a0="">
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-card/10 text-[var(--ui-ink)] text-[11px] font-bold border border-[var(--ui-border)]/30 tracking-wider uppercase mb-3" data-sp-f9d979a0="">
                    <span className="w-2 h-2 rounded-full bg-[var(--ui-success-bg)] animate-pulse" data-sp-f9d979a0="" />
                    <span data-sp-f9d979a0="">
                      {"SMARTPROP AI MARKET INTELLIGENCE · MODEL V1.3"}
                    </span>
                  </div>
                  <h3 className="text-xl sm:text-2xl font-semibold text-brand-navy tracking-tight" data-sp-f9d979a0="">
                    {" Nhận định chuyên sâu & Dự báo xu hướng "}
                    <span className="text-[var(--ui-ink)]" data-sp-f9d979a0="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.name)}
                      {"."}
                    </span>
                  </h3>
                </div>
                <SiteLink to="/advisor" className="self-start md:self-auto inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-[var(--ui-soft)] hover:bg-[var(--ui-soft)] text-[var(--ui-accent)] text-xs font-bold transition shadow-sm" data-sp-f9d979a0="">
                  <span data-sp-f9d979a0="">
                    {"Mở AI Advisor phân tích danh mục"}
                  </span>
                  <span aria-hidden="true" data-sp-f9d979a0="">
                    {"→"}
                  </span>
                </SiteLink>
              </div>
              <div className="relative z-10 grid grid-cols-1 md:grid-cols-3 gap-5 text-xs sm:text-[13px] leading-relaxed" data-sp-f9d979a0="">
                <div className="bg-brand-card/8 backdrop-blur-md rounded-2xl p-5 border border-brand-line/12" data-sp-f9d979a0="">
                  <div className="flex items-center gap-2 font-bold text-[var(--ui-ink)] uppercase tracking-wider text-xs mb-2.5" data-sp-f9d979a0="">
                    <svg className="size-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" data-sp-f9d979a0="">
                      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" data-sp-f9d979a0="" />
                      <polyline points="17 6 23 6 23 12" data-sp-f9d979a0="" />
                    </svg>
                    <span data-sp-f9d979a0="">
                      {"Động lực tăng giá"}
                    </span>
                  </div>
                  <p className="text-brand-navy/85" data-sp-f9d979a0="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.aiInsights.growthPotential)}
                  </p>
                </div>
                <div className="bg-brand-card/8 backdrop-blur-md rounded-2xl p-5 border border-brand-line/12" data-sp-f9d979a0="">
                  <div className="flex items-center gap-2 font-bold text-[var(--ui-success-text)] uppercase tracking-wider text-xs mb-2.5" data-sp-f9d979a0="">
                    <svg className="size-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" data-sp-f9d979a0="">
                      <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" data-sp-f9d979a0="" />
                    </svg>
                    <span data-sp-f9d979a0="">
                      {"Thanh khoản thị trường"}
                    </span>
                  </div>
                  <p className="text-brand-navy/85" data-sp-f9d979a0="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.aiInsights.liquidity)}
                  </p>
                </div>
                <div className="bg-brand-card/8 backdrop-blur-md rounded-2xl p-5 border border-brand-line/12" data-sp-f9d979a0="">
                  <div className="flex items-center gap-2 font-bold text-brand-navy uppercase tracking-wider text-xs mb-2.5" data-sp-f9d979a0="">
                    <svg className="size-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" data-sp-f9d979a0="">
                      <circle cx="12" cy="12" r="10" data-sp-f9d979a0="" />
                      <polyline points="12 6 12 12 16 14" data-sp-f9d979a0="" />
                    </svg>
                    <span data-sp-f9d979a0="">
                      {"Khuyến nghị chiến lược"}
                    </span>
                  </div>
                  <p className="text-brand-navy/85" data-sp-f9d979a0="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.aiInsights.recommendation)}
                  </p>
                </div>
              </div>
            </div>
          </section>
          <section id="listings" className="scroll-mt-32 bg-[var(--ui-surface)] rounded-3xl p-6 sm:p-8 lg:p-10 border border-[var(--ui-border)]" data-sp-f9d979a0="">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-6 mb-7 border-b border-[var(--ui-border)]" data-sp-f9d979a0="">
              <div data-sp-f9d979a0="">
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--ui-accent)] mb-2" data-sp-f9d979a0="">
                  {" 04 / BẤT ĐỘNG SẢN THỰC TẾ ĐANG NIÊM YẾT "}
                </p>
                <h2 className="text-2xl sm:text-3xl font-semibold text-[var(--ui-accent)] tracking-tight" data-sp-f9d979a0="">
                  {" Tin đăng công khai tại "}
                  <span className="text-[var(--ui-accent)]" data-sp-f9d979a0="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.name)}
                    {"."}
                  </span>
                </h2>
                <p className="text-xs text-[var(--ui-accent)] mt-1.5" data-sp-f9d979a0="">
                  {" Tin đã kiểm duyệt trên hệ thống SmartProp · Hỗ trợ đối chiếu bản đồ GIS và so sánh trực tiếp "}
                </p>
              </div>
              <SiteLink to={{
                path: "/listings",
                query: {
                  district: view.currentDistrict.shortName
                }
              }} className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[var(--ui-soft)] text-brand-navy hover:bg-[var(--ui-soft)] text-xs font-bold transition self-start sm:self-auto shadow-xs" data-sp-f9d979a0="">
                <span data-sp-f9d979a0="">
                  {"Xem tất cả tại "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.currentDistrict.shortName)}
                </span>
                <span aria-hidden="true" data-sp-f9d979a0="">
                  {"→"}
                </span>
              </SiteLink>
            </div>
            {view.loadingProperties ? <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-sp-f9d979a0="">
                {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(3, n => <div key={n} className="h-[420px] rounded-3xl bg-brand-card/60 animate-pulse border border-[var(--ui-border)]" data-sp-f9d979a0="" />)}
              </div> : view.properties.length ? <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-sp-f9d979a0="">
                {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.properties.slice(0, 6), item => <ListingCard key={item.id} property={item} className={classNames({
                "ring-2 ring-[var(--ui-border)] ring-offset-2": view.selectedMapPropertyId === item.id
              })} data-sp-f9d979a0="">
                    <button type="button" className="market-card-action" aria-pressed={view.selectedMapPropertyId === item.id} onClick={$event => {
                  view.focusOnDistrictMap(item.id);
                }} data-sp-f9d979a0="">
                      {" ⌖ Bản đồ "}
                    </button>
                    <button type="button" className="market-card-action compare" aria-pressed={view.compare.has(item.id)} onClick={$event => {
                  view.compare.toggle(item);
                }} data-sp-f9d979a0="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.compare.has(item.id) ? "✓ Đã chọn" : "+ So sánh")}
                    </button>
                  </ListingCard>)}
              </div> : <div className="rounded-3xl bg-brand-card p-12 text-center border border-[var(--ui-border)]" data-sp-f9d979a0="">
                <p className="text-lg font-semibold text-[var(--ui-accent)]" data-sp-f9d979a0="">
                  {"Chưa có tin đăng công khai tại khu vực này"}
                </p>
                <p className="text-xs text-[var(--ui-accent)] mt-2 mb-5" data-sp-f9d979a0="">
                  {"Hãy khám phá các quận lân cận hoặc xem toàn bộ danh sách bất động sản Đà Nẵng."}
                </p>
                <SiteLink to="/listings" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[var(--ui-soft)] text-brand-navy text-xs font-bold" data-sp-f9d979a0="">
                  <span data-sp-f9d979a0="">
                    {"Mở danh sách BĐS"}
                  </span>
                  <span aria-hidden="true" data-sp-f9d979a0="">
                    {"→"}
                  </span>
                </SiteLink>
              </div>}
          </section>
          <section id="neighboring" className="scroll-mt-32 bg-brand-card rounded-3xl p-6 sm:p-8 lg:p-10 border border-[var(--ui-border)] shadow-2xs space-y-8" data-sp-f9d979a0="">
            <TopSearchedAreas currentSlug={view.currentDistrict.slug} eyebrow="05 / XU HƯỚNG TÌM KIẾM · ĐÀ NẴNG" mode="market" onSelectDistrict={$event => {
              return view.selectDistrict?.($event);
            }} data-sp-f9d979a0="" />
          </section>
        </div>
      </div>
    </div></>;
});
