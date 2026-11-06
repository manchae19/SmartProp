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
import "./BusinessPage.css";
function setup(__props) {
  propsForSetup(__props, {
    title: String,
  });
  return {};
}
export default React.forwardRef(function BusinessPage(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section data-ui-view="BusinessPage"
      {...mergeProps({
        className: "completion-page",
      })}
    >
      <h1 {...mergeProps({})}>{display(ctx.title)}</h1>
      {ctx.$children ?? null}
    </section>,
  ]);
});
