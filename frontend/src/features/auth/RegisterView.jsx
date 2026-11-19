import React, { useRef } from "react";
import LoginView from "./LoginView.jsx";
function useRegisterViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  return {
    ...inputProps,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function RegisterView(props, ref) {
  const view = useRegisterViewState(props, ref);
  return <><LoginView initialRegister={true} {...view.rootAttributes} /></>;
});
