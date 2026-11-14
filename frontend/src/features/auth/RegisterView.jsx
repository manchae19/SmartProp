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
import LoginView from "./LoginView.jsx";
function setup(__props) {
  return {
    LoginView,
  };
}
export default React.forwardRef(function RegisterView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <LoginView
      {...mergeProps({
        initialRegister: true,
      })}
    />,
  ]);
});
