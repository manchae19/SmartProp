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
import { useRouter } from "../../shared/routing/router.jsx";
import { DISTRICT_PROFILES } from "./marketData.js";
function setup(__props) {
  const props = propsForSetup(__props, {
    currentSlug: {
      type: String,
      default: "",
    },
    eyebrow: {
      type: String,
      default: "XU HƯỚNG TÌM KIẾM · ĐÀ NẴNG",
    },
    mode: {
      type: String,
      default: "market", // 'market' -> navigates to /market/:slug, 'listings' -> navigates to /listings?district=...
    },
  });
  const emit = emitForProps(__props, ["select-district"]);
  const router = useRouter();

  // Ordered by search popularity (viewsCount)
  const orderedDistricts = computed(() => {
    const all = [
      DISTRICT_PROFILES["Sơn Trà"],
      DISTRICT_PROFILES["Hải Châu"],
      DISTRICT_PROFILES["Ngũ Hành Sơn"],
      DISTRICT_PROFILES["Liên Chiểu"],
      DISTRICT_PROFILES["Cẩm Lệ"],
      DISTRICT_PROFILES["Thanh Khê"],
    ].filter(Boolean);

    // If currentSlug is provided and matches one of the top 5, we can either keep Top 5 or rotate so all 5 other districts show
    if (props.currentSlug) {
      const others = all.filter((d) => d.slug !== props.currentSlug);
      if (others.length === 5) return others;
    }
    return all.slice(0, 5);
  });
  const featuredDistrict = computed(() => orderedDistricts.value[0] || null);
  const secondaryDistricts = computed(() => orderedDistricts.value.slice(1, 5));
  function handleSelect(district) {
    emit("select-district", district.slug);
    if (props.mode === "listings") {
      router.push({
        path: "/listings",
        query: {
          district: district.shortName,
        },
      });
    } else {
      router.push({
        path: `/market/${district.slug}`,
      });
      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    }
  }
  return {
    computed,
    useRouter,
    DISTRICT_PROFILES,
    props,
    emit,
    router,
    orderedDistricts,
    featuredDistrict,
    secondaryDistricts,
    handleSelect,
  };
}
export default React.forwardRef(function TopSearchedAreas(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div
      {...mergeProps({
        className: "top-searched-areas",
      })}
    >
      <div
        {...mergeProps({
          className:
            "flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6",
        })}
      >
        <div {...mergeProps({})}>
          <p
            {...mergeProps({
              className:
                "text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--ui-accent)] mb-2",
            })}
          >
            {display(ctx.eyebrow)}
          </p>
          <h2
            {...mergeProps({
              className:
                "text-2xl sm:text-3xl font-semibold text-[var(--ui-accent)] tracking-tight",
            })}
          >
            {" Khu vực được tìm kiếm "}
            <span
              {...mergeProps({
                className: "text-[var(--ui-accent)]",
              })}
            >
              {"nhiều nhất."}
            </span>
          </h2>
        </div>
        <RouterLink
          {...mergeProps({
            to: "/listings",
            className:
              "inline-flex items-center gap-2 text-xs font-bold text-[var(--ui-accent)] hover:text-[var(--ui-accent)] transition self-start sm:self-auto",
          })}
        >
          <span {...mergeProps({})}>{"Khám phá toàn bộ tin đăng Đà Nẵng"}</span>
          <span
            {...mergeProps({
              "aria-hidden": "true",
            })}
          >
            {"→"}
          </span>
        </RouterLink>
      </div>
      {ctx.featuredDistrict ? (
        <div
          {...mergeProps({
            className: "grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch",
          })}
        >
          <article
            {...mergeProps({
              onClick: ($event) => {
                ctx.handleSelect(ctx.featuredDistrict);
              },
              role: "button",
              tabIndex: "0",
              onKeyDown: ($event) => {
                if ($event.key !== "Enter") return;
                $event.preventDefault();
                ctx.handleSelect(ctx.featuredDistrict);
              },
              onKeyDown: ($event) => {
                if ($event.key !== " ") return;
                $event.preventDefault();
                ctx.handleSelect(ctx.featuredDistrict);
              },
              "aria-label": `${ctx.featuredDistrict.name}, Đà Nẵng - ${ctx.featuredDistrict.viewsCount} lượt xem`,
              className:
                "lg:col-span-6 relative min-h-[340px] sm:min-h-[400px] lg:h-[468px] rounded-[22px] overflow-hidden cursor-pointer group shadow-md border border-[var(--ui-border)] select-none",
            })}
          >
            <img
              {...mergeProps({
                src: ctx.featuredDistrict.image,
                alt: ctx.featuredDistrict.name,
                loading: "lazy",
                className:
                  "absolute inset-0 w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-105",
              })}
            />
            <div
              {...mergeProps({
                className:
                  "absolute inset-0 bg-gradient-to-t from-[var(--ui-soft)]/90 via-[var(--ui-soft)]/25 to-brand-cream/15 transition-opacity duration-300 group-hover:from-[var(--ui-soft)]/95",
                "aria-hidden": "true",
              })}
            />
            <div
              {...mergeProps({
                className: "absolute top-4 left-4 z-10 flex items-center gap-2",
              })}
            >
              <span
                {...mergeProps({
                  className:
                    "inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-[var(--ui-surface)]/95 backdrop-blur-md text-[var(--ui-ink)] text-xs font-bold shadow-md border border-[var(--ui-border)]",
                })}
              >
                <svg
                  {...mergeProps({
                    className: "size-3.5 text-[var(--ui-muted)] shrink-0",
                    viewBox: "0 0 24 24",
                    fill: "currentColor",
                  })}
                >
                  <path
                    {...mergeProps({
                      d: "M12 23c-4.97 0-9-3.58-9-8 0-3.19 2.13-6.02 4.5-7.86.37-.29.91-.03.91.44 0 1.18.47 2.26 1.29 3.01.29.27.76.11.83-.28.36-2.06 1.68-4.58 4.13-6.15.39-.25.9.06.86.52-.12 1.46.38 2.86 1.38 3.92 2.41 2.55 4.1 5.13 4.1 8.4 0 4.42-4.03 8-9 8z",
                    })}
                  />
                </svg>
                <span {...mergeProps({})}>
                  {display(ctx.featuredDistrict.viewsCount)}
                  {" lượt xem"}
                </span>
              </span>
            </div>
            <div
              {...mergeProps({
                className: "absolute top-4 right-4 z-10",
              })}
            >
              <span
                {...mergeProps({
                  className:
                    "inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-[var(--ui-soft)]/85 backdrop-blur-md text-[var(--ui-ink)] text-xs font-bold border border-[var(--ui-border)]/35",
                })}
              >
                <span {...mergeProps({})}>
                  {display(ctx.featuredDistrict.macro.avgPricePerM2)}
                </span>
                <span
                  {...mergeProps({
                    className: "text-[var(--ui-success-text)] ml-1",
                  })}
                >
                  {"▲ "}
                  {display(ctx.featuredDistrict.macro.priceGrowthYoY)}
                </span>
              </span>
            </div>
            <div
              {...mergeProps({
                className:
                  "absolute inset-x-0 bottom-0 p-6 sm:p-7 z-10 flex items-end justify-between gap-4",
              })}
            >
              <div {...mergeProps({})}>
                <h3
                  {...mergeProps({
                    className:
                      "text-2xl sm:text-[26px] font-bold text-brand-navy tracking-tight leading-tight group-hover:text-[var(--ui-ink)] transition-colors",
                  })}
                >
                  {display(ctx.featuredDistrict.name)}
                  {", Đà Nẵng "}
                </h3>
                <p
                  {...mergeProps({
                    className:
                      "text-xs sm:text-sm text-brand-navy/90 font-medium mt-1.5",
                  })}
                >
                  {display(ctx.featuredDistrict.activeListingsCount)}
                  {" bất động sản đang bán "}
                </p>
              </div>
              <span
                {...mergeProps({
                  className:
                    "w-10 h-10 rounded-full bg-brand-card/15 backdrop-blur-md border border-brand-line/25 text-brand-navy flex items-center justify-center group-hover:bg-[var(--ui-soft)] group-hover:text-[var(--ui-accent)] group-hover:border-[var(--ui-border)] transition-all shrink-0",
                })}
              >
                {" ↗ "}
              </span>
            </div>
          </article>
          <div
            {...mergeProps({
              className: "lg:col-span-6 grid grid-cols-1 sm:grid-cols-2 gap-5",
            })}
          >
            {renderList(ctx.secondaryDistricts, (item) => (
              <article
                key={item.id}
                {...mergeProps({
                  onClick: ($event) => {
                    ctx.handleSelect(item);
                  },
                  role: "button",
                  tabIndex: "0",
                  onKeyDown: ($event) => {
                    if ($event.key !== "Enter") return;
                    $event.preventDefault();
                    ctx.handleSelect(item);
                  },
                  onKeyDown: ($event) => {
                    if ($event.key !== " ") return;
                    $event.preventDefault();
                    ctx.handleSelect(item);
                  },
                  "aria-label": `${item.name}, Đà Nẵng - ${item.viewsCount} lượt xem`,
                  className:
                    "relative h-[224px] rounded-[20px] overflow-hidden cursor-pointer group shadow-sm border border-[var(--ui-border)] select-none",
                })}
              >
                <img
                  {...mergeProps({
                    src: item.image,
                    alt: item.name,
                    loading: "lazy",
                    className:
                      "absolute inset-0 w-full h-full object-cover transition-transform duration-700 ease-out group-hover:scale-105",
                  })}
                />
                <div
                  {...mergeProps({
                    className:
                      "absolute inset-0 bg-gradient-to-t from-[var(--ui-soft)]/90 via-[var(--ui-soft)]/25 to-brand-cream/10 transition-opacity duration-300 group-hover:from-[var(--ui-soft)]/95",
                    "aria-hidden": "true",
                  })}
                />
                <div
                  {...mergeProps({
                    className: "absolute top-3.5 left-3.5 z-10",
                  })}
                >
                  <span
                    {...mergeProps({
                      className:
                        "inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-[var(--ui-surface)]/95 backdrop-blur-md text-[var(--ui-ink)] text-[11px] font-bold shadow-sm border border-[var(--ui-border)]",
                    })}
                  >
                    <svg
                      {...mergeProps({
                        className: "size-3 text-[var(--ui-muted)] shrink-0",
                        viewBox: "0 0 24 24",
                        fill: "currentColor",
                      })}
                    >
                      <path
                        {...mergeProps({
                          d: "M12 23c-4.97 0-9-3.58-9-8 0-3.19 2.13-6.02 4.5-7.86.37-.29.91-.03.91.44 0 1.18.47 2.26 1.29 3.01.29.27.76.11.83-.28.36-2.06 1.68-4.58 4.13-6.15.39-.25.9.06.86.52-.12 1.46.38 2.86 1.38 3.92 2.41 2.55 4.1 5.13 4.1 8.4 0 4.42-4.03 8-9 8z",
                        })}
                      />
                    </svg>
                    <span {...mergeProps({})}>
                      {display(item.viewsCount)}
                      {" lượt xem"}
                    </span>
                  </span>
                </div>
                <div
                  {...mergeProps({
                    className: "absolute top-3.5 right-3.5 z-10",
                  })}
                >
                  <span
                    {...mergeProps({
                      className:
                        "px-2.5 py-1 rounded-lg bg-[var(--ui-soft)]/80 backdrop-blur-md text-[var(--ui-ink)] text-[10px] font-bold border border-brand-line/15",
                    })}
                  >
                    {display(item.macro.avgPricePerM2)}
                  </span>
                </div>
                <div
                  {...mergeProps({
                    className:
                      "absolute inset-x-0 bottom-0 p-4 sm:p-5 z-10 flex items-end justify-between gap-2",
                  })}
                >
                  <div {...mergeProps({})}>
                    <h3
                      {...mergeProps({
                        className:
                          "text-base sm:text-[17px] font-bold text-brand-navy tracking-tight leading-snug group-hover:text-[var(--ui-ink)] transition-colors",
                      })}
                    >
                      {display(item.name)}
                      {", Đà Nẵng "}
                    </h3>
                    <p
                      {...mergeProps({
                        className: "text-xs text-brand-navy/85 font-medium mt-0.5",
                      })}
                    >
                      {display(item.activeListingsCount)}
                      {" bất động sản đang bán "}
                    </p>
                  </div>
                  <span
                    {...mergeProps({
                      className:
                        "w-8 h-8 rounded-full bg-brand-card/15 backdrop-blur-md border border-brand-line/20 text-brand-navy text-xs flex items-center justify-center group-hover:bg-[var(--ui-soft)] group-hover:text-[var(--ui-accent)] transition-all shrink-0",
                    })}
                  >
                    {" ↗ "}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </div>
      ) : null}
    </div>,
  ]);
});
