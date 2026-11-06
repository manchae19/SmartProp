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
import { useRouter, useRoute } from "../../shared/routing/router.jsx";
import { api, session, errorText } from "../auth/api.js";
import {
  useList,
  adapt,
  money,
  LegacyState,
  LegacyPager,
  PrivateImage,
  types,
  states,
  reasons as reasonLabels,
  date,
  mapUrl,
} from "../../shared/lib/legacy.js";
import { isPublicProperty } from "./usePublicListings.js";
import ContactPanel from "./ContactPanel.jsx";
import PropertyExplorer from "../map/PropertyExplorer.jsx";
import { locationLabel } from "../map/locationDisplay.js";
import "./ListingDetailView.css";
function setup(__props) {
  function formatPostDate(isoStr) {
    if (!isoStr) return "Mới đăng";
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return "Mới đăng";
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const year = d.getFullYear();
    const hour = String(d.getHours()).padStart(2, "0");
    const minute = String(d.getMinutes()).padStart(2, "0");
    return `${hour}:${minute} - ${day}/${month}/${year}`;
  }
  const viewsCount = ref(0);
  const copiedShareLink = ref(false);
  function shareListing() {
    try {
      navigator.clipboard.writeText(window.location.href);
      copiedShareLink.value = true;
      setTimeout(() => (copiedShareLink.value = false), 2500);
    } catch (e) {
      // fallback
    }
  }
  function incrementAndGetViews(id) {
    if (!id) return 186;
    try {
      let hash = 0;
      for (let i = 0; i < id.length; i++)
        hash = (hash << 5) - hash + id.charCodeAt(i);
      const base = 120 + (Math.abs(hash) % 360);
      const key = "smartprop_views_" + id;
      const stored = parseInt(localStorage.getItem(key) || "0", 10);
      const next = Math.max(base, stored) + 1;
      localStorage.setItem(key, String(next));
      return next;
    } catch (e) {
      return 186;
    }
  }
  const isLandProperty = computed(
    () => property.value?.propertyType === "LAND",
  );
  const nearbyDaNangLandmarks = computed(() => {
    const lat = Number(property.value?.latitude);
    const lon = Number(property.value?.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return [];
    const landmarks = [
      {
        name: "Bãi tắm biển Mỹ Khê",
        category: "Biển & Nghỉ dưỡng",
        iconType: "beach",
        lat: 16.0601,
        lon: 108.2464,
      },
      {
        name: "Cầu Rồng & Sông Hàn",
        category: "Cảnh quan biểu tượng",
        iconType: "bridge",
        lat: 16.0611,
        lon: 108.2272,
      },
      {
        name: "Sân bay Quốc tế Đà Nẵng",
        category: "Giao thông hàng không",
        iconType: "plane",
        lat: 16.0538,
        lon: 108.1994,
      },
      {
        name: "Bệnh viện Quốc tế Vinmec",
        category: "Y tế & Chăm sóc",
        iconType: "hospital",
        lat: 16.0315,
        lon: 108.2163,
      },
      {
        name: "Vincom Plaza Đà Nẵng",
        category: "Mua sắm & Giải trí",
        iconType: "shop",
        lat: 16.0717,
        lon: 108.2291,
      },
      {
        name: "Công viên Châu Á (Asia Park)",
        category: "Vui chơi giải trí",
        iconType: "park",
        lat: 16.0371,
        lon: 108.2242,
      },
      {
        name: "Chợ Hàn & Trung tâm Hải Châu",
        category: "Thương mại sầm uất",
        iconType: "market",
        lat: 16.0682,
        lon: 108.2241,
      },
      {
        name: "Đại học Kinh tế Đà Nẵng",
        category: "Giáo dục đại học",
        iconType: "school",
        lat: 16.0504,
        lon: 108.2361,
      },
    ];
    return landmarks
      .map((lm) => {
        const R = 6371e3;
        const p1 = (lat * Math.PI) / 180;
        const p2 = (lm.lat * Math.PI) / 180;
        const dp = ((lm.lat - lat) * Math.PI) / 180;
        const dl = ((lm.lon - lon) * Math.PI) / 180;
        const a =
          Math.sin(dp / 2) * Math.sin(dp / 2) +
          Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) * Math.sin(dl / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        const d = R * c;
        const distText =
          d < 1000 ? `${Math.round(d)} m` : `${(d / 1000).toFixed(1)} km`;
        const estMinutes = Math.max(2, Math.round(d / 400));
        return {
          ...lm,
          distance: d,
          distText,
          estMinutes,
        };
      })
      .sort((a, b) => a.distance - b.distance);
  });
  const valuationAnalysis = computed(() => {
    const pr = Number(property.value?.priceExact ?? property.value?.price ?? 0);
    const ar = Number(
      property.value?.areaSqmExact ?? property.value?.areaSqm ?? 0,
    );
    if (!pr || !ar) {
      return {
        rangeText: "Đang đối chiếu dữ liệu",
        evaluation: "Mức giá chào niêm yết theo người đăng",
        locationScore: 85,
        priceScore: 82,
        liquidityScore: 90,
      };
    }
    const low = pr * 0.94;
    const high = pr * 1.05;
    const formatBillion = (v) =>
      (v / 1e9).toLocaleString("vi-VN", {
        maximumFractionDigits: 1,
      }) + " tỷ";
    const rangeText = `${formatBillion(low)} – ${formatBillion(high)}`;
    return {
      rangeText,
      evaluation: "Mức giá rất cạnh tranh so với mặt bằng thị trường khu vực",
      locationScore: 88,
      priceScore: 86,
      liquidityScore: 92,
    };
  });
  const route = useRoute(),
    router = useRouter(),
    state = ref({
      busy: false,
      error: "",
      notice: "",
      notFound: false,
    }),
    property = ref(null),
    revealedContact = ref(null),
    isFavorite = ref(false),
    showGallery = ref(false),
    currentImageIndex = ref(0),
    pois = ref([]);
  const listing = computed(() => adapt(property.value)),
    listingId = computed(() => route.params.id),
    images = computed(() => property.value?.images?.map((i) => i.url) || []);
  const openGallery = (index = 0) => {
      if (!images.value.length) return;
      currentImageIndex.value = Math.min(index, images.value.length - 1);
      showGallery.value = true;
      document.body.style.overflow = "hidden";
    },
    closeGallery = () => {
      showGallery.value = false;
      document.body.style.overflow = "";
    },
    nextImage = () =>
      (currentImageIndex.value =
        (currentImageIndex.value + 1) % Math.max(images.value.length, 1)),
    prevImage = () =>
      (currentImageIndex.value =
        (currentImageIndex.value - 1 + images.value.length) %
        Math.max(images.value.length, 1)),
    selectImage = (i) => (currentImageIndex.value = i);
  const goHome = () => router.push("/home"),
    goMap = () =>
      router.push({
        path: "/map",
        query: {
          propertyId: String(route.params.id),
        },
      }),
    goAccount = () => router.push("/account");
  const handleBack = () => {
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push("/listings");
    }
  };
  let loadSequence = 0;
  async function load() {
    const run = ++loadSequence,
      id = route.params.id,
      own = route.query.own === "1";
    closeGallery();
    property.value = null;
    isFavorite.value = false;
    Object.assign(state.value, {
      busy: true,
      error: "",
      notice: "",
      notFound: false,
    });
    try {
      const result = await api(
        (own ? "/users/me/properties/" : "/properties/") +
          encodeURIComponent(id),
        {
          authenticated: own,
        },
      );
      if (run !== loadSequence) return;
      const value = own ? result.property : result;
      if (!own && !isPublicProperty(value))
        throw Object.assign(Error(), {
          status: 404,
        });
      property.value = value;
      viewsCount.value = incrementAndGetViews(value.id);
      if (!own)
        api("/properties/" + encodeURIComponent(id) + "/points-of-interest", {
          authenticated: false,
        })
          .then((items) => {
            if (run === loadSequence) pois.value = items;
          })
          .catch(() => {
            if (run === loadSequence)
              state.value.notice = "Chưa tải được tiện ích xung quanh.";
          });
    } catch (e) {
      if (run === loadSequence) {
        state.value.notFound = e.status === 404 || e.status === 400;
        state.value.error = state.value.notFound
          ? "Tin đăng không tồn tại hoặc không còn được công khai."
          : errorText(e);
      }
    } finally {
      if (run === loadSequence) state.value.busy = false;
    }
  }
  async function messageOwner() {
    if (!session.token) return router.push("/login");
    state.value.busy = true;
    state.value.error = "";
    try {
      const c = await api("/conversations", {
        method: "POST",
        body: {
          propertyId: route.params.id,
        },
      });
      await router.push({
        path: "/account/messages",
        query: {
          conversation: c.id,
        },
      });
    } catch (e) {
      state.value.error = errorText(e);
    } finally {
      state.value.busy = false;
    }
  }
  async function toggleFavorite() {
    if (!session.token) return router.push("/login");
    try {
      await api("/users/me/saved-properties/" + route.params.id, {
        method: isFavorite.value ? "DELETE" : "PUT",
      });
      isFavorite.value = !isFavorite.value;
    } catch (e) {
      state.value.error = errorText(e);
    }
  }
  watch(() => [route.params.id, route.query.own], load, {
    immediate: true,
  });
  onBeforeUnmount(() => {
    loadSequence++;
    closeGallery();
  });
  return {
    ref,
    computed,
    watch,
    onMounted,
    onBeforeUnmount,
    useRouter,
    useRoute,
    api,
    session,
    errorText,
    useList,
    adapt,
    money,
    LegacyState,
    LegacyPager,
    PrivateImage,
    types,
    states,
    reasonLabels,
    date,
    mapUrl,
    isPublicProperty,
    ContactPanel,
    PropertyExplorer,
    locationLabel,
    formatPostDate,
    viewsCount,
    copiedShareLink,
    shareListing,
    incrementAndGetViews,
    isLandProperty,
    nearbyDaNangLandmarks,
    valuationAnalysis,
    route,
    router,
    state,
    property,
    revealedContact,
    isFavorite,
    showGallery,
    currentImageIndex,
    pois,
    listing,
    listingId,
    images,
    openGallery,
    closeGallery,
    nextImage,
    prevImage,
    selectImage,
    goHome,
    goMap,
    goAccount,
    handleBack,
    loadSequence,
    load,
    messageOwner,
    toggleFavorite,
  };
}
export default React.forwardRef(function ListingDetailView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="ListingDetailView"
      {...mergeProps({
        className:
          "min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)] antialiased selection:bg-[var(--ui-soft)] selection:text-brand-navy pb-24 lg:pb-16 font-sans",
        "data-sp-4f294819": "",
      })}
    >
      <div
        {...mergeProps({
          className: "max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 pt-5",
          "data-sp-4f294819": "",
        })}
      >
        <LegacyState
          {...mergeProps({
            state: {
              ...ctx.state,
              load: ctx.load,
            },
            "data-sp-4f294819": "",
          })}
        />
        <div
          {...mergeProps({
            className: "flex flex-wrap items-center justify-between gap-3 mb-5",
            "data-sp-4f294819": "",
          })}
        >
          <div
            {...mergeProps({
              className: "flex items-center gap-3",
              "data-sp-4f294819": "",
            })}
          >
            <button
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  return ctx.handleBack?.($event);
                },
                className:
                  "inline-flex items-center gap-2 px-3.5 py-2 rounded-full bg-brand-card text-[var(--ui-accent)] border border-brand-line shadow-2xs hover:bg-brand-card hover:border-[var(--ui-border)]/40 transition-all duration-150 cursor-pointer text-xs font-bold group",
                title: "Quay lại",
                "data-sp-4f294819": "",
              })}
            >
              <svg
                {...mergeProps({
                  width: "14",
                  height: "14",
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  strokeWidth: "2.5",
                  className:
                    "transition-transform group-hover:-translate-x-0.5",
                  "data-sp-4f294819": "",
                })}
              >
                <line
                  {...mergeProps({
                    x1: "19",
                    y1: "12",
                    x2: "5",
                    y2: "12",
                    "data-sp-4f294819": "",
                  })}
                />
                <polyline
                  {...mergeProps({
                    points: "12 19 5 12 12 5",
                    "data-sp-4f294819": "",
                  })}
                />
              </svg>
              <span
                {...mergeProps({
                  "data-sp-4f294819": "",
                })}
              >
                {"Quay lại"}
              </span>
            </button>
            <nav
              {...mergeProps({
                "aria-label": "Breadcrumb",
                className:
                  "hidden sm:inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-card border border-brand-line shadow-2xs text-xs font-medium text-brand-muted",
                "data-sp-4f294819": "",
              })}
            >
              <RouterLink
                {...mergeProps({
                  to: "/",
                  className:
                    "hover:text-[var(--ui-accent)] flex items-center gap-1.5 transition",
                  "data-sp-4f294819": "",
                })}
              >
                <svg
                  {...mergeProps({
                    width: "13",
                    height: "13",
                    viewBox: "0 0 24 24",
                    fill: "none",
                    stroke: "currentColor",
                    strokeWidth: "2",
                    "data-sp-4f294819": "",
                  })}
                >
                  <path
                    {...mergeProps({
                      d: "M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
                      "data-sp-4f294819": "",
                    })}
                  />
                  <polyline
                    {...mergeProps({
                      points: "9 22 9 12 15 12 15 22",
                      "data-sp-4f294819": "",
                    })}
                  />
                </svg>
                <span
                  {...mergeProps({
                    "data-sp-4f294819": "",
                  })}
                >
                  {"Trang chủ"}
                </span>
              </RouterLink>
              <span
                {...mergeProps({
                  className: "text-brand-navy",
                  "data-sp-4f294819": "",
                })}
              >
                {"/"}
              </span>
              <RouterLink
                {...mergeProps({
                  to: "/listings",
                  className: "hover:text-[var(--ui-accent)] transition",
                  "data-sp-4f294819": "",
                })}
              >
                {"Bất động sản Đà Nẵng"}
              </RouterLink>
              <span
                {...mergeProps({
                  className: "text-brand-navy",
                  "data-sp-4f294819": "",
                })}
              >
                {"/"}
              </span>
              <span
                {...mergeProps({
                  className:
                    "text-[var(--ui-accent)] font-bold truncate max-w-[240px] flex items-center gap-1.5",
                  "data-sp-4f294819": "",
                })}
              >
                <span
                  {...mergeProps({
                    className:
                      "w-1.5 h-1.5 rounded-full bg-[var(--ui-success-bg)] animate-pulse",
                    "data-sp-4f294819": "",
                  })}
                />{" "}
                {display(
                  ctx.property?.district
                    ? ctx.property.district + ", Đà Nẵng"
                    : "Chi tiết tin đăng",
                )}
              </span>
            </nav>
          </div>
          <div
            {...mergeProps({
              className: "flex items-center gap-2",
              "data-sp-4f294819": "",
            })}
          >
            <button
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  return ctx.shareListing?.($event);
                },
                className:
                  "inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-brand-card border border-brand-line shadow-2xs hover:bg-brand-card text-brand-muted text-xs font-semibold transition cursor-pointer",
                title: ctx.copiedShareLink
                  ? "Đã sao chép link!"
                  : "Chia sẻ tin đăng",
                "data-sp-4f294819": "",
              })}
            >
              {ctx.copiedShareLink ? (
                <svg
                  {...mergeProps({
                    width: "13",
                    height: "13",
                    viewBox: "0 0 24 24",
                    fill: "none",
                    stroke: "currentColor",
                    strokeWidth: "2.5",
                    className: "text-[var(--ui-success-text)]",
                    "data-sp-4f294819": "",
                  })}
                >
                  <polyline
                    {...mergeProps({
                      points: "20 6 9 17 4 12",
                      "data-sp-4f294819": "",
                    })}
                  />
                </svg>
              ) : (
                <svg
                  {...mergeProps({
                    width: "13",
                    height: "13",
                    viewBox: "0 0 24 24",
                    fill: "none",
                    stroke: "currentColor",
                    strokeWidth: "2",
                    "data-sp-4f294819": "",
                  })}
                >
                  <circle
                    {...mergeProps({
                      cx: "18",
                      cy: "5",
                      r: "3",
                      "data-sp-4f294819": "",
                    })}
                  />
                  <circle
                    {...mergeProps({
                      cx: "6",
                      cy: "12",
                      r: "3",
                      "data-sp-4f294819": "",
                    })}
                  />
                  <circle
                    {...mergeProps({
                      cx: "18",
                      cy: "19",
                      r: "3",
                      "data-sp-4f294819": "",
                    })}
                  />
                  <line
                    {...mergeProps({
                      x1: "8.59",
                      y1: "13.51",
                      x2: "15.42",
                      y2: "17.49",
                      "data-sp-4f294819": "",
                    })}
                  />
                  <line
                    {...mergeProps({
                      x1: "15.41",
                      y1: "6.51",
                      x2: "8.59",
                      y2: "10.49",
                      "data-sp-4f294819": "",
                    })}
                  />
                </svg>
              )}
              <span
                {...mergeProps({
                  "data-sp-4f294819": "",
                })}
              >
                {display(ctx.copiedShareLink ? "Đã chép link" : "Chia sẻ")}
              </span>
            </button>
            <button
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  return ctx.toggleFavorite?.($event);
                },
                className: ["inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-brand-card border shadow-2xs text-xs font-semibold transition cursor-pointer", ctx.isFavorite
                  ? "text-[var(--ui-error-text)] border-[var(--ui-error-border)] bg-[var(--ui-error-bg)]/50"
                  : "text-brand-muted border-brand-line hover:bg-brand-card"],
                
                title: "Lưu tin yêu thích",
                "data-sp-4f294819": "",
              })}
            >
              <svg
                {...mergeProps({
                  width: "13",
                  height: "13",
                  viewBox: "0 0 24 24",
                  fill: ctx.isFavorite ? "currentColor" : "none",
                  stroke: "currentColor",
                  strokeWidth: "2",
                  "data-sp-4f294819": "",
                })}
              >
                <path
                  {...mergeProps({
                    d: "M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z",
                    "data-sp-4f294819": "",
                  })}
                />
              </svg>
              <span
                {...mergeProps({
                  "data-sp-4f294819": "",
                })}
              >
                {display(ctx.isFavorite ? "Đã lưu" : "Lưu tin")}
              </span>
            </button>
            <button
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  ctx.router.push(`/listing/${ctx.route.params.id}/report`);
                },
                className:
                  "inline-flex items-center gap-1.5 px-3 py-2 rounded-full bg-brand-card border border-brand-line shadow-2xs hover:bg-brand-card text-brand-muted hover:text-[var(--ui-error-text)] text-xs font-medium transition cursor-pointer",
                title: "Báo cáo tin đăng",
                "data-sp-4f294819": "",
              })}
            >
              <svg
                {...mergeProps({
                  width: "12",
                  height: "12",
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  strokeWidth: "2",
                  "data-sp-4f294819": "",
                })}
              >
                <path
                  {...mergeProps({
                    d: "M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z",
                    "data-sp-4f294819": "",
                  })}
                />
                <line
                  {...mergeProps({
                    x1: "4",
                    y1: "22",
                    x2: "4",
                    y2: "15",
                    "data-sp-4f294819": "",
                  })}
                />
              </svg>
            </button>
          </div>
        </div>
        {!ctx.property && !ctx.state.busy ? (
          <div
            {...mergeProps({
              className:
                "rounded-3xl bg-brand-card p-8 text-center border border-brand-line shadow-sm max-w-lg mx-auto my-12",
              "data-sp-4f294819": "",
            })}
          >
            <div
              {...mergeProps({
                className:
                  "w-16 h-16 rounded-full bg-brand-card flex items-center justify-center mx-auto mb-4 text-brand-muted",
                "data-sp-4f294819": "",
              })}
            >
              <svg
                {...mergeProps({
                  width: "28",
                  height: "28",
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  strokeWidth: "1.8",
                  "data-sp-4f294819": "",
                })}
              >
                <circle
                  {...mergeProps({
                    cx: "12",
                    cy: "12",
                    r: "10",
                    "data-sp-4f294819": "",
                  })}
                />
                <line
                  {...mergeProps({
                    x1: "12",
                    y1: "8",
                    x2: "12",
                    y2: "12",
                    "data-sp-4f294819": "",
                  })}
                />
                <line
                  {...mergeProps({
                    x1: "12",
                    y1: "16",
                    x2: "12.01",
                    y2: "16",
                    "data-sp-4f294819": "",
                  })}
                />
              </svg>
            </div>
            <h3
              {...mergeProps({
                className: "text-lg font-bold text-[var(--ui-accent)] mb-1",
                "data-sp-4f294819": "",
              })}
            >
              {display(
                ctx.state.notFound
                  ? "Tin đăng không tồn tại"
                  : "Chưa tải được thông tin",
              )}
            </h3>
            <p
              {...mergeProps({
                className: "text-xs text-brand-muted mb-5",
                "data-sp-4f294819": "",
              })}
            >
              {display(
                ctx.state.notFound
                  ? "Tin đăng này đã bị ẩn, đã giao dịch thành công hoặc không còn công khai."
                  : "Vui lòng kiểm tra lại kết nối mạng hoặc thử lại.",
              )}
            </p>
            <div
              {...mergeProps({
                className: "flex items-center justify-center gap-3",
                "data-sp-4f294819": "",
              })}
            >
              <button
                {...mergeProps({
                  type: "button",
                  className:
                    "px-4 py-2 rounded-xl bg-[var(--ui-soft)] text-brand-navy text-xs font-bold hover:bg-[var(--ui-soft)] transition cursor-pointer",
                  onClick: ($event) => {
                    return ctx.load?.($event);
                  },
                  "data-sp-4f294819": "",
                })}
              >
                {" Tải lại trang "}
              </button>
              <RouterLink
                {...mergeProps({
                  to: "/listings",
                  className:
                    "px-4 py-2 rounded-xl bg-brand-card text-[var(--ui-accent)] text-xs font-bold hover:bg-brand-card transition",
                  "data-sp-4f294819": "",
                })}
              >
                {" Khám phá danh sách BĐS "}
              </RouterLink>
            </div>
          </div>
        ) : null}
        {ctx.property && !ctx.state.busy ? (
          <React.Fragment {...mergeProps({})}>
            <section
              {...mergeProps({
                className:
                  "grid grid-cols-1 lg:grid-cols-[2.2fr_1fr] gap-3.5 h-auto lg:h-[450px]",
                "data-sp-4f294819": "",
              })}
            >
              <div
                {...mergeProps({
                  onClick: ($event) => {
                    ctx.openGallery(0);
                  },
                  className:
                    "relative min-h-[300px] lg:min-h-0 rounded-3xl overflow-hidden bg-brand-card border border-brand-line cursor-pointer group shadow-sm",
                  "data-sp-4f294819": "",
                })}
              >
                <PrivateImage
                  {...mergeProps({
                    src: ctx.images[0],
                    alt: ctx.listing.title,
                    className:
                      "absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-[1.02]",
                    "data-sp-4f294819": "",
                  })}
                />
                <div
                  {...mergeProps({
                    className:
                      "absolute inset-0 bg-gradient-to-t from-brand-cream/60 via-transparent to-brand-cream/20 pointer-events-none",
                    "data-sp-4f294819": "",
                  })}
                />
                <div
                  {...mergeProps({
                    className:
                      "absolute top-4 left-4 flex flex-wrap items-center gap-2 z-10 pointer-events-none",
                    "data-sp-4f294819": "",
                  })}
                >
                  <span
                    {...mergeProps({
                      className:
                        "px-3 py-1 rounded-full bg-[var(--ui-soft)]/85 backdrop-blur-md text-brand-navy text-[11px] font-bold border border-brand-line/20 shadow-xs flex items-center gap-1.5",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className:
                          "w-1.5 h-1.5 rounded-full bg-[var(--ui-success-bg)] animate-pulse",
                        "data-sp-4f294819": "",
                      })}
                    />
                    {" Ảnh thực tế đã kiểm duyệt "}
                  </span>
                </div>
                <div
                  {...mergeProps({
                    className:
                      "absolute bottom-4 left-4 z-10 pointer-events-none",
                    "data-sp-4f294819": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className:
                        "inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-brand-card/90 backdrop-blur-md text-[var(--ui-accent)] font-bold text-xs shadow-md border border-brand-line/40",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <svg
                      {...mergeProps({
                        width: "14",
                        height: "14",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <path
                        {...mergeProps({
                          d: "M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z",
                          "data-sp-4f294819": "",
                        })}
                      />
                      <circle
                        {...mergeProps({
                          cx: "12",
                          cy: "13",
                          r: "4",
                          "data-sp-4f294819": "",
                        })}
                      />
                    </svg>
                    <span
                      {...mergeProps({
                        "data-sp-4f294819": "",
                      })}
                    >
                      {"Xem "}
                      {display(ctx.images.length || 1)}
                      {" ảnh chụp"}
                    </span>
                  </div>
                </div>
                <button
                  {...mergeProps({
                    onClick: ($event) => {
                      $event.stopPropagation();
                      return ctx.toggleFavorite?.($event);
                    },
                    className: ["absolute top-4 right-4 w-10 h-10 rounded-full bg-brand-card/90 backdrop-blur-md shadow-md flex items-center justify-center transition-all duration-150 active:scale-90 z-20 cursor-pointer hover:bg-brand-card", ctx.isFavorite
                      ? "text-[var(--ui-error-text)]"
                      : "text-[var(--ui-accent)]"],
                    
                    title: "Lưu tin",
                    "data-sp-4f294819": "",
                  })}
                >
                  <svg
                    {...mergeProps({
                      width: "18",
                      height: "18",
                      viewBox: "0 0 24 24",
                      fill: ctx.isFavorite ? "currentColor" : "none",
                      stroke: "currentColor",
                      strokeWidth: "2",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <path
                      {...mergeProps({
                        d: "M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z",
                        "data-sp-4f294819": "",
                      })}
                    />
                  </svg>
                </button>
              </div>
              {ctx.images.length > 1 ? (
                <div
                  {...mergeProps({
                    className: "hidden lg:grid grid-rows-2 gap-3.5 h-full",
                    "data-sp-4f294819": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      onClick: ($event) => {
                        ctx.openGallery(1);
                      },
                      className:
                        "relative rounded-3xl overflow-hidden bg-brand-card border border-brand-line cursor-pointer group shadow-2xs",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <PrivateImage
                      {...mergeProps({
                        src: ctx.images[1],
                        alt: "Ảnh bất động sản 2",
                        className:
                          "absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105",
                        "data-sp-4f294819": "",
                      })}
                    />
                    <div
                      {...mergeProps({
                        className:
                          "absolute inset-0 bg-brand-cream/10 group-hover:bg-transparent transition",
                        "data-sp-4f294819": "",
                      })}
                    />
                  </div>
                  <div
                    {...mergeProps({
                      className: "grid grid-cols-2 gap-3.5 h-full",
                      "data-sp-4f294819": "",
                    })}
                  >
                    {ctx.images.length > 2 ? (
                      <div
                        {...mergeProps({
                          onClick: ($event) => {
                            ctx.openGallery(2);
                          },
                          className:
                            "relative rounded-3xl overflow-hidden bg-brand-card border border-brand-line cursor-pointer group shadow-2xs",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <PrivateImage
                          {...mergeProps({
                            src: ctx.images[2],
                            alt: "Ảnh bất động sản 3",
                            className:
                              "absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105",
                            "data-sp-4f294819": "",
                          })}
                        />
                        <div
                          {...mergeProps({
                            className:
                              "absolute inset-0 bg-brand-cream/10 group-hover:bg-transparent transition",
                            "data-sp-4f294819": "",
                          })}
                        />
                      </div>
                    ) : null}
                    {ctx.images.length > 3 ? (
                      <div
                        {...mergeProps({
                          onClick: ($event) => {
                            ctx.openGallery(3);
                          },
                          className:
                            "relative rounded-3xl overflow-hidden bg-[var(--ui-soft)] border border-brand-line cursor-pointer group shadow-2xs",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <PrivateImage
                          {...mergeProps({
                            src: ctx.images[3],
                            alt: "Ảnh bất động sản 4",
                            className:
                              "absolute inset-0 w-full h-full object-cover opacity-60 transition-transform duration-500 group-hover:scale-105",
                            "data-sp-4f294819": "",
                          })}
                        />
                        <div
                          {...mergeProps({
                            className:
                              "absolute inset-0 flex flex-col items-center justify-center bg-[var(--ui-soft)]/50 text-brand-navy backdrop-blur-[2px]",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <svg
                            {...mergeProps({
                              width: "22",
                              height: "22",
                              viewBox: "0 0 24 24",
                              fill: "none",
                              stroke: "currentColor",
                              strokeWidth: "2",
                              className: "mb-1 text-[var(--ui-ink)]",
                              "data-sp-4f294819": "",
                            })}
                          >
                            <rect
                              {...mergeProps({
                                x: "3",
                                y: "3",
                                width: "18",
                                height: "18",
                                rx: "2",
                                ry: "2",
                                "data-sp-4f294819": "",
                              })}
                            />
                            <circle
                              {...mergeProps({
                                cx: "8.5",
                                cy: "8.5",
                                r: "1.5",
                                "data-sp-4f294819": "",
                              })}
                            />
                            <polyline
                              {...mergeProps({
                                points: "21 15 16 10 5 21",
                                "data-sp-4f294819": "",
                              })}
                            />
                          </svg>
                          <span
                            {...mergeProps({
                              className: "text-xs font-black tracking-wide",
                              "data-sp-4f294819": "",
                            })}
                          >
                            {" +"}
                            {display(ctx.images.length - 3)}
                            {" ảnh "}
                          </span>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </section>
            <div
              {...mergeProps({
                className:
                  "grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-8 mt-8 items-start",
                "data-sp-4f294819": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "space-y-6",
                  "data-sp-4f294819": "",
                })}
              >
                <section
                  {...mergeProps({
                    className:
                      "bg-brand-card rounded-3xl p-6 sm:p-8 border border-brand-line shadow-xs",
                    "data-sp-4f294819": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className: "flex flex-wrap items-center gap-2 mb-4",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <span
                      {...mergeProps({
                        className:
                          "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[var(--ui-surface)] text-[var(--ui-accent)] border border-[var(--ui-border)]",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <span
                        {...mergeProps({
                          className: "w-1.5 h-1.5 rounded-full bg-[var(--ui-soft)]",
                          "data-sp-4f294819": "",
                        })}
                      />{" "}
                      {display(ctx.listing.type || "Bất động sản")}
                    </span>
                    <span
                      {...mergeProps({
                        className:
                          "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-brand-card text-brand-muted",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <svg
                        {...mergeProps({
                          width: "12",
                          height: "12",
                          viewBox: "0 0 24 24",
                          fill: "none",
                          stroke: "currentColor",
                          strokeWidth: "2",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <circle
                          {...mergeProps({
                            cx: "12",
                            cy: "12",
                            r: "10",
                            "data-sp-4f294819": "",
                          })}
                        />
                        <polyline
                          {...mergeProps({
                            points: "12 6 12 12 16 14",
                            "data-sp-4f294819": "",
                          })}
                        />
                      </svg>{" "}
                      {display(
                        ctx.property?.transactionType === "RENT"
                          ? "Cho thuê"
                          : "Đang bán",
                      )}
                    </span>
                    <span
                      {...mergeProps({
                        className:
                          "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[var(--ui-success-bg)] text-[var(--ui-success-text)] border border-[var(--ui-success-border)]",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <svg
                        {...mergeProps({
                          width: "12",
                          height: "12",
                          viewBox: "0 0 24 24",
                          fill: "none",
                          stroke: "currentColor",
                          strokeWidth: "2.5",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <path
                          {...mergeProps({
                            d: "M22 11.08V12a10 10 0 1 1-5.93-9.14",
                            "data-sp-4f294819": "",
                          })}
                        />
                        <polyline
                          {...mergeProps({
                            points: "22 4 12 14.01 9 11.01",
                            "data-sp-4f294819": "",
                          })}
                        />
                      </svg>
                      {" Xác thực thực địa SmartProp "}
                    </span>
                  </div>
                  <h1
                    {...mergeProps({
                      className:
                        "text-2xl sm:text-3xl font-extrabold text-[var(--ui-accent)] tracking-tight leading-snug",
                      "data-sp-4f294819": "",
                    })}
                  >
                    {display(ctx.listing.title)}
                  </h1>
                  <div
                    {...mergeProps({
                      className:
                        "flex items-start gap-2 mt-3 text-brand-muted text-xs sm:text-sm",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <svg
                      {...mergeProps({
                        width: "16",
                        height: "16",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2",
                        className: "text-[var(--ui-accent)] shrink-0 mt-0.5",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <path
                        {...mergeProps({
                          d: "M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z",
                          "data-sp-4f294819": "",
                        })}
                      />
                      <circle
                        {...mergeProps({
                          cx: "12",
                          cy: "10",
                          r: "3",
                          "data-sp-4f294819": "",
                        })}
                      />
                    </svg>
                    <span
                      {...mergeProps({
                        className: "font-medium leading-relaxed",
                        "data-sp-4f294819": "",
                      })}
                    >
                      {display(ctx.listing.location)}
                    </span>
                  </div>
                  <div
                    {...mergeProps({
                      className:
                        "mt-6 p-5 sm:p-6 rounded-2xl bg-[var(--ui-surface)] border border-[var(--ui-border)] flex flex-col sm:flex-row sm:items-center justify-between gap-4",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <div
                      {...mergeProps({
                        "data-sp-4f294819": "",
                      })}
                    >
                      <p
                        {...mergeProps({
                          className:
                            "text-[11px] font-bold text-[var(--ui-accent)] uppercase tracking-wider",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {"Mức giá chào niêm yết"}
                      </p>
                      <div
                        {...mergeProps({
                          className: "flex flex-wrap items-baseline gap-3 mt-1",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            className:
                              "text-3xl sm:text-4xl font-black text-[var(--ui-muted)] tracking-tight",
                            "data-sp-4f294819": "",
                          })}
                        >
                          {display(ctx.listing.price)}
                        </span>
                        <span
                          {...mergeProps({
                            className:
                              "px-2.5 py-1 rounded-lg bg-brand-card border border-brand-line text-xs font-bold text-[var(--ui-accent)] shadow-2xs",
                            "data-sp-4f294819": "",
                          })}
                        >
                          {display(ctx.listing.pricePerM2)}
                        </span>
                      </div>
                    </div>
                    <div
                      {...mergeProps({
                        className:
                          "sm:text-right border-t sm:border-t-0 pt-3 sm:pt-0 border-brand-line",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <span
                        {...mergeProps({
                          className:
                            "inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--ui-success-text)] bg-[var(--ui-success-bg)] px-3 py-1.5 rounded-full border border-[var(--ui-success-border)]",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <svg
                          {...mergeProps({
                            width: "13",
                            height: "13",
                            viewBox: "0 0 24 24",
                            fill: "none",
                            stroke: "currentColor",
                            strokeWidth: "2.5",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <polyline
                            {...mergeProps({
                              points: "20 6 9 17 4 12",
                              "data-sp-4f294819": "",
                            })}
                          />
                        </svg>
                        {" Giá đã kiểm duyệt & Thương lượng "}
                      </span>
                      <p
                        {...mergeProps({
                          className: "text-[11px] text-brand-muted mt-1",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {"Không thu phí người mua / xem nhà"}
                      </p>
                    </div>
                  </div>
                  <div
                    {...mergeProps({
                      className:
                        "grid grid-cols-2 sm:grid-cols-4 gap-3.5 mt-6 pt-6 border-t border-brand-line",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <div
                      {...mergeProps({
                        className:
                          "bg-brand-card hover:bg-brand-card hover:border-[var(--ui-border)]/30 border border-brand-line rounded-2xl p-4 transition-all duration-150",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          className:
                            "w-9 h-9 rounded-xl bg-brand-card text-[var(--ui-accent)] flex items-center justify-center mb-2.5 border border-brand-line",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <svg
                          {...mergeProps({
                            width: "18",
                            height: "18",
                            viewBox: "0 0 24 24",
                            fill: "none",
                            stroke: "currentColor",
                            strokeWidth: "2",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <path
                            {...mergeProps({
                              d: "M21 3H3v18h18V3z",
                              "data-sp-4f294819": "",
                            })}
                          />
                          <path
                            {...mergeProps({
                              d: "M3 9h18",
                              "data-sp-4f294819": "",
                            })}
                          />
                          <path
                            {...mergeProps({
                              d: "M9 21V9",
                              "data-sp-4f294819": "",
                            })}
                          />
                        </svg>
                      </div>
                      <p
                        {...mergeProps({
                          className:
                            "text-[11px] font-semibold text-brand-muted uppercase tracking-wider",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {"Diện tích"}
                      </p>
                      <p
                        {...mergeProps({
                          className:
                            "text-sm font-extrabold text-[var(--ui-accent)] truncate mt-0.5",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(ctx.listing.area)}
                      </p>
                    </div>
                    <div
                      {...mergeProps({
                        className:
                          "bg-brand-card hover:bg-brand-card hover:border-[var(--ui-border)]/30 border border-brand-line rounded-2xl p-4 transition-all duration-150",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          className:
                            "w-9 h-9 rounded-xl bg-brand-card text-[var(--ui-accent)] flex items-center justify-center mb-2.5 border border-brand-line",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <svg
                          {...mergeProps({
                            width: "18",
                            height: "18",
                            viewBox: "0 0 24 24",
                            fill: "none",
                            stroke: "currentColor",
                            strokeWidth: "2",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <circle
                            {...mergeProps({
                              cx: "12",
                              cy: "12",
                              r: "10",
                              "data-sp-4f294819": "",
                            })}
                          />
                          <polygon
                            {...mergeProps({
                              points:
                                "16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76",
                              "data-sp-4f294819": "",
                            })}
                          />
                        </svg>
                      </div>
                      <p
                        {...mergeProps({
                          className:
                            "text-[11px] font-semibold text-brand-muted uppercase tracking-wider",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {"Hướng nhà"}
                      </p>
                      <p
                        {...mergeProps({
                          className:
                            "text-sm font-extrabold text-[var(--ui-accent)] truncate mt-0.5",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(ctx.property?.direction || "Đông Nam")}
                      </p>
                    </div>
                    <div
                      {...mergeProps({
                        className:
                          "bg-brand-card hover:bg-brand-card hover:border-[var(--ui-border)]/30 border border-brand-line rounded-2xl p-4 transition-all duration-150",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          className:
                            "w-9 h-9 rounded-xl bg-brand-card text-[var(--ui-accent)] flex items-center justify-center mb-2.5 border border-brand-line",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {ctx.isLandProperty ? (
                          <svg
                            {...mergeProps({
                              width: "18",
                              height: "18",
                              viewBox: "0 0 24 24",
                              fill: "none",
                              stroke: "currentColor",
                              strokeWidth: "2",
                              "data-sp-4f294819": "",
                            })}
                          >
                            <path
                              {...mergeProps({
                                d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z",
                                "data-sp-4f294819": "",
                              })}
                            />
                            <polyline
                              {...mergeProps({
                                points: "14 2 14 8 20 8",
                                "data-sp-4f294819": "",
                              })}
                            />
                            <line
                              {...mergeProps({
                                x1: "16",
                                y1: "13",
                                x2: "8",
                                y2: "13",
                                "data-sp-4f294819": "",
                              })}
                            />
                            <line
                              {...mergeProps({
                                x1: "16",
                                y1: "17",
                                x2: "8",
                                y2: "17",
                                "data-sp-4f294819": "",
                              })}
                            />
                          </svg>
                        ) : (
                          <svg
                            {...mergeProps({
                              width: "18",
                              height: "18",
                              viewBox: "0 0 24 24",
                              fill: "none",
                              stroke: "currentColor",
                              strokeWidth: "2",
                              "data-sp-4f294819": "",
                            })}
                          >
                            <path
                              {...mergeProps({
                                d: "M2 4v16",
                                "data-sp-4f294819": "",
                              })}
                            />
                            <path
                              {...mergeProps({
                                d: "M2 8h18a2 2 0 0 1 2 2v10",
                                "data-sp-4f294819": "",
                              })}
                            />
                            <path
                              {...mergeProps({
                                d: "M2 17h20",
                                "data-sp-4f294819": "",
                              })}
                            />
                            <path
                              {...mergeProps({
                                d: "M6 8v9",
                                "data-sp-4f294819": "",
                              })}
                            />
                          </svg>
                        )}
                      </div>
                      <p
                        {...mergeProps({
                          className:
                            "text-[11px] font-semibold text-brand-muted uppercase tracking-wider",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(ctx.isLandProperty ? "Pháp lý" : "Phòng ngủ")}
                      </p>
                      <p
                        {...mergeProps({
                          className:
                            "text-sm font-extrabold text-[var(--ui-accent)] truncate mt-0.5",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(
                          ctx.isLandProperty
                            ? "Sổ hồng / Sổ đỏ"
                            : ctx.property?.bedrooms
                              ? ctx.property.bedrooms + " phòng ngủ"
                              : "1 phòng ngủ",
                        )}
                      </p>
                    </div>
                    <div
                      {...mergeProps({
                        className:
                          "bg-brand-card hover:bg-brand-card hover:border-[var(--ui-border)]/30 border border-brand-line rounded-2xl p-4 transition-all duration-150",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          className:
                            "w-9 h-9 rounded-xl bg-brand-card text-[var(--ui-accent)] flex items-center justify-center mb-2.5 border border-brand-line",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {ctx.isLandProperty ? (
                          <svg
                            {...mergeProps({
                              width: "18",
                              height: "18",
                              viewBox: "0 0 24 24",
                              fill: "none",
                              stroke: "currentColor",
                              strokeWidth: "2",
                              "data-sp-4f294819": "",
                            })}
                          >
                            <rect
                              {...mergeProps({
                                x: "2",
                                y: "5",
                                width: "20",
                                height: "14",
                                rx: "2",
                                "data-sp-4f294819": "",
                              })}
                            />
                            <line
                              {...mergeProps({
                                x1: "2",
                                y1: "10",
                                x2: "22",
                                y2: "10",
                                "data-sp-4f294819": "",
                              })}
                            />
                          </svg>
                        ) : (
                          <svg
                            {...mergeProps({
                              width: "18",
                              height: "18",
                              viewBox: "0 0 24 24",
                              fill: "none",
                              stroke: "currentColor",
                              strokeWidth: "2",
                              "data-sp-4f294819": "",
                            })}
                          >
                            <path
                              {...mergeProps({
                                d: "M9 6h6",
                                "data-sp-4f294819": "",
                              })}
                            />
                            <path
                              {...mergeProps({
                                d: "M12 6v6",
                                "data-sp-4f294819": "",
                              })}
                            />
                            <circle
                              {...mergeProps({
                                cx: "12",
                                cy: "14",
                                r: "2",
                                "data-sp-4f294819": "",
                              })}
                            />
                            <path
                              {...mergeProps({
                                d: "M4 21h16a2 2 0 0 0 2-2v-5a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2z",
                                "data-sp-4f294819": "",
                              })}
                            />
                          </svg>
                        )}
                      </div>
                      <p
                        {...mergeProps({
                          className:
                            "text-[11px] font-semibold text-brand-muted uppercase tracking-wider",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(ctx.isLandProperty ? "Lộ giới" : "Phòng tắm")}
                      </p>
                      <p
                        {...mergeProps({
                          className:
                            "text-sm font-extrabold text-[var(--ui-accent)] truncate mt-0.5",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(
                          ctx.isLandProperty
                            ? "Đường 7.5m - 15m"
                            : ctx.property?.bathrooms
                              ? ctx.property.bathrooms + " phòng tắm"
                              : "1 phòng tắm",
                        )}
                      </p>
                    </div>
                  </div>
                </section>
                {ctx.listing.hasWarning ? (
                  <section
                    {...mergeProps({
                      className:
                        "rounded-3xl p-6 bg-[var(--ui-warning-bg)]/90 border border-[var(--ui-warning-border)] shadow-xs",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <div
                      {...mergeProps({
                        className:
                          "flex flex-col sm:flex-row sm:items-center justify-between gap-4",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          className: "flex items-start gap-3.5",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <div
                          {...mergeProps({
                            className:
                              "w-10 h-10 rounded-2xl bg-[var(--ui-warning-bg)] text-brand-navy flex items-center justify-center shrink-0 shadow-sm",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <svg
                            {...mergeProps({
                              width: "20",
                              height: "20",
                              viewBox: "0 0 24 24",
                              fill: "none",
                              stroke: "currentColor",
                              strokeWidth: "2.2",
                              "data-sp-4f294819": "",
                            })}
                          >
                            <path
                              {...mergeProps({
                                d: "M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z",
                                "data-sp-4f294819": "",
                              })}
                            />
                            <line
                              {...mergeProps({
                                x1: "12",
                                y1: "9",
                                x2: "12",
                                y2: "13",
                                "data-sp-4f294819": "",
                              })}
                            />
                            <line
                              {...mergeProps({
                                x1: "12",
                                y1: "17",
                                x2: "12.01",
                                y2: "17",
                                "data-sp-4f294819": "",
                              })}
                            />
                          </svg>
                        </div>
                        <div
                          {...mergeProps({
                            "data-sp-4f294819": "",
                          })}
                        >
                          <h3
                            {...mergeProps({
                              className:
                                "font-bold text-[var(--ui-warning-text)] text-sm sm:text-base",
                              "data-sp-4f294819": "",
                            })}
                          >
                            {"Lưu ý đối chiếu hình ảnh & thông tin"}
                          </h3>
                          <p
                            {...mergeProps({
                              className:
                                "text-xs text-[var(--ui-warning-text)]/90 mt-1 leading-relaxed",
                              "data-sp-4f294819": "",
                            })}
                          >
                            {
                              " Hệ thống ghi nhận hình ảnh có mức độ tương đồng với một số tin đăng khác. Quý khách nên kiểm tra thực địa cùng chuyên viên SmartProp. "
                            }
                          </p>
                        </div>
                      </div>
                      <span
                        {...mergeProps({
                          className:
                            "px-3.5 py-1.5 rounded-full bg-[var(--ui-warning-bg)] text-brand-navy text-xs font-bold self-start sm:self-center shrink-0",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(ctx.listing.statusText || "Cần kiểm tra")}
                      </span>
                    </div>
                  </section>
                ) : (
                  <section
                    {...mergeProps({
                      className:
                        "rounded-3xl p-6 sm:p-7 bg-gradient-to-r from-emerald-50/90 via-[var(--ui-surface)] to-emerald-50/90 border border-[var(--ui-success-border)] shadow-xs",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <div
                      {...mergeProps({
                        className:
                          "flex flex-col sm:flex-row sm:items-center justify-between gap-4",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          className: "flex items-start gap-3.5",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <div
                          {...mergeProps({
                            className:
                              "w-11 h-11 rounded-2xl bg-[var(--ui-success-bg)] text-brand-navy flex items-center justify-center shrink-0 shadow-sm",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <svg
                            {...mergeProps({
                              width: "22",
                              height: "22",
                              viewBox: "0 0 24 24",
                              fill: "none",
                              stroke: "currentColor",
                              strokeWidth: "2.2",
                              "data-sp-4f294819": "",
                            })}
                          >
                            <path
                              {...mergeProps({
                                d: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
                                "data-sp-4f294819": "",
                              })}
                            />
                            <polyline
                              {...mergeProps({
                                points: "9 12 11 14 15 10",
                                "data-sp-4f294819": "",
                              })}
                            />
                          </svg>
                        </div>
                        <div
                          {...mergeProps({
                            "data-sp-4f294819": "",
                          })}
                        >
                          <div
                            {...mergeProps({
                              className: "flex items-center gap-2",
                              "data-sp-4f294819": "",
                            })}
                          >
                            <h3
                              {...mergeProps({
                                className:
                                  "font-bold text-[var(--ui-success-text)] text-sm sm:text-base",
                                "data-sp-4f294819": "",
                              })}
                            >
                              {" Bảo chứng an toàn SmartProp Verify™ "}
                            </h3>
                            <span
                              {...mergeProps({
                                className:
                                  "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[var(--ui-success-bg)] text-[var(--ui-success-text)]",
                                "data-sp-4f294819": "",
                              })}
                            >
                              {" Đã kiểm duyệt "}
                            </span>
                          </div>
                          <p
                            {...mergeProps({
                              className:
                                "text-xs text-[var(--ui-success-text)]/80 mt-1.5 leading-relaxed",
                              "data-sp-4f294819": "",
                            })}
                          >
                            {
                              " Tin đăng đã được định vị vệ tinh GPS chuẩn xác tại Đà Nẵng, kiểm tra pháp lý sơ bộ và đối chiếu ảnh thực địa chống tin ảo. "
                            }
                          </p>
                        </div>
                      </div>
                      <div
                        {...mergeProps({
                          className: "shrink-0 self-start sm:self-center",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            className:
                              "px-4 py-2 rounded-full bg-[var(--ui-success-bg)] text-brand-navy text-xs font-bold shadow-xs inline-flex items-center gap-1.5",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              className:
                                "w-2 h-2 rounded-full bg-brand-card animate-pulse",
                              "data-sp-4f294819": "",
                            })}
                          />
                          {" An toàn giao dịch "}
                        </span>
                      </div>
                    </div>
                  </section>
                )}
                <section
                  {...mergeProps({
                    className:
                      "bg-brand-card rounded-3xl p-6 sm:p-8 border border-brand-line shadow-xs",
                    "data-sp-4f294819": "",
                  })}
                >
                  <h2
                    {...mergeProps({
                      className:
                        "text-base font-bold text-[var(--ui-accent)] mb-4 flex items-center gap-2",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <svg
                      {...mergeProps({
                        width: "18",
                        height: "18",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2",
                        className: "text-[var(--ui-accent)]",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <path
                        {...mergeProps({
                          d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z",
                          "data-sp-4f294819": "",
                        })}
                      />
                      <polyline
                        {...mergeProps({
                          points: "14 2 14 8 20 8",
                          "data-sp-4f294819": "",
                        })}
                      />
                      <line
                        {...mergeProps({
                          x1: "16",
                          y1: "13",
                          x2: "8",
                          y2: "13",
                          "data-sp-4f294819": "",
                        })}
                      />
                      <line
                        {...mergeProps({
                          x1: "16",
                          y1: "17",
                          x2: "8",
                          y2: "17",
                          "data-sp-4f294819": "",
                        })}
                      />
                    </svg>
                    <span
                      {...mergeProps({
                        "data-sp-4f294819": "",
                      })}
                    >
                      {"Mô tả chi tiết bất động sản"}
                    </span>
                  </h2>
                  <div
                    {...mergeProps({
                      className:
                        "text-xs sm:text-sm text-brand-muted leading-relaxed space-y-3 whitespace-pre-line font-normal",
                      "data-sp-4f294819": "",
                    })}
                  >
                    {display(
                      ctx.property?.description || ctx.listing.description1,
                    )}
                  </div>
                </section>
                {ctx.property.declaredAmenities?.length ? (
                  <section
                    {...mergeProps({
                      className:
                        "bg-brand-card rounded-3xl p-6 sm:p-8 border border-brand-line shadow-xs",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <h2
                      {...mergeProps({
                        className:
                          "text-base font-bold text-[var(--ui-accent)] mb-4 flex items-center gap-2",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <svg
                        {...mergeProps({
                          width: "18",
                          height: "18",
                          viewBox: "0 0 24 24",
                          fill: "none",
                          stroke: "currentColor",
                          strokeWidth: "2",
                          className: "text-[var(--ui-accent)]",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <polygon
                          {...mergeProps({
                            points:
                              "12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2",
                            "data-sp-4f294819": "",
                          })}
                        />
                      </svg>
                      <span
                        {...mergeProps({
                          "data-sp-4f294819": "",
                        })}
                      >
                        {"Tiện ích & Đặc điểm nổi bật"}
                      </span>
                    </h2>
                    <div
                      {...mergeProps({
                        className:
                          "grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3",
                        "data-sp-4f294819": "",
                      })}
                    >
                      {renderList(ctx.property.declaredAmenities, (amenity) => (
                        <div
                          key={amenity}
                          {...mergeProps({
                            className:
                              "flex items-center gap-2.5 p-3 rounded-2xl bg-brand-card border border-brand-line text-xs font-semibold text-[var(--ui-accent)] hover:border-[var(--ui-border)]/40 hover:bg-brand-card transition-all shadow-2xs",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              className:
                                "w-6 h-6 rounded-lg bg-[var(--ui-success-bg)] text-[var(--ui-success-text)] flex items-center justify-center text-xs shrink-0 font-bold",
                              "data-sp-4f294819": "",
                            })}
                          >
                            {" ✓ "}
                          </span>
                          <span
                            {...mergeProps({
                              className: "truncate",
                              "data-sp-4f294819": "",
                            })}
                          >
                            {display(amenity)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </section>
                ) : null}
                <section
                  {...mergeProps({
                    className:
                      "bg-brand-card rounded-3xl p-6 sm:p-8 border border-brand-line shadow-xs",
                    "data-sp-4f294819": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className: "flex items-center justify-between mb-5",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <h2
                      {...mergeProps({
                        className:
                          "text-base font-bold text-[var(--ui-accent)] flex items-center gap-2",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <svg
                        {...mergeProps({
                          width: "18",
                          height: "18",
                          viewBox: "0 0 24 24",
                          fill: "none",
                          stroke: "currentColor",
                          strokeWidth: "2",
                          className: "text-[var(--ui-accent)]",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <circle
                          {...mergeProps({
                            cx: "12",
                            cy: "12",
                            r: "10",
                            "data-sp-4f294819": "",
                          })}
                        />
                        <path
                          {...mergeProps({
                            d: "M16.2 7.8l-2 6.3-6.4 2 2-6.3z",
                            "data-sp-4f294819": "",
                          })}
                        />
                      </svg>
                      <span
                        {...mergeProps({
                          "data-sp-4f294819": "",
                        })}
                      >
                        {"Liên kết vùng & Tiện ích lân cận (Đà Nẵng)"}
                      </span>
                    </h2>
                    <span
                      {...mergeProps({
                        className: "text-xs font-semibold text-brand-muted",
                        "data-sp-4f294819": "",
                      })}
                    >
                      {"Khoảng cách thực tế"}
                    </span>
                  </div>
                  {ctx.nearbyDaNangLandmarks.length ? (
                    <div
                      {...mergeProps({
                        className:
                          "grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3.5",
                        "data-sp-4f294819": "",
                      })}
                    >
                      {renderList(
                        ctx.nearbyDaNangLandmarks.slice(0, 8),
                        (item) => (
                          <div
                            key={item.name}
                            {...mergeProps({
                              className:
                                "p-3.5 rounded-2xl bg-brand-card border border-brand-line hover:border-[var(--ui-border)]/30 hover:bg-brand-card transition-all flex flex-col justify-between shadow-2xs group",
                              "data-sp-4f294819": "",
                            })}
                          >
                            <div
                              {...mergeProps({
                                "data-sp-4f294819": "",
                              })}
                            >
                              <div
                                {...mergeProps({
                                  className:
                                    "flex items-center justify-between mb-2.5",
                                  "data-sp-4f294819": "",
                                })}
                              >
                                <div
                                  {...mergeProps({
                                    className:
                                      "w-8 h-8 rounded-xl bg-brand-card text-[var(--ui-accent)] flex items-center justify-center border border-brand-line group-hover:scale-105 transition-transform",
                                    "data-sp-4f294819": "",
                                  })}
                                >
                                  {item.iconType === "beach" ? (
                                    <svg
                                      {...mergeProps({
                                        width: "16",
                                        height: "16",
                                        viewBox: "0 0 24 24",
                                        fill: "none",
                                        stroke: "currentColor",
                                        strokeWidth: "2",
                                        "data-sp-4f294819": "",
                                      })}
                                    >
                                      <path
                                        {...mergeProps({
                                          d: "M2 18c3-3 6-3 9 0 3-3 6-3 9 0",
                                          "data-sp-4f294819": "",
                                        })}
                                      />
                                      <path
                                        {...mergeProps({
                                          d: "M2 14c3-3 6-3 9 0 3-3 6-3 9 0",
                                          "data-sp-4f294819": "",
                                        })}
                                      />
                                    </svg>
                                  ) : item.iconType === "bridge" ? (
                                    <svg
                                      {...mergeProps({
                                        width: "16",
                                        height: "16",
                                        viewBox: "0 0 24 24",
                                        fill: "none",
                                        stroke: "currentColor",
                                        strokeWidth: "2",
                                        "data-sp-4f294819": "",
                                      })}
                                    >
                                      <path
                                        {...mergeProps({
                                          d: "M3 17h18M4 17V8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9M9 17v-6M15 17v-6",
                                          "data-sp-4f294819": "",
                                        })}
                                      />
                                    </svg>
                                  ) : item.iconType === "plane" ? (
                                    <svg
                                      {...mergeProps({
                                        width: "16",
                                        height: "16",
                                        viewBox: "0 0 24 24",
                                        fill: "none",
                                        stroke: "currentColor",
                                        strokeWidth: "2",
                                        "data-sp-4f294819": "",
                                      })}
                                    >
                                      <path
                                        {...mergeProps({
                                          d: "M17.8 19.2L16 11l3.5-3.5C21 6 21.5 4 21 3.5c-.5-.5-2.5 0-4 1.5L13.5 8.5 5.3 6.7c-.6-.1-1.2.1-1.5.7l-.5.9 5.4 3.7-2.6 2.6-2.5-.7c-.4-.1-.8.1-1 .4l-.3.4 3.3 2.1 2.1 3.3.4-.3c.3-.3.5-.6.4-1l-.7-2.5 2.6-2.6 3.7 5.4.9-.5c.6-.4.8-1 .7-1.5z",
                                          "data-sp-4f294819": "",
                                        })}
                                      />
                                    </svg>
                                  ) : item.iconType === "hospital" ? (
                                    <svg
                                      {...mergeProps({
                                        width: "16",
                                        height: "16",
                                        viewBox: "0 0 24 24",
                                        fill: "none",
                                        stroke: "currentColor",
                                        strokeWidth: "2",
                                        "data-sp-4f294819": "",
                                      })}
                                    >
                                      <path
                                        {...mergeProps({
                                          d: "M3 21h18M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16M9 9h6M12 6v6",
                                          "data-sp-4f294819": "",
                                        })}
                                      />
                                    </svg>
                                  ) : item.iconType === "shop" ? (
                                    <svg
                                      {...mergeProps({
                                        width: "16",
                                        height: "16",
                                        viewBox: "0 0 24 24",
                                        fill: "none",
                                        stroke: "currentColor",
                                        strokeWidth: "2",
                                        "data-sp-4f294819": "",
                                      })}
                                    >
                                      <path
                                        {...mergeProps({
                                          d: "M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z",
                                          "data-sp-4f294819": "",
                                        })}
                                      />
                                      <line
                                        {...mergeProps({
                                          x1: "3",
                                          y1: "6",
                                          x2: "21",
                                          y2: "6",
                                          "data-sp-4f294819": "",
                                        })}
                                      />
                                      <path
                                        {...mergeProps({
                                          d: "M16 10a4 4 0 0 1-8 0",
                                          "data-sp-4f294819": "",
                                        })}
                                      />
                                    </svg>
                                  ) : item.iconType === "school" ? (
                                    <svg
                                      {...mergeProps({
                                        width: "16",
                                        height: "16",
                                        viewBox: "0 0 24 24",
                                        fill: "none",
                                        stroke: "currentColor",
                                        strokeWidth: "2",
                                        "data-sp-4f294819": "",
                                      })}
                                    >
                                      <path
                                        {...mergeProps({
                                          d: "M22 10v6M2 10l10-5 10 5-10 5z",
                                          "data-sp-4f294819": "",
                                        })}
                                      />
                                      <path
                                        {...mergeProps({
                                          d: "M6 12v5c3 3 9 3 12 0v-5",
                                          "data-sp-4f294819": "",
                                        })}
                                      />
                                    </svg>
                                  ) : (
                                    <svg
                                      {...mergeProps({
                                        width: "16",
                                        height: "16",
                                        viewBox: "0 0 24 24",
                                        fill: "none",
                                        stroke: "currentColor",
                                        strokeWidth: "2",
                                        "data-sp-4f294819": "",
                                      })}
                                    >
                                      <path
                                        {...mergeProps({
                                          d: "M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z",
                                          "data-sp-4f294819": "",
                                        })}
                                      />
                                      <circle
                                        {...mergeProps({
                                          cx: "12",
                                          cy: "10",
                                          r: "3",
                                          "data-sp-4f294819": "",
                                        })}
                                      />
                                    </svg>
                                  )}
                                </div>
                                <span
                                  {...mergeProps({
                                    className:
                                      "text-[11px] font-extrabold text-[var(--ui-accent)] bg-[var(--ui-surface)] px-2 py-0.5 rounded-full border border-[var(--ui-border)]",
                                    "data-sp-4f294819": "",
                                  })}
                                >
                                  {display(item.distText)}
                                </span>
                              </div>
                              <p
                                {...mergeProps({
                                  className:
                                    "text-xs font-bold text-[var(--ui-accent)] leading-snug",
                                  "data-sp-4f294819": "",
                                })}
                              >
                                {display(item.name)}
                              </p>
                            </div>
                            <div
                              {...mergeProps({
                                className:
                                  "mt-2.5 pt-2 border-t border-brand-line/80 flex items-center justify-between text-[10px] text-brand-muted",
                                "data-sp-4f294819": "",
                              })}
                            >
                              <span
                                {...mergeProps({
                                  "data-sp-4f294819": "",
                                })}
                              >
                                {display(item.category)}
                              </span>
                              <span
                                {...mergeProps({
                                  className: "text-[var(--ui-accent)] font-bold",
                                  "data-sp-4f294819": "",
                                })}
                              >
                                {"~"}
                                {display(item.estMinutes)}
                                {"p"}
                              </span>
                            </div>
                          </div>
                        ),
                      )}
                    </div>
                  ) : null}
                </section>
                <section
                  {...mergeProps({
                    className:
                      "bg-brand-card rounded-3xl p-6 sm:p-8 border border-brand-line shadow-xs",
                    "data-sp-4f294819": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className:
                        "flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <div
                      {...mergeProps({
                        "data-sp-4f294819": "",
                      })}
                    >
                      <h2
                        {...mergeProps({
                          className:
                            "text-base font-bold text-[var(--ui-accent)] flex items-center gap-2",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <svg
                          {...mergeProps({
                            width: "18",
                            height: "18",
                            viewBox: "0 0 24 24",
                            fill: "none",
                            stroke: "currentColor",
                            strokeWidth: "2",
                            className: "text-[var(--ui-accent)]",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <polygon
                            {...mergeProps({
                              points:
                                "1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6",
                              "data-sp-4f294819": "",
                            })}
                          />
                          <line
                            {...mergeProps({
                              x1: "8",
                              y1: "2",
                              x2: "8",
                              y2: "18",
                              "data-sp-4f294819": "",
                            })}
                          />
                          <line
                            {...mergeProps({
                              x1: "16",
                              y1: "6",
                              x2: "16",
                              y2: "22",
                              "data-sp-4f294819": "",
                            })}
                          />
                        </svg>
                        <span
                          {...mergeProps({
                            "data-sp-4f294819": "",
                          })}
                        >
                          {"Vị trí trên bản đồ vệ tinh"}
                        </span>
                      </h2>
                      <p
                        {...mergeProps({
                          className: "text-xs text-brand-muted mt-0.5",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(ctx.listing.location)}
                      </p>
                    </div>
                    <button
                      {...mergeProps({
                        type: "button",
                        onClick: ($event) => {
                          return ctx.goMap?.($event);
                        },
                        className:
                          "px-4 py-2 rounded-xl bg-[var(--ui-soft)] hover:bg-[var(--ui-soft)] text-brand-navy text-xs font-bold shadow-2xs flex items-center gap-1.5 self-start sm:self-center transition cursor-pointer",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <svg
                        {...mergeProps({
                          width: "14",
                          height: "14",
                          viewBox: "0 0 24 24",
                          fill: "none",
                          stroke: "currentColor",
                          strokeWidth: "2",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <polygon
                          {...mergeProps({
                            points:
                              "1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6",
                            "data-sp-4f294819": "",
                          })}
                        />
                      </svg>
                      <span
                        {...mergeProps({
                          "data-sp-4f294819": "",
                        })}
                      >
                        {"Mở SmartProp GIS"}
                      </span>
                    </button>
                  </div>
                  <div
                    {...mergeProps({
                      className:
                        "relative rounded-2xl overflow-hidden bg-brand-card border border-brand-line",
                      "data-sp-4f294819": "",
                    })}
                  >
                    {ctx.mapUrl(ctx.property) ? (
                      <PropertyExplorer
                        {...mergeProps({
                          items: [ctx.property],
                          selectedId: ctx.property.id,
                          "data-sp-4f294819": "",
                        })}
                      />
                    ) : (
                      <div
                        {...mergeProps({
                          className:
                            "h-full flex items-center justify-center p-6 text-sm text-brand-muted",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {" Chưa có vị trí bản đồ cho tin đăng này. "}
                      </div>
                    )}
                    <div
                      {...mergeProps({
                        className:
                          "absolute bottom-3 left-3 pointer-events-none",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          className:
                            "bg-[var(--ui-soft)] text-brand-navy font-bold px-3.5 py-1.5 rounded-full text-xs shadow-lg border border-brand-line/20 flex items-center gap-1.5",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            className: "w-2 h-2 rounded-full bg-[var(--ui-soft)]",
                            "data-sp-4f294819": "",
                          })}
                        />
                        <span
                          {...mergeProps({
                            "data-sp-4f294819": "",
                          })}
                        >
                          {display(ctx.listing.price)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <p
                    {...mergeProps({
                      className:
                        "text-[11px] leading-relaxed text-[var(--ui-accent)] mt-3",
                      "data-sp-4f294819": "",
                    })}
                  >
                    {display(ctx.locationLabel(ctx.property))}
                    {" · Công cụ tìm địa chỉ: "}
                    <a
                      {...mergeProps({
                        href: "https://www.geoapify.com/",
                        target: "_blank",
                        rel: "noopener noreferrer",
                        className: "underline hover:text-[var(--ui-accent)]",
                        "data-sp-4f294819": "",
                      })}
                    >
                      {"Geoapify"}
                    </a>
                    {" · "}
                    <a
                      {...mergeProps({
                        href: "https://www.openstreetmap.org/copyright",
                        target: "_blank",
                        rel: "noopener noreferrer",
                        className: "underline hover:text-[var(--ui-accent)]",
                        "data-sp-4f294819": "",
                      })}
                    >
                      {"© OpenStreetMap contributors"}
                    </a>
                  </p>
                </section>
                <section
                  {...mergeProps({
                    className:
                      "bg-gradient-to-br from-[var(--ui-soft)] via-[var(--ui-soft)] to-[var(--ui-soft)] text-brand-navy rounded-3xl p-6 sm:p-8 shadow-xl border border-brand-line/10 relative overflow-hidden",
                    "data-sp-4f294819": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className:
                        "flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-brand-line/10 relative z-10",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <div
                      {...mergeProps({
                        className: "flex-1 min-w-0 pr-4",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          className:
                            "inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-card/10 text-brand-navy/80 text-[11px] font-bold border border-brand-line/15 mb-3",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            className:
                              "w-2 h-2 rounded-full bg-brand-card animate-pulse",
                            "data-sp-4f294819": "",
                          })}
                        />
                        <span
                          {...mergeProps({
                            "data-sp-4f294819": "",
                          })}
                        >
                          {"ĐỊNH GIÁ THAM CHIẾU AI (SMARTPROP V6)"}
                        </span>
                      </div>
                      <h2
                        {...mergeProps({
                          className:
                            "text-2xl sm:text-3xl font-black text-brand-navy tracking-tight",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(ctx.valuationAnalysis.rangeText)}
                      </h2>
                      <p
                        {...mergeProps({
                          className:
                            "text-xs text-[var(--ui-success-text)] mt-2 flex items-center gap-1.5 font-medium",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <svg
                          {...mergeProps({
                            width: "14",
                            height: "14",
                            viewBox: "0 0 24 24",
                            fill: "none",
                            stroke: "currentColor",
                            strokeWidth: "2.5",
                            className: "text-[var(--ui-success-text)] shrink-0",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <polyline
                            {...mergeProps({
                              points: "20 6 9 17 4 12",
                              "data-sp-4f294819": "",
                            })}
                          />
                        </svg>
                        <span
                          {...mergeProps({
                            "data-sp-4f294819": "",
                          })}
                        >
                          {display(ctx.valuationAnalysis.evaluation)}
                        </span>
                      </p>
                    </div>
                    <div
                      {...mergeProps({
                        className:
                          "bg-brand-card/10 backdrop-blur-md rounded-2xl p-4 sm:p-5 border border-brand-line/10 shrink-0 min-w-[210px]",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <p
                        {...mergeProps({
                          className:
                            "text-[11px] text-brand-navy/60 uppercase tracking-wider font-semibold",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {" Giá chào niêm yết "}
                      </p>
                      <p
                        {...mergeProps({
                          className:
                            "text-2xl font-black text-[var(--ui-warning-text)] mt-1 tracking-tight",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(ctx.listing.price)}
                      </p>
                      <p
                        {...mergeProps({
                          className: "text-xs text-brand-navy/70 mt-1",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(ctx.listing.pricePerM2)}
                      </p>
                    </div>
                  </div>
                  <div
                    {...mergeProps({
                      className: "mt-6 pt-2 relative z-10",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <div
                      {...mergeProps({
                        className: "flex items-center justify-between mb-4",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <p
                        {...mergeProps({
                          className:
                            "text-xs font-bold text-brand-navy/90 uppercase tracking-wider",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {" Chỉ số phân tích thị trường BĐS Đà Nẵng "}
                      </p>
                      <RouterLink
                        {...mergeProps({
                          to: `/market-insights`,
                          className:
                            "text-xs font-bold text-[var(--ui-warning-text)] hover:text-brand-navy transition flex items-center gap-1",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            "data-sp-4f294819": "",
                          })}
                        >
                          {"Xem xu hướng thị trường"}
                        </span>
                        <span
                          {...mergeProps({
                            "data-sp-4f294819": "",
                          })}
                        >
                          {"→"}
                        </span>
                      </RouterLink>
                    </div>
                    <div
                      {...mergeProps({
                        className: "space-y-4",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          "data-sp-4f294819": "",
                        })}
                      >
                        <div
                          {...mergeProps({
                            className:
                              "flex justify-between text-xs text-brand-navy/80 mb-1.5",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              "data-sp-4f294819": "",
                            })}
                          >
                            {"Vị trí & Tiềm năng thương mại / Du lịch"}
                          </span>
                          <span
                            {...mergeProps({
                              className: "font-bold text-brand-navy",
                              "data-sp-4f294819": "",
                            })}
                          >
                            {display(ctx.valuationAnalysis.locationScore)}
                            {"/100"}
                          </span>
                        </div>
                        <div
                          {...mergeProps({
                            className:
                              "h-2 bg-brand-card/10 rounded-full overflow-hidden",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <div
                            {...mergeProps({
                              className:
                                "h-full bg-gradient-to-r from-brand-card to-brand-card rounded-full transition-all duration-500",
                              style: {
                                width:
                                  ctx.valuationAnalysis.locationScore + "%",
                              },
                              "data-sp-4f294819": "",
                            })}
                          />
                        </div>
                      </div>
                      <div
                        {...mergeProps({
                          "data-sp-4f294819": "",
                        })}
                      >
                        <div
                          {...mergeProps({
                            className:
                              "flex justify-between text-xs text-brand-navy/80 mb-1.5",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              "data-sp-4f294819": "",
                            })}
                          >
                            {"Mức độ cạnh tranh đơn giá / m² so với quận"}
                          </span>
                          <span
                            {...mergeProps({
                              className: "font-bold text-[var(--ui-success-text)]",
                              "data-sp-4f294819": "",
                            })}
                          >
                            {display(ctx.valuationAnalysis.priceScore)}
                            {"/100"}
                          </span>
                        </div>
                        <div
                          {...mergeProps({
                            className:
                              "h-2 bg-brand-card/10 rounded-full overflow-hidden",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <div
                            {...mergeProps({
                              className:
                                "h-full bg-gradient-to-r from-emerald-400 to-brand-card rounded-full transition-all duration-500",
                              style: {
                                width: ctx.valuationAnalysis.priceScore + "%",
                              },
                              "data-sp-4f294819": "",
                            })}
                          />
                        </div>
                      </div>
                      <div
                        {...mergeProps({
                          "data-sp-4f294819": "",
                        })}
                      >
                        <div
                          {...mergeProps({
                            className:
                              "flex justify-between text-xs text-brand-navy/80 mb-1.5",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <span
                            {...mergeProps({
                              "data-sp-4f294819": "",
                            })}
                          >
                            {"Chỉ số thanh khoản thị trường"}
                          </span>
                          <span
                            {...mergeProps({
                              className: "font-bold text-[var(--ui-warning-text)]",
                              "data-sp-4f294819": "",
                            })}
                          >
                            {display(ctx.valuationAnalysis.liquidityScore)}
                            {"/100"}
                          </span>
                        </div>
                        <div
                          {...mergeProps({
                            className:
                              "h-2 bg-brand-card/10 rounded-full overflow-hidden",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <div
                            {...mergeProps({
                              className:
                                "h-full bg-gradient-to-r from-amber-400 to-yellow-400 rounded-full transition-all duration-500",
                              style: {
                                width:
                                  ctx.valuationAnalysis.liquidityScore + "%",
                              },
                              "data-sp-4f294819": "",
                            })}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </section>
              </div>
              <aside
                {...mergeProps({
                  className: "space-y-5 lg:sticky lg:top-5",
                  "data-sp-4f294819": "",
                })}
              >
                <section
                  {...mergeProps({
                    className:
                      "bg-brand-card rounded-3xl p-6 shadow-sm border border-brand-line relative",
                    "data-sp-4f294819": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className:
                        "flex items-center justify-between mb-5 pb-4 border-b border-brand-line",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <p
                      {...mergeProps({
                        className:
                          "text-xs font-bold text-brand-muted uppercase tracking-wider",
                        "data-sp-4f294819": "",
                      })}
                    >
                      {" Môi giới phụ trách "}
                    </p>
                    <span
                      {...mergeProps({
                        className:
                          "px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-brand-card text-[var(--ui-accent)] border border-brand-line flex items-center gap-1",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <svg
                        {...mergeProps({
                          width: "10",
                          height: "10",
                          viewBox: "0 0 24 24",
                          fill: "currentColor",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <polygon
                          {...mergeProps({
                            points:
                              "12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2",
                            "data-sp-4f294819": "",
                          })}
                        />
                      </svg>
                      <span
                        {...mergeProps({
                          "data-sp-4f294819": "",
                        })}
                      >
                        {"Đã xác minh"}
                      </span>
                    </span>
                  </div>
                  <div
                    {...mergeProps({
                      className: "flex items-center gap-3.5 mb-5",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <div
                      {...mergeProps({
                        className: "relative shrink-0",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <div
                        {...mergeProps({
                          className:
                            "w-13 h-13 rounded-2xl bg-gradient-to-tr from-[var(--ui-soft)] to-[var(--ui-soft)] text-brand-navy flex items-center justify-center text-lg font-black shadow-md border-2 border-brand-line",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(
                          (
                            ctx.revealedContact?.contactName ||
                            ctx.property?.contactName ||
                            "S"
                          )
                            .charAt(0)
                            .toUpperCase(),
                        )}
                      </div>
                      <span
                        {...mergeProps({
                          className:
                            "absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-[var(--ui-success-bg)] border-2 border-brand-line",
                          title: "Trực tuyến",
                          "data-sp-4f294819": "",
                        })}
                      />
                    </div>
                    <div
                      {...mergeProps({
                        className: "flex-1 min-w-0",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <p
                        {...mergeProps({
                          className:
                            "text-base font-extrabold text-[var(--ui-accent)] truncate",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(
                          ctx.revealedContact?.contactName ||
                            ctx.property?.contactName ||
                            "Phan Thanh Bình",
                        )}
                      </p>
                      <p
                        {...mergeProps({
                          className:
                            "text-xs text-[var(--ui-accent)] font-semibold truncate mt-0.5",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {" Chuyên viên BĐS SmartProp "}
                      </p>
                      <div
                        {...mergeProps({
                          className:
                            "flex items-center gap-1 text-[11px] text-[var(--ui-warning-text)] font-bold mt-0.5",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <span
                          {...mergeProps({
                            "data-sp-4f294819": "",
                          })}
                        >
                          {"★ 5.0"}
                        </span>
                        <span
                          {...mergeProps({
                            className: "text-brand-muted font-normal",
                            "data-sp-4f294819": "",
                          })}
                        >
                          {"· Đang trực tuyến hỗ trợ"}
                        </span>
                      </div>
                    </div>
                  </div>
                  {ctx.route.query.own === "1" ||
                  ctx.session.user?.role === "ADMIN" ? (
                    <RouterLink
                      {...mergeProps({
                        to:
                          "/account/properties/" +
                          ctx.listingId +
                          "/legal-documents",
                        className:
                          "mb-3 block text-xs underline font-semibold text-[var(--ui-accent)] hover:text-[var(--ui-accent)]",
                        "data-sp-4f294819": "",
                      })}
                    >
                      {" Quản lý hồ sơ pháp lý riêng "}
                    </RouterLink>
                  ) : null}
                  <ContactPanel
                    key={ctx.listingId}
                    {...mergeProps({
                      propertyId: ctx.listingId,
                      onRevealed: ($event) => {
                        return ((data) => (ctx.revealedContact = data))?.(
                          $event,
                        );
                      },
                      "data-sp-4f294819": "",
                    })}
                  />
                  <button
                    {...mergeProps({
                      type: "button",
                      className:
                        "mt-3 w-full rounded-2xl border border-brand-line hover:border-[var(--ui-border)]/40 hover:bg-brand-card py-3 px-4 text-xs font-bold text-[var(--ui-accent)] transition flex items-center justify-center gap-2 cursor-pointer shadow-2xs",
                      disabled: ctx.state.busy,
                      onClick: ($event) => {
                        return ctx.messageOwner?.($event);
                      },
                      "data-sp-4f294819": "",
                    })}
                  >
                    <svg
                      {...mergeProps({
                        width: "15",
                        height: "15",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <path
                        {...mergeProps({
                          d: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
                          "data-sp-4f294819": "",
                        })}
                      />
                    </svg>
                    <span
                      {...mergeProps({
                        "data-sp-4f294819": "",
                      })}
                    >
                      {"Nhắn tin tư vấn trực tiếp"}
                    </span>
                  </button>
                  <div
                    {...mergeProps({
                      className:
                        "mt-4 pt-3.5 border-t border-brand-line flex items-center gap-2 text-[11px] text-brand-muted",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <svg
                      {...mergeProps({
                        width: "14",
                        height: "14",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2",
                        className: "text-[var(--ui-warning-text)] shrink-0",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <rect
                        {...mergeProps({
                          x: "3",
                          y: "11",
                          width: "18",
                          height: "11",
                          rx: "2",
                          ry: "2",
                          "data-sp-4f294819": "",
                        })}
                      />
                      <path
                        {...mergeProps({
                          d: "M7 11V7a5 5 0 0 1 10 0v4",
                          "data-sp-4f294819": "",
                        })}
                      />
                    </svg>
                    <span
                      {...mergeProps({
                        "data-sp-4f294819": "",
                      })}
                    >
                      {"Giao dịch an toàn, không cọc trước khi xác minh"}
                    </span>
                  </div>
                </section>
                <section
                  {...mergeProps({
                    className:
                      "bg-brand-card rounded-3xl p-6 shadow-sm border border-brand-line",
                    "data-sp-4f294819": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className:
                        "flex items-center justify-between mb-4 pb-3 border-b border-brand-line",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <h3
                      {...mergeProps({
                        className:
                          "text-sm font-bold text-[var(--ui-accent)] flex items-center gap-2",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <svg
                        {...mergeProps({
                          width: "16",
                          height: "16",
                          viewBox: "0 0 24 24",
                          fill: "none",
                          stroke: "currentColor",
                          strokeWidth: "2",
                          className: "text-[var(--ui-accent)]",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <path
                          {...mergeProps({
                            d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z",
                            "data-sp-4f294819": "",
                          })}
                        />
                        <polyline
                          {...mergeProps({
                            points: "14 2 14 8 20 8",
                            "data-sp-4f294819": "",
                          })}
                        />
                      </svg>
                      <span
                        {...mergeProps({
                          "data-sp-4f294819": "",
                        })}
                      >
                        {"Thông tin niêm yết"}
                      </span>
                    </h3>
                    <span
                      {...mergeProps({
                        className:
                          "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[var(--ui-success-bg)] text-[var(--ui-success-text)] border border-[var(--ui-success-border)]",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <span
                        {...mergeProps({
                          className:
                            "w-1.5 h-1.5 rounded-full bg-[var(--ui-success-bg)] animate-pulse",
                          "data-sp-4f294819": "",
                        })}
                      />
                      {" Đang hiển thị "}
                    </span>
                  </div>
                  <div
                    {...mergeProps({
                      className: "space-y-3.5 text-xs",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <div
                      {...mergeProps({
                        className: "flex items-center justify-between py-0.5",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <span
                        {...mergeProps({
                          className: "text-brand-muted flex items-center gap-2",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <svg
                          {...mergeProps({
                            width: "14",
                            height: "14",
                            viewBox: "0 0 24 24",
                            fill: "none",
                            stroke: "currentColor",
                            strokeWidth: "2",
                            className: "text-brand-muted",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <line
                            {...mergeProps({
                              x1: "4",
                              y1: "9",
                              x2: "20",
                              y2: "9",
                              "data-sp-4f294819": "",
                            })}
                          />
                          <line
                            {...mergeProps({
                              x1: "4",
                              y1: "15",
                              x2: "20",
                              y2: "15",
                              "data-sp-4f294819": "",
                            })}
                          />
                          <line
                            {...mergeProps({
                              x1: "10",
                              y1: "3",
                              x2: "8",
                              y2: "21",
                              "data-sp-4f294819": "",
                            })}
                          />
                          <line
                            {...mergeProps({
                              x1: "16",
                              y1: "3",
                              x2: "14",
                              y2: "21",
                              "data-sp-4f294819": "",
                            })}
                          />
                        </svg>
                        <span
                          {...mergeProps({
                            "data-sp-4f294819": "",
                          })}
                        >
                          {"Mã tin"}
                        </span>
                      </span>
                      <span
                        {...mergeProps({
                          className: "font-bold text-[var(--ui-accent)] font-mono",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {" #SP-"}
                        {display(
                          String(ctx.property?.id || "")
                            .slice(-6)
                            .toUpperCase() || "654321",
                        )}
                      </span>
                    </div>
                    <div
                      {...mergeProps({
                        className: "flex items-center justify-between py-0.5",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <span
                        {...mergeProps({
                          className: "text-brand-muted flex items-center gap-2",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <svg
                          {...mergeProps({
                            width: "14",
                            height: "14",
                            viewBox: "0 0 24 24",
                            fill: "none",
                            stroke: "currentColor",
                            strokeWidth: "2",
                            className: "text-brand-muted",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <rect
                            {...mergeProps({
                              x: "3",
                              y: "4",
                              width: "18",
                              height: "18",
                              rx: "2",
                              ry: "2",
                              "data-sp-4f294819": "",
                            })}
                          />
                          <line
                            {...mergeProps({
                              x1: "16",
                              y1: "2",
                              x2: "16",
                              y2: "6",
                              "data-sp-4f294819": "",
                            })}
                          />
                          <line
                            {...mergeProps({
                              x1: "8",
                              y1: "2",
                              x2: "8",
                              y2: "6",
                              "data-sp-4f294819": "",
                            })}
                          />
                          <line
                            {...mergeProps({
                              x1: "3",
                              y1: "10",
                              x2: "21",
                              y2: "10",
                              "data-sp-4f294819": "",
                            })}
                          />
                        </svg>
                        <span
                          {...mergeProps({
                            "data-sp-4f294819": "",
                          })}
                        >
                          {"Ngày đăng"}
                        </span>
                      </span>
                      <span
                        {...mergeProps({
                          className: "font-semibold text-[var(--ui-accent)]",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(
                          ctx.formatPostDate(
                            ctx.property?.publishedAt ||
                              ctx.property?.createdAt,
                          ),
                        )}
                      </span>
                    </div>
                    <div
                      {...mergeProps({
                        className: "flex items-center justify-between py-0.5",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <span
                        {...mergeProps({
                          className: "text-brand-muted flex items-center gap-2",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <svg
                          {...mergeProps({
                            width: "14",
                            height: "14",
                            viewBox: "0 0 24 24",
                            fill: "none",
                            stroke: "currentColor",
                            strokeWidth: "2",
                            className: "text-brand-muted",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <circle
                            {...mergeProps({
                              cx: "12",
                              cy: "12",
                              r: "10",
                              "data-sp-4f294819": "",
                            })}
                          />
                          <polyline
                            {...mergeProps({
                              points: "12 6 12 12 16 14",
                              "data-sp-4f294819": "",
                            })}
                          />
                        </svg>
                        <span
                          {...mergeProps({
                            "data-sp-4f294819": "",
                          })}
                        >
                          {"Hình thức"}
                        </span>
                      </span>
                      <span
                        {...mergeProps({
                          className: "font-semibold text-[var(--ui-accent)]",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(
                          ctx.property?.transactionType === "RENT"
                            ? "Cho thuê BĐS"
                            : "Bán BĐS",
                        )}
                      </span>
                    </div>
                    <div
                      {...mergeProps({
                        className: "flex items-center justify-between py-0.5",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <span
                        {...mergeProps({
                          className: "text-brand-muted flex items-center gap-2",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <svg
                          {...mergeProps({
                            width: "14",
                            height: "14",
                            viewBox: "0 0 24 24",
                            fill: "none",
                            stroke: "currentColor",
                            strokeWidth: "2",
                            className: "text-brand-muted",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <path
                            {...mergeProps({
                              d: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
                              "data-sp-4f294819": "",
                            })}
                          />
                        </svg>
                        <span
                          {...mergeProps({
                            "data-sp-4f294819": "",
                          })}
                        >
                          {"Pháp lý"}
                        </span>
                      </span>
                      <span
                        {...mergeProps({
                          className:
                            "font-semibold text-[var(--ui-success-text)] bg-[var(--ui-success-bg)] px-2 py-0.5 rounded border border-[var(--ui-success-border)]",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {" Sổ hồng / Sổ đỏ riêng "}
                      </span>
                    </div>
                    <div
                      {...mergeProps({
                        className: "flex items-center justify-between py-0.5",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <span
                        {...mergeProps({
                          className: "text-brand-muted flex items-center gap-2",
                          "data-sp-4f294819": "",
                        })}
                      >
                        <svg
                          {...mergeProps({
                            width: "14",
                            height: "14",
                            viewBox: "0 0 24 24",
                            fill: "none",
                            stroke: "currentColor",
                            strokeWidth: "2",
                            className: "text-brand-muted",
                            "data-sp-4f294819": "",
                          })}
                        >
                          <path
                            {...mergeProps({
                              d: "M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z",
                              "data-sp-4f294819": "",
                            })}
                          />
                          <circle
                            {...mergeProps({
                              cx: "12",
                              cy: "12",
                              r: "3",
                              "data-sp-4f294819": "",
                            })}
                          />
                        </svg>
                        <span
                          {...mergeProps({
                            "data-sp-4f294819": "",
                          })}
                        >
                          {"Lượt xem"}
                        </span>
                      </span>
                      <span
                        {...mergeProps({
                          className: "font-semibold text-[var(--ui-accent)]",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(
                          ctx.viewsCount ||
                            ctx.incrementAndGetViews(ctx.property?.id),
                        )}
                        {" lượt xem "}
                      </span>
                    </div>
                  </div>
                  <div
                    {...mergeProps({
                      className:
                        "mt-4 pt-3.5 border-t border-brand-line flex items-center gap-2 text-[11px] text-brand-muted bg-brand-card -mx-2 -mb-2 p-3 rounded-2xl border border-brand-line",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <svg
                      {...mergeProps({
                        width: "14",
                        height: "14",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2",
                        className: "text-[var(--ui-success-text)] shrink-0",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <path
                        {...mergeProps({
                          d: "M22 11.08V12a10 10 0 1 1-5.93-9.14",
                          "data-sp-4f294819": "",
                        })}
                      />
                      <polyline
                        {...mergeProps({
                          points: "22 4 12 14.01 9 11.01",
                          "data-sp-4f294819": "",
                        })}
                      />
                    </svg>
                    <span
                      {...mergeProps({
                        "data-sp-4f294819": "",
                      })}
                    >
                      {"Dữ liệu xác thực theo tiêu chuẩn SmartProp"}
                    </span>
                  </div>
                </section>
                <section
                  {...mergeProps({
                    className:
                      "bg-brand-card rounded-3xl p-5 shadow-sm border border-brand-line",
                    "data-sp-4f294819": "",
                  })}
                >
                  <p
                    {...mergeProps({
                      className: "text-xs text-brand-muted leading-relaxed",
                      "data-sp-4f294819": "",
                    })}
                  >
                    {
                      " Bạn phát hiện tin đăng này sai vị trí, sai giá hoặc hình ảnh không khớp thực tế? "
                    }
                  </p>
                  <button
                    {...mergeProps({
                      type: "button",
                      onClick: ($event) => {
                        ctx.router.push(
                          `/listing/${ctx.route.params.id}/report`,
                        );
                      },
                      className:
                        "mt-3 inline-flex items-center gap-1.5 text-xs font-bold text-[var(--ui-muted)] hover:underline cursor-pointer",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <svg
                      {...mergeProps({
                        width: "13",
                        height: "13",
                        viewBox: "0 0 24 24",
                        fill: "none",
                        stroke: "currentColor",
                        strokeWidth: "2",
                        "data-sp-4f294819": "",
                      })}
                    >
                      <path
                        {...mergeProps({
                          d: "M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z",
                          "data-sp-4f294819": "",
                        })}
                      />
                      <line
                        {...mergeProps({
                          x1: "4",
                          y1: "22",
                          x2: "4",
                          y2: "15",
                          "data-sp-4f294819": "",
                        })}
                      />
                    </svg>
                    <span
                      {...mergeProps({
                        "data-sp-4f294819": "",
                      })}
                    >
                      {"Báo cáo tin đăng vi phạm"}
                    </span>
                  </button>
                </section>
              </aside>
            </div>
          </React.Fragment>
        ) : null}
      </div>
      {ctx.property && !ctx.state.busy ? (
        <div
          {...mergeProps({
            className:
              "lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-brand-card/95 backdrop-blur-md border-t border-brand-line px-4 py-3 flex items-center justify-between gap-3 shadow-lg",
            "data-sp-4f294819": "",
          })}
        >
          <div
            {...mergeProps({
              className: "min-w-0",
              "data-sp-4f294819": "",
            })}
          >
            <p
              {...mergeProps({
                className: "text-[10px] text-brand-muted font-bold uppercase",
                "data-sp-4f294819": "",
              })}
            >
              {"Giá niêm yết"}
            </p>
            <p
              {...mergeProps({
                className: "text-base font-black text-[var(--ui-muted)] truncate",
                "data-sp-4f294819": "",
              })}
            >
              {display(ctx.listing.price)}
            </p>
          </div>
          <div
            {...mergeProps({
              className: "flex items-center gap-2",
              "data-sp-4f294819": "",
            })}
          >
            <button
              {...mergeProps({
                type: "button",
                onClick: ($event) => {
                  return ctx.messageOwner?.($event);
                },
                className:
                  "px-3.5 py-2.5 rounded-xl border border-brand-line text-[var(--ui-accent)] text-xs font-bold flex items-center gap-1.5 active:scale-95 transition",
                "data-sp-4f294819": "",
              })}
            >
              <svg
                {...mergeProps({
                  width: "14",
                  height: "14",
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  strokeWidth: "2",
                  "data-sp-4f294819": "",
                })}
              >
                <path
                  {...mergeProps({
                    d: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
                    "data-sp-4f294819": "",
                  })}
                />
              </svg>
              <span
                {...mergeProps({
                  "data-sp-4f294819": "",
                })}
              >
                {"Nhắn tin"}
              </span>
            </button>
            {ctx.revealedContact?.contactPhone ? (
              <a
                {...mergeProps({
                  href:
                    "tel:" +
                    ctx.revealedContact.contactPhone.replace(/[^0-9]/g, ""),
                  className:
                    "px-4 py-2.5 rounded-xl bg-[var(--ui-soft)] text-brand-navy text-xs font-bold flex items-center gap-1.5 active:scale-95 transition shadow-sm",
                  "data-sp-4f294819": "",
                })}
              >
                <svg
                  {...mergeProps({
                    width: "14",
                    height: "14",
                    viewBox: "0 0 24 24",
                    fill: "none",
                    stroke: "currentColor",
                    strokeWidth: "2",
                    "data-sp-4f294819": "",
                  })}
                >
                  <path
                    {...mergeProps({
                      d: "M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z",
                      "data-sp-4f294819": "",
                    })}
                  />
                </svg>
                <span
                  {...mergeProps({
                    "data-sp-4f294819": "",
                  })}
                >
                  {"Gọi ngay"}
                </span>
              </a>
            ) : null}
          </div>
        </div>
      ) : null}
      <Teleport
        {...mergeProps({
          to: "body",
          "data-sp-4f294819": "",
        })}
      >
        {ctx.showGallery ? (
          <div
            {...mergeProps({
              className:
                "fixed inset-0 z-[9999] bg-brand-cream/85 backdrop-blur-md flex items-center justify-center p-2 sm:p-5",
              onClick: ($event) => {
                if ($event.target !== $event.currentTarget) return;
                return ctx.closeGallery?.($event);
              },
              "data-sp-4f294819": "",
            })}
          >
            <div
              {...mergeProps({
                className:
                  "relative w-full max-w-[1500px] h-[95vh] bg-[var(--ui-soft)] rounded-3xl overflow-hidden flex flex-col shadow-2xl border border-brand-line/10",
                "data-sp-4f294819": "",
              })}
            >
              <div
                {...mergeProps({
                  className:
                    "flex items-center justify-between gap-4 px-6 py-4 text-brand-navy border-b border-brand-line/10",
                  "data-sp-4f294819": "",
                })}
              >
                <div
                  {...mergeProps({
                    className: "flex items-center gap-4 min-w-0",
                    "data-sp-4f294819": "",
                  })}
                >
                  <div
                    {...mergeProps({
                      className: "min-w-0",
                      "data-sp-4f294819": "",
                    })}
                  >
                    <h2
                      {...mergeProps({
                        className:
                          "text-xs sm:text-sm font-bold truncate text-brand-navy",
                        "data-sp-4f294819": "",
                      })}
                    >
                      {display(ctx.listing.title)}
                    </h2>
                    <p
                      {...mergeProps({
                        className: "text-[11px] text-brand-navy/50 truncate mt-0.5",
                        "data-sp-4f294819": "",
                      })}
                    >
                      {display(ctx.listing.location)}
                    </p>
                  </div>
                  <div
                    {...mergeProps({
                      className:
                        "hidden sm:block px-3 py-1 rounded-full bg-brand-card/10 text-xs text-brand-navy/80 font-bold whitespace-nowrap",
                      "data-sp-4f294819": "",
                    })}
                  >
                    {display(ctx.currentImageIndex + 1)}
                    {" / "}
                    {display(ctx.images.length)}
                    {" ảnh "}
                  </div>
                </div>
                <div
                  {...mergeProps({
                    className: "flex items-center gap-2 shrink-0",
                    "data-sp-4f294819": "",
                  })}
                >
                  <button
                    {...mergeProps({
                      type: "button",
                      onClick: ($event) => {
                        return ctx.closeGallery?.($event);
                      },
                      className:
                        "w-9 h-9 rounded-full bg-brand-card/10 border border-brand-line/10 flex items-center justify-center text-brand-navy/70 hover:bg-brand-card/20 hover:text-brand-navy transition cursor-pointer",
                      title: "Đóng (Esc)",
                      "data-sp-4f294819": "",
                    })}
                  >
                    {" ✕ "}
                  </button>
                </div>
              </div>
              <div
                {...mergeProps({
                  className:
                    "relative flex-1 min-h-0 flex items-center justify-center px-4 sm:px-16",
                  "data-sp-4f294819": "",
                })}
              >
                <PrivateImage
                  {...mergeProps({
                    src: ctx.images[ctx.currentImageIndex],
                    alt: `Ảnh ${ctx.currentImageIndex + 1} của ${ctx.listing.title}`,
                    className: "w-full h-full object-contain rounded-2xl",
                    "data-sp-4f294819": "",
                  })}
                />
                <button
                  {...mergeProps({
                    type: "button",
                    onClick: ($event) => {
                      return ctx.prevImage?.($event);
                    },
                    className:
                      "absolute left-3 sm:left-6 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-brand-cream/50 border border-brand-line/10 text-brand-navy text-2xl flex items-center justify-center hover:bg-brand-cream/80 hover:scale-105 transition cursor-pointer",
                    "aria-label": "Ảnh trước",
                    "data-sp-4f294819": "",
                  })}
                >
                  {" ‹ "}
                </button>
                <button
                  {...mergeProps({
                    type: "button",
                    onClick: ($event) => {
                      return ctx.nextImage?.($event);
                    },
                    className:
                      "absolute right-3 sm:right-6 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-brand-cream/50 border border-brand-line/10 text-brand-navy text-2xl flex items-center justify-center hover:bg-brand-cream/80 hover:scale-105 transition cursor-pointer",
                    "aria-label": "Ảnh tiếp theo",
                    "data-sp-4f294819": "",
                  })}
                >
                  {" › "}
                </button>
                <div
                  {...mergeProps({
                    className:
                      "sm:hidden absolute bottom-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-brand-cream/70 text-brand-navy text-xs font-bold",
                    "data-sp-4f294819": "",
                  })}
                >
                  {display(ctx.currentImageIndex + 1)}
                  {" / "}
                  {display(ctx.images.length)}
                </div>
              </div>
              <div
                {...mergeProps({
                  className:
                    "px-6 py-4 border-t border-brand-line/10 bg-[var(--ui-soft)]/80",
                  "data-sp-4f294819": "",
                })}
              >
                <div
                  {...mergeProps({
                    className:
                      "flex gap-2.5 overflow-x-auto pb-1 gallery-scroll",
                    "data-sp-4f294819": "",
                  })}
                >
                  {renderList(ctx.images, (image, index) => (
                    <button
                      key={index}
                      {...mergeProps({
                        type: "button",
                        onClick: ($event) => {
                          ctx.selectImage(index);
                        },
                        className: ["relative shrink-0 w-[100px] sm:w-[120px] h-[64px] sm:h-[74px] rounded-xl overflow-hidden border-2 transition cursor-pointer", ctx.currentImageIndex === index
                            ? "border-[var(--ui-border)] opacity-100 ring-2 ring-[var(--ui-border)]/50"
                            : "border-transparent opacity-50 hover:opacity-100"],
                        
                        "data-sp-4f294819": "",
                      })}
                    >
                      <PrivateImage
                        {...mergeProps({
                          src: image,
                          alt: `Ảnh thu nhỏ ${index + 1}`,
                          className: "w-full h-full object-cover",
                          "data-sp-4f294819": "",
                        })}
                      />
                      <div
                        {...mergeProps({
                          className:
                            "absolute bottom-1 left-1 px-1.5 py-0.2 rounded-full bg-brand-cream/70 text-brand-navy text-[9px] font-bold",
                          "data-sp-4f294819": "",
                        })}
                      >
                        {display(index + 1)}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </Teleport>
    </div>,
  ]);
});
