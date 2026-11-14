import React from "react";
import {
  useSetup,
  propsForSetup,
  emitForProps,
  exposeForSetup,
} from "../state/store.js";
import {
  mergeProps,
  bindRef,
  renderList,
  display,
  modelProps,
  rootProps,
  Teleport,
} from "./rendering.js";
import { RouterLink, RouterView } from "../routing/router.jsx";
import { computed } from "../state/store.js";
import { poiSvgPath } from "../../features/map/nearbyPlaces.js";
function setup(__props) {
  const props = propsForSetup(__props, {
    category: {
      type: String,
      default: "",
    },
  });
  const path = computed(() => poiSvgPath(props.category));
  return {
    computed,
    poiSvgPath,
    props,
    path,
  };
}
export default React.forwardRef(function PoiIcon(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <svg
      {...mergeProps({
        viewBox: "0 0 24 24",
        fill: "none",
        stroke: "currentColor",
        strokeWidth: "1.8",
        strokeLinecap: "round",
        strokeLinejoin: "round",
        className: "shrink-0",
        "aria-hidden": "true",
      })}
    >
      <path
        {...mergeProps({
          d: ctx.path,
        })}
      />
    </svg>,
  ]);
});
