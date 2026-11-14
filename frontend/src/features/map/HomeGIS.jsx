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
  onMounted,
  onBeforeUnmount,
  defineAsyncComponent,
} from "../../shared/state/store.js";
import "./HomeGIS.css";
function setup(__props) {
  const PropertyExplorer = defineAsyncComponent(
    () => import("./PropertyExplorer.jsx"),
  );
  const props = propsForSetup(__props, {
    items: {
      type: Array,
      default: () => [],
    },
    selectedId: String,
    total: Number,
    mapLink: Object,
    busy: Boolean,
    error: String,
  });
  const emit = emitForProps(__props, ["update:selectedId", "retry"]);
  const host = ref(null),
    activated = ref(false);
  const exploreLink = computed(() => ({
    ...(props.mapLink || {
      path: "/map",
    }),
    query: {
      ...(props.mapLink?.query || {}),
      ...(props.selectedId
        ? {
            propertyId: props.selectedId,
          }
        : {}),
    },
  }));
  let observer;
  onMounted(() => {
    if (!("IntersectionObserver" in window)) {
      activated.value = true;
      return;
    }
    observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          activated.value = true;
          observer.disconnect();
        }
      },
      {
        rootMargin: "160px",
      },
    );
    observer.observe(host.value);
  });
  onBeforeUnmount(() => observer?.disconnect());
  return {
    ref,
    computed,
    onMounted,
    onBeforeUnmount,
    defineAsyncComponent,
    PropertyExplorer,
    props,
    emit,
    host,
    activated,
    exploreLink,
    observer,
  };
}
export default React.forwardRef(function HomeGIS(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div
      {...mergeProps({
        ref: bindRef(ctx, "host"),
        className: "home-gis",
        "data-sp-98ad1ee1": "",
      })}
    >
      {ctx.error ? (
        <p
          {...mergeProps({
            role: "alert",
            className: "home-gis-message",
            "data-sp-98ad1ee1": "",
          })}
        >
          {display(ctx.error)}{" "}
          <button
            {...mergeProps({
              type: "button",
              onClick: ($event) => {
                ctx.emit("retry");
              },
              "data-sp-98ad1ee1": "",
            })}
          >
            {"Thử lại"}
          </button>
        </p>
      ) : null}
      {ctx.busy ? (
        <p
          {...mergeProps({
            role: "status",
            className: "home-gis-message",
            "data-sp-98ad1ee1": "",
          })}
        >
          {"Đang tải tin trên bản đồ…"}
        </p>
      ) : null}
      {ctx.activated ? (
        <ctx.PropertyExplorer
          {...mergeProps({
            items: ctx.items,
            selectedId: ctx.selectedId,
            exploreLink: ctx.exploreLink,
            preview: true,
            onSelect: ($event) => {
              ctx.emit("update:selectedId", $event);
            },
            "data-sp-98ad1ee1": "",
          })}
        />
      ) : (
        <button
          {...mergeProps({
            className: "home-gis-activate",
            type: "button",
            onClick: ($event) => {
              ctx.activated = true;
            },
            "data-sp-98ad1ee1": "",
          })}
        >
          {"⌖ Khám phá vị trí trên bản đồ"}
        </button>
      )}
    </div>,
  ]);
});
