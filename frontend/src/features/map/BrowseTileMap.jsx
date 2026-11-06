import React from "react";
import { useSetup, propsForSetup, emitForProps, exposeForSetup } from "../../shared/state/store.js";
import { mergeProps, bindRef, renderList, display, modelProps, rootProps, Teleport } from "../../shared/components/rendering.js";
import { RouterLink, RouterView } from "../../shared/routing/router.jsx";
import { computed, ref, watch, onMounted, onBeforeUnmount } from "../../shared/state/store.js";
import { projectPoint, unprojectPoint, visibleTiles } from "./postMap.js";
import { compactPrice } from "../property/property.js";
import { poiSymbol, poiLabel, poiColor, poiColorBg, poiColorBorder } from "./nearbyPlaces.js";
import { googlePointUrl } from "./googleMapsLocation.js";
import PoiIcon from "../../shared/components/PoiIcon.jsx";
import "./BrowseTileMap.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    points: {
      type: Array,
      default: () => []
    },
    selectedId: String,
    poiItems: {
      type: Array,
      default: () => []
    },
    selectedPoiId: String,
    boundary: {
      type: Object,
      default: null
    },
    mapLabel: {
      type: String,
      default: "Bản đồ tin công khai: kéo để di chuyển, phím mũi tên để dịch chuyển, cộng trừ để thu phóng"
    }
  });
  const emit = emitForProps(__props, ["select", "select-poi"]);
  const host = ref(null),
    width = ref(600),
    height = ref(440),
    zoom = ref(12);
  // Da Nang is a viewport only; every marker below comes from a public property DTO.
  const center = ref({
      latitude: 16.0544,
      longitude: 108.2022
    }),
    failed = ref(false),
    attempt = ref(0);
  let observer = null;
  const template = import.meta.env?.VITE_OSM_TILE_URL || "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  // Viewport tiles only; retain browser caching, Referer and visible attribution.
  // https://operations.osmfoundation.org/policies/tiles/ (reviewed 2026-10-26)
  const validTemplate = template.startsWith("https://") && ["{z}", "{x}", "{y}"].every(value => template.includes(value));
  const tiles = computed(() => visibleTiles(center.value, zoom.value, width.value, height.value));
  const boundaryRings = computed(() => {
    const g = props.boundary;
    return g?.type === "Polygon" ? g.coordinates : g?.type === "MultiPolygon" ? g.coordinates.flat() : [];
  });
  const boundaryPath = computed(() => {
    const c = projectPoint(center.value.latitude, center.value.longitude, zoom.value);
    return boundaryRings.value.map(ring => ring.map(([lon, lat], i) => {
      const p = projectPoint(lat, lon, zoom.value);
      return `${i ? "L" : "M"}${p.x - c.x + width.value / 2},${p.y - c.y + height.value / 2}`;
    }).join(" ") + "Z").join(" ");
  });
  function tileUrl(tile) {
    return validTemplate ? template.replace("{z}", tile.z).replace("{x}", tile.x).replace("{y}", tile.y) : "";
  }
  function markersFor(points) {
    const c = projectPoint(center.value.latitude, center.value.longitude, zoom.value),
      world = 256 * 2 ** zoom.value;
    return points.map(point => {
      const p = projectPoint(point.latitude, point.longitude, zoom.value);
      let dx = p.x - c.x;
      if (dx > world / 2) dx -= world;
      if (dx < -world / 2) dx += world;
      return {
        ...point,
        left: dx + width.value / 2,
        top: p.y - c.y + height.value / 2
      };
    }).filter(point => point.left > -80 && point.left < width.value + 80 && point.top > -30 && point.top < height.value + 30);
  }
  const markers = computed(() => markersFor(props.points));
  const poiMarkers = computed(() => markersFor(props.poiItems));
  const selectedPoiMarker = computed(() => poiMarkers.value.find(p => p.id === props.selectedPoiId) || null);
  const isPopupFlipped = computed(() => selectedPoiMarker.value && selectedPoiMarker.value.top < 135);
  function formatDistance(meters) {
    if (typeof meters !== "number" || !Number.isFinite(meters) || meters < 0) return "";
    if (meters < 1000) return `${Math.round(meters)} m`;
    return `${(meters / 1000).toFixed(1).replace(".", ",")} km`;
  }
  function fit() {
    const points = [...props.points, ...props.poiItems, ...boundaryRings.value.flat().map(([longitude, latitude]) => ({
      latitude,
      longitude
    }))];
    if (!points.length) return;
    const lats = points.map(point => point.latitude),
      lons = points.map(point => point.longitude);
    const minLat = Math.min(...lats),
      maxLat = Math.max(...lats),
      minLon = Math.min(...lons),
      maxLon = Math.max(...lons);
    center.value = {
      latitude: (minLat + maxLat) / 2,
      longitude: (minLon + maxLon) / 2
    };
    let target = 16;
    while (target > 3) {
      const p1 = projectPoint(maxLat, minLon, target),
        p2 = projectPoint(minLat, maxLon, target);
      if (Math.abs(p2.x - p1.x) <= Math.max(120, width.value - 60) && Math.abs(p2.y - p1.y) <= Math.max(120, height.value - 60)) break;
      target--;
    }
    zoom.value = Math.max(3, Math.min(18, target));
  }
  function focus() {
    const target = props.selectedPoiId ? props.poiItems.find(p => p.id === props.selectedPoiId) : props.points.find(p => p.id === props.selectedId);
    if (target) center.value = {
      latitude: target.latitude,
      longitude: target.longitude
    };
  }
  function pan(dx, dy) {
    const c = projectPoint(center.value.latitude, center.value.longitude, zoom.value);
    center.value = unprojectPoint(c.x + dx, c.y + dy, zoom.value);
  }
  function changeZoom(delta) {
    const next = Math.max(3, Math.min(19, zoom.value + delta));
    if (next !== zoom.value) zoom.value = next;
  }
  let drag = null;
  function pointerDown(event) {
    if (event.target.closest("[data-map-control]")) return;
    drag = {
      x: event.clientX,
      y: event.clientY,
      center: {
        ...center.value
      }
    };
    host.value?.setPointerCapture(event.pointerId);
  }
  function pointerMove(event) {
    if (!drag) return;
    const p = projectPoint(drag.center.latitude, drag.center.longitude, zoom.value);
    center.value = unprojectPoint(p.x - event.clientX + drag.x, p.y - event.clientY + drag.y, zoom.value);
  }
  function pointerUp(event) {
    drag = null;
    if (host.value.hasPointerCapture(event.pointerId)) host.value.releasePointerCapture(event.pointerId);
  }
  function keyboard(event) {
    if (event.key === "Escape" && props.selectedPoiId) {
      emit("select-poi", null);
      return;
    }
    if (event.target !== host.value) return;
    const moves = {
      ArrowLeft: [-80, 0],
      ArrowRight: [80, 0],
      ArrowUp: [0, -80],
      ArrowDown: [0, 80]
    };
    if (moves[event.key]) {
      event.preventDefault();
      pan(...moves[event.key]);
    } else if (["+", "=", "-"].includes(event.key)) {
      event.preventDefault();
      changeZoom(event.key === "-" ? -1 : 1);
    }
  }
  watch(() => props.points.map(p => `${p.id}:${p.latitude}:${p.longitude}`).join("|"), () => {
    fit();
    focus();
  });
  watch(() => props.poiItems.map(p => `${p.id}:${p.latitude}:${p.longitude}`).join("|"), () => {
    fit();
    focus();
  });
  watch(() => props.selectedId, focus);
  watch(() => props.selectedPoiId, focus);
  watch(() => props.boundary, fit);
  onMounted(() => {
    observer = new ResizeObserver(entries => {
      const box = entries[0].contentRect;
      width.value = box.width;
      height.value = box.height;
      fit();
      focus();
    });
    observer.observe(host.value);
    width.value = host.value.clientWidth;
    height.value = host.value.clientHeight;
    fit();
    focus();
  });
  onBeforeUnmount(() => observer?.disconnect());
  return {
    computed,
    ref,
    watch,
    onMounted,
    onBeforeUnmount,
    projectPoint,
    unprojectPoint,
    visibleTiles,
    compactPrice,
    poiSymbol,
    poiLabel,
    poiColor,
    poiColorBg,
    poiColorBorder,
    googlePointUrl,
    PoiIcon,
    props,
    emit,
    host,
    width,
    height,
    zoom,
    center,
    failed,
    attempt,
    observer,
    template,
    validTemplate,
    tiles,
    boundaryRings,
    boundaryPath,
    tileUrl,
    markersFor,
    markers,
    poiMarkers,
    selectedPoiMarker,
    isPopupFlipped,
    formatDistance,
    fit,
    focus,
    pan,
    changeZoom,
    drag,
    pointerDown,
    pointerMove,
    pointerUp,
    keyboard
  };
}
export default React.forwardRef(function BrowseTileMap(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [<div {...mergeProps({
    ref: bindRef(ctx, "host"),
    className: "browse-map",
    role: "region",
    tabIndex: "0",
    "aria-label": ctx.mapLabel,
    onPointerDown: $event => {
      return ctx.pointerDown?.($event);
    },
    onPointerMove: $event => {
      return ctx.pointerMove?.($event);
    },
    onPointerUp: $event => {
      return ctx.pointerUp?.($event);
    },
    onPointerCancel: $event => {
      ctx.drag = null;
    },
    onKeyDown: $event => {
      return ctx.keyboard?.($event);
    },
    "data-sp-434e5650": ""
  })}>
      {renderList(ctx.tiles, tile => <img key={ctx.attempt + ":" + tile.key} {...mergeProps({
      src: ctx.tileUrl(tile),
      alt: "",
      draggable: "false",
      referrerPolicy: "strict-origin-when-cross-origin",
      className: "map-tile",
      style: {
        left: tile.left + "px",
        top: tile.top + "px"
      },
      onError: $event => {
        ctx.failed = true;
      },
      "data-sp-434e5650": ""
    })} />)}
      {ctx.boundaryPath ? <svg {...mergeProps({
      className: "boundary-overlay",
      viewBox: `0 0 ${ctx.width} ${ctx.height}`,
      "aria-hidden": "true",
      "data-map-boundary": "",
      "data-sp-434e5650": ""
    })}>
          <path {...mergeProps({
        d: ctx.boundaryPath,
        fill: "#365a9220",
        stroke: "#365a92",
        strokeWidth: "2",
        fillRule: "evenodd",
        "data-sp-434e5650": ""
      })} />
        </svg> : null}
      {renderList(ctx.markers, point => <button key={point.id} {...mergeProps({
      type: "button",
      "data-map-control": "",
      className: ["price-pin", {
        selected: ctx.selectedId === point.id,
        rent: point.transactionType === "RENT"
      }],
      
      style: {
        left: point.left + "px",
        top: point.top + "px"
      },
      "aria-label": point.title + " · " + ctx.compactPrice(point),
      "aria-pressed": ctx.selectedId === point.id,
      "data-property-id": point.id,
      onClick: $event => {
        ctx.emit("select", point.id);
      },
      "data-sp-434e5650": ""
    })}>
          {display(ctx.compactPrice(point))}
        </button>)}
      {renderList(ctx.poiMarkers, point => <button key={"poi:" + point.id} {...mergeProps({
      type: "button",
      "data-map-control": "",
      className: ["poi-pin", {
        selected: ctx.selectedPoiId === point.id
      }],
      
      style: {
        left: point.left + "px",
        top: point.top + "px",
        backgroundColor: ctx.poiColor(point.category)
      },
      "aria-label": point.name + " · " + (point.categoryLabel || ctx.poiLabel(point.category)),
      title: point.name + " (" + (point.categoryLabel || ctx.poiLabel(point.category)) + ")",
      "aria-pressed": ctx.selectedPoiId === point.id,
      "data-poi-id": point.id,
      onClick: $event => {
        ctx.emit("select-poi", ctx.selectedPoiId === point.id ? null : point.id);
      },
      "data-sp-434e5650": ""
    })}>
          <PoiIcon {...mergeProps({
        category: point.category,
        className: "size-3.5 text-brand-navy",
        "data-sp-434e5650": ""
      })} />
        </button>)}
      {ctx.selectedPoiMarker ? <div {...mergeProps({
      "data-map-control": "",
      className: ["poi-map-popup", {
        flipped: ctx.isPopupFlipped
      }],
      
      style: {
        left: ctx.selectedPoiMarker.left + "px",
        top: ctx.selectedPoiMarker.top + "px"
      },
      onPointerDown: $event => {
        $event.stopPropagation();
        undefined;
      },
      "data-sp-434e5650": ""
    })}>
          <div {...mergeProps({
        className: "poi-popup-card",
        "data-sp-434e5650": ""
      })}>
            <div {...mergeProps({
          className: "poi-popup-header",
          "data-sp-434e5650": ""
        })}>
              <span {...mergeProps({
            className: "poi-popup-badge",
            style: {
              backgroundColor: ctx.poiColorBg(ctx.selectedPoiMarker.category),
              color: ctx.poiColor(ctx.selectedPoiMarker.category),
              borderColor: ctx.poiColorBorder(ctx.selectedPoiMarker.category)
            },
            "data-sp-434e5650": ""
          })}>
                <PoiIcon {...mergeProps({
              category: ctx.selectedPoiMarker.category,
              className: "size-3",
              "data-sp-434e5650": ""
            })} />
                <span {...mergeProps({
              "data-sp-434e5650": ""
            })}>
                  {display(ctx.selectedPoiMarker.categoryLabel || ctx.poiLabel(ctx.selectedPoiMarker.category))}
                </span>
              </span>
              <button {...mergeProps({
            type: "button",
            className: "poi-popup-close",
            "aria-label": "Đóng bảng tiện ích",
            title: "Đóng",
            onClick: $event => {
              $event.stopPropagation();
              ctx.emit("select-poi", null);
            },
            "data-sp-434e5650": ""
          })}>
                {"✕"}
              </button>
            </div>
            <div {...mergeProps({
          className: "poi-popup-title",
          "data-sp-434e5650": ""
        })}>
              {display(ctx.selectedPoiMarker.name)}
            </div>
            {ctx.selectedPoiMarker.address ? <p {...mergeProps({
          className: "poi-popup-source",
          "data-sp-434e5650": ""
        })}>
                {display(ctx.selectedPoiMarker.address)}
              </p> : null}
            {ctx.selectedPoiMarker.sourceName === "openstreetmap_overpass" && /^https:\/\/www\.openstreetmap\.org\/(node|way|relation)\/[1-9][0-9]*$/.test(ctx.selectedPoiMarker.sourceUrl) ? <a {...mergeProps({
          href: ctx.selectedPoiMarker.sourceUrl,
          target: "_blank",
          rel: "noopener noreferrer",
          className: "poi-popup-source",
          "data-sp-434e5650": ""
        })}>
                {"Nguồn: OpenStreetMap ↗"}
              </a> : null}
            <div {...mergeProps({
          className: "poi-popup-meta",
          "data-sp-434e5650": ""
        })}>
              {ctx.selectedPoiMarker.distanceMeters ? <span {...mergeProps({
            className: "poi-popup-dist",
            "data-sp-434e5650": ""
          })}>
                  <svg {...mergeProps({
              className: "size-3.5 text-[var(--ui-success-text)] inline mr-1 shrink-0",
              viewBox: "0 0 24 24",
              fill: "none",
              stroke: "currentColor",
              strokeWidth: "2.5",
              "data-sp-434e5650": ""
            })}>
                    <path {...mergeProps({
                strokeLinecap: "round",
                strokeLinejoin: "round",
                d: "M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z",
                "data-sp-434e5650": ""
              })} />
                    <path {...mergeProps({
                strokeLinecap: "round",
                strokeLinejoin: "round",
                d: "M15 11a3 3 0 11-6 0 3 3 0 016 0z",
                "data-sp-434e5650": ""
              })} />
                  </svg>
                  {" Cách BĐS ~"}
                  {display(ctx.formatDistance(ctx.selectedPoiMarker.distanceMeters))}
                </span> : null}
              {ctx.googlePointUrl(ctx.selectedPoiMarker.latitude, ctx.selectedPoiMarker.longitude) ? <a {...mergeProps({
            href: ctx.googlePointUrl(ctx.selectedPoiMarker.latitude, ctx.selectedPoiMarker.longitude),
            target: "_blank",
            rel: "noopener noreferrer",
            className: "poi-popup-link",
            "data-sp-434e5650": ""
          })}>
                  {"Chỉ đường ↗"}
                </a> : null}
            </div>
          </div>
          <div {...mergeProps({
        className: "poi-popup-arrow",
        "data-sp-434e5650": ""
      })} />
        </div> : null}
      <div {...mergeProps({
      "data-map-control": "",
      className: "map-controls",
      "data-sp-434e5650": ""
    })}>
        <button {...mergeProps({
        type: "button",
        "aria-label": "Phóng to bản đồ",
        disabled: ctx.zoom >= 19,
        onClick: $event => {
          ctx.changeZoom(1);
        },
        "data-sp-434e5650": ""
      })}>
          {"+"}
        </button>
        <button {...mergeProps({
        type: "button",
        "aria-label": "Thu nhỏ bản đồ",
        disabled: ctx.zoom <= 3,
        onClick: $event => {
          ctx.changeZoom(-1);
        },
        "data-sp-434e5650": ""
      })}>
          {"−"}
        </button>
        <button {...mergeProps({
        type: "button",
        className: "fit",
        "aria-label": "Xem tất cả ghim của trang hiện tại",
        onClick: $event => {
          return ctx.fit?.($event);
        },
        "data-sp-434e5650": ""
      })}>
          {"⛶"}
        </button>
      </div>
      {ctx.failed || !ctx.validTemplate ? <p {...mergeProps({
      "data-map-control": "",
      className: "tile-error",
      role: "status",
      "data-sp-434e5650": ""
    })}>
          {"Chưa tải đầy đủ nền bản đồ. "}
          <button {...mergeProps({
        type: "button",
        onClick: $event => {
          ctx.failed = false;
          ctx.attempt++;
        },
        "data-sp-434e5650": ""
      })}>
            {"Thử lại"}
          </button>
        </p> : null}
      <a {...mergeProps({
      "data-map-control": "",
      href: "https://www.openstreetmap.org/copyright",
      target: "_blank",
      rel: "noopener noreferrer",
      className: "map-attribution",
      "data-sp-434e5650": ""
    })}>
        {"© OpenStreetMap contributors"}
      </a>
    </div>]);
});
