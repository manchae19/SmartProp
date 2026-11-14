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
import { computed, ref, watch } from "../../shared/state/store.js";
import PropertyModerationFeedback from "./PropertyModerationFeedback.jsx";
import { useRouter } from "../../shared/routing/router.jsx";
import { api, session } from "../auth/api.js";
import {
  useList,
  LegacyState,
  LegacyPager,
  PrivateImage,
} from "../../shared/lib/legacy.js";
import { collectionProperty } from "../home/collection.js";
import { useCollection, ownStatus } from "../home/useCollection.js";
import "./MyListingView.css";
function setup(__props) {
  const router = useRouter();

  // SMARTPROP MY LISTINGS 2.0
  // Data is loaded from the existing backend.

  const activeFilter = ref("all");
  const searchText = ref("");
  const selectedListing = ref(null);
  const showEditNotice = ref(false);
  const state = useCollection(
    "/users/me/properties",
    "/users/me/properties/summary",
    () => ({
      keyword: searchText.value.trim(),
      status: ownStatus[activeFilter.value],
    }),
  );
  const listings = computed(() => state.items.map(collectionProperty));
  const count = (id) => state.summary?.byStatus?.[ownStatus[id]] ?? "—";
  const filters = computed(() => [
    {
      id: "all",
      label: "Tất cả",
      count: state.summary?.totalListings ?? "—",
    },
    ...Object.entries({
      draft: "Bản nháp",
      showing: "Đang hiển thị",
      pending: "Chờ duyệt",
      rejected: "Bị từ chối",
      hidden: "Đã ẩn",
      closed: "Đã đóng",
      expired: "Hết hạn",
    }).map(([id, label]) => ({
      id,
      label,
      count: count(id),
    })),
  ]);
  const filteredListings = listings;
  const totalViews = computed(() =>
    state.summary?.viewRecordingEnabled ? state.summary.recordedViews : "—",
  );
  const totalSaves = computed(() => state.summary?.savedRecords ?? "—");
  function statusClass(status) {
    if (status === "showing") {
      return "bg-[#E5F4EB] text-[#287B56]";
    }
    if (status === "pending") {
      return "bg-[#FFF1D9] text-[#A36A19]";
    }
    if (status === "rejected") {
      return "bg-[#FCE8E3] text-[#BD5D48]";
    }
    return "bg-[#EDF0F3] text-[#64748B]";
  }
  function openListing(item) {
    selectedListing.value = item;
  }
  function closeListing() {
    selectedListing.value = null;
  }
  function goToDetail(item) {
    router.push({
      path: "/listing/" + item.id,
      query: {
        own: "1",
      },
    });
  }
  function editListing(item) {
    router.push({
      path: "/post",
      query: {
        edit: item.id,
      },
    });
  }
  function closeEditNotice() {
    showEditNotice.value = false;
    selectedListing.value = null;
  }
  function goHome() {
    router.push("/home");
  }
  function goMap() {
    router.push("/map");
  }
  function goPost() {
    if (!canPost.value) {
      state.notice = publishNotice;
      return;
    }
    router.push("/post");
  }
  function goAccount() {
    router.push("/account");
  }
  const canPost = computed(() =>
    ["BROKER", "ADMIN"].includes(session.user?.role),
  );
  const publishNotice =
    "Bạn đang dùng tài khoản Người mua / người thuê (BUYER). Để đăng tin, hãy đăng nhập bằng tài khoản Chủ nhà / môi giới (BROKER) hoặc ADMIN.";
  watch(
    () => session.user?.role,
    (role) => {
      if (role === "BUYER") state.notice = publishNotice;
      else if (state.notice === publishNotice) state.notice = "";
    },
    {
      immediate: true,
    },
  );
  async function act(p, action) {
    await state.run(async () => {
      await api(
        "/properties/" +
          p.id +
          (action === "delete"
            ? "?expectedVersion=" + p.raw.contentVersion
            : "/" + action),
        {
          method: action === "delete" ? "DELETE" : "POST",
          ...(action === "delete"
            ? {}
            : {
                body: {
                  expectedVersion: p.raw.contentVersion,
                },
              }),
        },
      );
      await state.reload();
    });
  }
  return {
    computed,
    ref,
    watch,
    PropertyModerationFeedback,
    useRouter,
    api,
    session,
    useList,
    LegacyState,
    LegacyPager,
    PrivateImage,
    collectionProperty,
    useCollection,
    ownStatus,
    router,
    activeFilter,
    searchText,
    selectedListing,
    showEditNotice,
    state,
    listings,
    count,
    filters,
    filteredListings,
    totalViews,
    totalSaves,
    statusClass,
    openListing,
    closeListing,
    goToDetail,
    editListing,
    closeEditNotice,
    goHome,
    goMap,
    goPost,
    goAccount,
    canPost,
    publishNotice,
    act,
  };
}
export default React.forwardRef(function MyListingView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="MyListingView"
      {...mergeProps({
        className: "sp-my-listings min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)]",
        "data-sp-51b40b91": "",
      })}
    >
      <section
        {...mergeProps({
          className: "relative overflow-hidden border-b border-[var(--ui-border)]",
          "data-sp-51b40b91": "",
        })}
      >
        <div
          {...mergeProps({
            className:
              "pointer-events-none absolute -right-28 -top-32 h-[420px] w-[420px] rounded-full border border-[var(--ui-border)]/20",
            "data-sp-51b40b91": "",
          })}
        />
        <div
          {...mergeProps({
            className:
              "pointer-events-none absolute -right-10 -top-12 h-[280px] w-[280px] rounded-full border border-[var(--ui-border)]/20",
            "data-sp-51b40b91": "",
          })}
        />
        <div
          {...mergeProps({
            className:
              "relative mx-auto max-w-[1440px] px-5 py-12 md:px-10 md:py-16",
            "data-sp-51b40b91": "",
          })}
        >
          <div
            {...mergeProps({
              className: "flex flex-wrap items-end justify-between gap-8",
              "data-sp-51b40b91": "",
            })}
          >
            <div
              {...mergeProps({
                "data-sp-51b40b91": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "flex items-center gap-3",
                  "data-sp-51b40b91": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "h-px w-9 bg-[var(--ui-soft)]",
                    "data-sp-51b40b91": "",
                  })}
                />
                <p
                  {...mergeProps({
                    className:
                      "text-xs font-bold uppercase tracking-[0.22em] text-[var(--ui-muted)]",
                    "data-sp-51b40b91": "",
                  })}
                >
                  {" SMARTPROP / PROPERTY MANAGEMENT "}
                </p>
              </div>
              <h1
                {...mergeProps({
                  className:
                    "mt-6 text-[39px] font-medium leading-tight tracking-tight sm:text-[56px]",
                  "data-sp-51b40b91": "",
                })}
              >
                {" Quản lý "}
                <span
                  {...mergeProps({
                    className: "block italic text-[var(--ui-muted)]",
                    "data-sp-51b40b91": "",
                  })}
                >
                  {"bất động sản của bạn."}
                </span>
              </h1>
              <p
                {...mergeProps({
                  className: "mt-5 max-w-xl text-sm leading-7 text-[var(--ui-muted)]",
                  "data-sp-51b40b91": "",
                })}
              >
                {
                  " Theo dõi trạng thái tin đăng, lượt quan tâm và quản lý danh mục bất động sản của bạn trong một không gian trực quan. "
                }
              </p>
              <span
                {...mergeProps({
                  className:
                    "mt-5 inline-flex rounded-full border border-[var(--ui-border)] bg-[var(--ui-surface)] px-4 py-2 text-xs font-bold uppercase tracking-widest text-[var(--ui-muted)]",
                  "data-sp-51b40b91": "",
                })}
              >
                {" Dữ liệu từ hệ thống "}
              </span>
            </div>
            <button
              {...mergeProps({
                onClick: ($event) => {
                  return ctx.goPost?.($event);
                },
                className:
                  "rounded-full bg-[var(--ui-soft)] px-7 py-4 text-xs font-bold text-brand-navy shadow-lg transition hover:-translate-y-0.5 hover:bg-[var(--ui-soft)]",
                "data-sp-51b40b91": "",
              })}
            >
              {" + Đăng bất động sản mới ↗ "}
            </button>
          </div>
        </div>
      </section>
      <section
        {...mergeProps({
          className: "mx-auto max-w-[1440px] px-5 pt-10 md:px-10",
          "data-sp-51b40b91": "",
        })}
      >
        <div
          {...mergeProps({
            className: "grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-5",
            "data-sp-51b40b91": "",
          })}
        >
          <div
            {...mergeProps({
              className:
                "rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7",
              "data-sp-51b40b91": "",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]",
                "data-sp-51b40b91": "",
              })}
            >
              {" Tổng tin đăng "}
            </p>
            <div
              {...mergeProps({
                className: "mt-4 flex items-end justify-between",
                "data-sp-51b40b91": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "text-4xl font-semibold",
                  "data-sp-51b40b91": "",
                })}
              >
                {display(ctx.state.summary?.totalListings ?? "—")}
              </span>
              <span
                {...mergeProps({
                  className: "text-xl text-[var(--ui-ink)]",
                  "data-sp-51b40b91": "",
                })}
              >
                {"⌂"}
              </span>
            </div>
            <p
              {...mergeProps({
                className: "mt-3 text-xs text-[var(--ui-ink)]",
                "data-sp-51b40b91": "",
              })}
            >
              {"Danh mục của bạn"}
            </p>
          </div>
          <div
            {...mergeProps({
              className: "rounded-[20px] bg-[var(--ui-soft)] p-5 text-brand-navy sm:p-7",
              "data-sp-51b40b91": "",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-bold uppercase tracking-widest text-brand-navy/60",
                "data-sp-51b40b91": "",
              })}
            >
              {" Đang hiển thị "}
            </p>
            <div
              {...mergeProps({
                className: "mt-4 flex items-end justify-between",
                "data-sp-51b40b91": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "text-4xl font-semibold",
                  "data-sp-51b40b91": "",
                })}
              >
                {display(ctx.count("showing"))}
              </span>
              <span
                {...mergeProps({
                  className: "h-3 w-3 rounded-full bg-[var(--ui-soft)]",
                  "data-sp-51b40b91": "",
                })}
              />
            </div>
            <p
              {...mergeProps({
                className: "mt-3 text-xs text-brand-navy/55",
                "data-sp-51b40b91": "",
              })}
            >
              {"Tin đang hoạt động"}
            </p>
          </div>
          <div
            {...mergeProps({
              className:
                "rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7",
              "data-sp-51b40b91": "",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]",
                "data-sp-51b40b91": "",
              })}
            >
              {" Tổng lượt xem "}
            </p>
            <div
              {...mergeProps({
                className: "mt-4 flex items-end justify-between",
                "data-sp-51b40b91": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "text-4xl font-semibold",
                  "data-sp-51b40b91": "",
                })}
              >
                {display(ctx.totalViews)}
              </span>
              <span
                {...mergeProps({
                  className: "text-xl text-[var(--ui-ink)]",
                  "data-sp-51b40b91": "",
                })}
              >
                {"↗"}
              </span>
            </div>
            <p
              {...mergeProps({
                className: "mt-3 text-xs text-[var(--ui-ink)]",
                "data-sp-51b40b91": "",
              })}
            >
              {"Chưa có số liệu tương tác"}
            </p>
          </div>
          <div
            {...mergeProps({
              className:
                "rounded-[20px] border border-[var(--ui-border)] bg-brand-card p-5 sm:p-7",
              "data-sp-51b40b91": "",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-bold uppercase tracking-widest text-[var(--ui-ink)]",
                "data-sp-51b40b91": "",
              })}
            >
              {" Lượt lưu tin "}
            </p>
            <div
              {...mergeProps({
                className: "mt-4 flex items-end justify-between",
                "data-sp-51b40b91": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "text-4xl font-semibold",
                  "data-sp-51b40b91": "",
                })}
              >
                {display(ctx.totalSaves)}
              </span>
              <span
                {...mergeProps({
                  className: "text-xl text-[var(--ui-ink)]",
                  "data-sp-51b40b91": "",
                })}
              >
                {"♡"}
              </span>
            </div>
            <p
              {...mergeProps({
                className: "mt-3 text-xs text-[var(--ui-ink)]",
                "data-sp-51b40b91": "",
              })}
            >
              {"Người dùng quan tâm"}
            </p>
          </div>
        </div>
      </section>
      <div
        {...mergeProps({
          className: "mx-auto max-w-[1440px] px-5 pb-20 pt-12 md:px-10",
          "data-sp-51b40b91": "",
        })}
      >
        <LegacyState
          {...mergeProps({
            state: ctx.state,
            "data-sp-51b40b91": "",
          })}
        />
        {ctx.state.summaryError ? (
          <p
            {...mergeProps({
              role: "alert",
              "data-sp-51b40b91": "",
            })}
          >
            {display(ctx.state.summaryError)}{" "}
            <button
              {...mergeProps({
                onClick: ($event) => {
                  return ctx.state.loadSummary?.($event);
                },
                "data-sp-51b40b91": "",
              })}
            >
              {"Tải lại thống kê"}
            </button>
          </p>
        ) : null}
        <p
          {...mergeProps({
            className: "mb-4 text-xs text-[var(--ui-ink)]",
            "data-sp-51b40b91": "",
          })}
        >
          {display(ctx.state.totalElements)}
          {
            " kết quả · kết quả đã lọc trên toàn bộ dữ liệu. Số đếm trạng thái là tổng danh mục."
          }
        </p>
        <div
          {...mergeProps({
            className: "flex flex-wrap items-end justify-between gap-5",
            "data-sp-51b40b91": "",
          })}
        >
          <div
            {...mergeProps({
              "data-sp-51b40b91": "",
            })}
          >
            <p
              {...mergeProps({
                className:
                  "text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-muted)]",
                "data-sp-51b40b91": "",
              })}
            >
              {" YOUR COLLECTION / 01 "}
            </p>
            <h2
              {...mergeProps({
                className:
                  "mt-3 text-3xl font-medium tracking-tight sm:text-4xl",
                "data-sp-51b40b91": "",
              })}
            >
              {" Danh sách "}
              <span
                {...mergeProps({
                  className: "italic text-[var(--ui-muted)]",
                  "data-sp-51b40b91": "",
                })}
              >
                {"tin đăng."}
              </span>
            </h2>
            <p
              {...mergeProps({
                className: "mt-3 text-xs text-[var(--ui-ink)]",
                "data-sp-51b40b91": "",
              })}
            >
              {" Quản lý và theo dõi các bất động sản đã đăng. "}
            </p>
          </div>
          <div
            {...mergeProps({
              className:
                "flex w-full items-center gap-3 rounded-xl border border-[var(--ui-border)] bg-brand-card px-4 sm:w-[300px]",
              "data-sp-51b40b91": "",
            })}
          >
            <span
              {...mergeProps({
                className: "text-[var(--ui-muted)]",
                "data-sp-51b40b91": "",
              })}
            >
              {"⌕"}
            </span>
            <input
              {...mergeProps(
                {
                  type: "search",
                  placeholder: "Tìm tin đăng hoặc khu vực...",
                  "aria-label": "Tìm tin đăng",
                  className:
                    "h-12 min-w-0 w-full bg-transparent text-xs outline-none",
                  "data-sp-51b40b91": "",
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
        </div>
        <div
          {...mergeProps({
            className: "mt-8 flex flex-wrap gap-2",
            "data-sp-51b40b91": "",
          })}
        >
          {renderList(ctx.filters, (filter) => (
            <button
              key={filter.id}
              {...mergeProps({
                onClick: ($event) => {
                  ctx.activeFilter = filter.id;
                },
                className: ["rounded-full border px-4 py-2.5 text-xs font-semibold transition sm:px-5", ctx.activeFilter === filter.id
                    ? "border-[var(--ui-border)] bg-[var(--ui-soft)] text-brand-navy"
                    : "border-[var(--ui-border)] bg-brand-card text-[var(--ui-accent)] hover:border-[var(--ui-border)]"],
                
                "data-sp-51b40b91": "",
              })}
            >
              {display(filter.label)}{" "}
              <span
                {...mergeProps({
                  className: "ml-1 opacity-65",
                  "data-sp-51b40b91": "",
                })}
              >
                {display(filter.count)}
              </span>
            </button>
          ))}
        </div>
        <div
          {...mergeProps({
            className: "mb-5 mt-7 flex items-center justify-between gap-4",
            "data-sp-51b40b91": "",
          })}
        >
          <p
            {...mergeProps({
              className: "text-xs text-[var(--ui-ink)]",
              "data-sp-51b40b91": "",
            })}
          >
            {" Hiển thị "}
            <strong
              {...mergeProps({
                className: "text-[var(--ui-accent)]",
                "data-sp-51b40b91": "",
              })}
            >
              {display(ctx.filteredListings.length)}
            </strong>
            {" tin đăng "}
          </p>
          <span
            {...mergeProps({
              className: "text-xs uppercase tracking-widest text-[var(--ui-muted)]",
              "data-sp-51b40b91": "",
            })}
          >
            {" PROPERTY PORTFOLIO "}
          </span>
        </div>
        {ctx.filteredListings.length ? (
          <div
            {...mergeProps({
              className: "space-y-5",
              "data-sp-51b40b91": "",
            })}
          >
            {renderList(ctx.filteredListings, (listing) => (
              <article
                key={listing.id}
                {...mergeProps({
                  className:
                    "group grid min-w-0 overflow-hidden rounded-[22px] border border-[var(--ui-border)] bg-brand-card transition duration-300 hover:border-[var(--ui-border)] hover:shadow-[0_16px_45px_rgba(20,43,79,0.08)] lg:grid-cols-[245px_minmax(0,1fr)_230px]",
                  "data-sp-51b40b91": "",
                })}
              >
                <div
                  {...mergeProps({
                    className:
                      "relative h-[230px] overflow-hidden bg-[var(--ui-surface)] lg:h-full lg:min-h-[220px]",
                    "data-sp-51b40b91": "",
                  })}
                >
                  <PrivateImage
                    {...mergeProps({
                      src: listing.image,
                      alt: `${listing.title}`,
                      loading: "lazy",
                      className:
                        "h-full w-full object-cover transition duration-700 group-hover:scale-105",
                      "data-sp-51b40b91": "",
                    })}
                  />
                  <div
                    {...mergeProps({
                      className:
                        "absolute inset-0 bg-gradient-to-t from-[var(--ui-soft)]/45 to-transparent",
                      "data-sp-51b40b91": "",
                    })}
                  />
                  <span
                    {...mergeProps({
                      className:
                        "absolute bottom-4 left-4 text-xs font-bold uppercase tracking-[0.15em] text-brand-navy",
                      "data-sp-51b40b91": "",
                    })}
                  >
                    {display(listing.location)}
                  </span>
                </div>
                <div
                  {...mergeProps({
                    className:
                      "flex min-w-0 flex-col justify-center p-5 sm:p-7",
                    "data-sp-51b40b91": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className: "flex flex-wrap items-center gap-3",
                      "data-sp-51b40b91": "",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className: ["rounded-full px-3 py-1.5 text-xs font-bold", ctx.statusClass(listing.status)],
                        
                        "data-sp-51b40b91": "",
                      })}
                    >
                      {display(listing.statusText)}
                    </span>
                    {listing.statusSub ? (
                      <span
                        {...mergeProps({
                          className: "text-xs text-[var(--ui-ink)]",
                          "data-sp-51b40b91": "",
                        })}
                      >
                        {display(listing.statusSub)}
                      </span>
                    ) : null}
                  </div>
                  <h3
                    {...mergeProps({
                      className:
                        "mt-4 text-lg font-semibold leading-7 sm:text-xl",
                      "data-sp-51b40b91": "",
                    })}
                  >
                    {display(listing.title)}
                  </h3>
                  <p
                    {...mergeProps({
                      className: "mt-2 text-xs text-[var(--ui-ink)]",
                      "data-sp-51b40b91": "",
                    })}
                  >
                    {" ⌖ "}
                    {display(listing.location)}
                  </p>
                  <p
                    {...mergeProps({
                      className: "mt-3 text-xs leading-6 text-[var(--ui-accent)]",
                      "data-sp-51b40b91": "",
                    })}
                  >
                    {display(listing.info)}
                  </p>
                  <div
                    {...mergeProps({
                      className:
                        "mt-5 flex flex-wrap gap-5 border-t border-[var(--ui-border)] pt-4",
                      "data-sp-51b40b91": "",
                    })}
                  >
                    {listing.views !== null ? (
                      <React.Fragment {...mergeProps({})}>
                        <span
                          {...mergeProps({
                            className: "text-xs text-[var(--ui-ink)]",
                            "data-sp-51b40b91": "",
                          })}
                        >
                          <strong
                            {...mergeProps({
                              className: "mr-1 text-sm text-[var(--ui-accent)]",
                              "data-sp-51b40b91": "",
                            })}
                          >
                            {display(listing.views)}
                          </strong>
                          {" lượt xem "}
                        </span>
                        <span
                          {...mergeProps({
                            className: "text-xs text-[var(--ui-ink)]",
                            "data-sp-51b40b91": "",
                          })}
                        >
                          <strong
                            {...mergeProps({
                              className: "mr-1 text-sm text-[var(--ui-accent)]",
                              "data-sp-51b40b91": "",
                            })}
                          >
                            {display(listing.saves)}
                          </strong>
                          {" lượt lưu "}
                        </span>
                      </React.Fragment>
                    ) : (
                      <span
                        {...mergeProps({
                          className: "text-xs text-[var(--ui-ink)]",
                          "data-sp-51b40b91": "",
                        })}
                      >
                        {" Chưa có thống kê tương tác "}
                      </span>
                    )}
                  </div>
                </div>
                <div
                  {...mergeProps({
                    className:
                      "flex flex-col justify-between gap-6 border-t border-[var(--ui-border)] p-5 sm:p-7 lg:border-l lg:border-t-0",
                    "data-sp-51b40b91": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className: "lg:text-right",
                      "data-sp-51b40b91": "",
                    })}
                  >
                    <p
                      {...mergeProps({
                        className:
                          "text-xs uppercase tracking-widest text-[var(--ui-ink)]",
                        "data-sp-51b40b91": "",
                      })}
                    >
                      {" Giá đăng "}
                    </p>
                    <p
                      {...mergeProps({
                        className:
                          "mt-2 text-[25px] font-semibold tracking-tight",
                        "data-sp-51b40b91": "",
                      })}
                    >
                      {display(listing.priceText)}
                    </p>
                    <p
                      {...mergeProps({
                        className: "mt-1 text-xs text-[var(--ui-muted)]",
                        "data-sp-51b40b91": "",
                      })}
                    >
                      {display(listing.priceUnit)}
                    </p>
                  </div>
                  <div
                    {...mergeProps({
                      className: "flex flex-wrap gap-2 lg:justify-end",
                      "data-sp-51b40b91": "",
                    })}
                  >
                    <button
                      {...mergeProps({
                        onClick: ($event) => {
                          ctx.openListing(listing);
                        },
                        className:
                          "rounded-full border border-[var(--ui-border)] bg-brand-card px-5 py-3 text-xs font-semibold transition hover:border-[var(--ui-border)]",
                        "data-sp-51b40b91": "",
                      })}
                    >
                      {" Xem "}
                    </button>
                    <button
                      {...mergeProps({
                        onClick: ($event) => {
                          ctx.editListing(listing);
                        },
                        className: ["rounded-full px-5 py-3 text-xs font-semibold text-brand-navy transition hover:opacity-90", listing.status === "rejected"
                            ? "bg-[var(--ui-soft)]"
                            : "bg-[var(--ui-soft)]"],
                        
                        "data-sp-51b40b91": "",
                      })}
                    >
                      {display(
                        listing.status === "rejected"
                          ? "Sửa & gửi lại"
                          : "Sửa tin",
                      )}
                    </button>
                    {["draft", "rejected"].includes(listing.status) ? (
                      <button
                        {...mergeProps({
                          disabled: ctx.state.busy,
                          onClick: ($event) => {
                            ctx.act(listing, "submit");
                          },
                          className: "rounded-full border px-4 py-2 text-xs",
                          "data-sp-51b40b91": "",
                        })}
                      >
                        {"Gửi duyệt"}
                      </button>
                    ) : null}
                    {!["closed", "expired"].includes(listing.status) ? (
                      <button
                        {...mergeProps({
                          disabled: ctx.state.busy,
                          onClick: ($event) => {
                            ctx.act(listing, "close");
                          },
                          className: "rounded-full border px-4 py-2 text-xs",
                          "data-sp-51b40b91": "",
                        })}
                      >
                        {"Đóng tin"}
                      </button>
                    ) : null}
                    <button
                      {...mergeProps({
                        disabled: ctx.state.busy,
                        onClick: ($event) => {
                          ctx.act(listing, "delete");
                        },
                        className: "rounded-full border px-4 py-2 text-xs",
                        "data-sp-51b40b91": "",
                      })}
                    >
                      {"Xóa tin"}
                    </button>
                  </div>
                </div>
                <PropertyModerationFeedback
                  {...mergeProps({
                    id: listing.id,
                    "data-sp-51b40b91": "",
                  })}
                />
              </article>
            ))}
          </div>
        ) : (
          <div
            {...mergeProps({
              className:
                "rounded-[24px] border border-[var(--ui-border)] bg-brand-card px-6 py-20 text-center",
              "data-sp-51b40b91": "",
            })}
          >
            <div
              {...mergeProps({
                className:
                  "mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[var(--ui-surface)] text-3xl text-[var(--ui-muted)]",
                "data-sp-51b40b91": "",
              })}
            >
              {" ⌕ "}
            </div>
            <h3
              {...mergeProps({
                className: "mt-6 text-xl font-semibold",
                "data-sp-51b40b91": "",
              })}
            >
              {" Không tìm thấy tin đăng "}
            </h3>
            <p
              {...mergeProps({
                className: "mt-3 text-sm text-[var(--ui-ink)]",
                "data-sp-51b40b91": "",
              })}
            >
              {" Thử thay đổi trạng thái hoặc từ khóa tìm kiếm. "}
            </p>
            <button
              {...mergeProps({
                onClick: ($event) => {
                  ctx.activeFilter = "all";
                  ctx.searchText = "";
                },
                className:
                  "mt-6 rounded-full bg-[var(--ui-soft)] px-6 py-3 text-xs font-semibold text-brand-navy",
                "data-sp-51b40b91": "",
              })}
            >
              {" Xem tất cả tin đăng "}
            </button>
          </div>
        )}
        <section
          {...mergeProps({
            className:
              "relative mt-14 overflow-hidden rounded-[25px] bg-[var(--ui-soft)] px-7 py-10 text-brand-navy sm:px-10",
            "data-sp-51b40b91": "",
          })}
        >
          <div
            {...mergeProps({
              className:
                "pointer-events-none absolute -right-12 -top-24 h-72 w-72 rounded-full border border-[var(--ui-border)]/20",
              "data-sp-51b40b91": "",
            })}
          />
          <div
            {...mergeProps({
              className:
                "relative flex flex-wrap items-center justify-between gap-7",
              "data-sp-51b40b91": "",
            })}
          >
            <div
              {...mergeProps({
                "data-sp-51b40b91": "",
              })}
            >
              <p
                {...mergeProps({
                  className:
                    "text-xs font-bold uppercase tracking-[0.2em] text-[var(--ui-accent)]",
                  "data-sp-51b40b91": "",
                })}
              >
                {" SMARTPROP / YOUR NEXT LISTING "}
              </p>
              <h2
                {...mergeProps({
                  className: "mt-4 text-3xl font-medium",
                  "data-sp-51b40b91": "",
                })}
              >
                {" Sẵn sàng cho "}
                <span
                  {...mergeProps({
                    className: "italic text-[var(--ui-ink)]",
                    "data-sp-51b40b91": "",
                  })}
                >
                  {"tin đăng tiếp theo?"}
                </span>
              </h2>
              <p
                {...mergeProps({
                  className: "mt-4 max-w-xl text-sm leading-7 text-brand-navy/60",
                  "data-sp-51b40b91": "",
                })}
              >
                {
                  " Đăng tải bất động sản và tiếp tục xây dựng danh mục của bạn trên SmartProp. "
                }
              </p>
            </div>
            <button
              {...mergeProps({
                onClick: ($event) => {
                  return ctx.goPost?.($event);
                },
                className:
                  "rounded-full bg-[var(--ui-soft)] px-7 py-4 text-xs font-bold text-[var(--ui-accent)] transition hover:bg-[var(--ui-soft)]",
                "data-sp-51b40b91": "",
              })}
            >
              {" + Tạo tin đăng mới ↗ "}
            </button>
          </div>
        </section>
        <p
          {...mergeProps({
            className: "mt-7 text-center text-xs leading-6 text-[var(--ui-ink)]",
            "data-sp-51b40b91": "",
          })}
        >
          {" Thông tin và trạng thái tin đăng được tải từ tài khoản của bạn. "}
        </p>
        <LegacyPager
          {...mergeProps({
            state: ctx.state,
            "data-sp-51b40b91": "",
          })}
        />
      </div>
      {ctx.selectedListing && !ctx.showEditNotice ? (
        <div
          {...mergeProps({
            className:
              "fixed inset-0 z-50 flex items-center justify-center bg-[var(--ui-soft)]/70 p-4",
            onClick: ($event) => {
              if ($event.target !== $event.currentTarget) return;
              return ctx.closeListing?.($event);
            },
            "data-sp-51b40b91": "",
          })}
        >
          <div
            {...mergeProps({
              role: "dialog",
              "aria-modal": "true",
              "aria-labelledby": "listing-dialog-title",
              className:
                "w-full max-w-xl overflow-hidden rounded-[24px] bg-brand-card shadow-2xl",
              "data-sp-51b40b91": "",
            })}
          >
            <div
              {...mergeProps({
                className: "relative h-[220px]",
                "data-sp-51b40b91": "",
              })}
            >
              <PrivateImage
                {...mergeProps({
                  src: ctx.selectedListing.image,
                  alt: ctx.selectedListing.title,
                  className: "h-full w-full object-cover",
                  "data-sp-51b40b91": "",
                })}
              />
              <button
                {...mergeProps({
                  onClick: ($event) => {
                    return ctx.closeListing?.($event);
                  },
                  "aria-label": "Đóng",
                  className:
                    "absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full bg-brand-card text-[var(--ui-accent)]",
                  "data-sp-51b40b91": "",
                })}
              >
                {" ✕ "}
              </button>
            </div>
            <div
              {...mergeProps({
                className: "p-6 sm:p-8",
                "data-sp-51b40b91": "",
              })}
            >
              <span
                {...mergeProps({
                  className: ["rounded-full px-3 py-1.5 text-xs font-semibold", ctx.statusClass(ctx.selectedListing.status)],
                  
                  "data-sp-51b40b91": "",
                })}
              >
                {display(ctx.selectedListing.statusText)}
              </span>
              <h2
                {...mergeProps({
                  id: "listing-dialog-title",
                  className: "mt-5 text-2xl font-semibold",
                  "data-sp-51b40b91": "",
                })}
              >
                {display(ctx.selectedListing.title)}
              </h2>
              <p
                {...mergeProps({
                  className: "mt-3 text-sm text-[var(--ui-ink)]",
                  "data-sp-51b40b91": "",
                })}
              >
                {display(ctx.selectedListing.location)}
              </p>
              <p
                {...mergeProps({
                  className: "mt-3 text-sm text-[var(--ui-accent)]",
                  "data-sp-51b40b91": "",
                })}
              >
                {display(ctx.selectedListing.info)}
              </p>
              <p
                {...mergeProps({
                  className: "mt-6 text-2xl font-semibold",
                  "data-sp-51b40b91": "",
                })}
              >
                {display(ctx.selectedListing.priceText)}
              </p>
              <div
                {...mergeProps({
                  className: "mt-7 flex flex-wrap gap-3",
                  "data-sp-51b40b91": "",
                })}
              >
                {ctx.selectedListing ? (
                  <button
                    {...mergeProps({
                      onClick: ($event) => {
                        ctx.goToDetail(ctx.selectedListing);
                      },
                      className:
                        "rounded-full bg-[var(--ui-soft)] px-6 py-3 text-xs font-semibold text-brand-navy",
                      "data-sp-51b40b91": "",
                    })}
                  >
                    {" Mở trang chi tiết ↗ "}
                  </button>
                ) : null}
                <button
                  {...mergeProps({
                    onClick: ($event) => {
                      return ctx.closeListing?.($event);
                    },
                    className:
                      "rounded-full border border-[var(--ui-border)] px-6 py-3 text-xs font-semibold",
                    "data-sp-51b40b91": "",
                  })}
                >
                  {" Đóng "}
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
      {ctx.showEditNotice && ctx.selectedListing ? (
        <div
          {...mergeProps({
            className:
              "fixed inset-0 z-50 flex items-center justify-center bg-[var(--ui-soft)]/70 p-4",
            onClick: ($event) => {
              if ($event.target !== $event.currentTarget) return;
              return ctx.closeEditNotice?.($event);
            },
            "data-sp-51b40b91": "",
          })}
        >
          <div
            {...mergeProps({
              role: "dialog",
              "aria-modal": "true",
              "aria-labelledby": "edit-dialog-title",
              className:
                "w-full max-w-md rounded-[24px] bg-brand-card p-7 text-center shadow-2xl sm:p-9",
              "data-sp-51b40b91": "",
            })}
          >
            <div
              {...mergeProps({
                className:
                  "mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[var(--ui-surface)] text-2xl text-[var(--ui-muted)]",
                "data-sp-51b40b91": "",
              })}
            >
              {" ✎ "}
            </div>
            <h2
              {...mergeProps({
                id: "edit-dialog-title",
                className: "mt-5 text-2xl font-semibold",
                "data-sp-51b40b91": "",
              })}
            >
              {" Chỉnh sửa tin đăng "}
            </h2>
            <p
              {...mergeProps({
                className: "mt-4 text-sm leading-7 text-[var(--ui-accent)]",
                "data-sp-51b40b91": "",
              })}
            >
              {" Tin "}
              <strong
                {...mergeProps({
                  "data-sp-51b40b91": "",
                })}
              >
                {display(ctx.selectedListing.title)}
              </strong>
              {
                " chưa có trang chỉnh sửa được kết nối. Chức năng này cần được xây dựng ở bước tiếp theo. "
              }
            </p>
            <button
              {...mergeProps({
                onClick: ($event) => {
                  return ctx.closeEditNotice?.($event);
                },
                className:
                  "mt-7 rounded-full bg-[var(--ui-soft)] px-8 py-3 text-xs font-semibold text-brand-navy",
                "data-sp-51b40b91": "",
              })}
            >
              {" Đã hiểu "}
            </button>
          </div>
        </div>
      ) : null}
    </div>,
  ]);
});
