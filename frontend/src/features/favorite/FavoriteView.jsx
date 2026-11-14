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
import { useRouter } from "../../shared/routing/router.jsx";
import { api } from "../auth/api.js";
import {
  useList,
  LegacyState,
  LegacyPager,
  PrivateImage,
} from "../../shared/lib/legacy.js";
import { collectionProperty } from "../home/collection.js";
import { useCollection, typeCode } from "../home/useCollection.js";
import "./FavoriteView.css";
function setup(__props) {
  const router = useRouter();

  // SMARTPROP FAVORITES 2.0
  // Data is loaded from the existing backend.

  const activeFilter = ref("Tất cả");
  const sortType = ref("Mới lưu");
  const searchText = ref("");
  const removedItem = ref(null);
  const filters = ["Tất cả", "Nhà phố", "Căn hộ", "Đất nền"];
  const state = useCollection(
    "/users/me/saved-properties",
    "/users/me/saved-properties/summary",
    () => ({
      keyword: searchText.value.trim(),
      propertyType: typeCode[activeFilter.value],
      sort: {
        "Mới lưu": "newest",
        "Cũ nhất": "oldest",
        "Giá thấp": "priceAsc",
        "Giá cao": "priceDesc",
      }[sortType.value],
    }),
  );
  const listings = computed(() => state.items.map(collectionProperty));
  const filteredListings = listings;
  const propertyTypeCount = computed(() =>
    state.summary
      ? Object.keys(state.summary.byPropertyType || {}).length
      : "—",
  );
  const priceGroups = computed(() => state.summary?.priceGroups || []);
  const filterCount = (label) =>
    state.summary
      ? label === "Tất cả"
        ? state.summary.totalVisible
        : state.summary.byPropertyType?.[typeCode[label]] || 0
      : "—";
  function formatPrice(price) {
    return price.toLocaleString("vi-VN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  async function removeFavorite(id) {
    const item = listings.value.find((x) => x.id === id);
    if (!item || state.busy) return;
    await state.run(async () => {
      await api("/users/me/saved-properties/" + id, {
        method: "DELETE",
      });
      removedItem.value = item;
      await state.reload();
    });
  }
  async function undoRemove() {
    if (!removedItem.value || state.busy) return;
    await state.run(async () => {
      await api("/users/me/saved-properties/" + removedItem.value.id, {
        method: "PUT",
      });
      removedItem.value = null;
      await state.reload();
    });
  }
  function openListing(id) {
    router.push("/listing/" + id);
  }
  function resetFilters() {
    activeFilter.value = "Tất cả";
    searchText.value = "";
    sortType.value = "Mới lưu";
  }
  return {
    ref,
    computed,
    useRouter,
    api,
    useList,
    LegacyState,
    LegacyPager,
    PrivateImage,
    collectionProperty,
    useCollection,
    typeCode,
    router,
    activeFilter,
    sortType,
    searchText,
    removedItem,
    filters,
    state,
    listings,
    filteredListings,
    propertyTypeCount,
    priceGroups,
    filterCount,
    formatPrice,
    removeFavorite,
    undoRemove,
    openListing,
    resetFilters,
  };
}
export default React.forwardRef(function FavoriteView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="FavoriteView"
      {...mergeProps({
        className: "sp-favorites min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)]",
        "data-sp-928bf8cf": "",
      })}
    >
      <section
        {...mergeProps({
          className: "relative overflow-hidden border-b border-[var(--ui-border)]",
          "data-sp-928bf8cf": "",
        })}
      >
        <div
          {...mergeProps({
            className:
              "pointer-events-none absolute -right-28 -top-32 h-[420px] w-[420px] rounded-full border border-[var(--ui-border)]/20",
            "data-sp-928bf8cf": "",
          })}
        />
        <div
          {...mergeProps({
            className:
              "pointer-events-none absolute -right-10 -top-12 h-[280px] w-[280px] rounded-full border border-[var(--ui-border)]/20",
            "data-sp-928bf8cf": "",
          })}
        />
        <div
          {...mergeProps({
            className:
              "relative mx-auto max-w-[1440px] px-5 py-12 md:px-10 md:py-16",
            "data-sp-928bf8cf": "",
          })}
        >
          <div
            {...mergeProps({
              className: "flex flex-wrap items-end justify-between gap-8",
              "data-sp-928bf8cf": "",
            })}
          >
            <div
              {...mergeProps({
                "data-sp-928bf8cf": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "flex items-center gap-3",
                  "data-sp-928bf8cf": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "h-px w-9 bg-[var(--ui-soft)]",
                    "data-sp-928bf8cf": "",
                  })}
                />
                <p
                  {...mergeProps({
                    className:
                      "text-xs font-bold uppercase tracking-[0.22em] text-[var(--ui-muted)]",
                    "data-sp-928bf8cf": "",
                  })}
                >
                  {" SMARTPROP / SAVED COLLECTION "}
                </p>
              </div>
              <h1
                {...mergeProps({
                  className:
                    "mt-6 text-[39px] font-medium leading-tight tracking-tight sm:text-[56px]",
                  "data-sp-928bf8cf": "",
                })}
              >
                {" Những lựa chọn "}
                <span
                  {...mergeProps({
                    className: "block italic text-[var(--ui-muted)]",
                    "data-sp-928bf8cf": "",
                  })}
                >
                  {"bạn yêu thích."}
                </span>
              </h1>
              <p
                {...mergeProps({
                  className: "mt-5 max-w-2xl text-sm leading-7 text-[var(--ui-muted)]",
                  "data-sp-928bf8cf": "",
                })}
              >
                {
                  " Lưu giữ những bất động sản đáng quan tâm, so sánh mức giá và dễ dàng quay lại khám phá những không gian sống phù hợp. "
                }
              </p>
              <span
                {...mergeProps({
                  className:
                    "mt-5 inline-flex rounded-full border border-[var(--ui-border)] bg-[var(--ui-surface)] px-4 py-2 text-xs font-bold uppercase tracking-widest text-[var(--ui-muted)]",
                  "data-sp-928bf8cf": "",
                })}
              >
                {" Dữ liệu từ hệ thống "}
              </span>
            </div>
            <RouterLink
              {...mergeProps({
                to: "/listings",
                className:
                  "rounded-full bg-[var(--ui-soft)] px-7 py-4 text-xs font-bold text-brand-navy transition hover:bg-[var(--ui-soft)]",
                "data-sp-928bf8cf": "",
              })}
            >
              {" Khám phá thêm bất động sản ↗ "}
            </RouterLink>
          </div>
        </div>
      </section>
      <section
        {...mergeProps({
          className: "mx-auto max-w-[1440px] px-5 pt-10 md:px-10",
          "data-sp-928bf8cf": "",
        })}
      >
        <div
          {...mergeProps({
            className: "grid grid-cols-2 gap-3 lg:grid-cols-3 lg:gap-5",
            "data-sp-928bf8cf": "",
          })}
        >
          <div
            {...mergeProps({
              className:
                "rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7",
              "data-sp-928bf8cf": "",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]",
                "data-sp-928bf8cf": "",
              })}
            >
              {" Đã yêu thích "}
            </p>
            <div
              {...mergeProps({
                className: "mt-4 flex items-end justify-between",
                "data-sp-928bf8cf": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "text-4xl font-semibold",
                  "data-sp-928bf8cf": "",
                })}
              >
                {display(ctx.state.summary?.totalVisible ?? "—")}
              </span>
              <span
                {...mergeProps({
                  className: "text-xl text-[var(--ui-ink)]",
                  "data-sp-928bf8cf": "",
                })}
              >
                {"♥"}
              </span>
            </div>
            <p
              {...mergeProps({
                className: "mt-3 text-xs text-[var(--ui-ink)]",
                "data-sp-928bf8cf": "",
              })}
            >
              {"Bất động sản đã lưu"}
            </p>
          </div>
          <div
            {...mergeProps({
              className: "rounded-[20px] bg-[var(--ui-soft)] p-5 text-brand-navy sm:p-7",
              "data-sp-928bf8cf": "",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-bold uppercase tracking-widest text-brand-navy/60",
                "data-sp-928bf8cf": "",
              })}
            >
              {" Loại hình quan tâm "}
            </p>
            <div
              {...mergeProps({
                className: "mt-4 flex items-end justify-between",
                "data-sp-928bf8cf": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "text-4xl font-semibold",
                  "data-sp-928bf8cf": "",
                })}
              >
                {display(ctx.propertyTypeCount)}
              </span>
              <span
                {...mergeProps({
                  className: "text-xl text-[var(--ui-ink)]",
                  "data-sp-928bf8cf": "",
                })}
              >
                {"⌂"}
              </span>
            </div>
            <p
              {...mergeProps({
                className: "mt-3 text-xs text-brand-navy/55",
                "data-sp-928bf8cf": "",
              })}
            >
              {"Nhà phố · Căn hộ · Đất nền"}
            </p>
          </div>
          <div
            {...mergeProps({
              className:
                "col-span-2 rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7 lg:col-span-1",
              "data-sp-928bf8cf": "",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]",
                "data-sp-928bf8cf": "",
              })}
            >
              {" Tổng giá trị tham khảo "}
            </p>
            <div
              {...mergeProps({
                className: "mt-4 flex items-end justify-between",
                "data-sp-928bf8cf": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "text-3xl font-semibold sm:text-4xl",
                  "data-sp-928bf8cf": "",
                })}
              >
                {!ctx.priceGroups.length ? (
                  <span
                    {...mergeProps({
                      "data-sp-928bf8cf": "",
                    })}
                  >
                    {"—"}
                  </span>
                ) : null}
                {renderList(ctx.priceGroups, (g) => (
                  <span
                    key={g.transactionType + g.currency + g.priceUnit}
                    {...mergeProps({
                      className: "block text-sm",
                      "data-sp-928bf8cf": "",
                    })}
                  >
                    {display(
                      Number(g.amounts.totalAskingPrice).toLocaleString(
                        "vi-VN",
                      ),
                    )}{" "}
                    {display(g.currency)}
                    {" · "}
                    {display(g.transactionType === "SALE" ? "Bán" : "Thuê")}
                    {" / "}
                    {display(g.priceUnit)}
                  </span>
                ))}
              </span>
              <span
                {...mergeProps({
                  className: "text-xl text-[var(--ui-ink)]",
                  "data-sp-928bf8cf": "",
                })}
              >
                {"↗"}
              </span>
            </div>
            <p
              {...mergeProps({
                className: "mt-3 text-xs text-[var(--ui-ink)]",
                "data-sp-928bf8cf": "",
              })}
            >
              {"Giá chào toàn bộ tin còn hiển thị, tách theo giao dịch/đơn vị"}
            </p>
          </div>
        </div>
      </section>
      <div
        {...mergeProps({
          className: "mx-auto max-w-[1440px] px-5 pb-20 pt-12 md:px-10",
          "data-sp-928bf8cf": "",
        })}
      >
        <LegacyState
          {...mergeProps({
            state: ctx.state,
            "data-sp-928bf8cf": "",
          })}
        />
        {ctx.state.summaryError ? (
          <p
            {...mergeProps({
              role: "alert",
              "data-sp-928bf8cf": "",
            })}
          >
            {display(ctx.state.summaryError)}{" "}
            <button
              {...mergeProps({
                onClick: ($event) => {
                  return ctx.state.loadSummary?.($event);
                },
                "data-sp-928bf8cf": "",
              })}
            >
              {"Tải lại thống kê"}
            </button>
          </p>
        ) : null}
        <p
          {...mergeProps({
            className: "mb-4 text-xs text-[var(--ui-ink)]",
            "data-sp-928bf8cf": "",
          })}
        >
          {display(ctx.state.totalElements)}
          {" kết quả · kết quả đã lọc toàn bộ danh mục."}
        </p>
        <div
          {...mergeProps({
            className: "flex flex-wrap items-end justify-between gap-5",
            "data-sp-928bf8cf": "",
          })}
        >
          <div
            {...mergeProps({
              "data-sp-928bf8cf": "",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-muted)]",
                "data-sp-928bf8cf": "",
              })}
            >
              {" YOUR FAVORITES / 01 "}
            </p>
            <h2
              {...mergeProps({
                className:
                  "mt-3 text-3xl font-medium tracking-tight sm:text-4xl",
                "data-sp-928bf8cf": "",
              })}
            >
              {" Bộ sưu tập "}
              <span
                {...mergeProps({
                  className: "italic text-[var(--ui-muted)]",
                  "data-sp-928bf8cf": "",
                })}
              >
                {"của bạn."}
              </span>
            </h2>
            <p
              {...mergeProps({
                className: "mt-3 text-xs text-[var(--ui-ink)]",
                "data-sp-928bf8cf": "",
              })}
            >
              {display(ctx.state.totalElements)}
              {" bất động sản phù hợp với bộ lọc. "}
            </p>
          </div>
          <div
            {...mergeProps({
              className: "flex w-full flex-wrap gap-3 sm:w-auto",
              "data-sp-928bf8cf": "",
            })}
          >
            <div
              {...mergeProps({
                className:
                  "flex min-w-0 flex-1 items-center gap-2 rounded-xl border border-[var(--ui-border)] bg-brand-card px-4 sm:w-[260px]",
                "data-sp-928bf8cf": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "text-lg text-[var(--ui-muted)]",
                  "data-sp-928bf8cf": "",
                })}
              >
                {"⌕"}
              </span>
              <input
                {...mergeProps(
                  {
                    type: "search",
                    "aria-label": "Tìm kiếm tin đã lưu",
                    placeholder: "Tìm tin đăng, khu vực...",
                    className:
                      "h-12 min-w-0 w-full bg-transparent text-xs outline-none",
                    "data-sp-928bf8cf": "",
                  },
                  modelProps(
                    ctx.searchText,
                    ($value) => {
                      ctx.searchText = $value;
                    },
                    {
                      kind: "search",
                      value: "on",
                      number: false,
                      multiple: false,
                    },
                  ),
                )}
              />
            </div>
            <select
              {...mergeProps(
                {
                  "aria-label": "Sắp xếp tin yêu thích",
                  className:
                    "h-12 rounded-xl border border-[var(--ui-border)] bg-brand-card px-4 text-xs outline-none",
                  "data-sp-928bf8cf": "",
                },
                modelProps(
                  ctx.sortType,
                  ($value) => {
                    ctx.sortType = $value;
                  },
                  {
                    kind: "text",
                    value: "on",
                    number: false,
                    multiple: false,
                  },
                ),
              )}
            >
              <option
                {...mergeProps({
                  "data-sp-928bf8cf": "",
                })}
              >
                {"Mới lưu"}
              </option>
              <option
                {...mergeProps({
                  "data-sp-928bf8cf": "",
                })}
              >
                {"Cũ nhất"}
              </option>
              <option
                {...mergeProps({
                  "data-sp-928bf8cf": "",
                })}
              >
                {"Giá thấp"}
              </option>
              <option
                {...mergeProps({
                  "data-sp-928bf8cf": "",
                })}
              >
                {"Giá cao"}
              </option>
            </select>
          </div>
        </div>
        <div
          {...mergeProps({
            className: "mt-8 flex flex-wrap gap-2",
            "data-sp-928bf8cf": "",
          })}
        >
          {renderList(ctx.filters, (filter) => (
            <button
              key={filter}
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  ctx.activeFilter = filter;
                },
                className: ["rounded-full border px-4 py-2.5 text-xs font-semibold transition sm:px-5", ctx.activeFilter === filter
                    ? "border-[var(--ui-border)] bg-[var(--ui-soft)] text-brand-navy"
                    : "border-[var(--ui-border)] bg-brand-card text-[var(--ui-accent)] hover:border-[var(--ui-border)]"],
                
                "data-sp-928bf8cf": "",
              })}
            >
              {display(filter)}{" "}
              <span
                {...mergeProps({
                  className: "ml-1 opacity-65",
                  "data-sp-928bf8cf": "",
                })}
              >
                {display(ctx.filterCount(filter))}
              </span>
            </button>
          ))}
        </div>
        {ctx.removedItem ? (
          <div
            {...mergeProps({
              className:
                "mt-6 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-[var(--ui-border)] bg-[var(--ui-surface)] px-5 py-4",
              "data-sp-928bf8cf": "",
            })}
          >
            <p
              {...mergeProps({
                className: "text-xs text-[var(--ui-muted)]",
                "data-sp-928bf8cf": "",
              })}
            >
              {" Đã bỏ yêu thích: "}
              <strong
                {...mergeProps({
                  "data-sp-928bf8cf": "",
                })}
              >
                {display(ctx.removedItem.title)}
              </strong>
            </p>
            <button
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  return ctx.undoRemove?.($event);
                },
                className:
                  "text-xs font-bold text-[var(--ui-accent)] underline underline-offset-4",
                "data-sp-928bf8cf": "",
              })}
            >
              {" Hoàn tác "}
            </button>
          </div>
        ) : null}
        {ctx.filteredListings.length ? (
          <div
            {...mergeProps({
              className:
                "mt-8 grid min-w-0 grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3",
              "data-sp-928bf8cf": "",
            })}
          >
            {renderList(ctx.filteredListings, (item) => (
              <article
                key={item.id}
                {...mergeProps({
                  className:
                    "group min-w-0 overflow-hidden rounded-[22px] border border-[var(--ui-border)] bg-brand-card transition duration-300 hover:-translate-y-1 hover:border-[var(--ui-border)] hover:shadow-[0_18px_50px_rgba(20,43,79,.10)]",
                  "data-sp-928bf8cf": "",
                })}
              >
                <div
                  {...mergeProps({
                    className:
                      "relative h-[260px] overflow-hidden bg-[var(--ui-surface)]",
                    "data-sp-928bf8cf": "",
                  })}
                >
                  <PrivateImage
                    {...mergeProps({
                      src: item.image,
                      alt: `${item.title}`,
                      loading: "lazy",
                      className:
                        "h-full w-full object-cover transition duration-700 group-hover:scale-105",
                      "data-sp-928bf8cf": "",
                    })}
                  />
                  <div
                    {...mergeProps({
                      className:
                        "absolute inset-0 bg-gradient-to-t from-[var(--ui-soft)]/50 via-transparent to-transparent",
                      "data-sp-928bf8cf": "",
                    })}
                  />
                  <span
                    {...mergeProps({
                      className: ["absolute left-4 top-4 rounded-full px-3 py-2 text-xs font-bold shadow-sm", item.badgeColor === "green"
                          ? "bg-[var(--ui-surface)] text-[var(--ui-accent)]"
                          : "bg-[var(--ui-surface)] text-[var(--ui-muted)]"],
                      
                      "data-sp-928bf8cf": "",
                    })}
                  >
                    {display(item.badge)}
                  </span>
                  <button
                    {...mergeProps({
                      type: "button",
                      onClick: ($event) => {
                        ctx.removeFavorite(item.id);
                      },
                      "aria-label": `Bỏ yêu thích ${item.title}`,
                      title: "Bỏ yêu thích",
                      className:
                        "absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-full bg-[var(--ui-soft)] text-lg text-brand-navy transition hover:scale-110 hover:bg-[var(--ui-soft)]",
                      "data-sp-928bf8cf": "",
                    })}
                  >
                    {" ♥ "}
                  </button>
                  <span
                    {...mergeProps({
                      className:
                        "absolute bottom-5 left-5 text-xs font-bold uppercase tracking-[0.15em] text-brand-navy",
                      "data-sp-928bf8cf": "",
                    })}
                  >
                    {display(item.type)}
                    {" / Đà Nẵng "}
                  </span>
                </div>
                <div
                  {...mergeProps({
                    className: "p-6 sm:p-7",
                    "data-sp-928bf8cf": "",
                  })}
                >
                  <p
                    {...mergeProps({
                      className:
                        "text-xs font-bold uppercase tracking-[0.15em] text-[var(--ui-muted)]",
                      "data-sp-928bf8cf": "",
                    })}
                  >
                    {display(item.type)}
                  </p>
                  <h3
                    {...mergeProps({
                      className:
                        "mt-3 min-h-[56px] text-xl font-semibold leading-7",
                      "data-sp-928bf8cf": "",
                    })}
                  >
                    {display(item.title)}
                  </h3>
                  <p
                    {...mergeProps({
                      className: "mt-3 text-xs text-[var(--ui-ink)]",
                      "data-sp-928bf8cf": "",
                    })}
                  >
                    {" ⌖ "}
                    {display(item.location)}
                  </p>
                  <div
                    {...mergeProps({
                      className: "mt-6 border-y border-[var(--ui-border)] py-4",
                      "data-sp-928bf8cf": "",
                    })}
                  >
                    <p
                      {...mergeProps({
                        className: "text-xs text-[var(--ui-accent)]",
                        "data-sp-928bf8cf": "",
                      })}
                    >
                      {display(item.info)}
                    </p>
                  </div>
                  <div
                    {...mergeProps({
                      className: "mt-5 flex items-end justify-between gap-4",
                      "data-sp-928bf8cf": "",
                    })}
                  >
                    <div
                      {...mergeProps({
                        "data-sp-928bf8cf": "",
                      })}
                    >
                      <p
                        {...mergeProps({
                          className:
                            "text-xs uppercase tracking-widest text-[var(--ui-ink)]",
                          "data-sp-928bf8cf": "",
                        })}
                      >
                        {" Giá tham khảo "}
                      </p>
                      <p
                        {...mergeProps({
                          className:
                            "mt-2 text-[27px] font-semibold tracking-tight",
                          "data-sp-928bf8cf": "",
                        })}
                      >
                        {display(item.priceText)}{" "}
                        <span
                          {...mergeProps({
                            className: "text-base text-[var(--ui-muted)]",
                            "data-sp-928bf8cf": "",
                          })}
                        />
                      </p>
                    </div>
                    <button
                      {...mergeProps({
                        type: "button",
                        onClick: ($event) => {
                          ctx.openListing(item.id);
                        },
                        "aria-label": `Xem chi tiết ${item.title}`,
                        className:
                          "flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-[var(--ui-border)] text-lg transition group-hover:border-[var(--ui-border)] group-hover:bg-[var(--ui-soft)] group-hover:text-brand-navy",
                        "data-sp-928bf8cf": "",
                      })}
                    >
                      {" ↗ "}
                    </button>
                  </div>
                  <div
                    {...mergeProps({
                      className:
                        "mt-5 flex items-center justify-between border-t border-[var(--ui-border)] pt-4",
                      "data-sp-928bf8cf": "",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className: "text-xs text-[var(--ui-ink)]",
                        "data-sp-928bf8cf": "",
                      })}
                    >
                      {" ♡ "}
                      {display(item.saved)}
                    </span>
                    <button
                      {...mergeProps({
                        type: "button",
                        onClick: ($event) => {
                          ctx.openListing(item.id);
                        },
                        className:
                          "text-xs font-bold text-[var(--ui-accent)] hover:text-[var(--ui-muted)]",
                        "data-sp-928bf8cf": "",
                      })}
                    >
                      {" Xem chi tiết → "}
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div
            {...mergeProps({
              className:
                "mt-8 rounded-[24px] border border-[var(--ui-border)] bg-brand-card px-6 py-20 text-center",
              "data-sp-928bf8cf": "",
            })}
          >
            <div
              {...mergeProps({
                className:
                  "mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[var(--ui-surface)] text-3xl text-[var(--ui-muted)]",
                "data-sp-928bf8cf": "",
              })}
            >
              {" ♡ "}
            </div>
            <h3
              {...mergeProps({
                className: "mt-6 text-xl font-semibold",
                "data-sp-928bf8cf": "",
              })}
            >
              {" Chưa có bất động sản phù hợp "}
            </h3>
            <p
              {...mergeProps({
                className: "mt-3 text-sm text-[var(--ui-ink)]",
                "data-sp-928bf8cf": "",
              })}
            >
              {" Hãy thay đổi bộ lọc hoặc khám phá thêm tin đăng. "}
            </p>
            <button
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  return ctx.resetFilters?.($event);
                },
                className:
                  "mt-6 rounded-full bg-[var(--ui-soft)] px-6 py-3 text-xs font-semibold text-brand-navy",
                "data-sp-928bf8cf": "",
              })}
            >
              {" Xem tất cả tin yêu thích "}
            </button>
          </div>
        )}
        <section
          {...mergeProps({
            className:
              "relative mt-14 overflow-hidden rounded-[25px] bg-[var(--ui-soft)] px-7 py-10 text-brand-navy sm:px-10",
            "data-sp-928bf8cf": "",
          })}
        >
          <div
            {...mergeProps({
              className:
                "pointer-events-none absolute -right-12 -top-24 h-72 w-72 rounded-full border border-[var(--ui-border)]/20",
              "data-sp-928bf8cf": "",
            })}
          />
          <div
            {...mergeProps({
              className:
                "relative flex flex-wrap items-center justify-between gap-7",
              "data-sp-928bf8cf": "",
            })}
          >
            <div
              {...mergeProps({
                "data-sp-928bf8cf": "",
              })}
            >
              <p
                {...mergeProps({
                  className:
                    "text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-accent)]",
                  "data-sp-928bf8cf": "",
                })}
              >
                {" SMARTPROP / DISCOVER MORE "}
              </p>
              <h2
                {...mergeProps({
                  className: "mt-4 text-3xl font-medium",
                  "data-sp-928bf8cf": "",
                })}
              >
                {" Lựa chọn tiếp theo "}
                <span
                  {...mergeProps({
                    className: "italic text-[var(--ui-ink)]",
                    "data-sp-928bf8cf": "",
                  })}
                >
                  {" đang chờ bạn."}
                </span>
              </h2>
              <p
                {...mergeProps({
                  className: "mt-4 max-w-xl text-sm leading-7 text-brand-navy/60",
                  "data-sp-928bf8cf": "",
                })}
              >
                {
                  " Tiếp tục khám phá các bất động sản, tìm kiếm theo nhu cầu và mở rộng bộ sưu tập yêu thích của bạn. "
                }
              </p>
            </div>
            <RouterLink
              {...mergeProps({
                to: "/listings",
                className:
                  "rounded-full bg-[var(--ui-soft)] px-7 py-4 text-xs font-bold text-[var(--ui-accent)] transition hover:bg-[var(--ui-soft)]",
                "data-sp-928bf8cf": "",
              })}
            >
              {" Khám phá bất động sản ↗ "}
            </RouterLink>
          </div>
        </section>
        <p
          {...mergeProps({
            className: "mt-7 text-center text-xs leading-6 text-[var(--ui-ink)]",
            "data-sp-928bf8cf": "",
          })}
        >
          {
            " Tin đăng và trạng thái được tải từ hệ thống. Danh sách yêu thích được lưu theo tài khoản của bạn. "
          }
        </p>
        <LegacyPager
          {...mergeProps({
            state: ctx.state,
            "data-sp-928bf8cf": "",
          })}
        />
      </div>
    </div>,
  ]);
});
