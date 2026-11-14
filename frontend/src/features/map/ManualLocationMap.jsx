import React from "react";
import { useSetup, propsForSetup, emitForProps, exposeForSetup } from "../../shared/state/store.js";
import { mergeProps, bindRef, renderList, display, modelProps, rootProps, Teleport } from "../../shared/components/rendering.js";
import { RouterLink, RouterView } from "../../shared/routing/router.jsx";
import { ref, computed, onMounted, onBeforeUnmount, watch } from "../../shared/state/store.js";
import { validCoordinates } from "../property/postForm.js";
import { projectPoint, unprojectPoint, visibleTiles } from "./postMap.js";
import { projectPreviewRegion } from "./locationPreview.js";
import "./ManualLocationMap.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    latitude: {
      default: ""
    },
    longitude: {
      default: ""
    },
    disabled: Boolean,
    preview: Boolean,
    precision: String,
    previewRegion: Object
  });
  const emit = emitForProps(__props, ["select"]);
  // This initial center is only a viewport. No point is selected until a deliberate action.
  const center = ref(validCoordinates(props.latitude, props.longitude) ? {
    latitude: Number(props.latitude),
    longitude: Number(props.longitude)
  } : {
    latitude: 16.0544,
    longitude: 108.2022
  });
  const previewZoom = () => props.preview ? props.precision === "APPROXIMATE_AREA" ? 13 : props.precision === "APPROXIMATE_STREET" ? 15 : 17 : 17;
  const zoom = ref(validCoordinates(props.latitude, props.longitude) ? previewZoom() : 13),
    host = ref(null),
    width = ref(600),
    failed = ref(false),
    attempt = ref(0),
    hint = ref(""),
    draggingPin = ref(null);
  const height = 320,
    tiles = computed(() => visibleTiles(center.value, zoom.value, width.value, height));
  const areaOverlay = computed(() => props.preview ? projectPreviewRegion(props.previewRegion, center.value, zoom.value, width.value, height) : null);
  const template = import.meta.env?.VITE_OSM_TILE_URL || "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  const validTemplate = template.startsWith("https://") && ["{z}", "{x}", "{y}"].every(v => template.includes(v));
  function tileUrl(tile) {
    return validTemplate ? template.replace("{z}", tile.z).replace("{x}", tile.x).replace("{y}", tile.y) : "";
  }
  const marker = computed(() => {
    const point = draggingPin.value || {
      latitude: props.latitude,
      longitude: props.longitude
    };
    if (!validCoordinates(point.latitude, point.longitude)) return null;
    const p = projectPoint(Number(point.latitude), Number(point.longitude), zoom.value),
      c = projectPoint(center.value.latitude, center.value.longitude, zoom.value);
    return {
      left: p.x - c.x + width.value / 2,
      top: p.y - c.y + height / 2
    };
  });
  watch(() => [props.latitude, props.longitude, props.preview, props.precision], () => {
    if (validCoordinates(props.latitude, props.longitude)) {
      center.value = {
        latitude: Number(props.latitude),
        longitude: Number(props.longitude)
      };
      zoom.value = previewZoom();
    }
  });
  let observer, drag;
  function pan(dx, dy) {
    const c = projectPoint(center.value.latitude, center.value.longitude, zoom.value);
    center.value = unprojectPoint(c.x + dx, c.y + dy, zoom.value);
  }
  function changeZoom(delta) {
    if (!props.disabled) zoom.value = Math.max(3, Math.min(19, zoom.value + delta));
  }
  function selectAt(x, y) {
    if (props.disabled) return;
    const c = projectPoint(center.value.latitude, center.value.longitude, zoom.value),
      wx = c.x + x - width.value / 2,
      wy = c.y + y - height / 2,
      n = 2 ** zoom.value,
      tx = (Math.floor(wx / 256) % n + n) % n,
      ty = Math.floor(wy / 256),
      key = zoom.value + "/" + tx + "/" + ty;
    const tile = [...(host.value?.querySelectorAll("[data-tile-key]") || [])].find(image => image.dataset.tileKey === key);
    if (!tile?.complete || !tile.naturalWidth) {
      hint.value = "Phần bản đồ này chưa tải được. Hãy kiểm tra kết nối và thử lại trước khi chọn ghim.";
      return;
    }
    const point = unprojectPoint(wx, wy, zoom.value);
    if (!validCoordinates(point.latitude, point.longitude)) return;
    hint.value = "Đã đặt ghim. Kiểm tra địa chỉ rồi bấm Xác nhận vị trí.";
    emit("select", point);
  }
  function pointerDown(event) {
    if (props.disabled || event.button !== 0 || event.target.closest("[data-map-control]")) return;
    const box = host.value.getBoundingClientRect();
    drag = {
      x: event.clientX,
      y: event.clientY,
      box,
      center: {
        ...center.value
      },
      pin: !!event.target.closest("[data-location-pin]")
    };
    host.value.setPointerCapture(event.pointerId);
  }
  function pointerMove(event) {
    if (!drag) return;
    const p = projectPoint(drag.center.latitude, drag.center.longitude, zoom.value);
    if (drag.pin) {
      draggingPin.value = unprojectPoint(p.x + event.clientX - drag.box.left - width.value / 2, p.y + event.clientY - drag.box.top - height / 2, zoom.value);
      return;
    }
    center.value = unprojectPoint(p.x - (event.clientX - drag.x), p.y - (event.clientY - drag.y), zoom.value);
  }
  function pointerUp(event) {
    if (!drag) return;
    const start = drag;
    drag = null;
    draggingPin.value = null;
    if (start.pin || Math.hypot(event.clientX - start.x, event.clientY - start.y) < 5) selectAt(event.clientX - start.box.left, event.clientY - start.box.top);
    try {
      host.value.releasePointerCapture(event.pointerId);
    } catch {}
  }
  function cancelDrag() {
    drag = null;
    draggingPin.value = null;
  }
  function keyboard(event) {
    if (props.disabled) return;
    const moves = {
      ArrowLeft: [-64, 0],
      ArrowRight: [64, 0],
      ArrowUp: [0, -64],
      ArrowDown: [0, 64]
    };
    if (moves[event.key]) {
      event.preventDefault();
      pan(...moves[event.key]);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectAt(width.value / 2, height / 2);
    } else if (event.key === "+" || event.key === "=") {
      event.preventDefault();
      changeZoom(1);
    } else if (event.key === "-") {
      event.preventDefault();
      changeZoom(-1);
    }
  }
  function retry() {
    failed.value = false;
    hint.value = "";
    attempt.value++;
  }
  onMounted(() => {
    observer = new ResizeObserver(entries => width.value = Math.max(1, entries[0].contentRect.width));
    observer.observe(host.value);
  });
  onBeforeUnmount(() => observer?.disconnect());
  return {
    ref,
    computed,
    onMounted,
    onBeforeUnmount,
    watch,
    validCoordinates,
    projectPoint,
    unprojectPoint,
    visibleTiles,
    projectPreviewRegion,
    props,
    emit,
    center,
    previewZoom,
    zoom,
    host,
    width,
    failed,
    attempt,
    hint,
    draggingPin,
    height,
    tiles,
    areaOverlay,
    template,
    validTemplate,
    tileUrl,
    marker,
    observer,
    drag,
    pan,
    changeZoom,
    selectAt,
    pointerDown,
    pointerMove,
    pointerUp,
    cancelDrag,
    keyboard,
    retry
  };
}
export default React.forwardRef(function ManualLocationMap(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [<div {...mergeProps({
    className: "manual-map-wrap",
    "data-sp-6f96df0e": ""
  })}>
      <p {...mergeProps({
      id: "manual-map-help",
      className: "map-help",
      "data-sp-6f96df0e": ""
    })}>
        {"Bấm bản đồ để đặt ghim, kéo để di chuyển bản đồ hoặc kéo ghim để chỉnh. Dùng phím mũi tên rồi Enter để chọn điểm giữa bản đồ."}
      </p>
      <div {...mergeProps({
      ref: bindRef(ctx, "host"),
      className: "manual-map",
      tabIndex: "0",
      role: "region",
      "aria-label": "Bản đồ chọn vị trí bất động sản",
      "aria-describedby": "manual-map-help",
      "aria-disabled": ctx.disabled || undefined,
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
        return ctx.cancelDrag?.($event);
      },
      onKeyDown: $event => {
        return ctx.keyboard?.($event);
      },
      "data-sp-6f96df0e": ""
    })}>
        {renderList(ctx.tiles, tile => <img key={ctx.attempt + ":" + tile.key} {...mergeProps({
        src: ctx.tileUrl(tile),
        alt: "",
        draggable: "false",
        referrerPolicy: "strict-origin-when-cross-origin",
        className: "map-tile",
        "data-tile-key": tile.key,
        style: {
          left: tile.left + "px",
          top: tile.top + "px"
        },
        onError: $event => {
          ctx.failed = true;
        },
        "data-sp-6f96df0e": ""
      })} />)}
        {ctx.areaOverlay ? <svg {...mergeProps({
        className: "location-area",
        viewBox: "0 0 " + ctx.width + " " + ctx.height,
        role: "img",
        "aria-label": "Vùng minh họa quanh ghim đề xuất",
        "data-location-area": "illustrative",
        "data-sp-6f96df0e": ""
      })}>
            <title {...mergeProps({
          "data-sp-6f96df0e": ""
        })}>
              {"Vùng minh họa, không phải bán kính sai số đã xác minh"}
            </title>
            <circle {...mergeProps({
          cx: ctx.areaOverlay.cx,
          cy: ctx.areaOverlay.cy,
          r: ctx.areaOverlay.radius,
          "data-sp-6f96df0e": ""
        })} />
          </svg> : null}
        <span {...mergeProps({
        className: "map-crosshair",
        "aria-hidden": "true",
        "data-sp-6f96df0e": ""
      })}>
          {"+"}
        </span>
        {ctx.marker ? <span {...mergeProps({
        "data-location-pin": "",
        className: ["location-pin", {
          "preview-pin": ctx.preview
        }],
        style: {
          left: ctx.marker.left + "px",
          top: ctx.marker.top + "px"
        },
        role: "img",
        "aria-label": ctx.preview ? "Ghim đề xuất chưa xác nhận" : "Ghim vị trí đã chọn",
        
        "data-sp-6f96df0e": ""
      })}>
            {"●"}
          </span> : null}
        <div {...mergeProps({
        "data-map-control": "",
        className: "map-controls",
        onPointerDown: $event => {
          $event.stopPropagation();
          undefined;
        },
        onKeyDown: $event => {
          $event.stopPropagation();
          undefined;
        },
        "data-sp-6f96df0e": ""
      })}>
          <button {...mergeProps({
          type: "button",
          disabled: ctx.disabled || ctx.zoom >= 19,
          "aria-label": "Phóng to bản đồ",
          onClick: $event => {
            ctx.changeZoom(1);
          },
          "data-sp-6f96df0e": ""
        })}>
            {"+"}
          </button>
          <button {...mergeProps({
          type: "button",
          disabled: ctx.disabled || ctx.zoom <= 3,
          "aria-label": "Thu nhỏ bản đồ",
          onClick: $event => {
            ctx.changeZoom(-1);
          },
          "data-sp-6f96df0e": ""
        })}>
            {"−"}
          </button>
        </div>
        <button {...mergeProps({
        type: "button",
        "data-map-control": "",
        className: "choose-center",
        disabled: ctx.disabled,
        onPointerDown: $event => {
          $event.stopPropagation();
          undefined;
        },
        onKeyDown: $event => {
          $event.stopPropagation();
          undefined;
        },
        onClick: $event => {
          ctx.selectAt(ctx.width / 2, ctx.height / 2);
        },
        "data-sp-6f96df0e": ""
      })}>
          {"Đặt ghim ở dấu +"}
        </button>
        <a {...mergeProps({
        "data-map-control": "",
        href: "https://www.openstreetmap.org/copyright",
        target: "_blank",
        rel: "noopener noreferrer",
        className: "map-attribution",
        onPointerDown: $event => {
          $event.stopPropagation();
          undefined;
        },
        onKeyDown: $event => {
          $event.stopPropagation();
          undefined;
        },
        "data-sp-6f96df0e": ""
      })}>
          {"© OpenStreetMap contributors"}
        </a>
      </div>
      {ctx.areaOverlay ? <p {...mergeProps({
      className: "area-explanation",
      "data-sp-6f96df0e": ""
    })}>
          <span {...mergeProps({
        "aria-hidden": "true",
        className: "area-swatch",
        "data-sp-6f96df0e": ""
      })} />
          <span {...mergeProps({
        "data-sp-6f96df0e": ""
      })}>
            {display(ctx.previewRegion.label)}
          </span>
        </p> : null}
      {ctx.failed || !ctx.validTemplate ? <p {...mergeProps({
      role: "status",
      className: "map-error",
      "data-sp-6f96df0e": ""
    })}>
          {"Chưa tải đầy đủ bản đồ. Kiểm tra mạng rồi "}
          <button {...mergeProps({
        type: "button",
        className: "underline",
        onClick: $event => {
          return ctx.retry?.($event);
        },
        "data-sp-6f96df0e": ""
      })}>
            {"thử lại"}
          </button>
          {". Chỉ chọn được ghim ở phần bản đồ đã tải."}
        </p> : null}
      {ctx.hint ? <p {...mergeProps({
      role: "status",
      className: "map-help",
      "data-sp-6f96df0e": ""
    })}>
          {display(ctx.hint)}
        </p> : null}
    </div>]);
});
