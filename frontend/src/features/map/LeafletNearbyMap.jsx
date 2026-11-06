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
  watch,
  onMounted,
  onBeforeUnmount,
  nextTick,
} from "../../shared/state/store.js";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { POI_GROUPS, validPoint, distanceLabel } from "./nearbyExplorer.js";
import { publicMapPoint } from "./locationDisplay.js";
import { compactPrice } from "../property/property.js";
import "./LeafletNearbyMap.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    items: {
      type: Array,
      default: () => [],
    },
    selectedId: String,
    places: {
      type: Array,
      default: () => [],
    },
    radius: {
      type: Number,
      default: 1000,
    },
    showProperty: {
      type: Boolean,
      default: true,
    },
    showRadius: {
      type: Boolean,
      default: true,
    },
    activePoi: String,
    simple: Boolean,
  });
  const emit = emitForProps(__props, ["select", "select-poi"]);
  const element = ref(null),
    ready = ref(false),
    mapError = ref(""),
    baseLayer = ref("street");
  let map,
    street,
    properties,
    pois,
    circle,
    observer,
    tileErrors = 0,
    lastSelection = "";
  const pins = new Map(),
    poiPins = new Map();
  function icon(label, color, selected = false) {
    const span = document.createElement("span");
    span.className = "explorer-marker" + (selected ? " is-selected" : "");
    span.style.setProperty("--pin-color", color);
    span.textContent = label;
    return L.divIcon({
      html: span,
      className: "explorer-marker-wrap",
      iconSize: selected ? [42, 48] : [32, 38],
      iconAnchor: selected ? [21, 44] : [16, 35],
      popupAnchor: [0, -34],
    });
  }
  function popup(p, property = false) {
    const box = document.createElement("div");
    box.className = "explorer-popup";
    if (property && p.status === "PUBLISHED") {
      const cover = p.images?.find((i) => i.cover) || p.images?.[0];
      const prefix =
        "/api/v1/properties/" + encodeURIComponent(p.id) + "/images/";
      if (cover?.url?.startsWith(prefix) && cover.url.endsWith("/content")) {
        const photo = document.createElement("img");
        photo.src = cover.url;
        photo.alt = p.title || "Ảnh bất động sản";
        photo.className = "explorer-popup-photo";
        photo.loading = "lazy";
        photo.decoding = "async";
        photo.addEventListener("error", () => photo.remove(), {
          once: true,
        });
        box.append(photo);
      }
    }
    const title = document.createElement("strong");
    title.textContent = p.title || p.name;
    box.append(title);
    const text = document.createElement("p");
    text.textContent = property
      ? compactPrice(p) + (p.areaSqm ? " · " + p.areaSqm + " m²" : "")
      : distanceLabel(p.distanceMeters) + " · đường chim bay";
    box.append(text);
    if (property) {
      const link = document.createElement("a");
      link.textContent = "Xem chi tiết →";
      link.href = "/listing/" + encodeURIComponent(p.id);
      box.append(link);
    } else if (p.address) {
      const address = document.createElement("small");
      address.textContent = p.address;
      box.append(address);
    }
    return box;
  }
  function draw() {
    if (!map) return;
    const keepPropertyPopup = pins.get(props.selectedId)?.isPopupOpen();
    map.stop();
    map.closePopup();
    properties.clearLayers();
    pois.clearLayers();
    pins.clear();
    poiPins.clear();
    if (circle) {
      circle.remove();
      circle = null;
    }
    const selected = props.items.find(
      (p) => p.id === props.selectedId && publicMapPoint(p),
    );
    for (const p of props.items.filter(publicMapPoint)) {
      const active = p.id === props.selectedId;
      const marker = L.marker([Number(p.latitude), Number(p.longitude)], {
        icon: icon("⌂", active ? "#147d80" : "#234b70", active),
        zIndexOffset: active ? 500 : 0,
        title: p.title || "Bất động sản",
        keyboard: true,
      });
      marker
        .bindPopup(popup(p, true), {
          maxWidth: 260,
        })
        .on("click", () => emit("select", p.id));
      if (props.showProperty) marker.addTo(properties);
      pins.set(p.id, marker);
    }
    if (selected) {
      if (props.showRadius)
        circle = L.circle(
          [Number(selected.latitude), Number(selected.longitude)],
          {
            radius: props.radius,
            color: "#4075f5",
            weight: 2,
            dashArray: "7 6",
            fillColor: "#5795f5",
            fillOpacity: 0.09,
            interactive: false,
          },
        ).addTo(map);
      for (const p of props.places.filter(validPoint)) {
        const group =
          POI_GROUPS.find((g) => g.id === p.category) || POI_GROUPS[0];
        const marker = L.marker([Number(p.latitude), Number(p.longitude)], {
          icon: icon(group.icon, group.color),
          title: p.name,
          keyboard: true,
        }).addTo(pois);
        marker.bindPopup(popup(p)).on("click", () => emit("select-poi", p.id));
        poiPins.set(p.id, marker);
      }
      const key =
        selected.id +
        ":" +
        selected.latitude +
        ":" +
        selected.longitude +
        ":" +
        props.radius;
      if (lastSelection !== key) {
        lastSelection = key;
        map.fitBounds(
          L.latLng(
            Number(selected.latitude),
            Number(selected.longitude),
          ).toBounds(props.radius * 2),
          {
            padding: [45, 45],
            maxZoom: 17,
            animate: false,
          },
        );
        if (props.showProperty) pins.get(selected.id)?.openPopup();
      }
      if (keepPropertyPopup && props.showProperty)
        pins.get(selected.id)?.openPopup();
    } else if (props.items.some(publicMapPoint)) {
      lastSelection = "";
      map.fitBounds(
        L.latLngBounds(
          props.items
            .filter(publicMapPoint)
            .map((p) => [Number(p.latitude), Number(p.longitude)]),
        ),
        {
          padding: [45, 45],
          maxZoom: 14,
          animate: false,
        },
      );
    }
  }
  function center() {
    const p = props.items.find((p) => p.id === props.selectedId);
    if (p && publicMapPoint(p)) {
      map?.setView([Number(p.latitude), Number(p.longitude)], 16);
      pins.get(p.id)?.openPopup();
    }
  }
  watch(
    () => [
      props.items,
      props.selectedId,
      props.places,
      props.radius,
      props.showProperty,
      props.showRadius,
    ],
    draw,
    {
      deep: true,
    },
  );
  watch(
    () => props.activePoi,
    (id) => {
      const pin = poiPins.get(id);
      if (pin) {
        map.panTo(pin.getLatLng());
        pin.openPopup();
      }
    },
  );
  onMounted(async () => {
    await nextTick();
    map = L.map(element.value, {
      zoomControl: false,
      scrollWheelZoom: true,
      wheelDebounceTime: 80,
      wheelPxPerZoomLevel: 100,
      preferCanvas: true,
      zoomAnimation: false,
      fadeAnimation: false,
      markerZoomAnimation: false,
    });
    // Initial viewport only; no synthetic property marker is placed here.
    map.setView([16.06, 108.21], 12);
    L.control
      .zoom({
        position: "topright",
      })
      .addTo(map);
    L.control
      .scale({
        imperial: false,
        position: "bottomleft",
      })
      .addTo(map);
    street = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
    }).addTo(map);
    street.on("tileerror", () => {
      if (++tileErrors >= 4)
        mapError.value =
          "Chưa tải được bản đồ nền. Kiểm tra kết nối và thử lại.";
    });
    street.on("tileload", () => {
      mapError.value = "";
      tileErrors = 0;
    });
    properties = L.layerGroup().addTo(map);
    pois = L.layerGroup().addTo(map);
    observer = new ResizeObserver(() =>
      map?.invalidateSize({
        animate: false,
      }),
    );
    observer.observe(element.value);
    ready.value = true;
    draw();
  });
  function retryTiles() {
    tileErrors = 0;
    mapError.value = "";
    street?.redraw();
  }
  onBeforeUnmount(() => {
    observer?.disconnect();
    map?.remove();
    map = null;
  });
  return {
    ref,
    watch,
    onMounted,
    onBeforeUnmount,
    nextTick,
    L,
    POI_GROUPS,
    validPoint,
    distanceLabel,
    publicMapPoint,
    compactPrice,
    props,
    emit,
    element,
    ready,
    mapError,
    baseLayer,
    map,
    street,
    properties,
    pois,
    circle,
    observer,
    tileErrors,
    lastSelection,
    pins,
    poiPins,
    icon,
    popup,
    draw,
    center,
    retryTiles,
  };
}
export default React.forwardRef(function LeafletNearbyMap(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div
      {...mergeProps({
        className: "leaflet-explorer-shell",
      })}
    >
      <div
        {...mergeProps({
          ref: bindRef(ctx, "element"),
          className: "leaflet-explorer-canvas",
          "aria-label": "Bản đồ bất động sản và tiện ích xung quanh",
        })}
      />
      {!ctx.simple ? (
        <div
          {...mergeProps({
            className: "map-layer-choice",
            "aria-label": "Lớp bản đồ",
          })}
        >
          <button
            {...mergeProps({
              type: "button",
              "aria-pressed": ctx.baseLayer === "street",
            })}
          >
            {"Bản đồ"}
          </button>
          <button
            {...mergeProps({
              type: "button",
              disabled: true,
              title: "Chưa cấu hình nguồn ảnh vệ tinh có giấy phép",
            })}
          >
            {"Vệ tinh"}
          </button>
          <button
            {...mergeProps({
              type: "button",
              disabled: true,
              title: "Chưa cấu hình lớp vệ tinh và nhãn",
            })}
          >
            {"Bản đồ lai"}
          </button>
        </div>
      ) : null}
      <button
        {...mergeProps({
          className: "map-recenter",
          type: "button",
          onClick: ($event) => {
            return ctx.center?.($event);
          },
          "aria-label": "Đưa bản đồ về bất động sản đang chọn",
          title: "Về vị trí tin đang chọn",
        })}
      >
        {"⌖"}
      </button>
      {ctx.mapError ? (
        <div
          {...mergeProps({
            className: "map-tile-error",
            role: "alert",
          })}
        >
          {display(ctx.mapError)}{" "}
          <button
            {...mergeProps({
              type: "button",
              onClick: ($event) => {
                return ctx.retryTiles?.($event);
              },
            })}
          >
            {"Thử lại"}
          </button>
        </div>
      ) : null}
      {!ctx.ready ? (
        <div
          {...mergeProps({
            className: "map-boot",
          })}
        >
          {"Đang mở bản đồ…"}
        </div>
      ) : null}
    </div>,
  ]);
});
