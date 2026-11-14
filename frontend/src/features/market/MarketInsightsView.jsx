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
  watch,
  onMounted,
  onBeforeUnmount,
} from "../../shared/state/store.js";
import { useRoute, useRouter } from "../../shared/routing/router.jsx";
import { api } from "../auth/api.js";
import {
  DISTRICT_PROFILES,
  DISTRICT_LIST,
  getDistrictProfile,
} from "./marketData.js";
import { useComparison } from "../../shared/hooks/useComparison.js";
import PriceTrendChart from "./PriceTrendChart.jsx";
import BrowseTileMap from "../map/BrowseTileMap.jsx";
import ListingCard from "../property/ListingCard.jsx";
import TopSearchedAreas from "./TopSearchedAreas.jsx";
import "./MarketInsightsView.css";
function setup(__props) {
  const route = useRoute();
  const router = useRouter();
  const compare = useComparison();

  // District selection
  const selectedDistrictSlug = ref(route.params.district || "son-tra");
  const currentDistrict = computed(() =>
    getDistrictProfile(selectedDistrictSlug.value),
  );
  function selectDistrict(slug) {
    selectedDistrictSlug.value = slug;
    router.push({
      path: `/market/${slug}`,
    });
  }
  watch(
    () => route.params.district,
    (newSlug) => {
      if (newSlug) selectedDistrictSlug.value = newSlug;
    },
  );

  // Dynamic unit prices from district history
  const latestHousePrice = computed(() => {
    const arr = currentDistrict.value?.priceHistory?.house || [];
    return arr.length ? `${arr[arr.length - 1]},0 triệu/m²` : "145,0 triệu/m²";
  });
  const latestApartmentPrice = computed(() => {
    const arr = currentDistrict.value?.priceHistory?.apartment || [];
    return arr.length ? `${arr[arr.length - 1]},0 triệu/m²` : "62,0 triệu/m²";
  });

  // Real-time properties from database
  const properties = ref([]);
  const loadingProperties = ref(false);
  const selectedMapPropertyId = ref(null);
  async function fetchDistrictProperties() {
    loadingProperties.value = true;
    try {
      const districtName = currentDistrict.value.shortName;
      const res = await api(
        `/properties?district=${encodeURIComponent(districtName)}&size=6&limit=8`,
        {
          authenticated: false,
        },
      );
      const items = Array.isArray(res) ? res : res?.items || [];
      properties.value = items;
      selectedMapPropertyId.value =
        items.find(
          (p) =>
            Number.isFinite(Number(p.latitude)) &&
            Number.isFinite(Number(p.longitude)),
        )?.id || null;
    } catch (e) {
      properties.value = [];
      selectedMapPropertyId.value = null;
    } finally {
      loadingProperties.value = false;
    }
  }
  watch(
    () => currentDistrict.value.id,
    () => {
      fetchDistrictProperties();
    },
    {
      immediate: true,
    },
  );

  // Points for BrowseTileMap
  const mapPoints = computed(() => {
    return properties.value
      .filter(
        (p) =>
          Number.isFinite(Number(p.latitude)) &&
          Number.isFinite(Number(p.longitude)),
      )
      .map((p) => ({
        id: p.id,
        latitude: Number(p.latitude),
        longitude: Number(p.longitude),
        price: p.price,
        priceExact: p.priceExact,
        priceUnit: p.priceUnit,
        transactionType: p.transactionType,
        title: p.title,
      }));
  });
  function focusOnDistrictMap(propertyId) {
    selectedMapPropertyId.value = propertyId;
    scrollToSection("overview");
  }

  // In-page navigation tabs
  const activeSection = ref("overview");
  const inPageTabs = [
    {
      id: "overview",
      number: "01",
      label: "Tổng quan & GIS",
    },
    {
      id: "planning",
      number: "02",
      label: "Quy hoạch hạ tầng",
    },
    {
      id: "price-trend",
      number: "03",
      label: "Biến động đơn giá",
    },
    {
      id: "listings",
      number: "04",
      label: "Bất động sản mở bán",
    },
    {
      id: "neighboring",
      number: "05",
      label: "Khu vực tìm kiếm nhiều",
    },
  ];
  function scrollToSection(id) {
    activeSection.value = id;
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }
  let sectionObserver = null;
  onMounted(() => {
    if (typeof IntersectionObserver === "undefined") return;
    sectionObserver = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]?.target?.id) {
          activeSection.value = visible[0].target.id;
        }
      },
      {
        rootMargin: "-20% 0px -60% 0px",
        threshold: [0.05, 0.25, 0.5],
      },
    );
    for (const tab of inPageTabs) {
      const el = document.getElementById(tab.id);
      if (el) sectionObserver.observe(el);
    }
  });
  onBeforeUnmount(() => {
    sectionObserver?.disconnect();
  });

  // Accordion toggle state for planning section
  const expandedPanels = ref({
    planning1: true,
    planning2: true,
    planning3: false,
  });
  function togglePanel(panelKey) {
    expandedPanels.value[panelKey] = !expandedPanels.value[panelKey];
  }
  function handleBack() {
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push("/listings");
    }
  }
  return {
    ref,
    computed,
    watch,
    onMounted,
    onBeforeUnmount,
    useRoute,
    useRouter,
    api,
    DISTRICT_PROFILES,
    DISTRICT_LIST,
    getDistrictProfile,
    useComparison,
    PriceTrendChart,
    BrowseTileMap,
    ListingCard,
    TopSearchedAreas,
    route,
    router,
    compare,
    selectedDistrictSlug,
    currentDistrict,
    selectDistrict,
    latestHousePrice,
    latestApartmentPrice,
    properties,
    loadingProperties,
    selectedMapPropertyId,
    fetchDistrictProperties,
    mapPoints,
    focusOnDistrictMap,
    activeSection,
    inPageTabs,
    scrollToSection,
    sectionObserver,
    expandedPanels,
    togglePanel,
    handleBack,
  };
}
export default React.forwardRef(function MarketInsightsView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="MarketInsightsView"
      {...mergeProps({
        className:
          "market-luxury min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)] antialiased selection:bg-[var(--ui-soft)] selection:text-[var(--ui-ink)] pb-20",
        "data-sp-f9d979a0": "",
      })}
    >
      <div
        {...mergeProps({
          className: "max-w-[1280px] mx-auto px-5 sm:px-8 pt-6",
          "data-sp-f9d979a0": "",
        })}
      >
        <div
          {...mergeProps({
            className: "flex flex-wrap items-center justify-between gap-3 mb-6",
            "data-sp-f9d979a0": "",
          })}
        >
          <div
            {...mergeProps({
              className: "flex items-center gap-3",
              "data-sp-f9d979a0": "",
            })}
          >
            <button
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  return ctx.handleBack?.($event);
                },
                className:
                  "inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-card text-[var(--ui-accent)] border border-[var(--ui-border)] shadow-2xs hover:bg-[var(--ui-surface)] hover:border-[var(--ui-border)] transition-all cursor-pointer text-xs font-bold group",
                "data-sp-f9d979a0": "",
              })}
            >
              <svg
                {...mergeProps({
                  width: "14",
                  height: "14",
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  strokeWidth: "2.2",
                  className:
                    "transition-transform group-hover:-translate-x-0.5",
                  "data-sp-f9d979a0": "",
                })}
              >
                <line
                  {...mergeProps({
                    x1: "19",
                    y1: "12",
                    x2: "5",
                    y2: "12",
                    "data-sp-f9d979a0": "",
                  })}
                />
                <polyline
                  {...mergeProps({
                    points: "12 19 5 12 12 5",
                    "data-sp-f9d979a0": "",
                  })}
                />
              </svg>
              <span
                {...mergeProps({
                  "data-sp-f9d979a0": "",
                })}
              >
                {"Quay lại"}
              </span>
            </button>
            <nav
              {...mergeProps({
                "aria-label": "Breadcrumb",
                className:
                  "hidden sm:inline-flex items-center gap-2.5 px-4 py-2 rounded-full bg-brand-card border border-[var(--ui-border)] text-xs font-medium text-[var(--ui-accent)]",
                "data-sp-f9d979a0": "",
              })}
            >
              <RouterLink
                {...mergeProps({
                  to: "/",
                  className: "hover:text-[var(--ui-accent)] transition",
                  "data-sp-f9d979a0": "",
                })}
              >
                {"Trang chủ"}
              </RouterLink>
              <span
                {...mergeProps({
                  className: "text-[var(--ui-ink)]",
                  "data-sp-f9d979a0": "",
                })}
              >
                {"/"}
              </span>
              <RouterLink
                {...mergeProps({
                  to: "/market",
                  className: "hover:text-[var(--ui-accent)] transition",
                  "data-sp-f9d979a0": "",
                })}
              >
                {"Dữ liệu thị trường"}
              </RouterLink>
              <span
                {...mergeProps({
                  className: "text-[var(--ui-ink)]",
                  "data-sp-f9d979a0": "",
                })}
              >
                {"/"}
              </span>
              <span
                {...mergeProps({
                  className:
                    "text-[var(--ui-accent)] font-bold flex items-center gap-1.5",
                  "data-sp-f9d979a0": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "w-1.5 h-1.5 rounded-full bg-[var(--ui-soft)]",
                    "data-sp-f9d979a0": "",
                  })}
                />{" "}
                {display(ctx.currentDistrict.name)}
              </span>
            </nav>
          </div>
          <div
            {...mergeProps({
              className: "flex items-center gap-2.5",
              "data-sp-f9d979a0": "",
            })}
          >
            <RouterLink
              {...mergeProps({
                to: {
                  path: "/listings",
                  query: {
                    district: ctx.currentDistrict.shortName,
                  },
                },
                className:
                  "inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-card border border-[var(--ui-border)] hover:border-[var(--ui-border)] text-xs font-bold text-[var(--ui-accent)] transition",
                "data-sp-f9d979a0": "",
              })}
            >
              <span
                {...mergeProps({
                  "data-sp-f9d979a0": "",
                })}
              >
                {"Tin đăng "}
                {display(ctx.currentDistrict.shortName)}
              </span>
              <span
                {...mergeProps({
                  "aria-hidden": "true",
                  "data-sp-f9d979a0": "",
                })}
              >
                {"↗"}
              </span>
            </RouterLink>
            <RouterLink
              {...mergeProps({
                to: "/advisor",
                className:
                  "inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[var(--ui-soft)] text-[var(--ui-ink)] hover:bg-[var(--ui-soft)] text-xs font-bold transition shadow-xs",
                "data-sp-f9d979a0": "",
              })}
            >
              <span
                {...mergeProps({
                  "data-sp-f9d979a0": "",
                })}
              >
                {"Tư vấn đầu tư AI"}
              </span>
              <span
                {...mergeProps({
                  "aria-hidden": "true",
                  "data-sp-f9d979a0": "",
                })}
              >
                {"→"}
              </span>
            </RouterLink>
          </div>
        </div>
        <section
          {...mergeProps({
            className:
              "market-intro-banner relative overflow-hidden rounded-[28px] bg-gradient-to-br from-[var(--ui-soft)] via-[var(--ui-soft)] to-[var(--ui-soft)] text-brand-navy p-7 sm:p-10 lg:p-12 border border-[var(--ui-border)]/30 shadow-xl",
            "data-sp-f9d979a0": "",
          })}
        >
          <div
            {...mergeProps({
              className:
                "pointer-events-none absolute -right-20 -top-20 h-80 w-80 rounded-full bg-[var(--ui-soft)]/8 blur-3xl",
              "aria-hidden": "true",
              "data-sp-f9d979a0": "",
            })}
          />
          <div
            {...mergeProps({
              className:
                "pointer-events-none absolute -bottom-24 left-1/3 h-64 w-64 rounded-full bg-[var(--ui-soft)]/10 blur-3xl",
              "aria-hidden": "true",
              "data-sp-f9d979a0": "",
            })}
          />
          <div
            {...mergeProps({
              className:
                "relative z-10 flex flex-col lg:flex-row lg:items-end justify-between gap-8 pb-8 border-b border-brand-line/12",
              "data-sp-f9d979a0": "",
            })}
          >
            <div
              {...mergeProps({
                className: "max-w-3xl",
                "data-sp-f9d979a0": "",
              })}
            >
              <div
                {...mergeProps({
                  className:
                    "inline-flex items-center gap-2.5 text-xs font-bold uppercase tracking-[0.24em] text-[var(--ui-ink)] mb-3",
                  "data-sp-f9d979a0": "",
                })}
              >
                <span
                  {...mergeProps({
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {"⌖"}
                </span>
                <span
                  {...mergeProps({
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {"SMARTPROP MARKET INTELLIGENCE · ĐÀ NẴNG"}
                </span>
              </div>
              <h1
                {...mergeProps({
                  className:
                    "text-3xl sm:text-4xl lg:text-[46px] font-semibold tracking-tight leading-[1.14] text-brand-navy",
                  "data-sp-f9d979a0": "",
                })}
              >
                {" Báo cáo thị trường "}
                <span
                  {...mergeProps({
                    className: "text-[var(--ui-ink)] block sm:inline",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {display(ctx.currentDistrict.name)}
                  {"."}
                </span>
              </h1>
              <p
                {...mergeProps({
                  className:
                    "text-sm sm:text-[15px] text-brand-navy/80 mt-3.5 leading-relaxed max-w-2xl",
                  "data-sp-f9d979a0": "",
                })}
              >
                {display(ctx.currentDistrict.tagline)}
              </p>
            </div>
            <div
              {...mergeProps({
                className:
                  "flex flex-wrap sm:flex-nowrap items-stretch gap-3 shrink-0",
                "data-sp-f9d979a0": "",
              })}
            >
              <div
                {...mergeProps({
                  className:
                    "market-hero-metric px-5 py-4 min-w-[165px]",
                  "data-sp-f9d979a0": "",
                })}
              >
                <p
                  {...mergeProps({
                    className:
                      "text-[11px] uppercase tracking-wider text-brand-navy/65 font-semibold",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {"Đơn giá TB Đất nền"}
                </p>
                <p
                  {...mergeProps({
                    className:
                      "text-xl sm:text-2xl font-bold text-[var(--ui-ink)] mt-1 tracking-tight",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {display(ctx.currentDistrict.macro.avgPricePerM2)}
                </p>
                <p
                  {...mergeProps({
                    className:
                      "text-[11px] text-[var(--ui-success-text)] font-semibold mt-1 flex items-center gap-1",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <span
                    {...mergeProps({
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {"▲ "}
                    {display(ctx.currentDistrict.macro.priceGrowthYoY)}
                  </span>
                  <span
                    {...mergeProps({
                      className: "text-brand-navy/50 font-normal",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {"so với cùng kỳ"}
                  </span>
                </p>
              </div>
              <div
                {...mergeProps({
                  className:
                    "market-hero-metric px-5 py-4 min-w-[155px]",
                  "data-sp-f9d979a0": "",
                })}
              >
                <p
                  {...mergeProps({
                    className:
                      "text-[11px] uppercase tracking-wider text-brand-navy/65 font-semibold",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {"Chỉ số thanh khoản"}
                </p>
                <p
                  {...mergeProps({
                    className:
                      "text-xl sm:text-2xl font-bold text-brand-navy mt-1 tracking-tight",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {display(
                    ctx.currentDistrict.macro.liquidityRating.split(" ")[0],
                  )}{" "}
                  {display(
                    ctx.currentDistrict.macro.liquidityRating.split(" ")[1] ||
                      "",
                  )}
                </p>
                <p
                  {...mergeProps({
                    className: "text-[11px] text-brand-navy/70 mt-1",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {" Cập nhật Quý 4/2026 "}
                </p>
              </div>
            </div>
          </div>
          <div
            {...mergeProps({
              className: "relative z-10 pt-6",
              "data-sp-f9d979a0": "",
            })}
          >
            <div
              {...mergeProps({
                className:
                  "flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3.5",
                "data-sp-f9d979a0": "",
              })}
            >
              <p
                {...mergeProps({
                  className:
                    "text-[11px] font-bold uppercase tracking-[0.2em] text-brand-navy/60",
                  "data-sp-f9d979a0": "",
                })}
              >
                {" CHỌN QUẬN / KHU VỰC PHÂN TÍCH CHUYÊN SÂU "}
              </p>
              <span
                {...mergeProps({
                  className: "text-xs text-[var(--ui-ink)]/90 font-medium",
                  "data-sp-f9d979a0": "",
                })}
              >
                {" 6 quận trọng điểm · Dữ liệu chuẩn hóa & AI Valuation V6 "}
              </span>
            </div>
            <div
              {...mergeProps({
                className:
                  "grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5",
                "data-sp-f9d979a0": "",
              })}
            >
              {renderList(ctx.DISTRICT_LIST, (name) => (
                <button
                  key={name}
                  {...mergeProps({
                    type: "button",
                    onClick: ($event) => {
                      ctx.selectDistrict(ctx.DISTRICT_PROFILES[name].slug);
                    },
                    className: ["group px-4 py-3 rounded-2xl text-left transition-all cursor-pointer border flex flex-col justify-between", ctx.currentDistrict.shortName === name
                        ? "bg-[var(--ui-soft)] text-[var(--ui-accent)] border-[var(--ui-border)] shadow-lg"
                        : "bg-brand-card/7 text-brand-navy border-brand-line/12 hover:bg-brand-card/14 hover:border-[var(--ui-border)]/50"],
                    
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className:
                        "flex items-center justify-between gap-2 w-full mb-1",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className: "text-xs font-bold tracking-tight",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {display(name)}
                    </span>
                    <span
                      {...mergeProps({
                        className: ["w-2 h-2 rounded-full transition", ctx.currentDistrict.shortName === name
                            ? "bg-[var(--ui-soft)]"
                            : "bg-brand-card/25 group-hover:bg-[var(--ui-soft)]"],
                        
                        "data-sp-f9d979a0": "",
                      })}
                    />
                  </div>
                  <span
                    {...mergeProps({
                      className: ["text-[11px] font-semibold", ctx.currentDistrict.shortName === name
                          ? "text-[var(--ui-accent)]/80"
                          : "text-brand-navy/65"],
                      
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {display(ctx.DISTRICT_PROFILES[name].macro.avgPricePerM2)}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </section>
        <div
          {...mergeProps({
            className:
              "sticky top-[calc(var(--sp-header-height,64px)+10px)] z-30 my-7",
            "data-sp-f9d979a0": "",
          })}
        >
          <div
            {...mergeProps({
              className:
                "rounded-full bg-brand-card/95 backdrop-blur-md border border-[var(--ui-border)] shadow-sm p-1.5 flex items-center justify-between gap-1 overflow-x-auto",
              "data-sp-f9d979a0": "",
            })}
          >
            {renderList(ctx.inPageTabs, (tab) => (
              <button
                key={tab.id}
                {...mergeProps({
                  type: "button",
                  onClick: ($event) => {
                    ctx.scrollToSection(tab.id);
                  },
                  className: ["flex-1 min-w-fit px-4 py-2.5 rounded-full text-xs font-bold transition-all whitespace-nowrap cursor-pointer flex items-center justify-center gap-2", ctx.activeSection === tab.id
                      ? "bg-[var(--ui-soft)] text-[var(--ui-ink)] shadow-xs"
                      : "text-[var(--ui-accent)] hover:text-[var(--ui-accent)] hover:bg-[var(--ui-surface)]"],
                  
                  "data-sp-f9d979a0": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "text-[10px] opacity-70 font-mono",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {display(tab.number)}
                </span>
                <span
                  {...mergeProps({
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {display(tab.label)}
                </span>
              </button>
            ))}
          </div>
        </div>
        <div
          {...mergeProps({
            className: "space-y-12",
            "data-sp-f9d979a0": "",
          })}
        >
          <section
            {...mergeProps({
              id: "overview",
              className:
                "scroll-mt-32 grid grid-cols-1 lg:grid-cols-12 gap-7 items-start",
              "data-sp-f9d979a0": "",
            })}
          >
            <div
              {...mergeProps({
                className:
                  "lg:col-span-7 bg-brand-card rounded-3xl p-6 sm:p-8 border border-[var(--ui-border)] shadow-2xs",
                "data-sp-f9d979a0": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "pb-5 mb-6 border-b border-[var(--ui-border)]",
                  "data-sp-f9d979a0": "",
                })}
              >
                <p
                  {...mergeProps({
                    className:
                      "text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--ui-accent)] mb-2",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {" 01 / TỔNG QUAN VĨ MÔ & ĐỊA LÝ "}
                </p>
                <h2
                  {...mergeProps({
                    className:
                      "text-2xl sm:text-3xl font-semibold text-[var(--ui-accent)] tracking-tight",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {" Bức tranh toàn cảnh "}
                  <span
                    {...mergeProps({
                      className: "text-[var(--ui-accent)]",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {display(ctx.currentDistrict.name)}
                    {"."}
                  </span>
                </h2>
              </div>
              <div
                {...mergeProps({
                  className: "space-y-4 mb-7",
                  "data-sp-f9d979a0": "",
                })}
              >
                <div
                  {...mergeProps({
                    className:
                      "p-5 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)] border-l-4 border-l-[#183e54]",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className:
                        "flex items-center gap-2 text-xs font-bold text-[var(--ui-accent)] uppercase tracking-wider mb-2",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <svg
                      {...mergeProps({
                        className: "size-4 text-[var(--ui-accent)]",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      <path
                        {...mergeProps({
                          strokeLinecap: "round",
                          strokeLinejoin: "round",
                          d: "M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z",
                          "data-sp-f9d979a0": "",
                        })}
                      />
                      <path
                        {...mergeProps({
                          strokeLinecap: "round",
                          strokeLinejoin: "round",
                          d: "M15 11a3 3 0 11-6 0 3 3 0 016 0z",
                          "data-sp-f9d979a0": "",
                        })}
                      />
                    </svg>
                    <span
                      {...mergeProps({
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Vị trí địa lý & Kết nối giao thông cốt lõi"}
                    </span>
                  </div>
                  <p
                    {...mergeProps({
                      className:
                        "text-xs sm:text-[13px] leading-relaxed text-[var(--ui-accent)]",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {display(ctx.currentDistrict.overview)}
                  </p>
                </div>
                <div
                  {...mergeProps({
                    className:
                      "p-5 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)] border-l-4 border-l-[#198692]",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className:
                        "flex items-center gap-2 text-xs font-bold text-[var(--ui-accent)] uppercase tracking-wider mb-2",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <svg
                      {...mergeProps({
                        className: "size-4 text-[var(--ui-accent)]",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      <polyline
                        {...mergeProps({
                          points: "23 6 13.5 15.5 8.5 10.5 1 18",
                          "data-sp-f9d979a0": "",
                        })}
                      />
                      <polyline
                        {...mergeProps({
                          points: "17 6 23 6 23 12",
                          "data-sp-f9d979a0": "",
                        })}
                      />
                    </svg>
                    <span
                      {...mergeProps({
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Tiềm năng phát triển & Đặc tính thị trường"}
                    </span>
                  </div>
                  <p
                    {...mergeProps({
                      className:
                        "text-xs sm:text-[13px] leading-relaxed text-[var(--ui-accent)]",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {display(ctx.currentDistrict.aiInsights.growthPotential)}
                  </p>
                </div>
              </div>
              <div
                {...mergeProps({
                  className: "pt-6 border-t border-[var(--ui-border)]",
                  "data-sp-f9d979a0": "",
                })}
              >
                <div
                  {...mergeProps({
                    className: "flex items-center justify-between mb-4",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <p
                    {...mergeProps({
                      className:
                        "text-xs font-bold text-[var(--ui-accent)] uppercase tracking-[0.18em]",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {" CHỈ SỐ VĨ MÔ & MẶT BẰNG ĐƠN GIÁ "}
                  </p>
                  <span
                    {...mergeProps({
                      className: "text-[11px] text-[var(--ui-muted)]",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {"Đơn vị chuẩn hóa theo m²"}
                  </span>
                </div>
                <div
                  {...mergeProps({
                    className: "grid grid-cols-2 sm:grid-cols-3 gap-4",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className:
                        "p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <p
                      {...mergeProps({
                        className:
                          "text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Diện tích tự nhiên"}
                    </p>
                    <p
                      {...mergeProps({
                        className: "text-lg font-bold text-[var(--ui-accent)] mt-1.5",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {display(ctx.currentDistrict.macro.areaKm2)}
                    </p>
                    <p
                      {...mergeProps({
                        className: "text-[11px] text-[var(--ui-muted)] mt-1",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Quy hoạch đô thị Đà Nẵng"}
                    </p>
                  </div>
                  <div
                    {...mergeProps({
                      className:
                        "p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <p
                      {...mergeProps({
                        className:
                          "text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Quy mô dân số"}
                    </p>
                    <p
                      {...mergeProps({
                        className: "text-lg font-bold text-[var(--ui-accent)] mt-1.5",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {display(ctx.currentDistrict.macro.population)}
                    </p>
                    <p
                      {...mergeProps({
                        className:
                          "text-[11px] text-[var(--ui-accent)] font-semibold mt-1",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {display(ctx.currentDistrict.macro.density)}
                    </p>
                  </div>
                  <div
                    {...mergeProps({
                      className:
                        "p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <p
                      {...mergeProps({
                        className:
                          "text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Đơn giá TB Đất nền"}
                    </p>
                    <p
                      {...mergeProps({
                        className: "text-lg font-bold text-[var(--ui-muted)] mt-1.5",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {display(ctx.currentDistrict.macro.avgPricePerM2)}
                    </p>
                    <p
                      {...mergeProps({
                        className:
                          "text-[11px] text-[var(--ui-accent)] font-semibold mt-1",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"▲ "}
                      {display(ctx.currentDistrict.macro.priceGrowthYoY)}
                      {" YoY"}
                    </p>
                  </div>
                  <div
                    {...mergeProps({
                      className:
                        "p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <p
                      {...mergeProps({
                        className:
                          "text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Đơn giá TB Nhà phố"}
                    </p>
                    <p
                      {...mergeProps({
                        className: "text-lg font-bold text-[var(--ui-accent)] mt-1.5",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"~ "}
                      {display(ctx.latestHousePrice)}
                    </p>
                    <p
                      {...mergeProps({
                        className: "text-[11px] text-[var(--ui-muted)] mt-1",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Trục thương mại chính"}
                    </p>
                  </div>
                  <div
                    {...mergeProps({
                      className:
                        "p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <p
                      {...mergeProps({
                        className:
                          "text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Đơn giá TB Căn hộ"}
                    </p>
                    <p
                      {...mergeProps({
                        className: "text-lg font-bold text-[var(--ui-accent)] mt-1.5",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"~ "}
                      {display(ctx.latestApartmentPrice)}
                    </p>
                    <p
                      {...mergeProps({
                        className: "text-[11px] text-[var(--ui-muted)] mt-1",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Phân khúc thương mại & biển"}
                    </p>
                  </div>
                  <div
                    {...mergeProps({
                      className:
                        "p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <p
                      {...mergeProps({
                        className:
                          "text-[11px] font-semibold text-[var(--ui-accent)] uppercase tracking-wider",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Tin niêm yết công khai"}
                    </p>
                    <p
                      {...mergeProps({
                        className: "text-lg font-bold text-[var(--ui-accent)] mt-1.5",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {display(ctx.properties.length)}
                      {" BĐS"}
                    </p>
                    <p
                      {...mergeProps({
                        className:
                          "text-[11px] text-[var(--ui-accent)] font-semibold mt-1",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Thanh khoản: "}
                      {display(ctx.currentDistrict.macro.liquidityRating)}
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div
              {...mergeProps({
                className:
                  "lg:col-span-5 bg-brand-card rounded-3xl p-5 sm:p-6 border border-[var(--ui-border)] shadow-2xs lg:sticky lg:top-28",
                "data-sp-f9d979a0": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "flex items-center justify-between gap-3 mb-4",
                  "data-sp-f9d979a0": "",
                })}
              >
                <div
                  {...mergeProps({
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <p
                    {...mergeProps({
                      className:
                        "text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--ui-accent)]",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {"GIS SPATIAL EXPLORER"}
                  </p>
                  <h3
                    {...mergeProps({
                      className: "text-base font-bold text-[var(--ui-accent)] mt-0.5",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {" Bản đồ phân bố BĐS "}
                    {display(ctx.currentDistrict.shortName)}
                  </h3>
                </div>
                <span
                  {...mergeProps({
                    className:
                      "text-xs text-[var(--ui-accent)] font-bold bg-[var(--ui-surface)] border border-[var(--ui-border)] px-3 py-1 rounded-full",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {display(ctx.mapPoints.length)}
                  {" ghim tọa độ "}
                </span>
              </div>
              <div
                {...mergeProps({
                  className:
                    "h-[430px] rounded-2xl overflow-hidden border border-[var(--ui-border)] relative bg-[var(--ui-surface)]",
                  "data-sp-f9d979a0": "",
                })}
              >
                {ctx.mapPoints.length ? (
                  <BrowseTileMap
                    {...mergeProps({
                      points: ctx.mapPoints,
                      selectedId: ctx.selectedMapPropertyId,
                      onSelect: ($event) => {
                        return ((id) => ctx.router.push(`/listing/${id}`))?.(
                          $event,
                        );
                      },
                      "data-sp-f9d979a0": "",
                    })}
                  />
                ) : (
                  <div
                    {...mergeProps({
                      className:
                        "w-full h-full flex flex-col items-center justify-center bg-[var(--ui-surface)] text-[var(--ui-accent)] text-xs p-6 text-center",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <p
                      {...mergeProps({
                        className: "font-semibold text-[var(--ui-accent)] mb-1",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Đang tải tọa độ không gian..."}
                    </p>
                    <p
                      {...mergeProps({
                        className: "text-[11px] text-[var(--ui-muted)]",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Hiển thị các bất động sản có tọa độ xác thực tại "}
                      {display(ctx.currentDistrict.name)}
                    </p>
                  </div>
                )}
              </div>
              <div
                {...mergeProps({
                  className:
                    "mt-4 pt-3 border-t border-[var(--ui-border)] flex items-center justify-between text-xs text-[var(--ui-accent)]",
                  "data-sp-f9d979a0": "",
                })}
              >
                <span
                  {...mergeProps({
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {"Chọn nhãn giá trên bản đồ để mở chi tiết BĐS"}
                </span>
                <RouterLink
                  {...mergeProps({
                    to: {
                      path: "/map",
                      query: {
                        district: ctx.currentDistrict.shortName,
                      },
                    },
                    className:
                      "text-[var(--ui-accent)] hover:text-[var(--ui-accent)] font-bold transition inline-flex items-center gap-1",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <span
                    {...mergeProps({
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {"Mở toàn cảnh GIS"}
                  </span>
                  <span
                    {...mergeProps({
                      "aria-hidden": "true",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {"↗"}
                  </span>
                </RouterLink>
              </div>
            </div>
          </section>
          <section
            {...mergeProps({
              id: "planning",
              className:
                "scroll-mt-32 bg-brand-card rounded-3xl p-6 sm:p-8 lg:p-10 border border-[var(--ui-border)] shadow-2xs",
              "data-sp-f9d979a0": "",
            })}
          >
            <div
              {...mergeProps({
                className:
                  "flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 mb-7 border-b border-[var(--ui-border)]",
                "data-sp-f9d979a0": "",
              })}
            >
              <div
                {...mergeProps({
                  "data-sp-f9d979a0": "",
                })}
              >
                <p
                  {...mergeProps({
                    className:
                      "text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--ui-accent)] mb-2",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {" 02 / ĐỊNH HƯỚNG QUY HOẠCH ĐÔ THỊ 2030 – 2045 "}
                </p>
                <h2
                  {...mergeProps({
                    className:
                      "text-2xl sm:text-3xl font-semibold text-[var(--ui-accent)] tracking-tight",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {" Quy hoạch hạ tầng "}
                  <span
                    {...mergeProps({
                      className: "text-[var(--ui-accent)]",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {"& Động lực tăng trưởng."}
                  </span>
                </h2>
              </div>
              <p
                {...mergeProps({
                  className: "text-xs text-[var(--ui-accent)] max-w-md leading-relaxed",
                  "data-sp-f9d979a0": "",
                })}
              >
                {
                  " Các dự án hạ tầng trọng điểm và định hướng không gian đô thị tác động trực tiếp đến biên độ tăng giá dài hạn tại "
                }
                {display(ctx.currentDistrict.name)}
                {". "}
              </p>
            </div>
            <div
              {...mergeProps({
                className: "space-y-4",
                "data-sp-f9d979a0": "",
              })}
            >
              <div
                {...mergeProps({
                  className:
                    "rounded-2xl border border-[var(--ui-border)] overflow-hidden transition-all",
                  "data-sp-f9d979a0": "",
                })}
              >
                <button
                  {...mergeProps({
                    type: "button",
                    onClick: ($event) => {
                      ctx.togglePanel("planning1");
                    },
                    className: ["w-full px-6 py-4 flex items-center justify-between text-left text-xs sm:text-sm font-bold cursor-pointer transition-colors", ctx.expandedPanels.planning1
                      ? "bg-[var(--ui-soft)] text-brand-navy"
                      : "bg-[var(--ui-surface)] text-[var(--ui-accent)] hover:bg-[var(--ui-surface)]"],
                    
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className: "flex items-center gap-3.5",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className: ["text-xs font-mono px-2.5 py-1 rounded-full border", ctx.expandedPanels.planning1
                          ? "border-[var(--ui-border)]/40 text-[var(--ui-ink)] bg-brand-card/8"
                          : "border-[var(--ui-border)] text-[var(--ui-accent)] bg-brand-card"],
                        
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {" 01 "}
                    </span>
                    <span
                      {...mergeProps({
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Định hướng phát triển không gian đô thị & thương mại "}
                      {display(ctx.currentDistrict.name)}
                    </span>
                  </div>
                  <span
                    {...mergeProps({
                      className: ["text-xs transition-transform duration-200", [
                        ctx.expandedPanels.planning1
                          ? "rotate-180 text-[var(--ui-ink)]"
                          : "text-[var(--ui-accent)]",
                      ]],
                      
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {" ▼ "}
                  </span>
                </button>
                <div
                  {...mergeProps(
                    {
                      className:
                        "p-6 bg-brand-card text-xs sm:text-[13px] leading-relaxed text-[var(--ui-accent)] space-y-4 border-t border-[var(--ui-border)]",
                      "data-sp-f9d979a0": "",
                    },
                    {
                      style: {
                        display: ctx.expandedPanels.planning1
                          ? undefined
                          : "none",
                      },
                    },
                  )}
                >
                  <p
                    {...mergeProps({
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {
                      " Theo Quyết định điều chỉnh Quy hoạch chung TP. Đà Nẵng đến năm 2030, tầm nhìn 2045, "
                    }
                    <strong
                      {...mergeProps({
                        className: "text-[var(--ui-accent)]",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {display(ctx.currentDistrict.name)}
                    </strong>
                    {
                      " được định vị là cực tăng trưởng chiến lược với hệ sinh thái "
                    }
                    <strong
                      {...mergeProps({
                        className: "text-[var(--ui-accent)]",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {
                        "đô thị - thương mại dịch vụ - du lịch và cư trú chất lượng cao"
                      }
                    </strong>
                    {". "}
                  </p>
                  <div
                    {...mergeProps({
                      className: "grid grid-cols-1 md:grid-cols-2 gap-4 pt-1",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <div
                      {...mergeProps({
                        className:
                          "p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      <p
                        {...mergeProps({
                          className: "font-bold text-[var(--ui-accent)] mb-1.5",
                          "data-sp-f9d979a0": "",
                        })}
                      >
                        {"Tái cấu trúc không gian & Trục cảnh quan chủ đạo"}
                      </p>
                      <p
                        {...mergeProps({
                          className: "text-xs text-[var(--ui-accent)] leading-relaxed",
                          "data-sp-f9d979a0": "",
                        })}
                      >
                        {
                          "Ưu tiên phát triển các tổ hợp thương mại dịch vụ hiện đại, nâng cấp hạ tầng kỹ thuật ngầm hóa và mở rộng không gian công cộng phục vụ cư dân."
                        }
                      </p>
                    </div>
                    <div
                      {...mergeProps({
                        className:
                          "p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)]",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      <p
                        {...mergeProps({
                          className: "font-bold text-[var(--ui-accent)] mb-1.5",
                          "data-sp-f9d979a0": "",
                        })}
                      >
                        {"Kinh tế dịch vụ & Khai thác dòng tiền"}
                      </p>
                      <p
                        {...mergeProps({
                          className: "text-xs text-[var(--ui-accent)] leading-relaxed",
                          "data-sp-f9d979a0": "",
                        })}
                      >
                        {
                          "Gia tăng mật độ các tuyến phố chuyên doanh, tổ hợp văn phòng - lưu trú cao cấp nhằm tối ưu tỷ suất khai thác cho thuê bất động sản."
                        }
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div
                {...mergeProps({
                  className:
                    "rounded-2xl border border-[var(--ui-border)] overflow-hidden transition-all",
                  "data-sp-f9d979a0": "",
                })}
              >
                <button
                  {...mergeProps({
                    type: "button",
                    onClick: ($event) => {
                      ctx.togglePanel("planning2");
                    },
                    className: ["w-full px-6 py-4 flex items-center justify-between text-left text-xs sm:text-sm font-bold cursor-pointer transition-colors", ctx.expandedPanels.planning2
                      ? "bg-[var(--ui-soft)] text-brand-navy"
                      : "bg-[var(--ui-surface)] text-[var(--ui-accent)] hover:bg-[var(--ui-surface)]"],
                    
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className: "flex items-center gap-3.5",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className: ["text-xs font-mono px-2.5 py-1 rounded-full border", ctx.expandedPanels.planning2
                          ? "border-[var(--ui-border)]/40 text-[var(--ui-ink)] bg-brand-card/8"
                          : "border-[var(--ui-border)] text-[var(--ui-accent)] bg-brand-card"],
                        
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {" 02 "}
                    </span>
                    <span
                      {...mergeProps({
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Danh mục dự án hạ tầng & Giao thông trọng điểm tại "}
                      {display(ctx.currentDistrict.shortName)}
                    </span>
                  </div>
                  <span
                    {...mergeProps({
                      className: ["text-xs transition-transform duration-200", [
                        ctx.expandedPanels.planning2
                          ? "rotate-180 text-[var(--ui-ink)]"
                          : "text-[var(--ui-accent)]",
                      ]],
                      
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {" ▼ "}
                  </span>
                </button>
                <div
                  {...mergeProps(
                    {
                      className: "p-6 bg-brand-card border-t border-[var(--ui-border)]",
                      "data-sp-f9d979a0": "",
                    },
                    {
                      style: {
                        display: ctx.expandedPanels.planning2
                          ? undefined
                          : "none",
                      },
                    },
                  )}
                >
                  <div
                    {...mergeProps({
                      className: "grid grid-cols-1 md:grid-cols-3 gap-4",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {renderList(ctx.currentDistrict.infrastructure, (item) => (
                      <div
                        key={item.name}
                        {...mergeProps({
                          className:
                            "p-4 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)] flex flex-col justify-between gap-3",
                          "data-sp-f9d979a0": "",
                        })}
                      >
                        <div
                          {...mergeProps({
                            "data-sp-f9d979a0": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              className:
                                "text-[10px] font-bold px-2.5 py-1 rounded-full inline-block mb-2.5 bg-brand-card border border-[var(--ui-border)] text-[var(--ui-accent)] uppercase tracking-wider",
                              "data-sp-f9d979a0": "",
                            })}
                          >
                            {" ● "}
                            {display(item.status)}
                          </span>
                          <p
                            {...mergeProps({
                              className:
                                "font-bold text-[var(--ui-accent)] text-xs sm:text-[13px] leading-snug",
                              "data-sp-f9d979a0": "",
                            })}
                          >
                            {display(item.name)}
                          </p>
                        </div>
                        <p
                          {...mergeProps({
                            className: "text-[11px] text-[var(--ui-muted)]",
                            "data-sp-f9d979a0": "",
                          })}
                        >
                          {"Tác động trực tiếp tới giá trị kết nối khu vực"}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div
                {...mergeProps({
                  className:
                    "rounded-2xl border border-[var(--ui-border)] overflow-hidden transition-all",
                  "data-sp-f9d979a0": "",
                })}
              >
                <button
                  {...mergeProps({
                    type: "button",
                    onClick: ($event) => {
                      ctx.togglePanel("planning3");
                    },
                    className: ["w-full px-6 py-4 flex items-center justify-between text-left text-xs sm:text-sm font-bold cursor-pointer transition-colors", ctx.expandedPanels.planning3
                      ? "bg-[var(--ui-soft)] text-brand-navy"
                      : "bg-[var(--ui-surface)] text-[var(--ui-accent)] hover:bg-[var(--ui-surface)]"],
                    
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className: "flex items-center gap-3.5",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className: ["text-xs font-mono px-2.5 py-1 rounded-full border", ctx.expandedPanels.planning3
                          ? "border-[var(--ui-border)]/40 text-[var(--ui-ink)] bg-brand-card/8"
                          : "border-[var(--ui-border)] text-[var(--ui-accent)] bg-brand-card"],
                        
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {" 03 "}
                    </span>
                    <span
                      {...mergeProps({
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Hệ sinh thái tiện ích ngoại khu & Chất lượng sống"}
                    </span>
                  </div>
                  <span
                    {...mergeProps({
                      className: ["text-xs transition-transform duration-200", [
                        ctx.expandedPanels.planning3
                          ? "rotate-180 text-[var(--ui-ink)]"
                          : "text-[var(--ui-accent)]",
                      ]],
                      
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {" ▼ "}
                  </span>
                </button>
                <div
                  {...mergeProps(
                    {
                      className:
                        "p-6 bg-brand-card text-xs sm:text-[13px] leading-relaxed text-[var(--ui-accent)] border-t border-[var(--ui-border)]",
                      "data-sp-f9d979a0": "",
                    },
                    {
                      style: {
                        display: ctx.expandedPanels.planning3
                          ? undefined
                          : "none",
                      },
                    },
                  )}
                >
                  <p
                    {...mergeProps({
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <strong
                      {...mergeProps({
                        className: "text-[var(--ui-accent)]",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {display(ctx.currentDistrict.name)}
                    </strong>
                    {
                      " sở hữu mạng lưới tiện ích đô thị hoàn chỉnh trong bán kính 1–3 km: hệ thống trường học liên cấp, bệnh viện & trạm y tế, siêu thị thương mại, công viên cây xanh và các trục giao thông kết nối thẳng ra sân bay quốc tế Đà Nẵng cũng như bãi biển. "
                    }
                  </p>
                </div>
              </div>
            </div>
          </section>
          <section
            {...mergeProps({
              id: "price-trend",
              className: "scroll-mt-32 space-y-6",
              "data-sp-f9d979a0": "",
            })}
          >
            <PriceTrendChart
              {...mergeProps({
                history: ctx.currentDistrict.priceHistory,
                "data-sp-f9d979a0": "",
              })}
            />
            <div
              {...mergeProps({
                className:
                  "rounded-3xl p-6 sm:p-8 lg:p-10 bg-gradient-to-br from-[var(--ui-soft)] via-[var(--ui-soft)] to-[var(--ui-soft)] text-brand-navy shadow-xl border border-[var(--ui-border)]/35 relative overflow-hidden",
                "data-sp-f9d979a0": "",
              })}
            >
              <div
                {...mergeProps({
                  className:
                    "pointer-events-none absolute -right-16 -bottom-16 h-64 w-64 rounded-full bg-[var(--ui-soft)]/10 blur-3xl",
                  "aria-hidden": "true",
                  "data-sp-f9d979a0": "",
                })}
              />
              <div
                {...mergeProps({
                  className:
                    "relative z-10 flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 mb-6 border-b border-brand-line/12",
                  "data-sp-f9d979a0": "",
                })}
              >
                <div
                  {...mergeProps({
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className:
                        "inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-card/10 text-[var(--ui-ink)] text-[11px] font-bold border border-[var(--ui-border)]/30 tracking-wider uppercase mb-3",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className:
                          "w-2 h-2 rounded-full bg-[var(--ui-success-bg)] animate-pulse",
                        "data-sp-f9d979a0": "",
                      })}
                    />
                    <span
                      {...mergeProps({
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"SMARTPROP AI MARKET INTELLIGENCE · MODEL V6"}
                    </span>
                  </div>
                  <h3
                    {...mergeProps({
                      className:
                        "text-xl sm:text-2xl font-semibold text-brand-navy tracking-tight",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {" Nhận định chuyên sâu & Dự báo xu hướng "}
                    <span
                      {...mergeProps({
                        className: "text-[var(--ui-ink)]",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {display(ctx.currentDistrict.name)}
                      {"."}
                    </span>
                  </h3>
                </div>
                <RouterLink
                  {...mergeProps({
                    to: "/advisor",
                    className:
                      "self-start md:self-auto inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-[var(--ui-soft)] hover:bg-[var(--ui-soft)] text-[var(--ui-accent)] text-xs font-bold transition shadow-sm",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <span
                    {...mergeProps({
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {"Mở AI Advisor phân tích danh mục"}
                  </span>
                  <span
                    {...mergeProps({
                      "aria-hidden": "true",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {"→"}
                  </span>
                </RouterLink>
              </div>
              <div
                {...mergeProps({
                  className:
                    "relative z-10 grid grid-cols-1 md:grid-cols-3 gap-5 text-xs sm:text-[13px] leading-relaxed",
                  "data-sp-f9d979a0": "",
                })}
              >
                <div
                  {...mergeProps({
                    className:
                      "bg-brand-card/8 backdrop-blur-md rounded-2xl p-5 border border-brand-line/12",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className:
                        "flex items-center gap-2 font-bold text-[var(--ui-ink)] uppercase tracking-wider text-xs mb-2.5",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <svg
                      {...mergeProps({
                        className: "size-4 shrink-0",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2.2",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      <polyline
                        {...mergeProps({
                          points: "23 6 13.5 15.5 8.5 10.5 1 18",
                          "data-sp-f9d979a0": "",
                        })}
                      />
                      <polyline
                        {...mergeProps({
                          points: "17 6 23 6 23 12",
                          "data-sp-f9d979a0": "",
                        })}
                      />
                    </svg>
                    <span
                      {...mergeProps({
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Động lực tăng giá"}
                    </span>
                  </div>
                  <p
                    {...mergeProps({
                      className: "text-brand-navy/85",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {display(ctx.currentDistrict.aiInsights.growthPotential)}
                  </p>
                </div>
                <div
                  {...mergeProps({
                    className:
                      "bg-brand-card/8 backdrop-blur-md rounded-2xl p-5 border border-brand-line/12",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className:
                        "flex items-center gap-2 font-bold text-[var(--ui-success-text)] uppercase tracking-wider text-xs mb-2.5",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <svg
                      {...mergeProps({
                        className: "size-4 shrink-0",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2.2",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      <path
                        {...mergeProps({
                          d: "M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6",
                          "data-sp-f9d979a0": "",
                        })}
                      />
                    </svg>
                    <span
                      {...mergeProps({
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Thanh khoản thị trường"}
                    </span>
                  </div>
                  <p
                    {...mergeProps({
                      className: "text-brand-navy/85",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {display(ctx.currentDistrict.aiInsights.liquidity)}
                  </p>
                </div>
                <div
                  {...mergeProps({
                    className:
                      "bg-brand-card/8 backdrop-blur-md rounded-2xl p-5 border border-brand-line/12",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className:
                        "flex items-center gap-2 font-bold text-brand-navy uppercase tracking-wider text-xs mb-2.5",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <svg
                      {...mergeProps({
                        className: "size-4 shrink-0",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2.2",
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      <circle
                        {...mergeProps({
                          cx: "12",
                          cy: "12",
                          r: "10",
                          "data-sp-f9d979a0": "",
                        })}
                      />
                      <polyline
                        {...mergeProps({
                          points: "12 6 12 12 16 14",
                          "data-sp-f9d979a0": "",
                        })}
                      />
                    </svg>
                    <span
                      {...mergeProps({
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {"Khuyến nghị chiến lược"}
                    </span>
                  </div>
                  <p
                    {...mergeProps({
                      className: "text-brand-navy/85",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {display(ctx.currentDistrict.aiInsights.recommendation)}
                  </p>
                </div>
              </div>
            </div>
          </section>
          <section
            {...mergeProps({
              id: "listings",
              className:
                "scroll-mt-32 bg-[var(--ui-surface)] rounded-3xl p-6 sm:p-8 lg:p-10 border border-[var(--ui-border)]",
              "data-sp-f9d979a0": "",
            })}
          >
            <div
              {...mergeProps({
                className:
                  "flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-6 mb-7 border-b border-[var(--ui-border)]",
                "data-sp-f9d979a0": "",
              })}
            >
              <div
                {...mergeProps({
                  "data-sp-f9d979a0": "",
                })}
              >
                <p
                  {...mergeProps({
                    className:
                      "text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--ui-accent)] mb-2",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {" 04 / BẤT ĐỘNG SẢN THỰC TẾ ĐANG NIÊM YẾT "}
                </p>
                <h2
                  {...mergeProps({
                    className:
                      "text-2xl sm:text-3xl font-semibold text-[var(--ui-accent)] tracking-tight",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {" Tin đăng công khai tại "}
                  <span
                    {...mergeProps({
                      className: "text-[var(--ui-accent)]",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {display(ctx.currentDistrict.name)}
                    {"."}
                  </span>
                </h2>
                <p
                  {...mergeProps({
                    className: "text-xs text-[var(--ui-accent)] mt-1.5",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {
                    " Tin đã kiểm duyệt trên hệ thống SmartProp · Hỗ trợ đối chiếu bản đồ GIS và so sánh trực tiếp "
                  }
                </p>
              </div>
              <RouterLink
                {...mergeProps({
                  to: {
                    path: "/listings",
                    query: {
                      district: ctx.currentDistrict.shortName,
                    },
                  },
                  className:
                    "inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[var(--ui-soft)] text-brand-navy hover:bg-[var(--ui-soft)] text-xs font-bold transition self-start sm:self-auto shadow-xs",
                  "data-sp-f9d979a0": "",
                })}
              >
                <span
                  {...mergeProps({
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {"Xem tất cả tại "}
                  {display(ctx.currentDistrict.shortName)}
                </span>
                <span
                  {...mergeProps({
                    "aria-hidden": "true",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {"→"}
                </span>
              </RouterLink>
            </div>
            {ctx.loadingProperties ? (
              <div
                {...mergeProps({
                  className:
                    "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6",
                  "data-sp-f9d979a0": "",
                })}
              >
                {renderList(3, (n) => (
                  <div
                    key={n}
                    {...mergeProps({
                      className:
                        "h-[420px] rounded-3xl bg-brand-card/60 animate-pulse border border-[var(--ui-border)]",
                      "data-sp-f9d979a0": "",
                    })}
                  />
                ))}
              </div>
            ) : ctx.properties.length ? (
              <div
                {...mergeProps({
                  className:
                    "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6",
                  "data-sp-f9d979a0": "",
                })}
              >
                {renderList(ctx.properties.slice(0, 6), (item) => (
                  <ListingCard
                    key={item.id}
                    {...mergeProps({
                      property: item,
                      className: {
                        "ring-2 ring-[var(--ui-border)] ring-offset-2":
                          ctx.selectedMapPropertyId === item.id,
                      },
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    <button
                      {...mergeProps({
                        type: "button",
                        className: "market-card-action",
                        "aria-pressed": ctx.selectedMapPropertyId === item.id,
                        onClick: ($event) => {
                          ctx.focusOnDistrictMap(item.id);
                        },
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {" ⌖ Bản đồ "}
                    </button>
                    <button
                      {...mergeProps({
                        type: "button",
                        className: "market-card-action compare",
                        "aria-pressed": ctx.compare.has(item.id),
                        onClick: ($event) => {
                          ctx.compare.toggle(item);
                        },
                        "data-sp-f9d979a0": "",
                      })}
                    >
                      {display(
                        ctx.compare.has(item.id) ? "✓ Đã chọn" : "+ So sánh",
                      )}
                    </button>
                  </ListingCard>
                ))}
              </div>
            ) : (
              <div
                {...mergeProps({
                  className:
                    "rounded-3xl bg-brand-card p-12 text-center border border-[var(--ui-border)]",
                  "data-sp-f9d979a0": "",
                })}
              >
                <p
                  {...mergeProps({
                    className: "text-lg font-semibold text-[var(--ui-accent)]",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {"Chưa có tin đăng công khai tại khu vực này"}
                </p>
                <p
                  {...mergeProps({
                    className: "text-xs text-[var(--ui-accent)] mt-2 mb-5",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  {
                    "Hãy khám phá các quận lân cận hoặc xem toàn bộ danh sách bất động sản Đà Nẵng."
                  }
                </p>
                <RouterLink
                  {...mergeProps({
                    to: "/listings",
                    className:
                      "inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[var(--ui-soft)] text-brand-navy text-xs font-bold",
                    "data-sp-f9d979a0": "",
                  })}
                >
                  <span
                    {...mergeProps({
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {"Mở danh sách BĐS"}
                  </span>
                  <span
                    {...mergeProps({
                      "aria-hidden": "true",
                      "data-sp-f9d979a0": "",
                    })}
                  >
                    {"→"}
                  </span>
                </RouterLink>
              </div>
            )}
          </section>
          <section
            {...mergeProps({
              id: "neighboring",
              className:
                "scroll-mt-32 bg-brand-card rounded-3xl p-6 sm:p-8 lg:p-10 border border-[var(--ui-border)] shadow-2xs space-y-8",
              "data-sp-f9d979a0": "",
            })}
          >
            <TopSearchedAreas
              {...mergeProps({
                currentSlug: ctx.currentDistrict.slug,
                eyebrow: "05 / XU HƯỚNG TÌM KIẾM · ĐÀ NẴNG",
                mode: "market",
                onSelectDistrict: ($event) => {
                  return ctx.selectDistrict?.($event);
                },
                "data-sp-f9d979a0": "",
              })}
            />
          </section>
        </div>
      </div>
    </div>,
  ]);
});
